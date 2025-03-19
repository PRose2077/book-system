from flask import Blueprint, render_template, request, jsonify, current_app, copy_current_request_context
from app import mongo
from app.utils import (
    get_current_time,
    format_file_size, 
    save_file_to_hdfs, 
    count_csv_lines_efficient,
    process_file_async,
    manage_upload_queue
)
from werkzeug.utils import secure_filename
from app.models import UploadFile
import os
import logging
from datetime import datetime
from bson import ObjectId
from app.services.word_cloud_service import get_cached_word_cloud
from app.services.book_word_cloud_service import get_cached_book_word_cloud
from app.services.generate_result import generate_content 
from app.services.upload_word_cloud_service import get_upload_word_cloud
import uuid
from threading import Thread

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """主页"""
    # 获取带有必要字段的随机书籍
    books = list(mongo.db.books_info.aggregate([
        {'$sample': {'size': 8}},
        {'$project': {
            'book_id': 1,
            'book_title': 1,
            'author': 1,
            'cover_url': 1,
            'pub_year': 1
        }}
    ]))
    
    # 获取词云数据
    try:
        word_cloud_tags = get_cached_word_cloud()
        current_app.logger.info(f"获取到词云数据: {len(word_cloud_tags)} 个标签")
        if word_cloud_tags:
            current_app.logger.info(f"示例标签: {word_cloud_tags[:3]}")
    except Exception as e:
        current_app.logger.error(f"获取词云数据失败: {str(e)}")
        word_cloud_tags = []
    
    return render_template('index.html', 
                         random_books=books,
                         word_cloud_data=word_cloud_tags)

@main.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    books = []
    
    if keyword:
        # 使用正则表达式进行模糊搜索
        books = list(mongo.db.books_info.find({
            '$or': [
                {'book_title': {'$regex': keyword, '$options': 'i'}},
                {'author': {'$regex': keyword, '$options': 'i'}}
            ]
        }))
        
        # 处理每本书的数据
        for book in books:
            if '_id' in book and 'book_id' not in book:
                book['book_id'] = str(book['_id'])
            book['comment_count'] = mongo.db.comments_tags.count_documents({'book_id': book['book_id']})
    else:
        # 没有搜索关键词时，随机推荐8本书
        books = list(mongo.db.books_info.aggregate([
            {'$sample': {'size': 8}},
            {'$project': {
                'book_id': 1,
                'book_title': 1,
                'author': 1,
                'cover_url': 1,
                'pub_year': 1
            }}
        ]))
        
        # 获取评论数量
        for book in books:
            book['comment_count'] = mongo.db.comments_tags.count_documents({'book_id': book['book_id']})
        
    return render_template('search.html', 
                         books=books, 
                         keyword=keyword,
                         is_search=bool(keyword))

@main.route('/upload')
def upload():
    """上传页面"""
    try:
        # 从uploads集合获取上传历史记录
        uploads = list(mongo.db.uploads.find().sort('upload_time', -1))
        
        # 格式化数据
        formatted_uploads = []
        for upload in uploads:
            formatted_upload = {
                'filename': upload.get('filename', ''),
                'size': format_file_size(upload.get('size', 0)),
                'status': upload.get('status', 'pending'),
                'queue_position': upload.get('queue_position'),
                'upload_time': upload.get('upload_time', '').strftime('%Y-%m-%d %H:%M:%S') if upload.get('upload_time') else '-',
                'last_updated': upload.get('last_updated', '').strftime('%Y-%m-%d %H:%M:%S') if upload.get('last_updated') else '-',
                'processed_records': upload.get('processed_records', '-'),
                'total_records': upload.get('total_records', '-'),
                'error_message': upload.get('error_message', '-')
            }
            formatted_uploads.append(formatted_upload)
            
        return render_template('upload.html', uploads=formatted_uploads)
        
    except Exception as e:
        logger.error(f"获取上传历史失败: {str(e)}")
        return render_template('upload.html', uploads=[], error=str(e))

