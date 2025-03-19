#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 获取容器ID的函数
get_container_id() {
    docker ps -qf "name=mongodb-primary"
}

# 设置最大等待时间（秒）
MAX_WAIT=60
COUNTER=0

echo -e "${GREEN}等待MongoDB启动...${NC}"
until docker exec $(get_container_id) mongo --eval "print('waiting...')" 2>/dev/null
do
    echo -e "${RED}等待MongoDB就绪...${NC}"
    sleep 2
    COUNTER=$((COUNTER + 2))
    if [ $COUNTER -gt $MAX_WAIT ]; then
        echo -e "${RED}等待MongoDB超时，请检查容器日志${NC}"
        docker logs $(get_container_id)
        exit 1
    fi
done

echo -e "${GREEN}MongoDB已就绪，开始初始化副本集...${NC}"

# 使用admin用户进行认证并初始化副本集
docker exec $(get_container_id) mongo admin --eval '
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
sleep 2

# 等待PRIMARY节点
echo -e "${GREEN}等待PRIMARY节点...${NC}"
while true; do
    PRIMARY_CHECK=$(docker exec $(get_container_id) mongo admin --eval "db.auth('root', 'example'); rs.isMaster().ismaster" --quiet)
    if [ "$PRIMARY_CHECK" = "true" ]; then
        echo -e "${GREEN}PRIMARY节点已就绪！${NC}"
        break
    fi
    echo -e "${RED}等待PRIMARY节点...${NC}"
    sleep 2
done

echo -e "${GREEN}检查最终副本集状态...${NC}"
docker exec $(get_container_id) mongo admin --eval "db.auth('root', 'example'); rs.status()"

echo -e "${GREEN}MongoDB副本集初始化完成！${NC}"
