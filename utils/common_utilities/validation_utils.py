"""
验证工具模块

提供各种数据验证的实用工具函数，包括类型验证、格式验证、业务规则验证等。
"""

import re
import ipaddress
import json
import hashlib
from typing import Any, List, Dict, Optional, Union, Callable, Pattern, Set, Tuple
from datetime import datetime, date, time
from urllib.parse import urlparse
import inspect


class ValidationUtils:
    """通用验证工具类"""
    
    # 常用正则表达式模式
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'chinese_phone': r'^1[3-9]\d{9}$',
        'phone': r'^\+?[\d\s\-\(\)]{7,}$',
        'url': r'^https?://[^\s/$.?#].[^\s]*$',
        'ipv4': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        'ipv6': r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        'mac': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        'chinese_id': r'^[1-9]\d{5}(18|19|20)?\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$',
        'chinese': r'[\u4e00-\u9fff]',
        'username': r'^[a-zA-Z0-9_]{3,20}$',
        'password': r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'",.<>/?]{6,}$',
        'strong_password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'uuid4': r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        'hex_color': r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        'postal_code_cn': r'^[1-9]\d{5}$',
        'postal_code_us': r'^\d{5}(-\d{4})?$',
        'credit_card': r'^\d{4}-?\d{4}-?\d{4}-?\d{4}$',
        'date_ymd': r'^\d{4}-\d{2}-\d{2}$',
        'time': r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$',
        'datetime': r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',
        'domain': r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$',
        'semver': r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$',
        'html_tag': r'<[^>]+>',
        'base64': r'^[A-Za-z0-9+/]+=*$',
        'base64_url': r'^[A-Za-z0-9_-]+=*$',
        'md5': r'^[a-f0-9]{32}$',
        'sha1': r'^[a-f0-9]{40}$',
        'sha256': r'^[a-f0-9]{64}$',
    }
    
    @staticmethod
    def is_not_none(value: Any) -> bool:
        """检查值是否为None
        
        Args:
            value: 要检查的值
            
        Returns:
            是否不为None
        """
        return value is not None
    
    @staticmethod
    def is_none(value: Any) -> bool:
        """检查值是否为None
        
        Args:
            value: 要检查的值
            
        Returns:
            是否为None
        """
        return value is None
    
    @staticmethod
    def is_not_empty(value: Any) -> bool:
        """检查值是否非空
        
        Args:
            value: 要检查的值
            
        Returns:
            是否非空
        """
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) > 0
        return True
    
    @staticmethod
    def is_empty(value: Any) -> bool:
        """检查值是否为空
        
        Args:
            value: 要检查的值
            
        Returns:
            是否为空
        """
        return not ValidationUtils.is_not_empty(value)
    
    @staticmethod
    def is_type(value: Any, expected_type: Union[type, Tuple[type, ...]]) -> bool:
        """检查值的类型
        
        Args:
            value: 要检查的值
            expected_type: 期望的类型或类型元组
            
        Returns:
            类型是否匹配
        """
        return isinstance(value, expected_type)
    
    @staticmethod
    def is_in(value: Any, valid_values: Union[List, Set, Tuple]) -> bool:
        """检查值是否在有效值列表中
        
        Args:
            value: 要检查的值
            valid_values: 有效值列表
            
        Returns:
            是否在有效值列表中
        """
        return value in valid_values
    
    @staticmethod
    def is_not_in(value: Any, invalid_values: Union[List, Set, Tuple]) -> bool:
        """检查值是否不在无效值列表中
        
        Args:
            value: 要检查的值
            invalid_values: 无效值列表
            
        Returns:
            是否不在无效值列表中
        """
        return value not in invalid_values
    
    @staticmethod
    def is_between(value: Union[int, float], 
                  min_val: Optional[Union[int, float]] = None,
                  max_val: Optional[Union[int, float]] = None,
                  inclusive_min: bool = True,
                  inclusive_max: bool = True) -> bool:
        """检查值是否在指定范围内
        
        Args:
            value: 要检查的值
            min_val: 最小值
            max_val: 最大值
            inclusive_min: 是否包含最小值
            inclusive_max: 是否包含最大值
            
        Returns:
            是否在范围内
        """
        if min_val is not None:
            if inclusive_min and value < min_val:
                return False
            if not inclusive_min and value <= min_val:
                return False
        
        if max_val is not None:
            if inclusive_max and value > max_val:
                return False
            if not inclusive_max and value >= max_val:
                False
        
        return True
    
    @staticmethod
    def is_length_between(value: Union[str, List, Tuple, Dict, Set],
                         min_len: Optional[int] = None,
                         max_len: Optional[int] = None) -> bool:
        """检查长度是否在指定范围内
        
        Args:
            value: 要检查的值
            min_len: 最小长度
            max_len: 最大长度
            
        Returns:
            长度是否在范围内
        """
        length = len(value)
        
        if min_len is not None and length < min_len:
            return False
        if max_len is not None and length > max_len:
            return False
        
        return True
    
    @staticmethod
    def is_match_pattern(value: str, pattern: Union[str, Pattern]) -> bool:
        """检查字符串是否匹配正则表达式
        
        Args:
            value: 要检查的字符串
            pattern: 正则表达式模式或编译后的Pattern对象
            
        Returns:
            是否匹配
        """
        if isinstance(pattern, str):
            return bool(re.match(pattern, value))
        else:
            return bool(pattern.match(value))
    
    @staticmethod
    def is_email(email: str) -> bool:
        """验证邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否为有效邮箱
        """
        if not email or len(email) > 254:
            return False
        return bool(re.match(ValidationUtils.PATTERNS['email'], email))
    
    @staticmethod
    def is_phone(phone: str, country: str = 'CN') -> bool:
        """验证电话号码
        
        Args:
            phone: 电话号码
            country: 国家代码
            
        Returns:
            是否为有效电话号码
        """
        if country == 'CN':
            return bool(re.match(ValidationUtils.PATTERNS['chinese_phone'], phone))
        else:
            return bool(re.match(ValidationUtils.PATTERNS['phone'], phone))
    
    @staticmethod
    def is_url(url: str, require_http: bool = True) -> bool:
        """验证URL
        
        Args:
            url: URL地址
            require_http: 是否要求http/https协议
            
        Returns:
            是否为有效URL
        """
        try:
            result = urlparse(url)
            if require_http and result.scheme not in ('http', 'https'):
                return False
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def is_ip_address(ip: str) -> bool:
        """验证IP地址
        
        Args:
            ip: IP地址
            
        Returns:
            是否为有效IP地址
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_ipv4(ip: str) -> bool:
        """验证IPv4地址
        
        Args:
            ip: IPv4地址
            
        Returns:
            是否为有效IPv4地址
        """
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_ipv6(ip: str) -> bool:
        """验证IPv6地址
        
        Args:
            ip: IPv6地址
            
        Returns:
            是否为有效IPv6地址
        """
        try:
            ipaddress.IPv6Address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_mac_address(mac: str) -> bool:
        """验证MAC地址
        
        Args:
            mac: MAC地址
            
        Returns:
            是否为有效MAC地址
        """
        return bool(re.match(ValidationUtils.PATTERNS['mac'], mac))
    
    @staticmethod
    def is_domain(domain: str) -> bool:
        """验证域名
        
        Args:
            domain: 域名
            
        Returns:
            是否为有效域名
        """
        return bool(re.match(ValidationUtils.PATTERNS['domain'], domain))
    
    @staticmethod
    def is_credit_card(card_number: str, mask: bool = False) -> bool:
        """验证信用卡号（使用Luhn算法）
        
        Args:
            card_number: 信用卡号
            mask: 是否先移除格式字符（空格和连字符）
            
        Returns:
            是否为有效信用卡号
        """
        if mask:
            # 移除空格和连字符
            card_number = re.sub(r'[\s\-]', '', card_number)
        
        # 检查是否只包含数字
        if not card_number.isdigit():
            return False
        
        # Luhn算法
        total = 0
        reverse_digits = card_number[::-1]
        
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:  # 奇数位（从右数）
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
    
    @staticmethod
    def is_chinese_id(id_number: str) -> bool:
        """验证中国大陆身份证号
        
        Args:
            id_number: 身份证号
            
        Returns:
            是否为有效身份证号
        """
        # 基本格式检查
        if not re.match(ValidationUtils.PATTERNS['chinese_id'], id_number):
            return False
        
        # 校验码验证
        factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        
        if len(id_number) == 18:
            # 计算校验码
            total = 0
            for i in range(17):
                total += int(id_number[i]) * factors[i]
            
            check_index = total % 11
            expected_check = check_codes[check_index]
            
            # 验证校验码（支持大小写）
            return id_number[17].upper() == expected_check
        
        return True  # 15位身份证只做格式验证
    
    @staticmethod
    def is_chinese_phone(phone: str) -> bool:
        """验证中国大陆手机号
        
        Args:
            phone: 手机号
            
        Returns:
            是否为有效手机号
        """
        return bool(re.match(ValidationUtils.PATTERNS['chinese_phone'], phone))
    
    @staticmethod
    def is_chinese_postal_code(code: str) -> bool:
        """验证中国邮政编码
        
        Args:
            code: 邮政编码
            
        Returns:
            是否为有效邮政编码
        """
        return bool(re.match(ValidationUtils.PATTERNS['postal_code_cn'], code))
    
    @staticmethod
    def is_postal_code(code: str, country: str = 'CN') -> bool:
        """验证邮政编码
        
        Args:
            code: 邮政编码
            country: 国家代码
            
        Returns:
            是否为有效邮政编码
        """
        patterns = {
            'CN': ValidationUtils.PATTERNS['postal_code_cn'],
            'US': ValidationUtils.PATTERNS['postal_code_us'],
            'UK': r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$',
            'CA': r'^[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d$',
            'DE': r'^\d{5}$',
            'FR': r'^\d{5}$',
            'JP': r'^\d{3}-\d{4}$',
            'AU': r'^\d{4}$',
        }
        
        pattern = patterns.get(country.upper(), patterns['CN'])
        return bool(re.match(pattern, code))
    
    @staticmethod
    def is_strong_password(password: str, 
                          min_length: int = 8,
                          require_upper: bool = True,
                          require_lower: bool = True,
                          require_digit: bool = True,
                          require_special: bool = True) -> Tuple[bool, Dict[str, bool]]:
        """验证密码强度
        
        Args:
            password: 密码
            min_length: 最小长度
            require_upper: 是否需要大写字母
            require_lower: 是否需要小写字母
            require_digit: 是否需要数字
            require_special: 是否需要特殊字符
            
        Returns:
            (是否通过, 详细结果字典)
        """
        result = {
            'length_ok': len(password) >= min_length,
            'has_upper': bool(re.search(r'[A-Z]', password)),
            'has_lower': bool(re.search(r'[a-z]', password)),
            'has_digit': bool(re.search(r'\d', password)),
            'has_special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            'no_spaces': ' ' not in password,
            'no_chinese': not re.search(ValidationUtils.PATTERNS['chinese'], password)
        }
        
        # 检查是否满足所有要求
        passed = True
        if not result['length_ok']:
            passed = False
        if require_upper and not result['has_upper']:
            passed = False
        if require_lower and not result['has_lower']:
            passed = False
        if require_digit and not result['has_digit']:
            passed = False
        if require_special and not result['has_special']:
            passed = False
        if not result['no_spaces']:
            passed = False
        
        return passed, result
    
    @staticmethod
    def is_username(username: str, 
                   min_length: int = 3,
                   max_length: int = 20,
                   allow_underscore: bool = True,
                   allow_dot: bool = False,
                   allow_hyphen: bool = False) -> bool:
        """验证用户名
        
        Args:
            username: 用户名
            min_length: 最小长度
            max_length: 最大长度
            allow_underscore: 是否允许下划线
            allow_dot: 是否允许点
            allow_hyphen: 是否允许连字符
            
        Returns:
            是否为有效用户名
        """
        if not username or len(username) < min_length or len(username) > max_length:
            return False
        
        allowed_chars = r'a-zA-Z0-9'
        if allow_underscore:
            allowed_chars += '_'
        if allow_dot:
            allowed_chars += '\.'
        if allow_hyphen:
            allowed_chars += '\-'
        
        pattern = f'^[{allowed_chars}]+$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def is_hex_color(color: str) -> bool:
        """验证十六进制颜色值
        
        Args:
            color: 颜色值
            
        Returns:
            是否为有效十六进制颜色
        """
        return bool(re.match(ValidationUtils.PATTERNS['hex_color'], color))
    
    @staticmethod
    def is_uuid(uuid_string: str, version: Optional[int] = None) -> bool:
        """验证UUID
        
        Args:
            uuid_string: UUID字符串
            version: UUID版本（4或其他）
            
        Returns:
            是否为有效UUID
        """
        if version == 4:
            return bool(re.match(ValidationUtils.PATTERNS['uuid4'], uuid_string))
        else:
            return bool(re.match(ValidationUtils.PATTERNS['uuid'], uuid_string))
    
    @staticmethod
    def is_json(json_string: str) -> bool:
        """验证JSON格式
        
        Args:
            json_string: JSON字符串
            
        Returns:
            是否为有效JSON
        """
        try:
            json.loads(json_string)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    @staticmethod
    def is_date(date_string: str, format: Optional[str] = None) -> bool:
        """验证日期格式
        
        Args:
            date_string: 日期字符串
            format: 日期格式，None则自动检测
            
        Returns:
            是否为有效日期
        """
        if format:
            try:
                datetime.strptime(date_string, format)
                return True
            except ValueError:
                return False
        else:
            # 自动检测常见格式
            formats = [
                '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y',
                '%Y.%m.%d', '%m/%d/%Y', '%d.%m.%Y', '%Y%m%d'
            ]
            for fmt in formats:
                try:
                    datetime.strptime(date_string, fmt)
                    return True
                except ValueError:
                    continue
            return False
    
    @staticmethod
    def is_datetime(datetime_string: str, format: Optional[str] = None) -> bool:
        """验证日期时间格式
        
        Args:
            datetime_string: 日期时间字符串
            format: 日期时间格式，None则自动检测
            
        Returns:
            是否为有效日期时间
        """
        if format:
            try:
                datetime.strptime(datetime_string, format)
                return True
            except ValueError:
                return False
        else:
            # 自动检测常见格式
            formats = [
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M',
                '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ'
            ]
            for fmt in formats:
                try:
                    datetime.strptime(datetime_string, fmt)
                    return True
                except ValueError:
                    continue
            return False
    
    @staticmethod
    def is_time(time_string: str) -> bool:
        """验证时间格式
        
        Args:
            time_string: 时间字符串
            
        Returns:
            是否为有效时间
        """
        try:
            time.fromisoformat(time_string)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_base64(base64_string: str, urlsafe: bool = False) -> bool:
        """验证Base64格式
        
        Args:
            base64_string: Base64字符串
            urlsafe: 是否为URL安全的Base64
            
        Returns:
            是否为有效Base64
        """
        pattern = ValidationUtils.PATTERNS['base64_url'] if urlsafe else ValidationUtils.PATTERNS['base64']
        return bool(re.match(pattern, base64_string))
    
    @staticmethod
    def is_hash(hash_string: str, algorithm: str = 'md5') -> bool:
        """验证哈希值
        
        Args:
            hash_string: 哈希字符串
            algorithm: 哈希算法
            
        Returns:
            是否为有效哈希
        """
        patterns = {
            'md5': ValidationUtils.PATTERNS['md5'],
            'sha1': ValidationUtils.PATTERNS['sha1'],
            'sha256': ValidationUtils.PATTERNS['sha256'],
        }
        
        pattern = patterns.get(algorithm.lower())
        if not pattern:
            return False
        
        return bool(re.match(pattern, hash_string))
    
    @staticmethod
    def is_semver(version: str) -> bool:
        """验证语义化版本号
        
        Args:
            version: 版本号字符串
            
        Returns:
            是否为有效语义化版本
        """
        return bool(re.match(ValidationUtils.PATTERNS['semver'], version))
    
    @staticmethod
    def is_html(html_string: str) -> bool:
        """验证是否包含HTML标签
        
        Args:
            html_string: HTML字符串
            
        Returns:
            是否包含HTML标签
        """
        return bool(re.search(ValidationUtils.PATTERNS['html_tag'], html_string))
    
    @staticmethod
    def is_chinese(text: str) -> bool:
        """检查是否包含中文字符
        
        Args:
            text: 文本
            
        Returns:
            是否包含中文
        """
        return bool(re.search(ValidationUtils.PATTERNS['chinese'], text))
    
    @staticmethod
    def is_all_chinese(text: str) -> bool:
        """检查是否全部为中文字符
        
        Args:
            text: 文本
            
        Returns:
            是否全部为中文
        """
        return all('\u4e00' <= char <= '\u9fff' for char in text if char.strip())


class DataValidationUtils:
    """数据验证工具类"""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> Dict[str, List[str]]:
        """验证必填字段
        
        Args:
            data: 数据字典
            required_fields: 必填字段列表
            
        Returns:
            验证结果，包含缺失字段
        """
        missing = []
        present = []
        
        for field in required_fields:
            if field not in data or ValidationUtils.is_empty(data.get(field)):
                missing.append(field)
            else:
                present.append(field)
        
        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'present': present
        }
    
    @staticmethod
    def validate_field_types(data: Dict, field_types: Dict[str, Union[type, Tuple[type, ...]]]) -> Dict:
        """验证字段类型
        
        Args:
            data: 数据字典
            field_types: 字段类型字典 {字段名: 期望类型或类型元组}
            
        Returns:
            验证结果，包含类型错误的字段
        """
        errors = {}
        valid = True
        
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors[field] = {
                        'expected': str(expected_type),
                        'got': type(data[field]).__name__
                    }
                    valid = False
        
        return {
            'valid': valid,
            'errors': errors
        }
    
    @staticmethod
    def validate_field_ranges(data: Dict, field_ranges: Dict[str, Dict]) -> Dict:
        """验证字段范围
        
        Args:
            data: 数据字典
            field_ranges: 字段范围字典 {字段名: {'min': 最小值, 'max': 最大值, 'inclusive_min': True, 'inclusive_max': True}}
            
        Returns:
            验证结果，包含超出范围的字段
        """
        errors = {}
        valid = True
        
        for field, config in field_ranges.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (int, float)):
                    continue
                
                min_val = config.get('min')
                max_val = config.get('max')
                inclusive_min = config.get('inclusive_min', True)
                inclusive_max = config.get('inclusive_max', True)
                
                if min_val is not None:
                    if inclusive_min and value < min_val:
                        errors[field] = f"value {value} is less than minimum {min_val}"
                        valid = False
                    elif not inclusive_min and value <= min_val:
                        errors[field] = f"value {value} is less than or equal to minimum {min_val}"
                        valid = False
                
                if max_val is not None and valid:
                    if inclusive_max and value > max_val:
                        errors[field] = f"value {value} is greater than maximum {max_val}"
                        valid = False
                    elif not inclusive_max and value >= max_val:
                        errors[field] = f"value {value} is greater than or equal to maximum {max_val}"
                        valid = False
        
        return {
            'valid': valid,
            'errors': errors
        }
    
    @staticmethod
    def validate_field_lengths(data: Dict, field_lengths: Dict[str, Dict]) -> Dict:
        """验证字段长度
        
        Args:
            data: 数据字典
            field_lengths: 字段长度字典 {字段名: {'min': 最小长度, 'max': 最大长度}}
            
        Returns:
            验证结果，包含长度错误的字段
        """
        errors = {}
        valid = True
        
        for field, config in field_lengths.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not hasattr(value, '__len__'):
                    continue
                
                length = len(value)
                min_len = config.get('min')
                max_len = config.get('max')
                
                if min_len is not None and length < min_len:
                    errors[field] = f"length {length} is less than minimum {min_len}"
                    valid = False
                elif max_len is not None and length > max_len:
                    errors[field] = f"length {length} is greater than maximum {max_len}"
                    valid = False
        
        return {
            'valid': valid,
            'errors': errors
        }
    
    @staticmethod
    def validate_with_patterns(data: Dict, patterns: Dict[str, Union[str, Pattern]]) -> Dict:
        """使用正则表达式验证字段
        
        Args:
            data: 数据字典
            patterns: 正则表达式字典 {字段名: 模式}
            
        Returns:
            验证结果，包含不匹配的字段
        """
        errors = {}
        valid = True
        
        for field, pattern in patterns.items():
            if field in data and data[field] is not None:
                value = str(data[field])
                if not ValidationUtils.is_match_pattern(value, pattern):
                    errors[field] = f"value '{value}' does not match required pattern"
                    valid = False
        
        return {
            'valid': valid,
            'errors': errors
        }
    
    @staticmethod
    def validate_with_custom_rules(data: Dict, rules: Dict[str, Callable]) -> Dict:
        """使用自定义规则验证
        
        Args:
            data: 数据字典
            rules: 验证规则字典 {字段名: 验证函数}
            
        Returns:
            验证结果，包含验证错误的字段
        """
        errors = {}
        valid = True
        
        for field, rule in rules.items():
            if field in data:
                try:
                    result = rule(data[field])
                    if isinstance(result, bool):
                        if not result:
                            errors[field] = f"custom validation failed"
                            valid = False
                    elif isinstance(result, str):
                        errors[field] = result
                        valid = False
                except Exception as e:
                    errors[field] = str(e)
                    valid = False
        
        return {
            'valid': valid,
            'errors': errors
        }
    
    @staticmethod
    def validate_data(data: Dict, validation_schema: Dict) -> Dict:
        """综合验证数据
        
        Args:
            data: 要验证的数据
            validation_schema: 验证模式字典，包含各种验证规则
            
        Returns:
            完整的验证结果
        """
        result = {
            'valid': True,
            'errors': {},
            'warnings': {},
            'details': {}
        }
        
        # 验证必填字段
        if 'required' in validation_schema:
            required_result = DataValidationUtils.validate_required_fields(
                data, validation_schema['required']
            )
            if not required_result['valid']:
                result['valid'] = False
                result['errors']['required'] = required_result['missing']
        
        # 验证字段类型
        if 'types' in validation_schema:
            type_result = DataValidationUtils.validate_field_types(
                data, validation_schema['types']
            )
            if not type_result['valid']:
                result['valid'] = False
                result['errors']['types'] = type_result['errors']
        
        # 验证字段范围
        if 'ranges' in validation_schema:
            range_result = DataValidationUtils.validate_field_ranges(
                data, validation_schema['ranges']
            )
            if not range_result['valid']:
                result['valid'] = False
                result['errors']['ranges'] = range_result['errors']
        
        # 验证字段长度
        if 'lengths' in validation_schema:
            length_result = DataValidationUtils.validate_field_lengths(
                data, validation_schema['lengths']
            )
            if not length_result['valid']:
                result['valid'] = False
                result['errors']['lengths'] = length_result['errors']
        
        # 验证正则表达式
        if 'patterns' in validation_schema:
            pattern_result = DataValidationUtils.validate_with_patterns(
                data, validation_schema['patterns']
            )
            if not pattern_result['valid']:
                result['valid'] = False
                result['errors']['patterns'] = pattern_result['errors']
        
        # 自定义验证规则
        if 'custom' in validation_schema:
            custom_result = DataValidationUtils.validate_with_custom_rules(
                data, validation_schema['custom']
            )
            if not custom_result['valid']:
                result['valid'] = False
                result['errors']['custom'] = custom_result['errors']
        
        return result


class BusinessValidationUtils:
    """业务验证工具类"""
    
    @staticmethod
    def is_valid_age(birth_date: Union[date, datetime, str], 
                    min_age: int = 0, 
                    max_age: int = 150,
                    reference_date: Optional[Union[date, datetime]] = None) -> bool:
        """验证年龄是否在有效范围内
        
        Args:
            birth_date: 出生日期
            min_age: 最小年龄
            max_age: 最大年龄
            reference_date: 参考日期，默认当前日期
            
        Returns:
            年龄是否有效
        """
        from .date_utils import DateTimeUtils
        
        if isinstance(birth_date, str):
            birth_date = DateTimeUtils.parse_date(birth_date)
        
        if reference_date is None:
            reference_date = DateTimeUtils.today()
        
        if not birth_date:
            return False
        
        age = DateTimeUtils.get_age(birth_date, reference_date)
        return min_age <= age['years'] <= max_age
    
    @staticmethod
    def is_valid_id_card_with_name(id_number: str, name: str) -> bool:
        """验证身份证号和姓名是否匹配（简单校验）
        
        Args:
            id_number: 身份证号
            name: 姓名
            
        Returns:
            是否可能匹配
        """
        if not ValidationUtils.is_chinese_id(id_number):
            return False
        
        # 检查姓名长度（中国姓名通常2-4个汉字）
        if not name or len(name) < 2 or len(name) > 4:
            return False
        
        # 检查姓名是否包含非法字符
        if not all('\u4e00' <= char <= '\u9fff' for char in name if char.strip()):
            return False
        
        return True
    
    @staticmethod
    def is_valid_business_hours(hour: int, minute: int = 0,
                               start_hour: int = 9, end_hour: int = 18) -> bool:
        """验证是否在营业时间内
        
        Args:
            hour: 小时
            minute: 分钟
            start_hour: 开始小时
            end_hour: 结束小时
            
        Returns:
            是否在营业时间内
        """
        if hour < start_hour or hour > end_hour:
            return False
        if hour == end_hour and minute > 0:
            return False
        return True


class SanitizationUtils:
    """数据清理消毒工具类"""
    
    @staticmethod
    def sanitize_string(text: str, 
                       max_length: Optional[int] = None,
                       allowed_chars: Optional[str] = None,
                       strip_html: bool = True,
                       strip_whitespace: bool = True) -> str:
        """清理字符串
        
        Args:
            text: 原始字符串
            max_length: 最大长度
            allowed_chars: 允许的字符集
            strip_html: 是否移除HTML标签
            strip_whitespace: 是否移除多余空白
            
        Returns:
            清理后的字符串
        """
        if text is None:
            return ""
        
        text = str(text)
        
        if strip_html:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', '', text)
        
        if strip_whitespace:
            # 标准化空白字符
            text = ' '.join(text.split())
        
        if allowed_chars:
            # 只保留允许的字符
            text = ''.join(char for char in text if char in allowed_chars)
        
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """清理邮箱地址
        
        Args:
            email: 原始邮箱
            
        Returns:
            清理后的邮箱
        """
        email = SanitizationUtils.sanitize_string(
            email, 
            strip_html=True, 
            strip_whitespace=True
        )
        
        # 转换为小写
        email = email.lower()
        
        # 移除多余的点号（Gmail风格）
        local_part, domain = email.split('@') if '@' in email else (email, '')
        local_part = re.sub(r'\.+', '.', local_part)
        
        return f"{local_part}@{domain}" if domain else local_part
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """清理电话号码
        
        Args:
            phone: 原始电话号码
            
        Returns:
            清理后的电话号码
        """
        # 只保留数字和加号
        return re.sub(r'[^\d+]', '', phone)
    
    @staticmethod
    def sanitize_html(html_text: str, allow_tags: Optional[List[str]] = None) -> str:
        """清理HTML，移除危险标签
        
        Args:
            html_text: HTML文本
            allow_tags: 允许保留的标签列表
            
        Returns:
            清理后的HTML
        """
        if allow_tags is None:
            allow_tags = ['p', 'br', 'b', 'i', 'u', 'strong', 'em']
        
        # 移除危险标签及其内容
        dangerous_tags = ['script', 'object', 'embed', 'iframe', 'frame', 
                         'frameset', 'noframes', 'style', 'link']
        
        for tag in dangerous_tags:
            # 移除标签及其内容
            html_text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html_text, flags=re.IGNORECASE | re.DOTALL)
            # 移除自闭合标签
            html_text = re.sub(f'<{tag}[^>]*/?>', '', html_text, flags=re.IGNORECASE)
        
        # 只允许指定的标签
        if allow_tags:
            # 构建允许标签的正则
            allowed_pattern = '|'.join(allow_tags)
            # 保留允许的标签，移除其他标签
            html_text = re.sub(f'<(?!\/?({allowed_pattern})\s*\/?)[^>]+>', '', html_text)
        
        return html_text
    
    @staticmethod
    def sanitize_filename(filename: str, replacement: str = '_') -> str:
        """清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            replacement: 非法字符的替换字符
            
        Returns:
            清理后的文件名
        """
        # Windows/Linux/MacOS 文件名非法字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        clean_name = re.sub(illegal_chars, replacement, filename)
        
        # 移除前导和尾随的点号和空格
        clean_name = clean_name.strip('. ')
        
        # 确保文件名不为空
        if not clean_name:
            clean_name = f"file{replacement}name"
        
        return clean_name
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """清理路径，防止路径遍历攻击
        
        Args:
            path: 原始路径
            
        Returns:
            清理后的路径
        """
        # 规范化路径
        import os
        normalized = os.path.normpath(path)
        
        # 移除路径遍历尝试
        normalized = normalized.replace('..', '')
        
        # 移除前导斜杠
        return normalized.lstrip('/\\')


def validate_and_clean(data: Dict, rules: Dict) -> Tuple[bool, Dict, List[str]]:
    """验证并清理数据
    
    Args:
        data: 原始数据
        rules: 验证和清理规则
        
    Returns:
        (是否通过, 清理后的数据, 错误列表)
    """
    cleaned = {}
    errors = []
    
    for field, rule in rules.items():
        value = data.get(field)
        
        # 必填检查
        if rule.get('required', False) and ValidationUtils.is_empty(value):
            errors.append(f"Field '{field}' is required")
            continue
        
        if value is None:
            if 'default' in rule:
                cleaned[field] = rule['default']
            continue
        
        # 类型转换
        if 'type' in rule:
            from .conversion_utils import convert_if_possible
            converted = convert_if_possible(value, rule['type'])
            if converted is None and value is not None:
                errors.append(f"Field '{field}' cannot be converted to {rule['type'].__name__}")
                continue
            value = converted
        
        # 验证
        if 'validate' in rule:
            validator = rule['validate']
            if callable(validator):
                try:
                    if not validator(value):
                        errors.append(f"Field '{field}' failed validation")
                        continue
                except Exception as e:
                    errors.append(f"Field '{field}' validation error: {str(e)}")
                    continue
        
        # 清理
        if 'sanitize' in rule:
            sanitizer = rule['sanitize']
            if callable(sanitizer):
                try:
                    value = sanitizer(value)
                except Exception as e:
                    errors.append(f"Field '{field}' sanitization error: {str(e)}")
                    continue
        
        cleaned[field] = value
    
    return len(errors) == 0, cleaned, errors