@main.route('/api/upload/session-history', methods=['POST'])
def get_session_upload_history():
    """获取当前会话的上传历史"""
    try:
        file_ids = request.json.get('file_ids', [])
        
        # 将字符串ID转换为ObjectId
        object_ids = [ObjectId(file_id) for file_id in file_ids if ObjectId.is_valid(file_id)]
        
        # 只获取当前会话上传的文件记录
        uploads = list(mongo.db.uploads.find({'_id': {'$in': object_ids}}).sort('upload_time', -1))
        
        # 格式化数据
        formatted_uploads = []
        for upload in uploads:
            formatted_upload = {
                'file_id': str(upload['_id']),
                'filename': upload.get('filename', ''),
                'size': format_file_size(upload.get('size', 0)),
                'status': upload.get('status', 'pending'),
                'queue_position': upload.get('queue_position'),
                'upload_time': upload.get('upload_time', '').strftime('%Y-%m-%d %H:%M:%S') if upload.get('upload_time') else '-',
                'last_updated': upload.get('last_updated', '').strftime('%Y-%m-%d %H:%M:%S') if upload.get('last_updated') else '-',
                'total_records': upload.get('total_records', '-'),
                'error_message': upload.get('error_message', '-')
            }
            formatted_uploads.append(formatted_upload)
            
        return jsonify({
            'code': 0,
            'data': formatted_uploads
        })
        
    except Exception as e:
        logger.error(f"获取会话上传历史失败: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f"获取上传历史失败: {str(e)}"
        })

@main.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    temp_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'code': 1, 'msg': '没有文件被上传'})
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 1, 'msg': '没有选择文件'})
            
        if not file.filename.endswith('.csv'):
            return jsonify({'code': 1, 'msg': '只支持CSV文件'})
            
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # 保存文件到临时目录
        file.save(temp_path)
        logger.info(f"文件已保存到临时目录: {temp_path}")
        
        # 处理可能的book_id冲突
        try:
            import pandas as pd
            
            # 读取CSV文件
            logger.info("开始读取CSV文件...")
            df = pd.read_csv(temp_path)
            logger.info(f"成功读取CSV文件，列名: {df.columns.tolist()}")
            
            if 'book_id' not in df.columns or 'book_title' not in df.columns:
                raise Exception("CSV文件必须包含 book_id 和 book_title 列")
            
            # 检查每个book_id是否存在冲突
            modified = False
            unique_book_ids = df['book_id'].unique()
            logger.info(f"开始检查 {len(unique_book_ids)} 个唯一book_id")
            
            for book_id in unique_book_ids:
                existing_book = mongo.db.books_info.find_one({'book_id': str(book_id)})
                if existing_book:
                    logger.info(f"找到已存在的book_id: {book_id}")
                    current_title = df[df['book_id'] == book_id]['book_title'].iloc[0]
                    if existing_book['book_title'] != current_title:
                        new_book_id = str(book_id) + '9'
                        df.loc[df['book_id'] == book_id, 'book_id'] = new_book_id
                        modified = True
                        logger.info(f"检测到book_id冲突，将{book_id}修改为{new_book_id}")
                        logger.info(f"原书名: {existing_book['book_title']}, 新书名: {current_title}")
            
            if modified:
                # 如果有修改，保存更新后的文件
                logger.info("检测到修改，正在保存更新后的文件...")
                df.to_csv(temp_path, index=False)
                logger.info("已更新文件中的重复book_id")
            else:
                logger.info("未检测到需要修改的book_id")
            
            # 获取文件大小和总记录数
            file_size = os.path.getsize(temp_path)
            total_records = len(df)
            book_ids = [str(book_id) for book_id in df['book_id'].unique()]
            logger.info(f"文件大小: {file_size}, 总记录数: {total_records}")
            
        except Exception as e:
            logger.error(f"处理CSV文件失败: {str(e)}", exc_info=True)
            return jsonify({'code': 1, 'msg': f'处理CSV文件失败: {str(e)}'})
        
        # 获取当前队列位置
        queue_position = mongo.db.uploads.count_documents({'status': 'queued'}) + 1
        
        # 创建上传记录
        file_id = ObjectId()
        upload_record = {
            '_id': file_id,
            'filename': filename,
            'size': int(file_size),
            'upload_time': get_current_time(),
            'status': 'queued',
            'processed_records': 0,
            'total_records': total_records,
            'book_ids': book_ids,
            'last_updated': get_current_time(),
            'queue_position': queue_position
        }
        
        mongo.db.uploads.insert_one(upload_record)
        logger.info(f"已创建上传记录: {file_id}")
        
        # 保存到HDFS并启动异步处理
        if save_file_to_hdfs(temp_path, filename):
            # 管理上传队列
            manage_upload_queue()
            return jsonify({
                'code': 0, 
                'msg': '文件已上传并加入处理队列',
                'file_id': str(file_id),
                'queue_position': queue_position
            })
        else:
            mongo.db.uploads.delete_one({'_id': file_id})
            return jsonify({'code': 1, 'msg': '上传到HDFS失败'})
            
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'文件上传失败: {str(e)}'})
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"已清理临时文件: {temp_path}")
            except Exception as e:
                logger.error(f"删除临时文件失败: {str(e)}")

