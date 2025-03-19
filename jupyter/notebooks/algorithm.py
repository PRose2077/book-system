import os
import sys
import logging
import hanlp
import time
import jiagu
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, lit
from config import TAGS_MONGO_URI, MONGO_DATABASE, TAGS_OUTPUT_COLLECTION,BOOK_INFO_COLLECTION
from pyspark.sql.types import ArrayType, StringType, StructType, StructField

# 设置环境变量
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_base_schema():
    """获取基础schema(必需的列)"""
    return StructType([
        StructField("book_id", StringType(), True),
        StructField("book_title", StringType(), True),
        StructField("comment_id", StringType(), True),
        StructField("content", StringType(), True)
    ])

def get_full_schema():
    """获取完整schema(包含所有可能的列)"""
    return StructType([
        StructField("book_id", StringType(), True),
        StructField("book_title", StringType(), True),
        StructField("author", StringType(), True),
        StructField("cover_url", StringType(), True),
        StructField("publisher", StringType(), True),
        StructField("pub_year", StringType(), True),
        StructField("book_url", StringType(), True),
        StructField("comment_id", StringType(), True),
        StructField("user", StringType(), True),
        StructField("content", StringType(), True),
        StructField("rating", StringType(), True)
    ])

def read_csv_with_schema(spark, hdfs_path):
    """读取CSV文件并处理schema"""
    from pyspark.sql.functions import col, lit
    
    try:
        # 1. 读取并获取实际的列
        raw_df = spark.read.csv(
            hdfs_path,
            header=True,
            multiLine=True,
            escape='"',
            sep=',',
            inferSchema=False
        )
        actual_columns = raw_df.columns
        
        # 2. 检查必需的列是否存在
        required_columns = {'book_id', 'book_title', 'comment_id', 'content'}
        missing_required = required_columns - set(actual_columns)
        if missing_required:
            raise ValueError(f"CSV文件缺少必需的列: {missing_required}")
        
        # 3. 获取完整schema并处理列
        full_schema = get_full_schema()
        expected_columns = [field.name for field in full_schema.fields]
        
        # 4. 读取数据并处理列
        df = spark.read.csv(
            hdfs_path,
            header=True,
            multiLine=True,
            escape='"',
            sep=','
        )
        
        # 5. 选择列并补充缺失列
        selected_cols = []
        for expected_col in expected_columns:
            if expected_col in actual_columns:
                selected_cols.append(col(expected_col))
            else:
                selected_cols.append(lit(None).cast(StringType()).alias(expected_col))
        
        # 6. 返回最终的DataFrame
        return df.select(*selected_cols)
        
    except Exception as e:
        logger.error(f"读取CSV文件失败: {str(e)}")
        raise

def get_mongodb_config():
    """获取MongoDB配置"""
    mongo_uri = (
        f"{TAGS_MONGO_URI}&authSource=admin"
        "&retryWrites=true&w=majority"
        "&readPreference=primaryPreferred"
        "&connectTimeoutMS=10000&socketTimeoutMS=10000"
    )
    return mongo_uri

def create_spark_session():
    mongo_uri = get_mongodb_config()
    
    # 根据数据量调整Spark配置
    return SparkSession.builder \
        .appName("SentimentAnalysis") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://master:9000") \
        .config("spark.driver.memory", "2G") \
        .config("spark.executor.cores", "2") \
        .config("spark.executor.instances", "4") \
        .config("spark.executor.memory", "1G") \
        .config("spark.default.parallelism", "8") \
        .config("spark.sql.shuffle.partitions", "8") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.mongodb.input.uri", mongo_uri) \
        .config("spark.mongodb.output.uri", mongo_uri) \
        .config("spark.mongodb.write.connection.uri", mongo_uri) \
        .config("spark.mongodb.read.connection.uri", mongo_uri) \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0") \
        .config("spark.kryoserializer.buffer.max", "512m") \
        .config("spark.driver.maxResultSize", "1G") \
        .config("spark.network.timeout", "800s") \
        .config("spark.executor.heartbeatInterval", "60s") \
        .config("spark.memory.fraction", "0.6") \
        .config("spark.memory.storageFraction", "0.5") \
        .config("spark.cleaner.periodicGC.interval", "1min") \
        .getOrCreate()

# 创建 Spark 会话
spark = create_spark_session()

# 加载模型和创建广播变量
HanLP = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH)
HanLP_broadcast = spark.sparkContext.broadcast(HanLP)

# 从HDFS读取stopwords
stopwords_df = spark.read.text("hdfs://master:9000/input_data/stopwords.txt")
stopwords = set(stopwords_df.rdd.map(lambda r: r[0]).collect())
broadcast_stopwords = spark.sparkContext.broadcast(stopwords)

