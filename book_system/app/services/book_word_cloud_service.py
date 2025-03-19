from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

def get_book_word_cloud_data(book_id: str) -> Optional[Dict[str, Any]]:
    """
    获取单本书籍的词云数据，如果缓存过期则重新生成
    """
    try:
        # 连接MongoDB
        client = MongoClient('mongodb://root:example@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/?replicaSet=rs0&authSource=admin')
        db = client.spark_data
        
        # 获取当前时间
        current_time = datetime.utcnow()
        
        # 查找最新的词云数据
        cache_data = db.cache_data.find_one({
            "type": "book_word_cloud",
            "data.book_id": book_id,
            "created_at": {"$gt": current_time - timedelta(days=7)}  # 7天内的数据
        }, sort=[("created_at", -1)])  # 按创建时间降序排序
        
        if cache_data and "data" in cache_data:
            logger.info(f"找到书籍 {book_id} 的有效词云缓存数据")
            # 转换value为浮点数
            tags = cache_data["data"]["tags"]
            for tag in tags:
                tag['value'] = float(tag['value'])  # 将字符串转换为浮点数
            return {
                "tags": tags,
                "total_count": len(tags)
            }
        
        # 如果没有找到有效数据，生成新的词云数据
        logger.info(f"未找到书籍 {book_id} 的有效词云缓存数据，开始生成新数据")
        
        # 从comments_tags集合中获取该书籍的关键词数据
        pipeline = [
            {'$match': {'book_id': book_id}},
            {'$unwind': '$labels'},  # 展开labels数组
            {'$group': {
                '_id': '$labels',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 50}  # 限制50个最常见的关键词
        ]
        
        words = list(db.comments_tags.aggregate(pipeline))
        
        # 转换为词云数据格式
        tags = [{'name': str(item['_id']), 'value': float(item['count'])} for item in words]
        
        # 保存到缓存
        new_cache_data = {
            "type": "book_word_cloud",
            "data": {
                "book_id": book_id,
                "tags": tags,
            },
            "created_at": current_time,
            "expired_at": current_time + timedelta(days=7),
            "last_updated": current_time
        }
        
        db.cache_data.insert_one(new_cache_data)
        logger.info(f"成功生成并缓存书籍 {book_id} 的词云数据")
        
        return {
            "tags": tags,
            "total_count": len(tags)
        }
            
    except Exception as e:
        logger.error(f"获取书籍词云数据时发生错误: {str(e)}")
        return None
    finally:
        if 'client' in locals():
            client.close()

def get_cached_book_word_cloud(book_id: str) -> list:
    """
    获取书籍词云数据的包装函数，确保返回正确的JSON格式
    
    Args:
        book_id: 书籍ID
    
    Returns:
        list: 格式化的词云数据数组
    """
    try:
        word_cloud_data = get_book_word_cloud_data(book_id)
        if word_cloud_data is None or 'tags' not in word_cloud_data:
            logger.warning(f"书籍 {book_id} 使用默认词云数据")
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
        
        logger.info(f"成功格式化书籍 {book_id} 的 {len(formatted_tags)} 个标签")
        return formatted_tags
        
    except Exception as e:
        logger.error(f"获取书籍词云数据时发生未预期的错误: {str(e)}")
        return [] 