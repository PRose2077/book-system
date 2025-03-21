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

# 配置
MAX_RETRIES = 3
MAX_PAGES = 15  # 评论页数
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver(cookie_string=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--ignore-ssl-errors=yes')
    chrome_options.add_argument('--ignore-certificate-errors')
    # 获取 Python 的 Scripts 目录路径
    scripts_dir = os.path.join(sys.prefix, 'Scripts')
    chromedriver_path = os.path.join(scripts_dir, 'chromedriver.exe')
    print("正尝试使用"+chromedriver_path)
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 如果提供了 cookie_string，则添加它
    if cookie_string:
        driver.get("https://www.douban.com")
        for cookie in cookie_string.split('; '):
            name, value = cookie.strip().split('=', 1)
            driver.add_cookie({'name': name, 'value': value, 'domain': '.douban.com'})
    
    return driver

def get_page_content(driver, url):
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
        
        except (NoSuchElementException, TimeoutException):
            logging.info("没有找到'后页'按钮或等待超时，结束爬取")
            break
        except Exception as e:
            logging.error(f"爬取评论时发生错误: {e}")
            break
    
    return comments

def extract_comment_info(comment):
    return {
        'comment_id': comment.find('span', class_='comment-info').find('a', class_='comment-time')['href'].split('/')[-1] if comment.find('span', class_='comment-info').find('a', class_='comment-time') else 'No ID found',
        'user': comment.find('span', class_='comment-info').a.text if comment.find('span', class_='comment-info').a else 'No user found',
        'content': comment.find('p', class_='comment-content').text.strip().replace('\n', '\\n').replace('\r', '') if comment.find('p', class_='comment-content') else 'No content found',
        'rating': comment.find('span', class_='user-stars')['title'] if comment.find('span', class_='user-stars') else 'No rating'
    }

def save_results_to_csv(results, book_id):
    # 使用相对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # 只向上一级到项目根目录
    output_dir = os.path.join(project_root, 'docs', 'data', 'single_books')
    os.makedirs(output_dir, exist_ok=True)

    book_title = results['book_info']['title']
    # 清理书名以用作文件名，只保留英文字母和数字
    safe_book_title = ""
    for x in book_title:
        if x.isalnum() and ord(x) < 128:  # 只保留ASCII字母和数字
            safe_book_title += x
        elif x == ' ':
            safe_book_title += '_'
    
    # 如果清理后文件名为空，则使用book_id
    if not safe_book_title:
        safe_book_title = f"book_{book_id}"
    
    # 限制文件名长度
    safe_book_title = safe_book_title[:50] 

    filename = os.path.join(output_dir, f'{safe_book_title}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['book_id', 'book_title', 'author', 'cover_url', 'publisher', 'pub_year', 'book_url',
                         'comment_id', 'user', 'content', 'rating'])
        
        book_info = results['book_info']
        for comment in results['comments']:
            writer.writerow([
                book_info['book_id'], book_info['title'], book_info['author'],
                book_info['cover_url'], book_info['publisher'], book_info['pub_year'],
                book_info['url'], comment['comment_id'], comment['user'],
                comment['content'], comment['rating']
            ])
    
    logging.info(f"数据已保存到 {filename}")

def scrape_single_book(book_id, cookie_string=None):
    driver = setup_driver(cookie_string)
    base_url = "https://book.douban.com/subject/"
    
    try:
        url = f"{base_url}{book_id}/"
        logging.info(f"正在爬取: {url}")
        
        book_info = get_book_info(driver, url)
        if not book_info:
            logging.warning(f"跳过书籍 {url}：未找到作者")
            return
        
        book_comments = get_book_comments(driver, url)
        
        results = {
            'book_info': book_info,
            'comments': book_comments
        }
        
        save_results_to_csv(results, book_id)
        logging.info(f"完成爬取: {book_info['title']}")
        
    except Exception as e:
        logging.error(f"爬取失败: {url} - {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # 用户输入book_id
    book_id = input("请输入要爬取的豆瓣图书ID: ")
    
    # 这里使用你的cookie字符串
    cookie_string = ''
    scrape_single_book(book_id, cookie_string) 