@main.route('/upload/details/<file_id>')
def upload_details(file_id):
    """上传文件详情页面"""
    try:
        upload = mongo.db.uploads.find_one({'_id': ObjectId(file_id)})
        if not upload:
            return "文件不存在", 404
        
        # 格式化文件信息
        upload['size'] = format_file_size(upload['size'])
        if 'upload_time' in upload:
            upload['upload_time'] = upload['upload_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取相关书籍信息
        book_ids = upload.get('book_ids', [])
        books = list(mongo.db.books_info.find({'book_id': {'$in': book_ids}}))
        
        # 获取词云数据
        word_cloud_data = get_upload_word_cloud(file_id) if upload['status'] == 'completed' else []
        
        return render_template('upload_details.html',
                             upload=upload,
                             books=books,
                             word_cloud_data=word_cloud_data)
                             
    except Exception as e:
        logger.error(f"获取上传文件详情失败: {str(e)}")
        return "获取详情失败", 500

@main.route('/api/upload/<file_id>', methods=['DELETE'])
def delete_upload(file_id):
    """删除上传记录及相关数据"""
    try:
        # 获取上传记录
        upload = mongo.db.uploads.find_one({'_id': ObjectId(file_id)})
        if not upload:
            return jsonify({'code': 1, 'msg': '文件不存在'})
            
        # 获取相关的book_ids
        book_ids = upload.get('book_ids', [])
        
        # 开始删除操作
        with mongo.cx.start_session() as session:
            with session.start_transaction():
                # 删除上传记录
                mongo.db.uploads.delete_one({'_id': ObjectId(file_id)})
                
                # 删除相关的books_info记录
                if book_ids:
                    mongo.db.books_info.delete_many({'book_id': {'$in': book_ids}})
                    
                    # 删除相关的评论记录
                    mongo.db.comments_tags.delete_many({'book_id': {'$in': book_ids}})
                
        return jsonify({
            'code': 0, 
            'msg': '删除成功',
            'data': {
                'deleted_books': len(book_ids)
            }
        })
        
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'})

@main.route('/book/detail')
def book_detail():
    book_id = request.args.get('id')
    if not book_id:
        return "缺少书籍ID", 400
        
    # 获取来源页面信息
    from_page = request.args.get('from_page', 'index')
    file_id = request.args.get('file_id')
    
    # 获取书籍信息
    book = mongo.db.books_info.find_one({'book_id': book_id})
    if not book:
        return "书籍不存在", 404
    
    # 获取该书籍的所有评论
    all_comments = list(mongo.db.comments_tags.find({'book_id': book_id}))
    total_comments = len(all_comments)
    
    # 统计情感分布
    sentiment_counts = {'正面': 0, '负面': 0}
    for comment in all_comments:
        sentiment = comment.get('sentiment')
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
    
    # 转换为echarts所需的数据格式
    sentiment_data = [
        {'name': '正面评论', 'value': sentiment_counts['正面']},
        {'name': '负面评论', 'value': sentiment_counts['负面']}
    ]
    
    # 获取词云数据
    tag_data = get_cached_book_word_cloud(book_id)
    
    # 只获取最新的5条评论
    comments = all_comments[:5]
    
    # 分页相关变量
    page = int(request.args.get('page', 1))
    per_page = 5  # 每页显示5条评论
    
    return render_template('book_detail.html',
                         book=book,
                         comments=comments,
                         total_comments=total_comments,
                         sentiment_data=sentiment_data,
                         tag_data=tag_data,
                         page=page,
                         per_page=per_page,
                         from_page=from_page,
                         file_id=file_id)  

@main.route('/book/comments')
def book_comments():
    """书籍评论列表页面"""
    book_id = request.args.get('book_id')
    if not book_id:
        return "缺少书籍ID", 400
        
    # 获取书籍信息
    book = mongo.db.books_info.find_one({'book_id': book_id})
    if not book:
        return "书籍不存在", 404
    
    # 获取筛选条件
    filters = {
        'sentiment': request.args.get('sentiment', ''),
    }
    
    # 构建查询条件
    query = {'book_id': book_id}
    if filters['sentiment']:
        # 修改这里以匹配数据库中的sentiment字段格式
        if filters['sentiment'] == 'positive':
            query['sentiment'] = '正面'
        elif filters['sentiment'] == 'negative':
            query['sentiment'] = '负面'
    
    # 分页参数
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        page = 1
        per_page = 20
    
    # 获取总数
    total = mongo.db.comments_tags.count_documents(query)
    
    # 获取评论（带分页）
    comments = list(mongo.db.comments_tags.find(query)
                   .sort('_id', -1)  # 按ID倒序，最新的在前面
                   .skip((page-1)*per_page)
                   .limit(per_page))
    
    # 处理评论数据
    for comment in comments:
        # 直接使用数据库中的sentiment值
        comment['sentiment_text'] = comment['sentiment']
        comment['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        comment['tags'] = comment.get('labels', [])
    
    return render_template('book_comments.html',
                         book=book,
                         comments=comments,
                         total=total,
                         page=page,
                         per_page=per_page,
                         filters=filters)

@main.route('/api/tags/generate', methods=['POST'])
def generate_from_tags():
    """根据标签生成内容"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 1, 'msg': '请求数据为空'})
            
        tags = data.get('tags', [])
        tag_infos = data.get('tag_infos', [])
        writing_type = data.get('writing_type')
        
        if not writing_type:
            return jsonify({'code': 1, 'msg': '请选择写作类型'})
            
        if not tags and not tag_infos:
            return jsonify({'code': 1, 'msg': '请至少添加一个标签'})
        
        # 生成唯一ID作为任务标识
        task_id = str(uuid.uuid4())
        
        # 创建生成任务记录
        generation_task = {
            '_id': task_id,
            'tags': tags,
            'tag_infos': tag_infos,
            'writing_type': writing_type,
            'status': 'processing',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'content': None,
            'user_id': request.cookies.get('user_id', 'anonymous')  # 可选：记录用户标识
        }
        
        # 保存到数据库
        mongo.db.generation_results.insert_one(generation_task)
        
        # 获取当前应用实例
        app = current_app._get_current_object()
        
        # 定义异步生成内容的函数
        def generate_content_async(task_id, tags, tag_infos, writing_type):
            with app.app_context():
                try:
                    # 生成内容
                    content = generate_content(tags, tag_infos, writing_type)
                    
                    # 更新数据库
                    mongo.db.generation_results.update_one(
                        {'_id': task_id},
                        {
                            '$set': {
                                'status': 'completed',
                                'content': content,
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )
                    logger.info(f"内容生成完成，任务ID: {task_id}")
                except Exception as e:
                    # 更新为失败状态
                    mongo.db.generation_results.update_one(
                        {'_id': task_id},
                        {
                            '$set': {
                                'status': 'failed',
                                'error': str(e),
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )
                    logger.error(f"内容生成失败，任务ID: {task_id}, 错误: {str(e)}")
        
        # 启动异步线程
        thread = Thread(target=generate_content_async, args=(task_id, tags, tag_infos, writing_type))
        thread.daemon = True
        thread.start()
        
        # 立即返回任务ID
        return jsonify({'code': 0, 'msg': '内容生成已开始', 'task_id': task_id})
        
    except Exception as e:
        current_app.logger.error(f"生成内容时发生错误: {str(e)}")
        return jsonify({'code': 1, 'msg': f'生成内容时发生错误: {str(e)}'})

@main.route('/api/generation/status/<task_id>', methods=['GET'])
def check_generation_status(task_id):
    """检查生成任务状态"""
    try:
        # 从请求参数中获取是否需要记录日志
        log_request = request.args.get('log', '0') == '1'
        
        # 从数据库查询任务状态
        task = mongo.db.generation_results.find_one({'_id': task_id})
        
        if not task:
            if log_request:
                current_app.logger.warning(f'找不到指定的生成任务: {task_id}')
            return jsonify({'code': 1, 'msg': '找不到指定的生成任务'})
            
        # 返回任务状态
        result = {
            'code': 0,
            'status': task['status'],
            'updated_at': task['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 如果任务已完成，返回生成的内容
        if task['status'] == 'completed':
            result['content'] = task['content']
            # 只有在完成状态时记录日志
            if log_request:
                current_app.logger.info(f'任务已完成: {task_id}')
        elif task['status'] == 'failed':
            result['error'] = task.get('error', '未知错误')
            # 只有在失败状态时记录日志
            if log_request:
                current_app.logger.info(f'任务失败: {task_id}, 错误: {result["error"]}')
            
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"检查生成状态时发生错误: {str(e)}")
        return jsonify({'code': 1, 'msg': f'检查生成状态时发生错误: {str(e)}'})

@main.route('/generation/results')
def generation_results():
    """生成结果列表页面"""
    try:
        # 获取用户最近的生成结果
        user_id = request.cookies.get('user_id', 'anonymous')
        results = list(mongo.db.generation_results.find(
            {'user_id': user_id},
            {'content': 0}  # 不返回内容字段以减少数据量
        ).sort('created_at', -1).limit(20))
        
        # 格式化日期
        for result in results:
            result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            result['updated_at'] = result['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('generation_results.html', results=results)
        
    except Exception as e:
        logger.error(f"获取生成结果列表失败: {str(e)}")
        return render_template('generation_results.html', results=[], error=str(e))

@main.route('/generation/result/<task_id>')
def generation_result_detail(task_id):
    """生成结果详情页面"""
    try:
        # 获取生成结果详情
        result = mongo.db.generation_results.find_one({'_id': task_id})
        
        if not result:
            return "找不到指定的生成结果", 404
            
        # 格式化日期
        result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        result['updated_at'] = result['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('generation_result_detail.html', result=result)
        
    except Exception as e:
        logger.error(f"获取生成结果详情失败: {str(e)}")
        return "获取详情失败", 500

@main.route('/api/tags/recommended')
def recommended_tags():
    """获取随机推荐标签"""
    try:
        # 随机选择5本书
        random_books = list(mongo.db.books_info.aggregate([
            {'$sample': {'size': 5}},
            {'$project': {'book_id': 1}}
        ]))
        
        book_ids = [book['book_id'] for book in random_books]
        
        # 从这些书的评论中获取标签
        pipeline = [
            {'$match': {'book_id': {'$in': book_ids}}},
            {'$unwind': '$labels'},
            {'$group': {'_id': '$labels', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},  # 按出现次数排序
            {'$limit': 10}  # 获取前10个标签
        ]
        
        tags = list(mongo.db.comments_tags.aggregate(pipeline))
        recommended_tags = [tag['_id'] for tag in tags]
        
        return jsonify({'code': 0, 'data': recommended_tags})
    except Exception as e:
        current_app.logger.error(f"获取推荐标签时发生错误: {str(e)}")
        return jsonify({'code': 1, 'msg': str(e)})

@main.route('/api/generation/result/<task_id>', methods=['DELETE'])
def delete_generation_result(task_id):
    """删除生成结果"""
    try:
        # 从数据库中删除生成结果
        result = mongo.db.generation_results.delete_one({'_id': task_id})
        
        if result.deleted_count == 0:
            return jsonify({'code': 1, 'msg': '找不到指定的生成结果'})
            
        return jsonify({
            'code': 0, 
            'msg': '删除成功'
        })
        
    except Exception as e:
        logger.error(f"删除生成结果失败: {str(e)}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'})