def extract_keywords(text, top_n=5):
    """使用jiagu提取文本关键词"""
    try:
        return jiagu.keywords(text, top_n)
    except Exception as e:
        logger.error(f"关键词提取失败: {str(e)}")
        return []

def generate_summary(text, num_sentences=2):
    """使用jiagu生成文本摘要"""
    if not text or not isinstance(text, str):
        logger.warning("输入文本为空或非字符串类型")
        return ""
        
    if len(text.strip()) < 10 or text.count('。') < 2:
        return text.strip()
        
    try:
        summary = jiagu.summarize(text, num_sentences)
        
        if summary and len(summary) > 0:
            cleaned_sentences = [s.strip() for s in summary if s and s.strip()]
            
            if cleaned_sentences:
                result = "。".join(cleaned_sentences)
                return result if result.endswith("。") else result + "。"
            
        sentences = [s.strip() for s in text.split('。') if s.strip()]
        if sentences:
            summary = sentences[:min(num_sentences, len(sentences))]
            return "。".join(summary) + "。"
            
        return text.strip()
        
    except Exception as e:
        logger.warning(f"摘要生成发生错误: {str(e)}, 文本长度: {len(text)}")
        logger.debug(f"问题文本: {text[:100]}...")
        return text.strip()

def extract_labels(text, keywords):
    """使用HanLP提取文本标签"""
    try:
        local_HanLP = HanLP_broadcast.value
        doc = local_HanLP(text, tasks=['tok/fine', 'pos/ctb', 'dep', 'sdp'])
        tags = set()
        
        words = doc['tok/fine']
        pos_tags = doc['pos/ctb']
        sdp = doc['sdp']
        
        # 1. 优先添加关键词
        tags.update(keywords)
        
        # 2. 提取语义依存关系
        for i, word_relations in enumerate(sdp):
            for relation in word_relations:
                if isinstance(relation, tuple) and len(relation) == 2:
                    head, rel = relation
                    if head != 0:  # 跳过根节点
                        head_word = words[head - 1]
                        current_word = words[i]
                        
                        if pos_tags[i].startswith(('N', 'V', 'JJ')) or pos_tags[head-1].startswith(('N', 'V', 'JJ')):
                            if rel in ['Exp', 'Cont', 'Datv', 'eResu', 'ePurp', 'eCau']:
                                tag = head_word + current_word
                            elif rel in ['Desc', 'mNeg', 'mDegr', 'mMod', 'mFreq', 'mTime', 'mScope', 'mPoss']:
                                tag = current_word + head_word
                            else:
                                continue
                            
                            if 2 <= len(tag) <= 8 and (tag in keywords or any(word in keywords for word in tag)):
                                tags.add(tag)
        
        # 3. 提取连续的名词短语
        for i in range(len(words) - 1):
            if pos_tags[i].startswith('N') and pos_tags[i+1].startswith('N'):
                tag = words[i] + words[i+1]
                if 2 <= len(tag) <= 8:
                    tags.add(tag)
        
        # 4. 标签精简和去重
        final_tags = set()
        for tag in tags:
            if isinstance(tag, str) and 2 <= len(tag) <= 8 and not any(punct in tag for punct in ['，', '。', '：', '；', '、']):
                final_tags.add(tag)
        
        # 5. 返回结果
        return list(final_tags)[:10]  # 返回10个标签
    except Exception as e:
        logger.error(f"标签提取失败: {str(e)}")
        return []

@udf(StructType([
    StructField("jiagu_summary", StringType()),
    StructField("keywords", ArrayType(StringType())),
    StructField("labels", ArrayType(StringType())),
    StructField("sentiment", StringType())
]))
def process_text(text):
    """处理文本的UDF函数"""
    if not text or not isinstance(text, str):
        logger.warning("输入文本为空或非字符串类型")
        return ("", [], [], "")
    
    try:
        keywords = extract_keywords(text)
        summary = generate_summary(text)
        labels = extract_labels(summary, keywords)
        
        sentiment = jiagu.sentiment(text)
        sentiment_label = "正面" if sentiment[0] == "positive" else "负面"
        
        return (summary, keywords, labels, sentiment_label)
    except Exception as e:
        logger.error(f"文本处理失败: {str(e)}")
        return ("", [], [], "")

