#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}开始初始化Hadoop环境...${NC}"
#启动集群
echo -e "${GREEN}启动集群...${NC}"
./start-hadoop.sh

# 获取master容器ID
MASTER_CONTAINER=$(docker ps -qf "name=spark-1")

# 格式化namenode
echo -e "${GREEN}格式化namenode...${NC}"
docker exec $MASTER_CONTAINER hdfs namenode -format

# 调用start-hadoop.sh脚本重启整个环境
echo -e "${GREEN}重启集群环境...${NC}"
./start-hadoop.sh

# 创建HDFS用户目录
echo -e "${GREEN}创建HDFS用户目录...${NC}"
docker exec $MASTER_CONTAINER hdfs dfs -mkdir -p /input_data
docker exec $MASTER_CONTAINER hdfs dfs -chown dr.who:dr.who /input_data
docker exec $MASTER_CONTAINER hdfs dfs -chmod 755 /input_data

# 上传停用词文件
echo -e "${GREEN}上传停用词文件到HDFS...${NC}"
# 首先将本地文件复制到容器内
docker cp ./stopwords.txt $MASTER_CONTAINER:/tmp/stopwords.txt
# 然后从容器上传到HDFS
docker exec $MASTER_CONTAINER hdfs dfs -put /tmp/stopwords.txt /input_data/
# 验证文件是否上传成功
docker exec $MASTER_CONTAINER hdfs dfs -ls /input_data/

echo -e "${GREEN}Hadoop环境初始化完成！${NC}" 