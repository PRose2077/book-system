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
from tqdm import tqdm  # 添加进度条支持
import random

# 从 cdcSingleBook.py 导入所需函数
from cdcSingleBook import (
    setup_driver, get_page_content, get_book_info,
    get_book_comments, extract_comment_info, save_results_to_csv
)

def batch_scrape_books(book_ids, cookie_string=None):
    """
    批量爬取多本书的信息
    """
    driver = setup_driver(cookie_string)
    base_url = "https://book.douban.com/subject/"
    
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
                
                save_results_to_csv(results, book_id)
                logging.info(f"完成爬取: {book_info['title']}")
                
                # 如果不是最后一本书，则添加较长的随机睡眠时间
                if i < len(book_ids) - 1:
                    sleep_time = random.uniform(1, 30)  # 随机休眠1-30秒
                    logging.info(f"休息 {sleep_time:.1f} 秒后继续爬取下一本...")
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"爬取失败: {url} - {e}")
                continue
                
    finally:
        driver.quit()

if __name__ == "__main__":
    print("欢迎使用豆瓣图书批量爬取工具")
    
    # 获取要爬取的数量
    while True:
        try:
            num_books = int(input("请输入要爬取的图书数量: "))
            if num_books > 0:
                break
            print("请输入大于0的数字")
        except ValueError:
            print("请输入有效的数字")
    
    # 收集所有book_ids
    book_ids = []
    print(f"\n请依次输入{num_books}个豆瓣图书ID（每输入一个按回车确认）：")
    for i in range(num_books):
        while True:
            book_id = input(f"请输入第 {i+1} 个图书ID: ").strip()
            if book_id.isdigit():  # 确保输入的是数字
                book_ids.append(book_id)
                break
            print("请输入有效的图书ID（纯数字）")
    
    # 确认信息
    print("\n您输入的图书ID如下：")
    for i, book_id in enumerate(book_ids, 1):
        print(f"{i}. {book_id}")
    
    confirm = input("\n确认开始爬取？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消爬取")
        sys.exit()
    
    # 这里使用你的cookie字符串
    cookie_string = 'bid=8PppVIODNJQ; douban-fav-remind=1; viewed="36973903"; push_noty_num=0; push_doumail_num=0; _pk_id.100001.3ac3=55e92198f58f5051.1728138489.; ct=y; _vwo_uuid_v2=DBF40900BB21EBAC36C7AC72CAECC666D|197e08c5f4f00c6764f70a87233e50bd; __utmz=30149280.1728794105.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmv=30149280.25331; dbcl2="253310741:ACnufV+9lZI"; __utmz=81379588.1728895494.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __yadk_uid=NQY4bH5nN2n02PcpgDwIPYmDHaIS5i5X; __utma=30149280.766482741.1728794105.1729434282.1729588221.8; __utma=81379588.349112918.1728895494.1729434282.1729588221.7; ck=V1R_; ap_v=0,6.0'
    
    try:
        batch_scrape_books(book_ids, cookie_string)
        print("\n所有图书爬取完成！")
    except Exception as e:
        print(f"\n爬取过程中发生错误: {e}") 