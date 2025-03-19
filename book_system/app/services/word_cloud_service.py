import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    explode, col, count, when, desc, lit, expr,
    countDistinct  
)

logger = logging.getLogger(__name__)

def run_word_cloud_task() -> bool:
    """
    运行词云生成脚本
    Returns:
        bool: 是否成功运行脚本
    """
    try:
        # MongoDB配置
        MONGO_USER = "root"
        MONGO_PASSWORD = "example"
        MONGO_DATABASE = "spark_data"
        MONGO_REPLICA_SET = "rs0"
        MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/{MONGO_DATABASE}?replicaSet={MONGO_REPLICA_SET}&authSource=admin"

        # 创建SparkSession
        spark = SparkSession.builder \
            .appName("WordCloudGenerator") \
            .config("spark.mongodb.read.connection.uri", MONGO_URI) \
            .config("spark.mongodb.write.connection.uri", MONGO_URI) \
            .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0") \
            .config("spark.mongodb.read.readPreference.name", "primaryPreferred") \
            .config("spark.mongodb.write.writeConcern.w", "majority") \
            .getOrCreate()

        logger.info("Spark会话创建成功")

        # 从MongoDB读取评论数据
        comments_df = spark.read \
            .format("mongodb") \
            .option("database", MONGO_DATABASE) \
            .option("collection", "comments_tags") \
            .load()

        # 打印数据结构，用于调试
        logger.info(f"数据框架结构: {comments_df.schema}")
        logger.info(f"成功读取评论数据，总数：{comments_df.count()}")

        # 展开标签数组并计算权重
        tags_df = comments_df \
            .select(
                explode("labels").alias("tag"),
                "sentiment",
                "book_id"  # 添加book_id用于后续可能的分组
            ) \
            .where(col("tag").isNotNull())

        # 计算标签权重
        weighted_tags = tags_df \
            .groupBy("tag") \
            .agg(
                count("*").alias("total_count"),
                count(when(col("sentiment") == "正面", True)).alias("positive_count"),
                countDistinct("book_id").alias("book_count")  # 计算出现在多少本书中
            ) \
            .withColumn(
                "weight",
                (col("total_count") * 0.4) +  # 总出现次数权重
                (col("positive_count") * 0.3) +  # 正面评价权重
                (col("book_count") * 0.3)  # 书籍覆盖度权重
            ) \
            .orderBy(desc("weight")) \
            .limit(200)

        # 获取权重统计
        weight_stats = weighted_tags.agg(
            expr("max(weight) as max_weight"),
            expr("min(weight) as min_weight")
        ).collect()[0]

        max_weight = float(weight_stats["max_weight"])
        min_weight = float(weight_stats["min_weight"])
        
        logger.info(f"权重范围: {min_weight} - {max_weight}")

        # 标准化权重值到1-100范围
        if max_weight > min_weight:
            weighted_tags = weighted_tags.withColumn(
                "normalized_weight",
                1 + ((col("weight") - lit(min_weight)) / lit(max_weight - min_weight)) * 99
            )
        else:
            weighted_tags = weighted_tags.withColumn("normalized_weight", lit(50.0))

        # 收集标签数据
        tags_list = weighted_tags.select(
            col("tag").alias("name"),
            col("normalized_weight").cast("double").alias("value"),
            col("total_count"),
            col("book_count")
        ).collect()

        # 转换为所需的格式
        tags_data = [{
            "name": str(row["name"]),
            "value": float(row["value"]),
            "total_count": int(row["total_count"]),
            "book_count": int(row["book_count"])
        } for row in tags_list]
        
        logger.info(f"生成了 {len(tags_data)} 个标签")

        # 准备缓存数据
        current_time = datetime.utcnow()
        cache_data = spark.createDataFrame([{
            "type": "word_cloud",
            "data": {
                "word_cloud": {
                    "tags": tags_data,
                    "total_count": len(tags_data)
                }
            },
            "created_at": current_time,
            "expired_at": current_time + timedelta(hours=24),#过期时间
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
        return True

    except Exception as e:
        logger.error(f"生成词云数据时发生错误: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        if 'spark' in locals():
            spark.stop()
        return False

def get_word_cloud_data() -> Optional[Dict[str, Any]]:
    """
    获取词云数据，如果缓存过期则重新生成
    """
    try:
        # 连接MongoDB
        client = MongoClient('mongodb://root:example@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/?replicaSet=rs0&authSource=admin')
        db = client.spark_data
        
        # 获取当前时间
        current_time = datetime.utcnow()
        
        # 查找最新的词云数据
        cache_data = db.cache_data.find_one({
            "type": "word_cloud",
            "expired_at": {"$gt": current_time}  # 只获取未过期的数据
        }, sort=[("created_at", -1)])
        
        if cache_data and "data" in cache_data and "word_cloud" in cache_data["data"]:
            logger.info("找到有效的词云缓存数据")
            return cache_data["data"]["word_cloud"]
        
        # 如果没有找到有效数据，调用脚本生成新的词云数据
        logger.info("未找到有效的词云缓存数据，开始生成新数据")
        
        # 调用词云生成脚本
        if not run_word_cloud_task():
            logger.error("词云生成失败")
            return None
            
        # 重新查询生成的数据
        new_cache_data = db.cache_data.find_one({
            "type": "word_cloud",
            "created_at": {"$gt": current_time}
        }, sort=[("created_at", -1)])
        
        if new_cache_data and "data" in new_cache_data and "word_cloud" in new_cache_data["data"]:
            logger.info("成功获取新生成的词云数据")
            return new_cache_data["data"]["word_cloud"]
        else:
            logger.error("未找到新生成的词云数据")
            return None
            
    except Exception as e:
        logger.error(f"获取词云数据时发生错误: {str(e)}")
        return None
    finally:
        if 'client' in locals():
            client.close()

def get_cached_word_cloud() -> List[Dict[str, Any]]:
    """
    获取词云数据的包装函数，确保返回正确的JSON格式
    
    Returns:
        list: 格式化的词云数据数组
    """
    try:
        word_cloud_data = get_word_cloud_data()
        if word_cloud_data is None or 'tags' not in word_cloud_data:
            logger.warning("使用默认词云数据")
            return []
            
        # 直接返回tags数组
        tags = word_cloud_data['tags']

        # 确保每个标签都有正确的格式
        formatted_tags = []
        for tag in tags:
            if isinstance(tag, dict) and 'name' in tag and 'value' in tag:
                formatted_tags.append({
                    'name': str(tag['name']),  # 确保name是字符串
                    'value': float(tag['value'])  # 确保value是浮点数
                })
        
        logger.info(f"成功格式化 {len(formatted_tags)} 个标签")
        return formatted_tags
        
    except Exception as e:
        logger.error(f"获取词云数据时发生未预期的错误: {str(e)}")
        return []