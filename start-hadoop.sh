#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始启动集群环境...${NC}"

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
sleep 10

# 获取spark master容器ID
SPARK_CONTAINER_ID=$(docker ps -q -f name=spark-1)

if [ -z "$SPARK_CONTAINER_ID" ]; then
    echo -e "${RED}错误: 找不到spark master容器${NC}"
    exit 1
fi


# 在spark容器中执行start-hadoop.sh
echo -e "${GREEN}启动Hadoop服务...${NC}"
docker exec $SPARK_CONTAINER_ID /opt/start-hadoop.sh

if [ $? -eq 0 ]; then
    echo -e "${GREEN}所有服务已成功启动！${NC}"
    echo -e "可以通过以下地址访问服务："
    echo -e "Spark UI: http://localhost:8080"
    echo -e "Hadoop UI: http://localhost:9870"
    echo -e "Jupyter Notebook: http://localhost:8888"
    echo -e "MongoDB: localhost:27017"
    echo -e "Flask应用: http://localhost:5000"
else
    echo -e "${RED}错误: Hadoop启动失败${NC}"
    exit 1
fi