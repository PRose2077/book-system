#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示帮助信息的函数
show_help() {
    echo -e "${YELLOW}使用说明${NC}"
    echo "此脚本用于将本地文件上传至HDFS集群"
    echo
    echo -e "${YELLOW}用法:${NC}"
    echo "  $0 <本地文件路径> <HDFS目标路径>"
    echo
    echo -e "${YELLOW}参数:${NC}"
    echo "  <本地文件路径>  要上传的本地文件的完整路径"
    echo "  <HDFS目标路径>  HDFS上的目标目录路径"
    echo
    echo -e "${YELLOW}示例:${NC}"
    echo "  $0 /home/cdc/data.csv /input_data"
    echo "  $0 ./myfile.txt /user/hadoop/data"
    echo
    echo -e "${YELLOW}注意:${NC}"
    echo "  - 确保本地文件存在且有读取权限"
    echo "  - HDFS路径如果不存在会自动创建"
    echo "  - 如果HDFS上已存在同名文件会被覆盖"
    echo "  - HDFS路径必须以/开头（会自动添加）"
    echo "  - 文件将以dr.who用户身份上传"
}

# 处理帮助参数
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

# 检查参数数量
if [ $# -ne 2 ]; then
    echo -e "${RED}错误: 参数数量不正确${NC}"
    echo -e "使用 '$0 --help' 查看帮助信息"
    exit 1
fi

# 获取参数
LOCAL_FILE="$1"
HDFS_PATH="$2"

# 确保HDFS路径以/开头
if [[ ! "$HDFS_PATH" =~ ^/ ]]; then
    HDFS_PATH="/$HDFS_PATH"
    echo -e "${YELLOW}注意: HDFS路径已自动添加前导斜杠，实际路径为: $HDFS_PATH${NC}"
fi

CONTAINER_PATH="/opt"
CONTAINER_NAME="spark-1"

# 检查本地文件是否存在
if [ ! -f "$LOCAL_FILE" ]; then
    echo -e "${RED}错误: 找不到文件 $LOCAL_FILE${NC}"
    exit 1
fi

# 获取容器ID
CONTAINER_ID=$(docker ps -q -f name=$CONTAINER_NAME)

if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}错误: 找不到名为 $CONTAINER_NAME 的容器${NC}"
    exit 1
fi

# 获取文件名（不包含路径）
FILENAME=$(basename "$LOCAL_FILE")

# 复制文件到容器
echo -e "${GREEN}正在复制文件到容器...${NC}"
docker cp "$LOCAL_FILE" "$CONTAINER_ID:$CONTAINER_PATH"

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 文件复制失败${NC}"
    exit 1
fi

# 在容器内执行HDFS上传命令
echo -e "${GREEN}正在上传文件到HDFS路径 $HDFS_PATH...${NC}"

# 首先检查HDFS目标路径是否存在，如果不存在则创建并设置权限
docker exec $CONTAINER_ID bash -c "hdfs dfs -test -d $HDFS_PATH || (hdfs dfs -mkdir -p $HDFS_PATH && hdfs dfs -chown dr.who:dr.who $HDFS_PATH && hdfs dfs -chmod 755 $HDFS_PATH)"

# 上传文件并设置所有者为dr.who
docker exec $CONTAINER_ID bash -c "hdfs dfs -put -f $CONTAINER_PATH/$FILENAME $HDFS_PATH && hdfs dfs -chown dr.who:dr.who $HDFS_PATH/$FILENAME && hdfs dfs -chmod 644 $HDFS_PATH/$FILENAME"
UPLOAD_STATUS=$?

# 清理容器中的临时文件
echo "清理容器中的临时文件..."
docker exec $CONTAINER_ID rm -f "$CONTAINER_PATH/$FILENAME"

if [ $UPLOAD_STATUS -eq 0 ]; then
    echo -e "${GREEN}文件成功上传到HDFS${NC}"
    # 显示文件在HDFS中的位置
    echo -e "文件完整路径: $HDFS_PATH/$FILENAME"
    # 显示文件详细信息
    echo -e "验证文件信息:"
    docker exec $CONTAINER_ID hdfs dfs -ls "$HDFS_PATH/$FILENAME"
    
    # 显示文件在HDFS中的权限和内容大小
    echo -e "\nHDFS文件详细信息:"
    docker exec $CONTAINER_ID hdfs dfs -stat "%F %p %u:%g %b %n" "$HDFS_PATH/$FILENAME"
else
    echo -e "${RED}错误: HDFS上传失败${NC}"
    exit 1
fi