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
from tqdm import tqdm
import random
import urllib.parse

# 从 cdcSingleBook.py 导入所需函数
from cdcSingleBook import (
    setup_driver, get_page_content, get_book_info,
    get_book_comments, extract_comment_info, save_results_to_csv
)

def save_to_single_csv(results, tag_name):
    """
    将所有书籍的数据保存到同一个CSV文件
    """
    # 使用相对路径，并加入标签名和时间戳
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, 'docs', 'data', 'tag_books')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f'{tag_name}_{timestamp}.csv')
    
    # 写入CSV文件
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
    
    print(f"\n所有数据已保存到: {filename}")

def batch_scrape_books(book_ids, cookie_string=None, tag_name=None):
    """
    批量爬取多本书的信息
    """
    driver = setup_driver(cookie_string)
    base_url = "https://book.douban.com/subject/"
    
    # 每爬取 BATCH_SIZE 本书就休息一次
    BATCH_SIZE = 5
    all_results = []  # 存储所有书籍的结果
    
    try:
        # 使用tqdm创建进度条
        for i, book_id in enumerate(tqdm(book_ids, desc="爬取进度")):
            try:
                url = f"{base_url}{book_id}/"
                logging.info(f"正在爬取: {url}")
                
                book_info = get_book_info(driver, url)
                if not book_info:
                    logging.warning(f"跳过书籍 {url}：未找到作者")
                    continue
                
                book_comments = get_book_comments(driver, url)
                
                results = {
                    'book_info': book_info,
                    'comments': book_comments
                }
                
                all_results.append(results)  # 将结果添加到列表中
                logging.info(f"完成爬取: {book_info['title']}")
                
                # 每本书之间的短暂休息
                time.sleep(random.uniform(1, 10))
                
                # 每爬取 BATCH_SIZE 本书后的长时间休息
                if (i + 1) % BATCH_SIZE == 0 and i + 1 < len(book_ids):
                    sleep_time = random.uniform(20, 40)  # 休息20-40秒
                    print(f"\n已爬取 {i + 1} 本书，休息 {sleep_time:.1f} 秒后继续...")
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"爬取失败: {url} - {e}")
                continue
                
    finally:
        driver.quit()
        
    # 所有数据爬取完成后，一次性保存到CSV
    if all_results:
        save_to_single_csv(all_results, tag_name)

def get_book_ids_from_tag(driver, tag_url, max_books=50):
    """从标签页面获取图书ID"""
    book_ids = []
    page = 0
    
    # 每抓取 BATCH_SIZE 本书就休息一次
    BATCH_SIZE = 10
    
    while len(book_ids) < max_books:
        current_url = f"{tag_url}&start={page*20}"
        try:
            driver.get(current_url)
            time.sleep(random.uniform(2, 4))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            book_list = soup.find_all('li', class_='subject-item')
            
            if not book_list:
                break
            
            books_before = len(book_ids)
            
            for book in book_list:
                if len(book_ids) >= max_books:
                    break
                    
                info = book.find('div', class_='info')
                if not info:
                    continue
                    
                title_element = info.find('a')
                if not title_element:
                    continue
                    
                book_url = title_element['href']
                book_id = book_url.split('/')[-2]
                book_title = title_element.get_text(strip=True)
                
                print(f"找到书籍: {book_title} (ID: {book_id})")
                book_ids.append(book_id)
            
            # 检查是否需要休息
            books_added = len(book_ids) - books_before
            if books_added > 0 and len(book_ids) % BATCH_SIZE == 0 and len(book_ids) < max_books:
                sleep_time = random.uniform(10, 20)
                print(f"\n已获取 {len(book_ids)} 本书的信息，休息 {sleep_time:.1f} 秒后继续...")
                time.sleep(sleep_time)
            
            page += 1
            
        except Exception as e:
            print(f"获取第 {page+1} 页时出错: {e}")
            break
            
        # 翻页后的短暂休息
        time.sleep(random.uniform(2, 4))
    
    return book_ids

def get_tag_url(tag):
    """将标签转换为URL"""
    base_url = "https://book.douban.com/tag/"
    # 对标签进行URL编码
    encoded_tag = urllib.parse.quote(tag)
    return f"{base_url}{encoded_tag}?type=R"

if __name__ == "__main__":
    print("欢迎使用豆瓣标签图书批量爬取工具")
    
    # 获取用户输入的标签
    tag = input("\n请输入要爬取的豆瓣图书标签（例如：用户体验、小说、科技）: ").strip()
    if not tag:
        print("标签不能为空，程序退出")
        sys.exit(1)
    
    # 设置标签URL
    tag_url = get_tag_url(tag)
    print(f"\n将爬取标签「{tag}」下的图书...")
    
    # 获取要爬取的数量
    while True:
        try:
            max_books = int(input("\n请输入要爬取的图书数量（最大50本）: "))
            if 0 < max_books <= 50:
                break
            print("请输入1-50之间的数字")
        except ValueError:
            print("请输入有效的数字")
    
    # 这里使用你的cookie字符串
    cookie_string = 'bid=Fgxz09xSzMk; viewed="37005845_37008509_36389921_36710597"; douban-fav-remind=1; _vwo_uuid_v2=D3B1985B74566E8133964F8AA346D8585|a2dde6ac55434340ae24723b94c01203; dbcl2="253310741:uX6HbAxxn5Y"; push_noty_num=0; push_doumail_num=0; ck=FLyV; __utmc=30149280; __utmz=30149280.1742959753.11.6.utmcsr=cn.bing.com|utmccn=(referral)|utmcmd=referral|utmcct=/; frodotk_db="e80a5e1886507b39b81f1a4992f171ab"; ap_v=0,6.0; __utma=30149280.446198933.1739373311.1742965617.1742971848.14; __utmt_douban=1; __utmb=30149280.13.10.1742971848'
    
    try:
        # 首先获取书籍ID
        driver = setup_driver(cookie_string)
        print(f"\n正在获取「{tag}」标签下的图书ID...")
        book_ids = get_book_ids_from_tag(driver, tag_url, max_books)
        driver.quit()
        
        if not book_ids:
            print("未找到任何图书ID，程序退出")
            sys.exit(1)
            
        print(f"\n成功获取 {len(book_ids)} 本书的ID")
        print("\n即将开始爬取这些书的详细信息...")
        
        # 确认信息
        confirm = input("\n确认开始爬取这些书的详细信息？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消爬取")
            sys.exit()
        
        # 开始批量爬取，传入标签名
        batch_scrape_books(book_ids, cookie_string, tag)
        print("\n所有图书爬取完成！")
        
    except Exception as e:
        print(f"\n爬取过程中发生错误: {e}")
    finally:
        if 'driver' in locals():
            driver.quit() 