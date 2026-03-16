"""
字符串工具模块

提供各种字符串操作的实用工具函数，包括字符串处理、格式化、验证、转换等。
"""

import re
import string
import unicodedata
import hashlib
import base64
import json
import html
import random
from typing import List, Dict, Optional, Union, Any, Set, Pattern, Callable, Tuple
from urllib.parse import quote, unquote, urlparse
import textwrap


class StringUtils:
    """字符串工具类"""
    
    # 常见字符集
    ASCII_LETTERS = string.ascii_letters
    ASCII_LOWERCASE = string.ascii_lowercase
    ASCII_UPPERCASE = string.ascii_uppercase
    DIGITS = string.digits
    PUNCTUATION = string.punctuation
    PRINTABLE = string.printable
    WHITESPACE = string.whitespace
    
    # 常用正则表达式模式
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'url': r'^https?://[^\s/$.?#].[^\s]*$',
        'phone': r'^\+?[\d\s\-\(\)]{7,}$',
        'chinese_phone': r'^1[3-9]\d{9}$',
        'ipv4': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        'ipv6': r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        'mac': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'uuid4': r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        'chinese': r'[\u4e00-\u9fff]',
        'username': r'^[a-zA-Z0-9_]{3,20}$',
        'password': r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'",.<>/?]{6,}$',
        'strong_password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        'hex_color': r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        'date_ymd': r'^\d{4}-\d{2}-\d{2}$',
        'time': r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$',
        'datetime': r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',
        'domain': r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$',
        'html_tag': r'<[^>]+>',
        'base64': r'^[A-Za-z0-9+/]+=*$',
        'base64_url': r'^[A-Za-z0-9_-]+=*$',
        'md5': r'^[a-f0-9]{32}$',
        'sha1': r'^[a-f0-9]{40}$',
        'sha256': r'^[a-f0-9]{64}$',
    }
    
    @staticmethod
    def is_empty(s: Optional[str]) -> bool:
        """判断字符串是否为空
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为空
        """
        return s is None or len(s.strip()) == 0
    
    @staticmethod
    def is_not_empty(s: Optional[str]) -> bool:
        """判断字符串是否不为空
        
        Args:
            s: 输入字符串
            
        Returns:
            是否不为空
        """
        return not StringUtils.is_empty(s)
    
    @staticmethod
    def is_blank(s: Optional[str]) -> bool:
        """判断字符串是否为空或只包含空白字符
        
        Args:
            s: 输入字符串
            
        Returns:
            是否空白
        """
        return s is None or len(s.strip()) == 0
    
    @staticmethod
    def is_not_blank(s: Optional[str]) -> bool:
        """判断字符串是否不为空白
        
        Args:
            s: 输入字符串
            
        Returns:
            是否不为空白
        """
        return not StringUtils.is_blank(s)
    
    @staticmethod
    def default_if_empty(s: Optional[str], default: str = '') -> str:
        """如果字符串为空则返回默认值
        
        Args:
            s: 输入字符串
            default: 默认值
            
        Returns:
            原字符串或默认值
        """
        return s if StringUtils.is_not_empty(s) else default
    
    @staticmethod
    def default_if_blank(s: Optional[str], default: str = '') -> str:
        """如果字符串为空白则返回默认值
        
        Args:
            s: 输入字符串
            default: 默认值
            
        Returns:
            原字符串或默认值
        """
        return s if StringUtils.is_not_blank(s) else default
    
    @staticmethod
    def null_to_empty(s: Optional[str]) -> str:
        """将None转换为空字符串
        
        Args:
            s: 输入字符串
            
        Returns:
            非空字符串
        """
        return s if s is not None else ''
    
    @staticmethod
    def empty_to_null(s: Optional[str]) -> Optional[str]:
        """将空字符串转换为None
        
        Args:
            s: 输入字符串
            
        Returns:
            None或原字符串
        """
        return None if StringUtils.is_empty(s) else s
    
    @staticmethod
    def trim(s: Optional[str]) -> str:
        """去除首尾空白
        
        Args:
            s: 输入字符串
            
        Returns:
            去除空白后的字符串
        """
        return s.strip() if s else ''
    
    @staticmethod
    def trim_start(s: Optional[str]) -> str:
        """去除开头空白
        
        Args:
            s: 输入字符串
            
        Returns:
            去除开头空白后的字符串
        """
        return s.lstrip() if s else ''
    
    @staticmethod
    def trim_end(s: Optional[str]) -> str:
        """去除结尾空白
        
        Args:
            s: 输入字符串
            
        Returns:
            去除结尾空白后的字符串
        """
        return s.rstrip() if s else ''
    
    @staticmethod
    def trim_all(s: Optional[str]) -> str:
        """去除所有空白字符
        
        Args:
            s: 输入字符串
            
        Returns:
            去除所有空白后的字符串
        """
        if not s:
            return ''
        return ''.join(s.split())
    
    @staticmethod
    def normalize_whitespace(s: str) -> str:
        """标准化空白字符（多个空格合并为一个）
        
        Args:
            s: 输入字符串
            
        Returns:
            标准化后的字符串
        """
        return ' '.join(s.split())
    
    @staticmethod
    def truncate(s: str, max_length: int, suffix: str = '...') -> str:
        """截断字符串
        
        Args:
            s: 输入字符串
            max_length: 最大长度
            suffix: 截断后缀
            
        Returns:
            截断后的字符串
        """
        if len(s) <= max_length:
            return s
        return s[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def truncate_middle(s: str, max_length: int, separator: str = '...') -> str:
        """从中间截断字符串
        
        Args:
            s: 输入字符串
            max_length: 最大长度
            separator: 分隔符
            
        Returns:
            截断后的字符串
        """
        if len(s) <= max_length:
            return s
        
        half = (max_length - len(separator)) // 2
        return s[:half] + separator + s[-half:]
    
    @staticmethod
    def pad_left(s: str, width: int, pad_char: str = ' ') -> str:
        """左填充
        
        Args:
            s: 输入字符串
            width: 目标宽度
            pad_char: 填充字符
            
        Returns:
            填充后的字符串
        """
        return s.rjust(width, pad_char)
    
    @staticmethod
    def pad_right(s: str, width: int, pad_char: str = ' ') -> str:
        """右填充
        
        Args:
            s: 输入字符串
            width: 目标宽度
            pad_char: 填充字符
            
        Returns:
            填充后的字符串
        """
        return s.ljust(width, pad_char)
    
    @staticmethod
    def pad_center(s: str, width: int, pad_char: str = ' ') -> str:
        """居中填充
        
        Args:
            s: 输入字符串
            width: 目标宽度
            pad_char: 填充字符
            
        Returns:
            填充后的字符串
        """
        return s.center(width, pad_char)
    
    @staticmethod
    def repeat(s: str, count: int) -> str:
        """重复字符串
        
        Args:
            s: 输入字符串
            count: 重复次数
            
        Returns:
            重复后的字符串
        """
        return s * count
    
    @staticmethod
    def reverse(s: str) -> str:
        """反转字符串
        
        Args:
            s: 输入字符串
            
        Returns:
            反转后的字符串
        """
        return s[::-1]
    
    @staticmethod
    def substring(s: str, start: int, end: Optional[int] = None) -> str:
        """获取子字符串
        
        Args:
            s: 输入字符串
            start: 开始索引
            end: 结束索引（不包含）
            
        Returns:
            子字符串
        """
        if end is None:
            return s[start:]
        return s[start:end]
    
    @staticmethod
    def left(s: str, n: int) -> str:
        """获取左边n个字符
        
        Args:
            s: 输入字符串
            n: 字符数
            
        Returns:
            左边子字符串
        """
        return s[:n]
    
    @staticmethod
    def right(s: str, n: int) -> str:
        """获取右边n个字符
        
        Args:
            s: 输入字符串
            n: 字符数
            
        Returns:
            右边子字符串
        """
        return s[-n:] if n > 0 else ''
    
    @staticmethod
    def capitalize(s: str) -> str:
        """首字母大写
        
        Args:
            s: 输入字符串
            
        Returns:
            首字母大写的字符串
        """
        return s.capitalize() if s else ''
    
    @staticmethod
    def capitalize_first(s: str) -> str:
        """首字母大写，其余不变
        
        Args:
            s: 输入字符串
            
        Returns:
            首字母大写的字符串
        """
        if not s:
            return ''
        return s[0].upper() + s[1:]
    
    @staticmethod
    def uncapitalize_first(s: str) -> str:
        """首字母小写
        
        Args:
            s: 输入字符串
            
        Returns:
            首字母小写的字符串
        """
        if not s:
            return ''
        return s[0].lower() + s[1:]
    
    @staticmethod
    def title_case(s: str) -> str:
        """标题格式（每个单词首字母大写）
        
        Args:
            s: 输入字符串
            
        Returns:
            标题格式的字符串
        """
        return s.title() if s else ''
    
    @staticmethod
    def sentence_case(s: str) -> str:
        """句子格式（首字母大写，其余小写）
        
        Args:
            s: 输入字符串
            
        Returns:
            句子格式的字符串
        """
        if not s:
            return ''
        return s[0].upper() + s[1:].lower()
    
    @staticmethod
    def upper(s: str) -> str:
        """转换为大写
        
        Args:
            s: 输入字符串
            
        Returns:
            大写字符串
        """
        return s.upper() if s else ''
    
    @staticmethod
    def lower(s: str) -> str:
        """转换为小写
        
        Args:
            s: 输入字符串
            
        Returns:
            小写字符串
        """
        return s.lower() if s else ''
    
    @staticmethod
    def swap_case(s: str) -> str:
        """大小写互换
        
        Args:
            s: 输入字符串
            
        Returns:
            大小写互换后的字符串
        """
        return s.swapcase() if s else ''
    
    @staticmethod
    def camel_to_snake(s: str) -> str:
        """驼峰命名转下划线命名
        
        Args:
            s: 驼峰命名字符串
            
        Returns:
            下划线命名字符串
        """
        if not s:
            return ''
        
        # 处理连续大写字母
        s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', s)
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
        return s.lower()
    
    @staticmethod
    def snake_to_camel(s: str, capitalize_first: bool = False) -> str:
        """下划线命名转驼峰命名
        
        Args:
            s: 下划线命名字符串
            capitalize_first: 是否首字母大写（大驼峰）
            
        Returns:
            驼峰命名字符串
        """
        if not s:
            return ''
        
        components = s.split('_')
        if capitalize_first:
            return ''.join(word.capitalize() for word in components)
        else:
            return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    @staticmethod
    def snake_to_kebab(s: str) -> str:
        """下划线命名转短横线命名
        
        Args:
            s: 下划线命名字符串
            
        Returns:
            短横线命名字符串
        """
        return s.replace('_', '-') if s else ''
    
    @staticmethod
    def kebab_to_snake(s: str) -> str:
        """短横线命名转下划线命名
        
        Args:
            s: 短横线命名字符串
            
        Returns:
            下划线命名字符串
        """
        return s.replace('-', '_') if s else ''
    
    @staticmethod
    def kebab_to_camel(s: str, capitalize_first: bool = False) -> str:
        """短横线命名转驼峰命名
        
        Args:
            s: 短横线命名字符串
            capitalize_first: 是否首字母大写
            
        Returns:
            驼峰命名字符串
        """
        snake = StringUtils.kebab_to_snake(s)
        return StringUtils.snake_to_camel(snake, capitalize_first)
    
    @staticmethod
    def to_slug(s: str, separator: str = '-', lowercase: bool = True) -> str:
        """生成URL友好的slug
        
        Args:
            s: 输入字符串
            separator: 单词分隔符
            lowercase: 是否转为小写
            
        Returns:
            slug字符串
        """
        if not s:
            return ''
        
        # 移除重音符号
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        
        # 移除非字母数字字符
        s = re.sub(r'[^a-zA-Z0-9\s-]', '', s)
        
        # 替换空格和连字符为分隔符
        s = re.sub(r'[\s-]+', separator, s)
        
        # 移除首尾分隔符
        s = s.strip(separator)
        
        if lowercase:
            s = s.lower()
        
        return s
    
    @staticmethod
    def remove_accents(s: str) -> str:
        """移除重音符号
        
        Args:
            s: 输入字符串
            
        Returns:
            移除重音后的字符串
        """
        nfkd_form = unicodedata.normalize('NFKD', s)
        return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    @staticmethod
    def remove_non_ascii(s: str, replacement: str = '') -> str:
        """移除非ASCII字符
        
        Args:
            s: 输入字符串
            replacement: 替换字符
            
        Returns:
            处理后的字符串
        """
        return re.sub(r'[^\x00-\x7F]+', replacement, s)
    
    @staticmethod
    def remove_non_alphanumeric(s: str, replacement: str = '') -> str:
        """移除非字母数字字符
        
        Args:
            s: 输入字符串
            replacement: 替换字符
            
        Returns:
            处理后的字符串
        """
        return re.sub(r'[^a-zA-Z0-9]+', replacement, s)
    
    @staticmethod
    def remove_html_tags(s: str) -> str:
        """移除HTML标签
        
        Args:
            s: 包含HTML标签的字符串
            
        Returns:
            移除标签后的字符串
        """
        return re.sub(r'<[^>]+>', '', s)
    
    @staticmethod
    def escape_html(s: str) -> str:
        """转义HTML字符
        
        Args:
            s: 原始字符串
            
        Returns:
            转义后的字符串
        """
        return html.escape(s, quote=True)
    
    @staticmethod
    def unescape_html(s: str) -> str:
        """反转义HTML字符
        
        Args:
            s: 转义后的字符串
            
        Returns:
            原始字符串
        """
        return html.unescape(s)
    
    @staticmethod
    def escape_regex(s: str) -> str:
        """转义正则表达式特殊字符
        
        Args:
            s: 原始字符串
            
        Returns:
            转义后的字符串
        """
        return re.escape(s)
    
    @staticmethod
    def escape_sql(s: str) -> str:
        """转义SQL字符串（简单转义）
        
        Args:
            s: 原始字符串
            
        Returns:
            转义后的字符串
        """
        if not s:
            return ''
        return s.replace("'", "''")
    
    @staticmethod
    def escape_json(s: str) -> str:
        """转义JSON字符串
        
        Args:
            s: 原始字符串
            
        Returns:
            转义后的字符串
        """
        return json.dumps(s)[1:-1]
    
    @staticmethod
    def unescape_json(s: str) -> str:
        """反转义JSON字符串
        
        Args:
            s: 转义后的字符串
            
        Returns:
            原始字符串
        """
        return json.loads(f'"{s}"')
    
    @staticmethod
    def contains(s: str, substring: str, case_sensitive: bool = True) -> bool:
        """检查是否包含子字符串
        
        Args:
            s: 原始字符串
            substring: 子字符串
            case_sensitive: 是否区分大小写
            
        Returns:
            是否包含
        """
        if not s or not substring:
            return False
        
        if case_sensitive:
            return substring in s
        else:
            return substring.lower() in s.lower()
    
    @staticmethod
    def starts_with(s: str, prefix: str, case_sensitive: bool = True) -> bool:
        """检查是否以指定前缀开头
        
        Args:
            s: 原始字符串
            prefix: 前缀
            case_sensitive: 是否区分大小写
            
        Returns:
            是否以指定前缀开头
        """
        if not s or not prefix:
            return False
        
        if case_sensitive:
            return s.startswith(prefix)
        else:
            return s.lower().startswith(prefix.lower())
    
    @staticmethod
    def ends_with(s: str, suffix: str, case_sensitive: bool = True) -> bool:
        """检查是否以指定后缀结尾
        
        Args:
            s: 原始字符串
            suffix: 后缀
            case_sensitive: 是否区分大小写
            
        Returns:
            是否以指定后缀结尾
        """
        if not s or not suffix:
            return False
        
        if case_sensitive:
            return s.endswith(suffix)
        else:
            return s.lower().endswith(suffix.lower())
    
    @staticmethod
    def count_occurrences(s: str, substring: str, overlap: bool = False) -> int:
        """计算子字符串出现次数
        
        Args:
            s: 原始字符串
            substring: 子字符串
            overlap: 是否允许重叠匹配
            
        Returns:
            出现次数
        """
        if not s or not substring:
            return 0
        
        if not overlap:
            return s.count(substring)
        else:
            count = 0
            start = 0
            while True:
                pos = s.find(substring, start)
                if pos == -1:
                    break
                count += 1
                start = pos + 1
            return count
    
    @staticmethod
    def index_of(s: str, substring: str, start: int = 0) -> int:
        """查找子字符串首次出现的位置
        
        Args:
            s: 原始字符串
            substring: 子字符串
            start: 开始搜索的位置
            
        Returns:
            索引位置，未找到返回-1
        """
        return s.find(substring, start)
    
    @staticmethod
    def last_index_of(s: str, substring: str) -> int:
        """查找子字符串最后出现的位置
        
        Args:
            s: 原始字符串
            substring: 子字符串
            
        Returns:
            索引位置，未找到返回-1
        """
        return s.rfind(substring)
    
    @staticmethod
    def replace(s: str, old: str, new: str, count: int = -1) -> str:
        """替换字符串
        
        Args:
            s: 原始字符串
            old: 要替换的子字符串
            new: 新字符串
            count: 替换次数，-1表示全部替换
            
        Returns:
            替换后的字符串
        """
        return s.replace(old, new, count) if count >= 0 else s.replace(old, new)
    
    @staticmethod
    def replace_regex(s: str, pattern: str, replacement: str, count: int = 0) -> str:
        """使用正则表达式替换
        
        Args:
            s: 原始字符串
            pattern: 正则表达式模式
            replacement: 替换字符串
            count: 替换次数，0表示全部替换
            
        Returns:
            替换后的字符串
        """
        return re.sub(pattern, replacement, s, count=count)
    
    @staticmethod
    def extract(s: str, pattern: str, group: int = 0) -> Optional[str]:
        """使用正则表达式提取内容
        
        Args:
            s: 原始字符串
            pattern: 正则表达式模式
            group: 要提取的分组
            
        Returns:
            提取的内容，未匹配返回None
        """
        match = re.search(pattern, s)
        if match:
            return match.group(group)
        return None
    
    @staticmethod
    def extract_all(s: str, pattern: str, group: int = 0) -> List[str]:
        """提取所有匹配的内容
        
        Args:
            s: 原始字符串
            pattern: 正则表达式模式
            group: 要提取的分组
            
        Returns:
            提取的内容列表
        """
        return re.findall(pattern, s)
    
    @staticmethod
    def split(s: str, separator: Optional[str] = None, maxsplit: int = -1) -> List[str]:
        """分割字符串
        
        Args:
            s: 原始字符串
            separator: 分隔符，None表示按空白字符分割
            maxsplit: 最大分割次数
            
        Returns:
            分割后的列表
        """
        if separator is None:
            return s.split(maxsplit=maxsplit) if maxsplit >= 0 else s.split()
        return s.split(separator, maxsplit) if maxsplit >= 0 else s.split(separator)
    
    @staticmethod
    def split_lines(s: str, keep_ends: bool = False) -> List[str]:
        """按行分割
        
        Args:
            s: 原始字符串
            keep_ends: 是否保留换行符
            
        Returns:
            行列表
        """
        if keep_ends:
            return re.split(r'(?<=[\n\r])', s)
        return s.splitlines()
    
    @staticmethod
    def join(separator: str, items: List[str]) -> str:
        """连接字符串列表
        
        Args:
            separator: 分隔符
            items: 字符串列表
            
        Returns:
            连接后的字符串
        """
        return separator.join(items)
    
    @staticmethod
    def concat(*args: str) -> str:
        """连接多个字符串
        
        Args:
            *args: 要连接的字符串
            
        Returns:
            连接后的字符串
        """
        return ''.join(args)
    
    @staticmethod
    def wrap(s: str, width: int = 80, break_long_words: bool = True) -> List[str]:
        """自动换行
        
        Args:
            s: 原始字符串
            width: 每行最大宽度
            break_long_words: 是否断长词
            
        Returns:
            换行后的行列表
        """
        return textwrap.wrap(s, width=width, break_long_words=break_long_words)
    
    @staticmethod
    def fill(s: str, width: int = 80, break_long_words: bool = True) -> str:
        """自动换行并连接
        
        Args:
            s: 原始字符串
            width: 每行最大宽度
            break_long_words: 是否断长词
            
        Returns:
            换行后的字符串
        """
        return textwrap.fill(s, width=width, break_long_words=break_long_words)
    
    @staticmethod
    def indent(s: str, prefix: str = '    ') -> str:
        """缩进文本
        
        Args:
            s: 原始字符串
            prefix: 缩进前缀
            
        Returns:
            缩进后的字符串
        """
        return textwrap.indent(s, prefix)
    
    @staticmethod
    def dedent(s: str) -> str:
        """移除公共缩进
        
        Args:
            s: 原始字符串
            
        Returns:
            移除缩进后的字符串
        """
        return textwrap.dedent(s)
    
    @staticmethod
    def shorten(s: str, width: int = 80, placeholder: str = '...') -> str:
        """缩短文本到指定宽度
        
        Args:
            s: 原始字符串
            width: 目标宽度
            placeholder: 占位符
            
        Returns:
            缩短后的字符串
        """
        return textwrap.shorten(s, width=width, placeholder=placeholder)
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """计算编辑距离（Levenshtein距离）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return StringUtils.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def hamming_distance(s1: str, s2: str) -> int:
        """计算汉明距离
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            汉明距离，长度不同返回-1
        """
        if len(s1) != len(s2):
            return -1
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))
    
    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """计算字符串相似度
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            相似度（0-1）
        """
        distance = StringUtils.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1.0 - distance / max_len
    
    @staticmethod
    def longest_common_substring(s1: str, s2: str) -> str:
        """查找最长公共子串
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            最长公共子串
        """
        if not s1 or not s2:
            return ''
        
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        end_pos = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_pos = i
        
        return s1[end_pos - max_len:end_pos]
    
    @staticmethod
    def longest_common_prefix(strs: List[str]) -> str:
        """查找最长公共前缀
        
        Args:
            strs: 字符串列表
            
        Returns:
            最长公共前缀
        """
        if not strs:
            return ''
        
        prefix = strs[0]
        for s in strs[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ''
        return prefix
    
    @staticmethod
    def longest_common_suffix(strs: List[str]) -> str:
        """查找最长公共后缀
        
        Args:
            strs: 字符串列表
            
        Returns:
            最长公共后缀
        """
        if not strs:
            return ''
        
        suffix = strs[0]
        for s in strs[1:]:
            while not s.endswith(suffix):
                suffix = suffix[1:]
                if not suffix:
                    return ''
        return suffix
    
    @staticmethod
    def mask(s: str, visible_chars: int = 4, mask_char: str = '*') -> str:
        """掩码字符串
        
        Args:
            s: 原始字符串
            visible_chars: 可见字符数
            mask_char: 掩码字符
            
        Returns:
            掩码后的字符串
        """
        if not s:
            return ''
        if len(s) <= visible_chars:
            return s
        return s[:visible_chars] + mask_char * (len(s) - visible_chars)
    
    @staticmethod
    def mask_email(email: str) -> str:
        """掩码邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            掩码后的邮箱
        """
        if '@' not in email:
            return StringUtils.mask(email)
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[:2] + '***'
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """掩码手机号
        
        Args:
            phone: 手机号
            
        Returns:
            掩码后的手机号
        """
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 11:
            return digits[:3] + '****' + digits[-4:]
        return StringUtils.mask(phone)
    
    @staticmethod
    def to_hex(s: str, encoding: str = 'utf-8', prefix: bool = False) -> str:
        """转换为十六进制字符串
        
        Args:
            s: 原始字符串
            encoding: 编码
            prefix: 是否添加0x前缀
            
        Returns:
            十六进制字符串
        """
        hex_str = s.encode(encoding).hex()
        if prefix:
            return f"0x{hex_str}"
        return hex_str
    
    @staticmethod
    def from_hex(hex_str: str, encoding: str = 'utf-8') -> str:
        """从十六进制字符串恢复
        
        Args:
            hex_str: 十六进制字符串
            encoding: 编码
            
        Returns:
            原始字符串
        """
        hex_str = hex_str.replace('0x', '').replace('0X', '')
        return bytes.fromhex(hex_str).decode(encoding)
    
    @staticmethod
    def to_base64(s: str, encoding: str = 'utf-8') -> str:
        """转换为Base64
        
        Args:
            s: 原始字符串
            encoding: 编码
            
        Returns:
            Base64字符串
        """
        return base64.b64encode(s.encode(encoding)).decode('ascii')
    
    @staticmethod
    def from_base64(b64_str: str, encoding: str = 'utf-8') -> str:
        """从Base64恢复
        
        Args:
            b64_str: Base64字符串
            encoding: 编码
            
        Returns:
            原始字符串
        """
        return base64.b64decode(b64_str).decode(encoding)
    
    @staticmethod
    def to_md5(s: str, encoding: str = 'utf-8') -> str:
        """计算MD5哈希
        
        Args:
            s: 原始字符串
            encoding: 编码
            
        Returns:
            MD5哈希值
        """
        return hashlib.md5(s.encode(encoding)).hexdigest()
    
    @staticmethod
    def to_sha256(s: str, encoding: str = 'utf-8') -> str:
        """计算SHA256哈希
        
        Args:
            s: 原始字符串
            encoding: 编码
            
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(s.encode(encoding)).hexdigest()


class TextValidationUtils:
    """文本验证工具类"""
    
    @staticmethod
    def is_alpha(s: str) -> bool:
        """检查是否只包含字母
        
        Args:
            s: 输入字符串
            
        Returns:
            是否只包含字母
        """
        return s.isalpha() if s else False
    
    @staticmethod
    def is_digit(s: str) -> bool:
        """检查是否只包含数字
        
        Args:
            s: 输入字符串
            
        Returns:
            是否只包含数字
        """
        return s.isdigit() if s else False
    
    @staticmethod
    def is_alphanumeric(s: str) -> bool:
        """检查是否只包含字母和数字
        
        Args:
            s: 输入字符串
            
        Returns:
            是否只包含字母和数字
        """
        return s.isalnum() if s else False
    
    @staticmethod
    def is_lowercase(s: str) -> bool:
        """检查是否全部小写
        
        Args:
            s: 输入字符串
            
        Returns:
            是否全部小写
        """
        return s.islower() if s else False
    
    @staticmethod
    def is_uppercase(s: str) -> bool:
        """检查是否全部大写
        
        Args:
            s: 输入字符串
            
        Returns:
            是否全部大写
        """
        return s.isupper() if s else False
    
    @staticmethod
    def is_space(s: str) -> bool:
        """检查是否只包含空白字符
        
        Args:
            s: 输入字符串
            
        Returns:
            是否只包含空白字符
        """
        return s.isspace() if s else False
    
    @staticmethod
    def is_title_case(s: str) -> bool:
        """检查是否为标题格式
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为标题格式
        """
        return s.istitle() if s else False
    
    @staticmethod
    def is_printable(s: str) -> bool:
        """检查是否所有字符都是可打印的
        
        Args:
            s: 输入字符串
            
        Returns:
            是否所有字符都可打印
        """
        return all(c in string.printable for c in s) if s else True
    
    @staticmethod
    def is_ascii(s: str) -> bool:
        """检查是否所有字符都是ASCII
        
        Args:
            s: 输入字符串
            
        Returns:
            是否所有字符都是ASCII
        """
        return all(ord(c) < 128 for c in s) if s else True
    
    @staticmethod
    def is_chinese(s: str) -> bool:
        """检查是否包含中文字符
        
        Args:
            s: 输入字符串
            
        Returns:
            是否包含中文
        """
        return bool(re.search(StringUtils.PATTERNS['chinese'], s)) if s else False
    
    @staticmethod
    def is_all_chinese(s: str) -> bool:
        """检查是否全部为中文
        
        Args:
            s: 输入字符串
            
        Returns:
            是否全部为中文
        """
        if not s:
            return False
        return all('\u4e00' <= c <= '\u9fff' for c in s if c.strip())
    
    @staticmethod
    def is_email(s: str) -> bool:
        """检查是否为有效的邮箱地址
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效邮箱
        """
        return bool(re.match(StringUtils.PATTERNS['email'], s)) if s else False
    
    @staticmethod
    def is_url(s: str) -> bool:
        """检查是否为有效的URL
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效URL
        """
        return bool(re.match(StringUtils.PATTERNS['url'], s)) if s else False
    
    @staticmethod
    def is_phone(s: str, country: str = 'CN') -> bool:
        """检查是否为有效的电话号码
        
        Args:
            s: 输入字符串
            country: 国家代码
            
        Returns:
            是否为有效电话号码
        """
        if country == 'CN':
            return bool(re.match(StringUtils.PATTERNS['chinese_phone'], s)) if s else False
        else:
            return bool(re.match(StringUtils.PATTERNS['phone'], s)) if s else False
    
    @staticmethod
    def is_ipv4(s: str) -> bool:
        """检查是否为有效的IPv4地址
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效IPv4地址
        """
        return bool(re.match(StringUtils.PATTERNS['ipv4'], s)) if s else False
    
    @staticmethod
    def is_ipv6(s: str) -> bool:
        """检查是否为有效的IPv6地址
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效IPv6地址
        """
        return bool(re.match(StringUtils.PATTERNS['ipv6'], s)) if s else False
    
    @staticmethod
    def is_mac(s: str) -> bool:
        """检查是否为有效的MAC地址
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效MAC地址
        """
        return bool(re.match(StringUtils.PATTERNS['mac'], s)) if s else False
    
    @staticmethod
    def is_uuid(s: str, version: Optional[int] = None) -> bool:
        """检查是否为有效的UUID
        
        Args:
            s: 输入字符串
            version: UUID版本
            
        Returns:
            是否为有效UUID
        """
        if version == 4:
            return bool(re.match(StringUtils.PATTERNS['uuid4'], s)) if s else False
        else:
            return bool(re.match(StringUtils.PATTERNS['uuid'], s)) if s else False
    
    @staticmethod
    def is_domain(s: str) -> bool:
        """检查是否为有效的域名
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效域名
        """
        return bool(re.match(StringUtils.PATTERNS['domain'], s)) if s else False
    
    @staticmethod
    def is_username(s: str, min_len: int = 3, max_len: int = 20) -> bool:
        """检查是否为有效的用户名
        
        Args:
            s: 输入字符串
            min_len: 最小长度
            max_len: 最大长度
            
        Returns:
            是否为有效用户名
        """
        if not s or len(s) < min_len or len(s) > max_len:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', s))
    
    @staticmethod
    def is_strong_password(password: str, min_length: int = 8) -> Tuple[bool, Dict[str, bool]]:
        """检查密码强度
        
        Args:
            password: 密码
            min_length: 最小长度
            
        Returns:
            (是否通过, 详细结果)
        """
        result = {
            'length_ok': len(password) >= min_length,
            'has_upper': bool(re.search(r'[A-Z]', password)),
            'has_lower': bool(re.search(r'[a-z]', password)),
            'has_digit': bool(re.search(r'\d', password)),
            'has_special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            'no_spaces': ' ' not in password
        }
        
        passed = all(result.values())
        return passed, result
    
    @staticmethod
    def is_hex_color(s: str) -> bool:
        """检查是否为有效的十六进制颜色值
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效颜色值
        """
        return bool(re.match(StringUtils.PATTERNS['hex_color'], s)) if s else False
    
    @staticmethod
    def is_json(s: str) -> bool:
        """检查是否为有效的JSON
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效JSON
        """
        try:
            json.loads(s)
            return True
        except:
            return False
    
    @staticmethod
    def is_base64(s: str) -> bool:
        """检查是否为有效的Base64
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效Base64
        """
        return bool(re.match(StringUtils.PATTERNS['base64'], s)) if s else False
    
    @staticmethod
    def is_md5(s: str) -> bool:
        """检查是否为有效的MD5哈希
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效MD5
        """
        return bool(re.match(StringUtils.PATTERNS['md5'], s)) if s else False
    
    @staticmethod
    def is_sha256(s: str) -> bool:
        """检查是否为有效的SHA256哈希
        
        Args:
            s: 输入字符串
            
        Returns:
            是否为有效SHA256
        """
        return bool(re.match(StringUtils.PATTERNS['sha256'], s)) if s else False


class TextProcessingUtils:
    """文本处理工具类"""
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """提取邮箱地址
        
        Args:
            text: 文本
            
        Returns:
            邮箱地址列表
        """
        return re.findall(StringUtils.PATTERNS['email'], text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """提取URL
        
        Args:
            text: 文本
            
        Returns:
            URL列表
        """
        return re.findall(StringUtils.PATTERNS['url'], text)
    
    @staticmethod
    def extract_phones(text: str, country: str = 'CN') -> List[str]:
        """提取电话号码
        
        Args:
            text: 文本
            country: 国家代码
            
        Returns:
            电话号码列表
        """
        if country == 'CN':
            return re.findall(StringUtils.PATTERNS['chinese_phone'], text)
        else:
            return re.findall(StringUtils.PATTERNS['phone'], text)
    
    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """提取数字
        
        Args:
            text: 文本
            
        Returns:
            数字列表
        """
        return re.findall(r'\d+', text)
    
    @staticmethod
    def extract_chinese(text: str) -> List[str]:
        """提取中文字符
        
        Args:
            text: 文本
            
        Returns:
            中文字符列表
        """
        return re.findall(StringUtils.PATTERNS['chinese'], text)
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """提取日期
        
        Args:
            text: 文本
            
        Returns:
            日期字符串列表
        """
        return re.findall(r'\d{4}-\d{2}-\d{2}', text)
    
    @staticmethod
    def extract_times(text: str) -> List[str]:
        """提取时间
        
        Args:
            text: 文本
            
        Returns:
            时间字符串列表
        """
        return re.findall(r'\d{2}:\d{2}:\d{2}', text)
    
    @staticmethod
    def extract_ip_addresses(text: str) -> List[str]:
        """提取IP地址
        
        Args:
            text: 文本
            
        Returns:
            IP地址列表
        """
        ipv4 = re.findall(StringUtils.PATTERNS['ipv4'], text)
        ipv6 = re.findall(StringUtils.PATTERNS['ipv6'], text)
        return ipv4 + ipv6
    
    @staticmethod
    def extract_html_tags(text: str) -> List[str]:
        """提取HTML标签
        
        Args:
            text: 文本
            
        Returns:
            HTML标签列表
        """
        return re.findall(StringUtils.PATTERNS['html_tag'], text)
    
    @staticmethod
    def word_count(text: str) -> int:
        """统计单词数
        
        Args:
            text: 文本
            
        Returns:
            单词数量
        """
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    @staticmethod
    def char_count(text: str, include_spaces: bool = True) -> int:
        """统计字符数
        
        Args:
            text: 文本
            include_spaces: 是否包含空格
            
        Returns:
            字符数量
        """
        if include_spaces:
            return len(text)
        else:
            return len(text.replace(' ', ''))
    
    @staticmethod
    def line_count(text: str) -> int:
        """统计行数
        
        Args:
            text: 文本
            
        Returns:
            行数
        """
        return len(text.splitlines())
    
    @staticmethod
    def sentence_count(text: str) -> int:
        """统计句子数
        
        Args:
            text: 文本
            
        Returns:
            句子数
        """
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])
    
    @staticmethod
    def word_frequency(text: str) -> Dict[str, int]:
        """统计词频
        
        Args:
            text: 文本
            
        Returns:
            词频字典
        """
        words = re.findall(r'\b\w+\b', text.lower())
        freq = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
        return freq
    
    @staticmethod
    def most_common_words(text: str, n: int = 10) -> List[Tuple[str, int]]:
        """获取最常见的单词
        
        Args:
            text: 文本
            n: 返回数量
            
        Returns:
            (单词, 次数)列表
        """
        from collections import Counter
        words = re.findall(r'\b\w+\b', text.lower())
        return Counter(words).most_common(n)
    
    @staticmethod
    def remove_duplicate_lines(text: str, keep_order: bool = True) -> str:
        """移除重复行
        
        Args:
            text: 文本
            keep_order: 是否保持顺序
            
        Returns:
            处理后的文本
        """
        lines = text.splitlines()
        if keep_order:
            seen = set()
            result = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    result.append(line)
        else:
            result = list(set(lines))
        
        return '\n'.join(result)
    
    @staticmethod
    def remove_empty_lines(text: str) -> str:
        """移除空行
        
        Args:
            text: 文本
            
        Returns:
            处理后的文本
        """
        lines = [line for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)
    
    @staticmethod
    def add_line_numbers(text: str, start: int = 1, format: str = '{:4d} ') -> str:
        """添加行号
        
        Args:
            text: 文本
            start: 起始行号
            format: 行号格式
            
        Returns:
            带行号的文本
        """
        lines = text.splitlines()
        numbered = []
        for i, line in enumerate(lines, start):
            numbered.append(format.format(i) + line)
        return '\n'.join(numbered)
    
    @staticmethod
    def wrap_lines(text: str, width: int = 80, indent: str = '') -> str:
        """自动换行
        
        Args:
            text: 文本
            width: 每行最大宽度
            indent: 缩进
            
        Returns:
            换行后的文本
        """
        lines = text.splitlines()
        wrapped = []
        for line in lines:
            wrapped.extend(textwrap.wrap(line, width=width, initial_indent=indent, subsequent_indent=indent))
        return '\n'.join(wrapped)
    
    @staticmethod
    def center_text(text: str, width: int, fill_char: str = ' ') -> str:
        """文本居中
        
        Args:
            text: 文本
            width: 总宽度
            fill_char: 填充字符
            
        Returns:
            居中后的文本
        """
        return text.center(width, fill_char)
    
    @staticmethod
    def align_left(text: str, width: int, fill_char: str = ' ') -> str:
        """左对齐
        
        Args:
            text: 文本
            width: 总宽度
            fill_char: 填充字符
            
        Returns:
            左对齐的文本
        """
        return text.ljust(width, fill_char)
    
    @staticmethod
    def align_right(text: str, width: int, fill_char: str = ' ') -> str:
        """右对齐
        
        Args:
            text: 文本
            width: 总宽度
            fill_char: 填充字符
            
        Returns:
            右对齐的文本
        """
        return text.rjust(width, fill_char)


