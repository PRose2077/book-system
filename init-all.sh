#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}开始初始化集群环境...${NC}"

# 启动docker-compose环境
echo -e "${GREEN}启动docker-compose服务...${NC}"
docker-compose up -d --remove-orphans

# 检查docker-compose是否成功启动
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: docker-compose启动失败${NC}"
    exit 1
fi

# 等待容器完全启动
echo -e "${GREEN}等待容器启动完成...${NC}"
sleep 15

# 获取容器ID
SPARK_CONTAINER_ID=$(docker ps -q -f name=spark-app-spark-1)
MONGO_CONTAINER_ID=$(docker ps -q -f name=spark-app-mongodb-primary-1)

if [ -z "$SPARK_CONTAINER_ID" ] || [ -z "$MONGO_CONTAINER_ID" ]; then
    echo -e "${RED}错误: 找不到必要的容器${NC}"
    echo -e "${RED}SPARK_CONTAINER_ID: $SPARK_CONTAINER_ID${NC}"
    echo -e "${RED}MONGO_CONTAINER_ID: $MONGO_CONTAINER_ID${NC}"
    echo -e "${RED}当前运行的容器:${NC}"
    docker ps
    exit 1
fi

# 初始化HDFS - 使用-force参数跳过交互式确认
echo -e "${GREEN}初始化HDFS...${NC}"
docker exec $SPARK_CONTAINER_ID hdfs namenode -format -force
docker exec $SPARK_CONTAINER_ID /opt/start-hadoop.sh


# 检查HDFS服务状态
echo -e "${GREEN}检查HDFS服务状态...${NC}"
docker exec $SPARK_CONTAINER_ID jps

# 创建HDFS目录
echo -e "${GREEN}创建HDFS目录...${NC}"
docker exec $SPARK_CONTAINER_ID hdfs dfs -mkdir -p /input_data
docker exec $SPARK_CONTAINER_ID hdfs dfs -chown dr.who:dr.who /input_data
docker exec $SPARK_CONTAINER_ID hdfs dfs -chmod 755 /input_data

# 上传停用词文件
echo -e "${GREEN}上传停用词文件到HDFS...${NC}"
# 首先将本地文件复制到容器内
docker cp ./stopwords.txt $SPARK_CONTAINER_ID:/tmp/stopwords.txt
# 然后从容器上传到HDFS
docker exec $SPARK_CONTAINER_ID hdfs dfs -put /tmp/stopwords.txt /input_data/
# 验证文件是否上传成功
docker exec $SPARK_CONTAINER_ID hdfs dfs -ls /input_data/

# 初始化MongoDB副本集
echo -e "${GREEN}初始化MongoDB副本集...${NC}"
docker exec $MONGO_CONTAINER_ID mongo admin --eval '
db.auth("root", "example");
rs.initiate({
    _id: "rs0",
    members: [
        {_id: 0, host: "mongodb-primary:27017", priority: 2},
        {_id: 1, host: "mongodb-secondary1:27017", priority: 1},
        {_id: 2, host: "mongodb-secondary2:27017", priority: 1}
    ]
});'

echo -e "${GREEN}等待副本集初始化...${NC}"
sleep 15

# 重启整个环境
echo -e "${GREEN}重启整个集群环境...${NC}"
docker-compose down
docker-compose up -d

# 等待服务重新启动
echo -e "${GREEN}等待服务重新启动...${NC}"
sleep 20

# 启动Hadoop服务
SPARK_CONTAINER_ID=$(docker ps -q -f name=spark-app-spark-1)
echo -e "${GREEN}启动Hadoop服务...${NC}"
docker exec $SPARK_CONTAINER_ID /opt/start-hadoop.sh

# 再次等待HDFS服务完全启动
echo -e "${GREEN}等待HDFS服务启动...${NC}"
sleep 10

# 验证HDFS是否正常工作
echo -e "${GREEN}验证HDFS服务...${NC}"
docker exec $SPARK_CONTAINER_ID hdfs dfsadmin -report

echo -e "${GREEN}初始化完成！${NC}"
echo -e "可以通过以下地址访问服务："
echo -e "Spark UI: http://localhost:8080"
echo -e "Hadoop UI: http://localhost:9870"
echo -e "Jupyter Notebook: http://localhost:8888"
echo -e "MongoDB: localhost:27017" 