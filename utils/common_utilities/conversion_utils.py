"""
转换工具模块

提供各种数据类型转换的实用工具函数。
"""

from typing import Any, Union, Dict, List, Optional, Callable
import json
import base64
import pickle
import csv
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlencode, parse_qs


class ConversionUtils:
    """转换工具类"""
    
    @staticmethod
    def to_string(value: Any) -> str:
        """转换为字符串
        
        Args:
            value: 要转换的值
            
        Returns:
            字符串表示
        """
        if value is None:
            return ""
        return str(value)
    
    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        """转换为整数
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            整数
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        """转换为浮点数
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            浮点数
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_bool(value: Any, default: bool = False) -> bool:
        """转换为布尔值
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            布尔值
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'y')
        try:
            return bool(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_list(value: Any, default: List = None) -> List:
        """转换为列表
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            列表
        """
        if default is None:
            default = []
        
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str):
            return value.split(',')
        try:
            return list(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def to_dict(value: Any, default: Dict = None) -> Dict:
        """转换为字典
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            字典
        """
        if default is None:
            default = {}
        
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        try:
            return dict(value)
        except (TypeError, ValueError):
            return default


class EncodingConversion:
    """编码转换类"""
    
    @staticmethod
    def to_base64(data: Union[str, bytes]) -> str:
        """转换为Base64编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base64编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def from_base64(encoded_data: str) -> bytes:
        """从Base64解码
        
        Args:
            encoded_data: Base64编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b64decode(encoded_data.encode('ascii'))
    
    @staticmethod
    def to_url_encoding(text: str) -> str:
        """URL编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            URL编码字符串
        """
        return quote(text)
    
    @staticmethod
    def from_url_encoding(encoded_text: str) -> str:
        """URL解码
        
        Args:
            encoded_text: URL编码字符串
            
        Returns:
            解码后的文本
        """
        return unquote(encoded_text)
    
    @staticmethod
    def to_hex(data: Union[str, bytes]) -> str:
        """转换为十六进制
        
        Args:
            data: 要转换的数据
            
        Returns:
            十六进制字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data.hex()
    
    @staticmethod
    def from_hex(hex_string: str) -> bytes:
        """从十六进制转换
        
        Args:
            hex_string: 十六进制字符串
            
        Returns:
            字节数据
        """
        return bytes.fromhex(hex_string)


class DataFormatConversion:
    """数据格式转换类"""
    
    @staticmethod
    def csv_to_dict_list(csv_content: str) -> List[Dict]:
        """CSV转换为字典列表
        
        Args:
            csv_content: CSV内容
            
        Returns:
            字典列表
        """
        lines = csv_content.strip().split('\n')
        if not lines:
            return []
        
        reader = csv.DictReader(lines)
        return list(reader)
    
    @staticmethod
    def dict_list_to_csv(data: List[Dict]) -> str:
        """字典列表转换为CSV
        
        Args:
            data: 字典列表
            
        Returns:
            CSV字符串
        """
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    @staticmethod
    def xml_to_dict(xml_content: str) -> Dict:
        """XML转换为字典
        
        Args:
            xml_content: XML内容
            
        Returns:
            字典表示
        """
        try:
            root = ET.fromstring(xml_content)
            return ConversionUtils._xml_to_dict(root)
        except ET.ParseError:
            return {}
    
    @staticmethod
    def dict_to_xml(data: Dict, root_tag: str = 'root') -> str:
        """字典转换为XML
        
        Args:
            data: 字典数据
            root_tag: 根标签名
            
        Returns:
            XML字符串
        """
        root = ET.Element(root_tag)
        ConversionUtils._dict_to_xml(root, data)
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def _xml_to_dict(element) -> Dict:
        """内部方法：将XML元素转换为字典"""
        result = {}
        
        # 处理属性
        if element.attrib:
            result['@attributes'] = element.attrib
        
        # 处理文本内容
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            result['#text'] = element.text.strip()
        
        # 处理子元素
        for child in element:
            child_data = ConversionUtils._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    @staticmethod
    def _dict_to_xml(element, data: Dict) -> None:
        """内部方法：将字典转换为XML元素"""
        for key, value in data.items():
            if key == '@attributes':
                element.attrib.update(value)
            elif key == '#text':
                element.text = str(value)
            elif isinstance(value, list):
                for item in value:
                    sub_element = ET.SubElement(element, key)
                    ConversionUtils._dict_to_xml(sub_element, item)
            elif isinstance(value, dict):
                sub_element = ET.SubElement(element, key)
                ConversionUtils._dict_to_xml(sub_element, value)
            else:
                sub_element = ET.SubElement(element, key)
                sub_element.text = str(value)


class SerializationUtils:
    """序列化工具类"""
    
    @staticmethod
    def to_pickle(data: Any) -> bytes:
        """使用pickle序列化
        
        Args:
            data: 要序列化的数据
            
        Returns:
            序列化后的字节数据
        """
        return pickle.dumps(data)
    
    @staticmethod
    def from_pickle(pickled_data: bytes) -> Any:
        """使用pickle反序列化
        
        Args:
            pickled_data: 序列化数据
            
        Returns:
            反序列化后的对象
        """
        return pickle.loads(pickled_data)
    
    @staticmethod
    def to_json(data: Any, indent: int = None) -> str:
        """转换为JSON字符串
        
        Args:
            data: 要转换的数据
            indent: 缩进空格数
            
        Returns:
            JSON字符串
        """
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def from_json(json_string: str) -> Any:
        """从JSON字符串解析
        
        Args:
            json_string: JSON字符串
            
        Returns:
            解析后的对象
        """
        return json.loads(json_string)


def convert_value(value: Any, target_type: type, 
                 default: Any = None, **kwargs) -> Any:
    """通用值转换函数
    
    Args:
        value: 要转换的值
        target_type: 目标类型
        default: 默认值
        **kwargs: 转换函数的额外参数
        
    Returns:
        转换后的值
    """
    type_converters = {
        str: ConversionUtils.to_string,
        int: ConversionUtils.to_int,
        float: ConversionUtils.to_float,
        bool: ConversionUtils.to_bool,
        list: ConversionUtils.to_list,
        dict: ConversionUtils.to_dict
    }
    
    converter = type_converters.get(target_type)
    if converter:
        return converter(value, default, **kwargs)
    
    try:
        return target_type(value, **kwargs)
    except (ValueError, TypeError):
        return default


def safe_convert(value: Any, target_type: type, 
                converter: Callable = None, **kwargs) -> tuple:
    """安全转换值
    
    Args:
        value: 要转换的值
        target_type: 目标类型
        converter: 自定义转换函数
        **kwargs: 转换函数的额外参数
        
    Returns:
        (成功标志, 转换结果)
    """
    try:
        if converter:
            result = converter(value, **kwargs)
        else:
            result = convert_value(value, target_type, **kwargs)
        return True, result
    except Exception as e:
        return False, str(e)