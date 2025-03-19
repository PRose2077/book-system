# 通用配置
MONGO_USER = "root"
MONGO_PASSWORD = "example"
MONGO_HOST = "mongodb-primary"  # 使用容器名作为主机名
MONGO_PORT = "27017"
MONGO_DATABASE = "spark_data"
MONGO_REPLICA_SET = "rs0"  # 添加副本集名称

# books_info配置
BOOKS_MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT},{MONGO_HOST.replace('primary', 'secondary1')}:27017,{MONGO_HOST.replace('primary', 'secondary2')}:27017/{MONGO_DATABASE}?replicaSet={MONGO_REPLICA_SET}"
OUTPUT_COLLECTION = "books_info"
BOOK_INFO_COLLECTION = "books_info" 

# comment_tags配置
TAGS_MONGO_URI = BOOKS_MONGO_URI  # 使用相同的连接URI
TAGS_OUTPUT_COLLECTION = "comments_tags"


MONGO_OPTIONS = {
    "authSource": "admin",
    "retryWrites": "true",
    "w": "1",
    "readPreference": "primaryPreferred",
    "connectTimeoutMS": "10000",
    "socketTimeoutMS": "10000",
    "journal": "false",
    "wtimeoutMS": "5000"
}

# 构建完整的连接URI
def build_mongo_uri(base_uri):
    options = "&".join(f"{k}={v}" for k, v in MONGO_OPTIONS.items())
    return f"{base_uri}&{options}"

# 更新连接URI
TAGS_MONGO_URI = build_mongo_uri(TAGS_MONGO_URI)
BOOKS_MONGO_URI = build_mongo_uri(BOOKS_MONGO_URI)