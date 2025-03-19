import os

class Config:
    
    SECRET_KEY = 'example'
    MONGO_URI = 'mongodb://root:example@mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/spark_data?authSource=admin&replicaSet=rs0'
    # 统一UPLOAD_FOLDER的定义
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # 文件大小限制
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    
    # HDFS配置
    HDFS_HOST = 'master'
    HDFS_PORT = 9000
    HDFS_USER = 'root'
    
    # Spark配置
    SPARK_MASTER = 'spark://master:7077'
    JUPYTER_HOST = 'jupyter'

    # 讯飞星火API配置 (HTTP调用)
    SPARK_APP_ID = 'a5085e2a'
    SPARK_API_KEY = 'aedf96d80bf4e0ee3aad2f196fb1f194'
    SPARK_API_PASSWORD = 'kopbbHMkIkUENNWroLfr:CLnztuEaRbYtYBeIJYGL'