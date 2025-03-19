import os
import logging
from typing import List, Dict, Any, Optional
from threading import Thread
import subprocess
from datetime import datetime, timezone
from flask import current_app
from app import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import re

logger = logging.getLogger(__name__)

def get_current_time():
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)

def format_file_size(size: int) -> str:
    """
    格式化文件大小
    
    Args:
        size: 文件大小(字节)
    
    Returns:
        str: 格式化后的文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def save_file_to_hdfs(local_path: str, filename: str) -> bool:
    """
    使用 HDFS 命令行工具将文件保存到 HDFS
    """
    try:
        hdfs_path = f"/input_data/{filename}"
        
        # 使用 hadoop fs 命令上传文件
        result = subprocess.run(
            ['hadoop', 'fs', '-put', '-f', local_path, hdfs_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        
        if result.returncode == 0:
            logger.info(f"文件已成功上传到HDFS: {hdfs_path}")
            return True
        else:
            logger.error(f"上传文件到HDFS失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"保存文件到HDFS时发生错误: {str(e)}")
        return False
    finally:
        # 清理临时文件
        try:
            os.remove(local_path)
            logger.info(f"已清理临时文件: {local_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {str(e)}")


def run_spark_algorithm(file_id: str, filename: str, batch_size: int = 1000):
    """
    运行Spark算法处理文件
    """
    hdfs_path = f"/input_data/{filename}"
    try:
        # 首先验证文件格式
        if not filename.endswith('.csv'):
            raise Exception("只支持CSV格式文件")
            
        # 更新状态为处理中
        mongo.db.uploads.update_one(
            {'_id': ObjectId(file_id)},
            {'$set': {
                'status': 'processing',
                'last_updated': get_current_time()
            }}
        )
        
        logger.info(f"开始处理文件: {filename}, batch_size: {batch_size}")
        
        # 直接在当前进程中运行算法
        import sys
        import importlib.util
        
        # 保存原始参数
        orig_argv = sys.argv
        
        try:
            # 直接从算法目录加载配置文件
            spec = importlib.util.spec_from_file_location(
                "algorithm_config", 
                "/opt/notebooks/config.py"
            )
            algorithm_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(algorithm_config)
            
            # 将配置模块添加到sys.modules
            sys.modules['config'] = algorithm_config
            
            # 设置新参数
            sys.argv = ['algorithm.py', filename, str(batch_size)]
            
            # 执行算法文件
            with open('/opt/notebooks/algorithm.py', 'r') as f:
                exec(f.read(), {'__name__': '__main__'})
            
            # 如果执行到这里没有抛出异常，说明处理成功
            # 更新状态为完成
            mongo.db.uploads.update_one(
                {'_id': ObjectId(file_id)},
                {'$set': {
                    'status': 'completed',
                    'last_updated': get_current_time()
                }}
            )

            # 处理完成后调用process_upload_complete 
            process_upload_complete(file_id)
            logger.info(f"文件 {filename} 处理完成")
            
            # 处理完成后删除HDFS文件
            try:
                delete_hdfs_file(hdfs_path)
                logger.info(f"已清理HDFS临时文件: {hdfs_path}")
            except Exception as e:
                logger.warning(f"清理HDFS文件失败: {str(e)}")
            
            return True
            
        finally:
            # 恢复原始参数
            sys.argv = orig_argv
            
            # 清理sys.modules
            if 'config' in sys.modules:
                del sys.modules['config']
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"处理文件 {filename} 时发生错误: {error_msg}")
        
        # 更新上传记录状态
        mongo.db.uploads.update_one(
            {'_id': ObjectId(file_id)},
            {'$set': {
                'status': 'failed',
                'error_message': error_msg,
                'last_updated': get_current_time()
            }}
        )
        
        # 即使处理失败也尝试删除HDFS文件
        try:
            delete_hdfs_file(hdfs_path)
            logger.info(f"已清理HDFS临时文件: {hdfs_path}")
        except Exception as e:
            logger.warning(f"清理HDFS文件失败: {str(e)}")
            
        # 处理失败后也调用process_upload_complete来处理下一个任务
        process_upload_complete(file_id)
            
        return False

def delete_hdfs_file(hdfs_path: str) -> bool:
    """
    使用 hadoop fs 命令删除 HDFS 文件
    """
    try:
        result = subprocess.run(
            ['hadoop', 'fs', '-rm', hdfs_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        
        if result.returncode == 0:
            logger.info(f"已删除HDFS文件: {hdfs_path}")
            return True
        else:
            logger.error(f"删除HDFS文件失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"删除HDFS文件时发生错误: {str(e)}")
        return False

def generate_wordcloud() -> List[Dict[str, Any]]:
    """
    生成词云图数据
    
    Returns:
        List[Dict[str, Any]]: 词云数据列表
    """
    try:
        # 从数据库获取评论关键词
        pipeline = [
            {'$unwind': '$keywords'},  # 展开keywords数组
            {'$group': {
                '_id': '$keywords',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},  # 按出现次数降序排序
            {'$limit': 100}  # 获取前100个关键词
        ]
        
        words = list(mongo.db.comments_tags.aggregate(pipeline))
        
        # 如果没有数据，返回空列表
        if not words:
            logger.warning("未找到关键词数据")
            return []
        
        # 获取最大和最小计数，用于归一化
        max_count = max(word['count'] for word in words)
        min_count = min(word['count'] for word in words)
        count_range = max_count - min_count
        
        # 转换为词云数据格式，并进行权重归一化
        word_cloud_data = []
        for item in words:
            if count_range > 0:
                # 归一化到12-60的范围
                normalized_value = 12 + (item['count'] - min_count) * 48 / count_range
            else:
                normalized_value = 36  # 如果所有计数都相同，使用中间值
                
            word_cloud_data.append({
                'name': str(item['_id']),
                'value': float(normalized_value)
            })
        
        logger.info(f"成功生成词云数据，共 {len(word_cloud_data)} 个标签")
        return word_cloud_data
        
    except Exception as e:
        logger.error(f"生成词云数据时发生错误: {str(e)}")
        return []

def get_book_tags(book_id: str) -> List[Dict[str, Any]]:
    """
    获取指定书籍的标签云数据
    
    Args:
        book_id: 书籍ID
    
    Returns:
        List[Dict[str, Any]]: 标签云数据列表
    """
    try:
        # 获取指定书籍的所有标签
        pipeline = [
            {'$match': {'book_id': book_id}},
            {'$unwind': '$labels'},  # 展开labels数组
            {'$group': {
                '_id': '$labels',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 50}  # 限制标签数量
        ]
        
        tags = list(mongo.db.comments_tags.aggregate(pipeline))
        
        if not tags:
            logger.warning(f"未找到书籍 {book_id} 的标签数据")
            return []
        
        # 获取最大和最小计数，用于归一化
        max_count = max(tag['count'] for tag in tags)
        min_count = min(tag['count'] for tag in tags)
        count_range = max_count - min_count
        
        # 转换为标签云数据格式
        tag_cloud_data = []
        for item in tags:
            if count_range > 0:
                normalized_value = 12 + (item['count'] - min_count) * 48 / count_range
            else:
                normalized_value = 36
                
            tag_cloud_data.append({
                'name': str(item['_id']),
                'value': float(normalized_value)
            })
        
        logger.info(f"成功生成书籍 {book_id} 的标签云数据，共 {len(tag_cloud_data)} 个标签")
        return tag_cloud_data
        
    except Exception as e:
        logger.error(f"获取书籍标签时发生错误: {str(e)}")
        return []

def get_sentiment_stats(book_id: str) -> Dict[str, int]:
    """
    获取指定书籍的情感统计数据
    
    Args:
        book_id: 书籍ID
    
    Returns:
        Dict[str, int]: 情感统计数据
    """
    try:
        pipeline = [
            {'$match': {'book_id': book_id}},
            {'$group': {
                '_id': None,
                'total': {'$sum': 1},
                'positive': {'$sum': {'$cond': [{'$eq': ['$sentiment', '正面']}, 1, 0]}},
                'negative': {'$sum': {'$cond': [{'$eq': ['$sentiment', '负面']}, 1, 0]}}
            }}
        ]
        
        result = list(mongo.db.comments_tags.aggregate(pipeline))
        
        if not result:
            logger.warning(f"未找到书籍 {book_id} 的情感统计数据")
            return {'total': 0, 'positive': 0, 'negative': 0}
            
        stats = result[0]
        return {
            'total': stats['total'],
            'positive': stats['positive'],
            'negative': stats['negative']
        }
        
    except Exception as e:
        logger.error(f"获取情感统计时发生错误: {str(e)}")
        return {'total': 0, 'positive': 0, 'negative': 0}

def count_csv_lines_efficient(file_path, sample_size=65536):
    """
    高效计算大文件的行数，支持多种编码格式
    
    Args:
        file_path: 文件路径
        sample_size: 采样大小，用于估算大文件的行数
        
    Returns:
        int: 估算的总行数
    """
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']  # 常见中文编码
    
    def try_read_file(encoding):
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size <= sample_size * 2:
                # 小文件直接计算
                with open(file_path, 'r', encoding=encoding) as f:
                    return sum(1 for _ in f) - 1  # 减去标题行
            
            # 大文件采样估算
            with open(file_path, 'r', encoding=encoding) as f:
                # 读取开头部分
                start = f.read(sample_size)
                f.seek(max(file_size - sample_size, 0))  # 跳到接近文件末尾
                end = f.read(sample_size)
                
                # 计算平均行长度
                total_lines = start.count('\n') + end.count('\n')
                total_size = len(start) + len(end)
                avg_line_length = total_size / total_lines if total_lines > 0 else 100
                
                # 估算总行数
                estimated_lines = int(file_size / avg_line_length)
                
                logger.info(f"文件 {os.path.basename(file_path)} 行数估算: 平均行长度={avg_line_length:.2f}, 估算总行数={estimated_lines}, 编码={encoding}")
                
                return max(0, estimated_lines - 1)  # 减去标题行
                
        except UnicodeDecodeError:
            return None
        except Exception as e:
            logger.error(f"使用编码 {encoding} 读取文件时发生错误: {str(e)}")
            return None
    
    # 尝试不同的编码
    for encoding in encodings:
        result = try_read_file(encoding)
        if result is not None:
            return result
    
    # 如果所有编码都失败，记录错误并返回0
    logger.error(f"无法使用任何支持的编码读取文件: {file_path}")
    return 0


def manage_upload_queue():
    """更新队列中任务的位置"""
    try:
        # 首先检查是否有正在处理的任务
        processing_task = mongo.db.uploads.find_one({'status': 'processing'})
        
        if not processing_task:
            # 如果没有正在处理的任务，查找第一个排队的任务
            next_task = mongo.db.uploads.find_one(
                {'status': 'queued'},
                sort=[('upload_time', 1)]
            )
            
            if next_task:
                # 更新任务状态为处理中
                mongo.db.uploads.update_one(
                    {'_id': next_task['_id']},
                    {
                        '$set': {
                            'status': 'processing',
                            'queue_position': 1,
                            'last_updated': get_current_time()
                        }
                    }
                )
                # 启动处理
                process_file_async(str(next_task['_id']), next_task['filename'])
        
        # 获取所有排队的任务并更新位置
        queued_tasks = list(mongo.db.uploads.find({
            'status': 'queued'
        }).sort('upload_time', 1))
        
        # 更新排队任务的位置
        for position, task in enumerate(queued_tasks, 2):  # 从2开始，因为1是处理中的任务
            mongo.db.uploads.update_one(
                {'_id': task['_id']},
                {
                    '$set': {
                        'queue_position': position,
                        'last_updated': get_current_time()
                    }
                }
            )
        
        # 记录队列状态
        logger.info(f"当前队列状态: 处理中任务: {'有' if processing_task else '无'}, 排队任务数: {len(queued_tasks)}")
                
    except Exception as e:
        logger.error(f"更新队列位置时发生错误: {str(e)}")

def process_upload_complete(file_id):
    """处理完成后的操作"""
    try:
        # 更新当前文件状态为完成
        mongo.db.uploads.update_one(
            {'_id': ObjectId(file_id)},
            {
                '$set': {
                    'status': 'completed',
                    'queue_position': None,
                    'last_updated': get_current_time()
                }
            }
        )
        
        # 获取下一个待处理的任务（队列位置为2的任务）
        next_task = mongo.db.uploads.find_one(
            {'status': 'queued', 'queue_position': 2}
        )
        
        if next_task:
            # 更新下一个任务的状态为处理中，位置为1
            mongo.db.uploads.update_one(
                {'_id': next_task['_id']},
                {
                    '$set': {
                        'status': 'processing',
                        'queue_position': 1,
                        'last_updated': get_current_time()
                    }
                }
            )
            
            # 更新其他排队任务的位置（位置-1）
            mongo.db.uploads.update_many(
                {
                    'status': 'queued',
                    'queue_position': {'$gt': 2}  # 位置大于2的任务
                },
                {
                    '$inc': {'queue_position': -1}  # 位置减1
                }
            )
            
            # 启动下一个文件的处理
            file_id = str(next_task['_id'])
            filename = next_task['filename']
            #开始处理
            run_spark_algorithm(file_id, filename)
            
    except Exception as e:
        logger.error(f"更新处理完成状态时发生错误: {str(e)}")

def process_file_async(file_id: str, filename: str):
    """
    异步处理文件
    """
    try:
        # 检查文件记录是否存在
        file_info = mongo.db.uploads.find_one({'_id': ObjectId(file_id)})
        if not file_info:
            raise Exception(f"找不到文件记录，ID: {file_id}")
        
        # 检查文件状态
        if file_info['status'] not in ['queued', 'processing']:
            raise Exception(f"文件状态不正确: {file_info['status']}")
        
        # 启动异步处理线程
        thread = Thread(target=run_spark_algorithm, args=(file_id, filename))
        thread.daemon = True
        thread.start()
        
        logger.info(f"已启动异步处理线程，文件ID: {file_id}, 文件名: {filename}")
        
    except Exception as e:
        error_msg = f"启动处理失败: {str(e)}"
        logger.error(error_msg)
        # 更新上传记录状态为失败
        mongo.db.uploads.update_one(
            {'_id': ObjectId(file_id)},
            {
                '$set': {
                    'status': 'failed',
                    'error_message': error_msg,
                    'queue_position': None,
                    'last_updated': get_current_time()
                }
            }
        )
        # 如果当前任务失败，尝试处理队列中的下一个任务
        manage_upload_queue()