"""
网页浏览器工具集成模块
提供网页浏览、自动化操作和内容提取功能
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import json
import time

logger = logging.getLogger(__name__)

class WebBrowserTool:
    """网页浏览器工具类"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.setup_session()
        
    def setup_session(self):
        """设置请求会话"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def initialize_driver(self):
        """初始化浏览器驱动"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("浏览器驱动初始化成功")
            return True
        except Exception as e:
            logger.error(f"浏览器驱动初始化失败: {e}")
            return False
    
    async def navigate_to_url(self, url: str, wait_time: int = 5) -> Dict[str, Any]:
        """导航到指定URL"""
        try:
            if not self.driver:
                if not self.initialize_driver():
                    return {"success": False, "error": "浏览器驱动初始化失败"}
            
            self.driver.get(url)
            await asyncio.sleep(wait_time)  # 等待页面加载
            
            # 获取页面信息
            title = self.driver.title
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            return {
                "success": True,
                "title": title,
                "url": current_url,
                "content": self.extract_text_content(page_source)
            }
        except Exception as e:
            logger.error(f"页面导航失败: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_text_content(self, html_content: str) -> str:
        """从HTML中提取文本内容"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取文本
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"文本内容提取失败: {e}")
            return ""
    
    async def fill_form(self, form_data: Dict[str, str]) -> Dict[str, Any]:
        """填充表单"""
        try:
            for field, value in form_data.items():
                element = self.driver.find_element(By.NAME, field)
                element.clear()
                element.send_keys(value)
            
            return {"success": True, "message": "表单填充完成"}
        except Exception as e:
            logger.error(f"表单填充失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, selector: str, by: str = By.CSS_SELECTOR) -> Dict[str, Any]:
        """点击页面元素"""
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by, selector))
            )
            element.click()
            return {"success": True, "message": "元素点击成功"}
        except Exception as e:
            logger.error(f"元素点击失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def take_screenshot(self, filename: str) -> Dict[str, Any]:
        """截取屏幕截图"""
        try:
            self.driver.save_screenshot(filename)
            return {"success": True, "filename": filename}
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """执行JavaScript脚本"""
        try:
            result = self.driver.execute_script(script)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_info(self) -> Dict[str, Any]:
        """获取页面详细信息"""
        try:
            info = {
                "title": self.driver.title,
                "url": self.driver.current_url,
                "cookies": self.driver.get_cookies(),
                "local_storage": self.driver.execute_script("return window.localStorage;"),
                "session_storage": self.driver.execute_script("return window.sessionStorage;")
            }
            return {"success": True, "info": info}
        except Exception as e:
            logger.error(f"页面信息获取失败: {e}")
            return {"success": False, "error": str(e)}
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

class WebContentExtractor:
    """网页内容提取器"""
    
    @staticmethod
    async def extract_links(html_content: str, base_url: str) -> List[Dict[str, str]]:
        """提取页面中的所有链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            full_url = urljoin(base_url, link['href'])
            links.append({
                "text": link.get_text(strip=True),
                "url": full_url,
                "title": link.get('title', '')
            })
        
        return links
    
    @staticmethod
    async def extract_images(html_content: str, base_url: str) -> List[Dict[str, str]]:
        """提取页面中的所有图片"""
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []
        
        for img in soup.find_all('img', src=True):
            full_url = urljoin(base_url, img['src'])
            images.append({
                "src": full_url,
                "alt": img.get('alt', ''),
                "title": img.get('title', '')
            })
        
        return images
    
    @staticmethod
    async def extract_tables(html_content: str) -> List[List[List[str]]]:
        """提取页面中的表格数据"""
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = []
        
        for table in soup.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if row_data:
                    table_data.append(row_data)
            if table_data:
                tables.append(table_data)
        
        return tables
