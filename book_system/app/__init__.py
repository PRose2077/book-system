from flask import Flask
from flask_pymongo import PyMongo
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
from app.spark.word_cloud_generator import generate_word_cloud
import os

mongo = PyMongo()
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    mongo.init_app(app)
    
    # 添加定时任务
    scheduler.add_job(
        func=generate_word_cloud,
        trigger='interval',
        hours=24,
        id='generate_word_cloud_job',
        name='Generate Word Cloud'
    )
    scheduler.start()

    from app.routes import main
    app.register_blueprint(main)
    
    # 确保导入generate_result模块
    from app.services import generate_result
    
    return app