def generate_random_string(length: int = 8, 
                          chars: str = string.ascii_letters + string.digits) -> str:
    """生成随机字符串
    
    Args:
        length: 字符串长度
        chars: 字符集
        
    Returns:
        随机字符串
    """
    return ''.join(random.choice(chars) for _ in range(length))


def generate_uuid4() -> str:
    """生成UUID v4
    
    Returns:
        UUID字符串
    """
    import uuid
    return str(uuid.uuid4())


def generate_random_hex(length: int) -> str:
    """生成随机十六进制字符串
    
    Args:
        length: 长度
        
    Returns:
        随机十六进制字符串
    """
    return generate_random_string(length, '0123456789abcdef')


def generate_random_digits(length: int) -> str:
    """生成随机数字字符串
    
    Args:
        length: 长度
        
    Returns:
        随机数字字符串
    """
    return generate_random_string(length, string.digits)


def highlight(text: str, keyword: str, 
             before: str = '**', after: str = '**',
             case_sensitive: bool = False) -> str:
    """高亮显示关键词
    
    Args:
        text: 原始文本
        keyword: 关键词
        before: 高亮前缀
        after: 高亮后缀
        case_sensitive: 是否区分大小写
        
    Returns:
        高亮后的文本
    """
    if not keyword:
        return text
    
    if case_sensitive:
        return text.replace(keyword, f"{before}{keyword}{after}")
    else:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        return pattern.sub(lambda m: f"{before}{m.group(0)}{after}", text)


def pluralize(word: str, count: int, plural_form: Optional[str] = None) -> str:
    """根据数量返回单复数形式
    
    Args:
        word: 单词
        count: 数量
        plural_form: 复数形式，None则自动转换
        
    Returns:
        单复数形式的单词
    """
    if count == 1:
        return word
    
    if plural_form:
        return plural_form
    
    # 简单复数规则
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    elif word.endswith('y') and word[-2] not in 'aeiou':
        return word[:-1] + 'ies'
    else:
        return word + 's'


def abbreviate(text: str, max_length: int = 3) -> str:
    """生成缩写
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        缩写
    """
    words = text.split()
    if len(words) == 1:
        return text[:max_length].upper()
    
    # 取每个单词的首字母
    abbr = ''.join(word[0] for word in words if word)
    return abbr[:max_length].upper()


def initials(name: str, max_chars: int = 2) -> str:
    """获取姓名首字母
    
    Args:
        name: 姓名
        max_chars: 最大字符数
        
    Returns:
        首字母
    """
    parts = name.split()
    initials = ''.join(part[0].upper() for part in parts if part)
    return initials[:max_chars]