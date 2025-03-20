from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import logging
import sys
import os
import time
import random
import re
import pandas as pd

# 配置
MAX_RETRIES = 3
MAX_PAGES = 15  # 评论页数
BOOKS_PER_TAG = 50  # 每个标签抓取的书籍数量

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 文件路径配置
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs')
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
    
DATA_DIR = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)  

TAGS_FILE = os.path.join(BASE_DIR, 'taglist.csv')
ALL_BOOKS_FILE = os.path.join(BASE_DIR, 'all_books_un.csv')
MASTER_DATA_FILE = os.path.join(BASE_DIR, 'master_books_data.csv')
LOG_FILE = os.path.join(BASE_DIR, 'scraper.log')

def setup_driver(cookie_string=None):
    """设置并返回Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--ignore-ssl-errors=yes')
    chrome_options.add_argument('--ignore-certificate-errors')
    
    scripts_dir = os.path.join(sys.prefix, 'Scripts')
    chromedriver_path = os.path.join(scripts_dir, 'chromedriver.exe')
    
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    if cookie_string:
        driver.get("https://www.douban.com")
        for cookie in cookie_string.split('; '):
            name, value = cookie.strip().split('=', 1)
            driver.add_cookie({'name': name, 'value': value, 'domain': '.douban.com'})
    
    return driver

def get_tag_books(driver, tag, max_books=BOOKS_PER_TAG):
    """从指定标签页获取图书信息"""
    books = []
    page = 0
    
    while len(books) < max_books:
        url = f"https://book.douban.com/tag/{tag}?start={page*20}&type=T"
        try:
            driver.get(url)
            time.sleep(random.uniform(2, 5))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            book_list = soup.find_all('li', class_='subject-item')
            
            if not book_list:
                break
                
            for book in book_list:
                if len(books) >= max_books:
                    break
                    
                info = book.find('div', class_='info')
                if not info:
                    continue
                    
                title_element = info.find('a')
                if not title_element:
                    continue
                    
                book_url = title_element['href']
                subject_id = book_url.split('/')[-2]
                
                pub_info = info.find('div', class_='pub').text.strip() if info.find('div', class_='pub') else ''
                
                books.append({
                    'subject_id': subject_id,
                    'title': title_element.get_text(strip=True),
                    'url': book_url,
                    'pub_info': pub_info,
                    'tag': tag
                })
            
            page += 1
            logging.info(f"已从标签 '{tag}' 获取 {len(books)} 本书")
            
        except Exception as e:
            logging.error(f"处理标签 '{tag}' 第 {page} 页时出错: {e}")
            break
            
        time.sleep(random.uniform(3, 8))
    
    return books

def save_books_to_csv(books, output_file):
    """保存图书信息到CSV文件"""
    mode = 'a' if os.path.exists(output_file) else 'w'
    write_header = not os.path.exists(output_file)
    
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        fieldnames = ['subject_id', 'title', 'url', 'pub_info', 'tag', 'scraped']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()
        
        for book in books:
            book['scraped'] = 'False'  # 添加scraped字段
            writer.writerow(book)

def remove_duplicates(input_file, output_file):
    """删除重复的图书记录"""
    if not os.path.exists(input_file):
        logging.error(f"输入文件不存在: {input_file}")
        return
    
    try:
        df = pd.read_csv(input_file)
        df_no_duplicates = df.drop_duplicates(subset=['subject_id'])
        df_no_duplicates.to_csv(output_file, index=False)
        logging.info(f"已删除重复记录，从 {len(df)} 条记录减少到 {len(df_no_duplicates)} 条")
    except Exception as e:
        logging.error(f"处理重复记录时出错: {e}")

def create_book_list(tags_file, output_file):
    """从标签创建图书列表"""
    if not os.path.exists(tags_file):
        logging.error(f"标签文件不存在: {tags_file}")
        return False
        
    temp_output = output_file + '.temp'
    driver = setup_driver()
    
    try:
        # 读取标签
        with open(tags_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            tags = [row[0] for row in reader]
        
        total_books = 0
        for tag in tags:
            try:
                books = get_tag_books(driver, tag)
                save_books_to_csv(books, temp_output)
                total_books += len(books)
                logging.info(f"标签 '{tag}' 处理完成，获取 {len(books)} 本书")
                time.sleep(random.uniform(10, 30))
            except Exception as e:
                logging.error(f"处理标签 '{tag}' 时出错: {e}")
        
        # 删除重复记录
        remove_duplicates(temp_output, output_file)
        if os.path.exists(temp_output):
            os.remove(temp_output)
            
        logging.info(f"图书列表创建完成，总共获取 {total_books} 本书")
        return True
        
    except Exception as e:
        logging.error(f"创建图书列表时出错: {e}")
        return False
    finally:
        driver.quit()

def get_unscraped_book_ids(csv_file, num_samples=5):
    """获取未爬取过的图书ID"""
    book_ids = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if 'scraped' not in fieldnames:
            fieldnames.append('scraped')
        
        rows = list(reader)
        for row in rows:
            if 'scraped' not in row or not row['scraped'] or row['scraped'].lower() != 'true':
                book_ids.append(row['subject_id'])
                if len(book_ids) == num_samples:
                    break
    
    return book_ids, fieldnames, rows

def get_page_content(driver, url):
    """获取页面内容"""
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(url)
            time.sleep(5)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return driver.page_source
        except TimeoutException as e:
            logging.warning(f"请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
    
    raise Exception(f"达到最大重试次数 ({MAX_RETRIES})，无法获取页面内容")

def get_book_info(driver, url):
    """获取图书基本信息"""
    content = get_page_content(driver, url)
    soup = BeautifulSoup(content, 'html.parser')
    
    book_info = {
        'book_id': url.split('/')[-2],
        'title': soup.find('h1').text.strip() if soup.find('h1') else '未找到标题',
        'author': None,
        'cover_url': None,
        'publisher': '未找到出版社',
        'pub_year': '未找到出版年份',
        'url': url
    }
    
    # 获取封面图片URL
    cover_img = soup.find('a', class_='nbg')
    if cover_img and cover_img.find('img'):
        book_info['cover_url'] = cover_img.find('img')['src']
    
    info_div = soup.find('div', id='info')
    if info_div:
        author_tag = info_div.find('a')
        book_info['author'] = author_tag.text.strip() if author_tag else None
        
        publisher_tag = info_div.find('span', string='出版社:')
        book_info['publisher'] = publisher_tag.next_sibling.strip() if publisher_tag else '未找到出版社'
        
        pub_year_tag = info_div.find('span', string='出版年:')
        book_info['pub_year'] = pub_year_tag.next_sibling.strip() if pub_year_tag else '未找到出版年份'
    
    return book_info if book_info['author'] else None

def get_book_comments(driver, url, max_pages=MAX_PAGES):
    """获取图书评论"""
    comments = []
    driver.get(url + "comments/")
    
    for page in range(max_pages):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "comment"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            comment_elements = soup.find_all('div', class_='comment')
            
            if not comment_elements:
                logging.info(f"第 {page + 1} 页没有评论，结束爬取")
                break
            
            for comment in comment_elements:
                comment_info = extract_comment_info(comment)
                comments.append(comment_info)
            
            logging.info(f"已爬取第 {page + 1} 页评论")
            
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '后页')]"))
            )
            next_button.click()
            
            WebDriverWait(driver, 10).until(
                EC.staleness_of(next_button)
            )
            
            time.sleep(random.uniform(2, 5))
        
        except (NoSuchElementException, TimeoutException):
            logging.info("没有找到'后页'按钮或等待超时，结束爬取")
            break
        except Exception as e:
            logging.error(f"爬取评论时发生错误: {e}")
            break
    
    return comments

def extract_comment_info(comment):
    """从评论HTML中提取信息"""
    return {
        'comment_id': comment.find('span', class_='comment-info').find('a', class_='comment-time')['href'].split('/')[-1] if comment.find('span', class_='comment-info').find('a', class_='comment-time') else 'No ID found',
        'user': comment.find('span', class_='comment-info').a.text if comment.find('span', class_='comment-info').a else 'No user found',
        'content': comment.find('p', class_='comment-content').text.strip().replace('\n', '\\n').replace('\r', '') if comment.find('p', class_='comment-content') else 'No content found',
        'rating': comment.find('span', class_='user-stars')['title'] if comment.find('span', class_='user-stars') else 'No rating'
    }

def update_csv_file(csv_file, fieldnames, rows, scraped_ids):
    """更新原始CSV文件中的爬取状态"""
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            if row['subject_id'] in scraped_ids:
                row['scraped'] = 'True'
            writer.writerow(row)

def save_results_to_csv(results):
    """保存爬取结果到CSV文件"""
    # 创建带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(DATA_DIR, f'books_data_{timestamp}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['book_id', 'book_title', 'author', 'cover_url', 'publisher', 
                        'pub_year', 'book_url', 'comment_id', 'user', 'content', 'rating'])
        
        for result in results:
            book_info = result['book_info']
            for comment in result['comments']:
                writer.writerow([
                    book_info['book_id'], book_info['title'], book_info['author'],
                    book_info['cover_url'], book_info['publisher'], book_info['pub_year'],
                    book_info['url'], comment['comment_id'], comment['user'],
                    comment['content'], comment['rating']
                ])
    
    logging.info(f"数据已保存到 {filename}")
    append_to_master_csv(results)

def append_to_master_csv(results):
    """将结果追加到主数据文件"""
    file_exists = os.path.isfile(MASTER_DATA_FILE)
    
    with open(MASTER_DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['book_id', 'book_title', 'author', 'cover_url', 'publisher', 
                           'pub_year', 'book_url', 'comment_id', 'user', 'content', 'rating'])
        
        for result in results:
            book_info = result['book_info']
            for comment in result['comments']:
                writer.writerow([
                    book_info['book_id'], book_info['title'], book_info['author'],
                    book_info['cover_url'], book_info['publisher'], book_info['pub_year'],
                    book_info['url'], comment['comment_id'], comment['user'],
                    comment['content'], comment['rating']
                ])
    
    logging.info(f"数据已追加到 {MASTER_DATA_FILE}")

def main(csv_file, num_samples=5, cookie_string=None):
    """主要爬取流程"""
    book_ids, fieldnames, rows = get_unscraped_book_ids(csv_file, num_samples)
    driver = setup_driver(cookie_string)
    base_url = "https://book.douban.com/subject/"
    results = []
    scraped_ids = []
    
    try:
        for book_id in book_ids:
            try:
                url = f"{base_url}{book_id}/"
                logging.info(f"正在爬取: {url}")
                book_info = get_book_info(driver, url)
                if not book_info:
                    logging.warning(f"跳过书籍 {url}：未找到作者")
                    continue
                
                book_comments = get_book_comments(driver, url)
                
                results.append({
                    'book_info': book_info,
                    'comments': book_comments
                })
                scraped_ids.append(book_id)
                logging.info(f"完成爬取: {book_info['title']}")
                
                time.sleep(random.uniform(5, 15))
            except Exception as e:
                logging.error(f"爬取失败: {url} - {e}")
        
        save_results_to_csv(results)
        update_csv_file(csv_file, fieldnames, rows, scraped_ids)
    finally:
        driver.quit()

def main_loop(csv_file, num_samples=5, cookie_string=None):
    """持续运行的主循环"""
    while True:
        main(csv_file, num_samples, cookie_string)
        wait_time = random.uniform(180, 1800)
        logging.info(f"等待 {wait_time:.2f} 秒后开始下一次爬取")
        time.sleep(wait_time)

def initialize_scraper():
    """初始化爬虫程序"""
    if not os.path.exists(ALL_BOOKS_FILE):
        logging.info("未找到图书列表，开始创建...")
        if not create_book_list(TAGS_FILE, ALL_BOOKS_FILE):
            logging.error("创建图书列表失败")
            return False
    return True

if __name__ == "__main__":
    # 豆瓣Cookie字符串
    cookie_string = 'bid=Fgxz09xSzMk; ap_v=0,6.0; viewed="37008509_36389921_36710597"'
    num_samples = 2  # 每次爬取的书籍数量
    
    if initialize_scraper():
        try:
            main_loop(ALL_BOOKS_FILE, num_samples, cookie_string)
        except KeyboardInterrupt:
            logging.info("程序被用户中断")
        except Exception as e:
            logging.error(f"程序异常终止: {e}")