def process_and_write_to_mongodb(spark, input_file, batch_size=500):
    """采用分布式读写架构处理CSV文件并将结果写入MongoDB"""
    try:
        from pyspark.sql.window import Window
        from pyspark.sql.functions import row_number, monotonically_increasing_id, spark_partition_id, lit
        
        hdfs_path = f"hdfs://master:9000/input_data/{input_file}"
        logger.info(f"从HDFS读取数据: {hdfs_path}")
        
        # 使用schema读取数据
        df = read_csv_with_schema(spark, hdfs_path)
        
        # 确保基础必需的列存在且有值
        df = df.filter(
            col("book_id").isNotNull() & 
            col("book_title").isNotNull() & 
            col("comment_id").isNotNull() & 
            col("content").isNotNull()
        )
                
        total_records = df.count()
        logger.info(f"有效记录数: {total_records}")
        
        if total_records == 0:
            logger.warning("没有找到有效记录")
            return

        # 计算合理的分区数
        available_cores = min(6, spark.sparkContext.defaultParallelism)
        max_parallel_tasks = 4
        records_per_partition = 1000
        num_partitions = min(
            max_parallel_tasks,
            max(1, total_records // records_per_partition)
        )
        
        logger.info(f"使用 {num_partitions} 个分区进行分布式处理")
        
        # 智能化处理策略：根据数据量选择处理方式
        large_dataset_threshold = 50000  # 大数据集阈值
        
        if total_records <= large_dataset_threshold:
            # 小数据集：直接基于分区并行处理
            logger.info("采用单批次分布式处理策略")
            
            # 使用book_id作为分区键进行分区
            df_partitioned = df.repartitionByRange(num_partitions, "book_id")
            
            # 处理文本内容 - 这一步在Spark Workers上并行执行
            processed_df = df_partitioned.withColumn(
                "processed_text", 
                process_text(col("content"))
            )
            
            # 选择并重命名列
            result_df = processed_df.select(
                col("book_id"),
                col("comment_id"),
                col("content"),
                col("processed_text.jiagu_summary").alias("jiagu_summary"),
                col("processed_text.keywords").alias("keywords"),
                col("processed_text.labels").alias("labels"),
                col("processed_text.sentiment").alias("sentiment")
            )
            
            # 过滤掉空值
            result_df = result_df.filter(
                col("jiagu_summary").isNotNull() & 
                col("sentiment").isNotNull()
            )
            
            # 缓存结果以避免重复计算
            result_df.cache()
            
            # 获取处理后的记录数
            processed_count = result_df.count()
            logger.info(f"处理完成，共 {processed_count} 条有效记录")
            
       
            logger.info("开始分布式写入MongoDB")
            result_df.write \
                .format("mongodb") \
                .mode("append") \
                .option("database", MONGO_DATABASE) \
                .option("collection", TAGS_OUTPUT_COLLECTION) \
                .option("writeConcern.w", "majority") \
                .option("replaceDocument", "false") \
                .option("maxBatchSize", 512) \
                .option("ordered", "false") \
                .save()
            
            logger.info(f"分布式写入完成，共写入 {processed_count} 条记录")
            
            # 释放缓存
            result_df.unpersist()
            
        else:
            # 大数据集：分批处理，每批次内部采用分布式处理
            logger.info("采用多批次分布式处理策略")
            
            # 动态调整批处理大小
            adjusted_batch_size = min(max(batch_size, total_records // 20), 5000)
            logger.info(f"调整批处理大小为: {adjusted_batch_size}")
            
            # 计算批次数
            num_batches = (total_records + adjusted_batch_size - 1) // adjusted_batch_size
            
            # 添加批次ID列
            df_with_id = df.withColumn("id", monotonically_increasing_id())
            
            # 记录总处理和写入的记录数
            total_processed = 0
            
            for batch_num in range(num_batches):
                logger.info(f"处理批次 {batch_num + 1}/{num_batches}")
                
                try:
                    # 记录批处理开始时间
                    batch_start_time = time.time()
                    
                    # 获取当前批次
                    current_batch = df_with_id.filter(
                        (col("id") % lit(num_batches)) == lit(batch_num)
                    ).drop("id")
                    
                    # 使用book_id作为分区键进行分区
                    batch_partitioned = current_batch.repartitionByRange(num_partitions, "book_id")
                    
                    # 处理文本内容 - 这一步在Spark Workers上并行执行
                    processed_batch = batch_partitioned.withColumn(
                        "processed_text", 
                        process_text(col("content"))
                    )
                    
                    # 选择并重命名列
                    result_batch = processed_batch.select(
                        col("book_id"),
                        col("comment_id"),
                        col("content"),
                        col("processed_text.jiagu_summary").alias("jiagu_summary"),
                        col("processed_text.keywords").alias("keywords"),
                        col("processed_text.labels").alias("labels"),
                        col("processed_text.sentiment").alias("sentiment")
                    )
                    
                    # 过滤掉空值
                    result_batch = result_batch.filter(
                        col("jiagu_summary").isNotNull() & 
                        col("sentiment").isNotNull()
                    )
                    
                    # 缓存结果以避免重复计算
                    result_batch.cache()
                    
                    # 获取处理后的记录数
                    batch_processed_count = result_batch.count()
                    logger.info(f"批次 {batch_num + 1} 处理完成，共 {batch_processed_count} 条有效记录")
                    
                    # 使用MongoDB Spark Connector进行分布式写入
                    # 这一步会在Spark Workers上并行执行，每个分区独立写入
                    logger.info(f"开始批次 {batch_num + 1} 分布式写入MongoDB")
                    result_batch.write \
                        .format("mongodb") \
                        .mode("append") \
                        .option("database", MONGO_DATABASE) \
                        .option("collection", TAGS_OUTPUT_COLLECTION) \
                        .option("writeConcern.w", "majority") \
                        .option("replaceDocument", "false") \
                        .option("maxBatchSize", 512) \
                        .option("ordered", "false") \
                        .save()
                    
                    # 更新总处理记录数
                    total_processed += batch_processed_count
                    
                    # 释放缓存
                    result_batch.unpersist()
                    
                    # 计算并记录批处理时长
                    batch_end_time = time.time()
                    batch_duration = batch_end_time - batch_start_time
                    logger.info(f"批次 {batch_num + 1} 完成，耗时: {batch_duration:.2f} 秒")
                    
                    # 清理内存
                    if batch_num % 2 == 0:
                        spark.catalog.clearCache()
                        import gc
                        gc.collect()
                        logger.info("已清理缓存和内存")
                    
                except Exception as e:
                    logger.error(f"处理批次 {batch_num + 1} 时出错: {str(e)}")
                    spark.catalog.clearCache()
                    import gc
                    gc.collect()
                    logger.info("发生错误，已清理缓存和内存")
                    continue
            
            logger.info(f"所有批次处理完成，共处理 {total_processed} 条记录")
        
        logger.info(f"所有记录处理和写入完成，总数: {total_records}")
        
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        raise

# 主程序入口
if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            logger.error("请提供输入文件名！使用方式: python algorithm.py <input_file> [batch_size]")
            sys.exit(1)
            
        INPUT_FILE = sys.argv[1]
        BATCH_SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 500  # 默认批次大小
        
        logger.info(f"开始处理文件: {INPUT_FILE}")
        
        # 检查文件大小并调整处理策略
        try:
            from subprocess import check_output
            hdfs_path = f"hdfs://master:9000/input_data/{INPUT_FILE}"
            file_info = check_output(["hdfs", "dfs", "-du", "-h", hdfs_path]).decode('utf-8')
            logger.info(f"文件信息: {file_info.strip()}")
            
            # 如果文件超过100MB，调整批处理大小
            if "M" in file_info and float(file_info.split()[0].replace('M', '')) > 100:
                BATCH_SIZE = min(2000, BATCH_SIZE * 2)
                logger.info(f"文件较大，调整批处理大小为: {BATCH_SIZE}")
        except Exception as e:
            logger.warning(f"获取文件信息失败: {str(e)}")
        
        # 第一步：处理书籍基本信息
        logger.info("=== 第一步：处理书籍基本信息 ===")
        try:
            hdfs_path = f"hdfs://master:9000/input_data/{INPUT_FILE}"
            
            # 使用新的读取函数
            df = read_csv_with_schema(spark, hdfs_path)
            
            # 处理书籍信息
            book_info_df = df.select(
                "book_id",
                "book_title",
                "author",
                "cover_url",
                "publisher",
                "pub_year",
                "book_url"
            ).dropDuplicates(["book_id"])
            
            # 写入MongoDB
            book_info_df.write \
                .format("mongodb") \
                .mode("append") \
                .option("database", MONGO_DATABASE) \
                .option("collection", BOOK_INFO_COLLECTION) \
                .option("writeConcern.w", "majority") \
                .option("replaceDocument", "false") \
                .save()
                
            logger.info(f"成功写入 {book_info_df.count()} 条书籍信息到 {BOOK_INFO_COLLECTION}")
            
            # 清理缓存
            spark.catalog.clearCache()
            
        except Exception as e:
            logger.error(f"处理书籍信息时出错: {str(e)}")
            raise
            
        # 第二步：处理评论数据
        logger.info("\n=== 第二步：处理评论数据 ===")
        process_and_write_to_mongodb(spark, INPUT_FILE, BATCH_SIZE)
        
        logger.info("所有处理完成")
        
    except Exception as e:
        logger.error(f"程序运行失败: {str(e)}")
        sys.exit(1)
    finally:
        # 确保清理所有资源
        try:
            spark.catalog.clearCache()
            logger.info("已清理Spark缓存")
        except:
            pass
        spark.stop()
