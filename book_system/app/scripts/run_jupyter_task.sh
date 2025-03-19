#!/bin/bash

# 检查参数
if [ -z "$1" ]; then
    echo "Usage: $0 <task_name>"
    exit 1
fi

TASK_NAME=$1

# 在容器中创建临时文件
docker exec $(docker ps -qf "name=jupyter") bash -c 'cat << "EOF" > /opt/notebooks/word_cloud_task.py
import os
import sys
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, col, count, when, desc, current_timestamp, expr, lit, array, struct, collect_list
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB配置
MONGO_USER = "root"
MONGO_PASSWORD = "example"
MONGO_DATABASE = "spark_data"
MONGO_REPLICA_SET = "rs0"

def create_spark_session():
    # MongoDB连接配置
    mongo_configs = {
        "spark.mongodb.read.connection.uri": f"mongodb://root:example@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/{MONGO_DATABASE}?replicaSet={MONGO_REPLICA_SET}&authSource=admin",
        "spark.mongodb.write.connection.uri": f"mongodb://root:example@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/{MONGO_DATABASE}?replicaSet={MONGO_REPLICA_SET}&authSource=admin",
        "spark.jars.packages": "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0",
        "spark.mongodb.read.readPreference.name": "primaryPreferred",
        "spark.mongodb.write.writeConcern.w": "majority"
    }

    # 创建SparkSession
    builder = SparkSession.builder \
        .appName("WordCloudGenerator") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://master:9000") \
        .config("spark.driver.memory", "2G") \
        .config("spark.executor.cores", "2") \
        .config("spark.executor.instances", "3") \
        .config("spark.executor.memory", "900M") \
        .config("spark.default.parallelism", "6") \
        .config("spark.sql.shuffle.partitions", "6") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.kryoserializer.buffer.max", "512M")

    # 添加MongoDB配置
    for key, value in mongo_configs.items():
        builder = builder.config(key, value)

    return builder.getOrCreate()

try:
    # 创建Spark会话
    spark = create_spark_session()
    logger.info("Spark会话创建成功")

    # 从MongoDB读取评论数据
    comments_df = spark.read \
        .format("mongodb") \
        .option("database", MONGO_DATABASE) \
        .option("collection", "comments_tags") \
        .load()

    logger.info(f"成功读取评论数据，总数：{comments_df.count()}")

    # 展开标签数组并计算权重
    tags_df = comments_df.select(
        explode(col("labels")).alias("tag"),
        col("sentiment")
    ).where(col("tag").isNotNull())

    # 计算标签权重
    weighted_tags = tags_df.groupBy("tag") \
        .agg(
            count("*").alias("total_count"),
            count(when(col("sentiment") == "正面", True)).alias("positive_count")
        ) \
        .withColumn(
            "weight",
            (col("total_count") * 0.6) + (col("positive_count") * 0.4)
        ) \
        .orderBy(desc("weight")) \
        .limit(200)

    # 标准化权重值到1-100范围
    weight_stats = weighted_tags.agg(
        expr("max(weight) as max_weight"),
        expr("min(weight) as min_weight")
    ).collect()[0]
    
    max_weight = float(weight_stats["max_weight"])
    min_weight = float(weight_stats["min_weight"])
    weight_range = max_weight - min_weight

    if weight_range > 0:
        weighted_tags = weighted_tags.withColumn(
            "normalized_weight",
            1 + ((col("weight") - lit(min_weight)) / lit(weight_range)) * 99
        )
    else:
        weighted_tags = weighted_tags.withColumn("normalized_weight", lit(50.0))

    # 收集标签数据
    tags_list = weighted_tags.select(
        col("tag").alias("name"),
        col("normalized_weight").cast("double").alias("value")
    ).collect()

    # 转换为所需的格式
    tags_data = [{"name": row["name"], "value": float(row["value"])} for row in tags_list]

    # 获取当前时间
    current_time = datetime.utcnow()
    expired_time = current_time + timedelta(hours=24)

    # 准备缓存数据
    cache_data = spark.createDataFrame([{
        "type": "word_cloud",
        "data": {
            "word_cloud": {
                "tags": tags_data,
                "total_count": len(tags_data)
            }
        },
        "created_at": current_time,
        "expired_at": expired_time,
        "last_updated": current_time
    }])

    # 写入MongoDB
    cache_data.write \
        .format("mongodb") \
        .mode("overwrite") \
        .option("database", MONGO_DATABASE) \
        .option("collection", "cache_data") \
        .save()

    logger.info("词云数据生成成功")
    spark.stop()

except Exception as e:
    logger.error(f"生成词云数据时发生错误: {str(e)}")
    if "spark" in locals():
        spark.stop()
    sys.exit(1)

EOF'

# 在jupyter容器中执行Python脚本
docker exec $(docker ps -qf "name=jupyter") python3 /opt/notebooks/word_cloud_task.py

# 清理容器中的临时文件
docker exec $(docker ps -qf "name=jupyter") rm -f /opt/notebooks/word_cloud_task.py