# Spark MongoDB 书评分析系统

这是一个基于 Spark 和 MongoDB 的分布式书评分析系统，能够对大规模图书评论数据进行处理和分析，提供情感分析、关键词提取、标签生成等功能。

## 功能特点

- **分布式数据处理**
  - 使用 Spark 进行大规模数据并行处理
  - HDFS 分布式存储支持
  - MongoDB 副本集保证数据可靠性

- **文本分析功能**
  - 评论情感分析（正面/负面）
  - 关键词提取
  - 自动标签生成
  - 文本摘要生成

- **可视化界面**
  - 书籍信息展示
  - 评论数据分析
  - 标签词云展示
  - 情感分布统计

- **数据管理**
  - CSV 文件批量导入
  - 实时处理进度展示
  - 处理结果持久化存储

## 技术栈

- **后端**
  - Apache Spark：分布式数据处理
  - MongoDB：数据存储
  - Flask：Web 应用框架
  - HanLP：中文自然语言处理
  - Jiagu：文本分析工具

- **前端**
  - Layui：UI 框架
  - ECharts：数据可视化
  - jQuery：交互处理

- **部署**
  - Docker：容器化部署
  - Docker Compose：服务编排
  
# Spark MongoDB 数据处理集群

这是一个基于Docker Compose的分布式数据处理环境，集成了Apache Spark、MongoDB副本集和Jupyter Notebook。

## 系统架构

- **Spark集群**
  - 1个Master节点
  - 2个Worker节点
  - Jupyter Notebook接口

- **MongoDB副本集**
  - 1个Primary节点
  - 2个Secondary节点
  - 使用keyfile认证

## 前置要求

- Docker Engine
- Docker Compose
- 至少4GB可用内存
- 至少10GB磁盘空间


## 更换yum源（仅作参考）
https://developer.aliyun.com/mirror/centos
## docker的安装方法（仅作参考）
https://blog.csdn.net/qq_43331014/article/details/141195947
## 安装docker-compose
前往github查看版本
https://github.com/docker/compose/releases/

选择版本下载到/usr/local/bin/docker-compose
可以用命令(记得更换想要的版本)
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```
赋予执行权限
```bash
sudo chmod +x /usr/local/bin/docker-compose
```
## 快速开始

1. 创建文件夹（需要进入项目文件目录）
```bash
mkdir -p spark/share \
    hadoop/{namenode,datanode1,datanode2,logs,logs1,logs2} \
    mongodb/keyfile
```
2. 创建MongoDB认证文件
```bash
openssl rand -base64 756 > mongodb/keyfile/mongo-keyfile
chmod 400 mongodb/keyfile/mongo-keyfile
chown 999:999 mongodb/keyfile/mongo-keyfile 
```

3.构建镜像

```bash
docker-compose build
```



4.启动集群

初始化仅需在首次使用时：

```bash
./init-all.sh
```
日常启动：
```bash
./star-hadoop.sh
```

