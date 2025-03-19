import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app import mongo
from bson import ObjectId

logger = logging.getLogger(__name__)

def get_upload_word_cloud(file_id: str) -> List[Dict[str, Any]]:
    """
    获取上传文件的词云数据
    
    Args:
        file_id: 上传文件的ID
    
    Returns:
        List[Dict]: 词云数据列表
    """
    try:
        current_time = datetime.utcnow()
        
        # 查找缓存的词云数据
        cache_data = mongo.db.cache_data.find_one({
            "type": "upload_word_cloud",
            "data.file_id": file_id,
            "expired_at": {"$gt": current_time}
        })
        
        if cache_data:
            logger.info(f"找到缓存的词云数据，包含 {len(cache_data['data']['tags'])} 个标签")
            return cache_data["data"]["tags"]
            
        # 如果没有缓存，获取文件信息
        upload = mongo.db.uploads.find_one({'_id': ObjectId(file_id)})
        if not upload:
            logger.error(f"找不到上传文件记录: {file_id}")
            return []
            
        book_ids = upload.get('book_ids', [])
        
        # 生成词云数据
        pipeline = [
            {'$match': {'book_id': {'$in': book_ids}}},
            {'$unwind': '$labels'},
            {'$group': {
                '_id': '$labels',
                'count': {'$sum': 1},
                'positive_count': {
                    '$sum': {'$cond': [{'$eq': ['$sentiment', '正面']}, 1, 0]}
                },
                'book_count': {'$addToSet': '$book_id'}
            }},
            {'$project': {
                'tag': '$_id',
                'total_count': '$count',
                'positive_ratio': {
                    '$divide': ['$positive_count', '$count']
                },
                'book_coverage': {
                    '$size': '$book_count'
                }
            }}
        ]
        
        tags = list(mongo.db.comments_tags.aggregate(pipeline))
        
        # 计算权重
        weighted_tags = []
        for tag in tags:
            weight = (
                tag['total_count'] * 0.4 +  # 出现次数权重
                tag['positive_ratio'] * 0.3 +  # 正面评价权重
                (tag['book_coverage'] / len(book_ids)) * 0.3  # 书籍覆盖度权重
            )
            weighted_tags.append({
                'name': tag['tag'],
                'value': weight
            })
        
        # 排序并限制数量
        weighted_tags.sort(key=lambda x: x['value'], reverse=True)
        weighted_tags = weighted_tags[:100]
        
        # 保存到缓存
        cache_data = {
            "type": "upload_word_cloud",
            "data": {
                "file_id": file_id,
                "tags": weighted_tags
            },
            "created_at": current_time,
            "expired_at": current_time + timedelta(hours=24),
            "last_updated": current_time
        }
        
        mongo.db.cache_data.insert_one(cache_data)
        logger.info(f"生成并缓存了 {len(weighted_tags)} 个词云标签")
        
        return weighted_tags
        
    except Exception as e:
        logger.error(f"生成上传文件词云数据时发生错误: {str(e)}")
        return []