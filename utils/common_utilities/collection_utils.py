"""
转换工具模块

提供各种数据类型转换的实用工具函数，包括类型转换、编码转换、格式转换等。
"""

from typing import Any, Union, Dict, List, Optional, Callable, Tuple, Type
import json
import base64
import pickle
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from urllib.parse import quote, unquote, urlencode, parse_qs
import binascii
import html
import codecs
import ast
from datetime import datetime, date
import re


class ConversionUtils:
    """类型转换工具类"""
    
    @staticmethod
    def to_string(value: Any, default: str = '') -> str:
        """转换为字符串
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            字符串表示
        """
        if value is None:
            return default
        try:
            return str(value)
        except Exception:
            return default
    
    @staticmethod
    def to_int(value: Any, default: int = 0, base: int = 10) -> int:
        """转换为整数
        
        Args:
            value: 要转换的值
            default: 默认值
            base: 进制（10, 16, 8, 2等）
            
        Returns:
            整数
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, str):
                # 处理十六进制字符串（如 '0xff'）
                if value.startswith(('0x', '0X')):
                    return int(value, 16)
                # 处理二进制字符串（如 '0b1010'）
                elif value.startswith(('0b', '0B')):
                    return int(value, 2)
                # 处理八进制字符串（如 '0o77'）
                elif value.startswith(('0o', '0O')):
                    return int(value, 8)
            return int(value, base) if isinstance(value, str) else int(value)
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
    def to_bool(value: Any, default: bool = False, strict: bool = False) -> bool:
        """转换为布尔值
        
        Args:
            value: 要转换的值
            default: 默认值
            strict: 是否严格模式（只有明确的值才返回True）
            
        Returns:
            布尔值
        """
        if value is None:
            return default
        
        if strict:
            # 严格模式：只有 True/true/1/yes/on 才返回 True
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value == 1
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on', 'y')
            return default
        else:
            # 宽松模式：使用 Python 的 bool 转换规则
            try:
                return bool(value)
            except Exception:
                return default
    
    @staticmethod
    def to_list(value: Any, default: Optional[List] = None, split_str: bool = True) -> List:
        """转换为列表
        
        Args:
            value: 要转换的值
            default: 默认值
            split_str: 是否分割字符串（按逗号分割）
            
        Returns:
            列表
        """
        if default is None:
            default = []
        
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, tuple):
            return list(value)
        
        if isinstance(value, set):
            return list(value)
        
        if isinstance(value, str) and split_str:
            return [item.strip() for item in value.split(',') if item.strip()]
        
        try:
            return list(value)
        except (TypeError, ValueError):
            return [value]
    
    @staticmethod
    def to_tuple(value: Any, default: Optional[Tuple] = None) -> Tuple:
        """转换为元组
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            元组
        """
        if default is None:
            default = ()
        
        if value is None:
            return default
        
        if isinstance(value, tuple):
            return value
        
        if isinstance(value, list):
            return tuple(value)
        
        try:
            return tuple(value)
        except (TypeError, ValueError):
            return (value,)
    
    @staticmethod
    def to_set(value: Any, default: Optional[set] = None) -> set:
        """转换为集合
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            集合
        """
        if default is None:
            default = set()
        
        if value is None:
            return default
        
        if isinstance(value, set):
            return value
        
        try:
            return set(value)
        except (TypeError, ValueError):
            return {value}
    
    @staticmethod
    def to_dict(value: Any, default: Optional[Dict] = None) -> Dict:
        """转换为字典
        
        Args:
            value: 要转换的值
            default: 默认值
            
        Returns:
            字典
        """
        if default is None:
            default = {}
        
        if value is None:
            return default
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                # 尝试解析 JSON
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    # 尝试解析 Python 字典字符串
                    return ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return default
        
        try:
            return dict(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def to_bytes(value: Any, encoding: str = 'utf-8') -> bytes:
        """转换为字节
        
        Args:
            value: 要转换的值
            encoding: 编码
            
        Returns:
            字节数据
        """
        if value is None:
            return b''
        
        if isinstance(value, bytes):
            return value
        
        if isinstance(value, str):
            return value.encode(encoding)
        
        if isinstance(value, (int, float)):
            return str(value).encode(encoding)
        
        try:
            return bytes(value)
        except TypeError:
            return str(value).encode(encoding)
    
    @staticmethod
    def to_hex(value: Union[str, bytes, int], prefix: bool = False) -> str:
        """转换为十六进制字符串
        
        Args:
            value: 要转换的值
            prefix: 是否添加 0x 前缀
            
        Returns:
            十六进制字符串
        """
        if isinstance(value, str):
            value = value.encode('utf-8')
        
        if isinstance(value, bytes):
            hex_str = binascii.hexlify(value).decode('ascii')
        elif isinstance(value, int):
            hex_str = format(value, 'x')
        else:
            hex_str = ''
        
        if prefix and hex_str:
            return f"0x{hex_str}"
        return hex_str
    
    @staticmethod
    def from_hex(hex_string: str) -> bytes:
        """从十六进制字符串转换
        
        Args:
            hex_string: 十六进制字符串
            
        Returns:
            字节数据
        """
        hex_string = hex_string.replace('0x', '').replace('0X', '')
        return binascii.unhexlify(hex_string)
    
    @staticmethod
    def to_binary(value: int, bits: int = 8, prefix: bool = False) -> str:
        """转换为二进制字符串
        
        Args:
            value: 整数值
            bits: 位数
            prefix: 是否添加 0b 前缀
            
        Returns:
            二进制字符串
        """
        if bits > 0:
            bin_str = format(value, f'0{bits}b')
        else:
            bin_str = bin(value)[2:]
        
        if prefix:
            return f"0b{bin_str}"
        return bin_str
    
    @staticmethod
    def from_binary(bin_string: str) -> int:
        """从二进制字符串转换
        
        Args:
            bin_string: 二进制字符串
            
        Returns:
            整数值
        """
        bin_string = bin_string.replace('0b', '').replace('0B', '')
        return int(bin_string, 2)
    
    @staticmethod
    def to_octal(value: int, prefix: bool = False) -> str:
        """转换为八进制字符串
        
        Args:
            value: 整数值
            prefix: 是否添加 0o 前缀
            
        Returns:
            八进制字符串
        """
        oct_str = oct(value)[2:]
        if prefix:
            return f"0o{oct_str}"
        return oct_str
    
    @staticmethod
    def from_octal(oct_string: str) -> int:
        """从八进制字符串转换
        
        Args:
            oct_string: 八进制字符串
            
        Returns:
            整数值
        """
        oct_string = oct_string.replace('0o', '').replace('0O', '')
        return int(oct_string, 8)
    
    @staticmethod
    def to_datetime(value: Any, format: str = None) -> Optional[datetime]:
        """转换为日期时间
        
        Args:
            value: 要转换的值
            format: 日期格式字符串
            
        Returns:
            日期时间对象
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        
        if isinstance(value, str):
            try:
                if format:
                    return datetime.strptime(value, format)
                else:
                    from dateutil import parser
                    return parser.parse(value)
            except (ValueError, ImportError):
                try:
                    # 常见格式尝试
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%Y-%m-%d',
                        '%Y/%m/%d %H:%M:%S',
                        '%Y/%m/%d %H:%M',
                        '%Y/%m/%d',
                        '%d/%m/%Y %H:%M:%S',
                        '%d/%m/%Y %H:%M',
                        '%d/%m/%Y'
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        return None
    
    @staticmethod
    def to_date(value: Any, format: str = None) -> Optional[date]:
        """转换为日期
        
        Args:
            value: 要转换的值
            format: 日期格式字符串
            
        Returns:
            日期对象
        """
        dt = ConversionUtils.to_datetime(value, format)
        return dt.date() if dt else None
    
    @staticmethod
    def to_timestamp(value: Any) -> Optional[float]:
        """转换为时间戳
        
        Args:
            value: 要转换的值
            
        Returns:
            时间戳
        """
        dt = ConversionUtils.to_datetime(value)
        return dt.timestamp() if dt else None
    
    @staticmethod
    def to_json(value: Any, ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
        """转换为JSON字符串
        
        Args:
            value: 要转换的值
            ensure_ascii: 是否确保ASCII
            indent: 缩进空格数
            
        Returns:
            JSON字符串
        """
        try:
            return json.dumps(value, ensure_ascii=ensure_ascii, indent=indent, default=str)
        except Exception:
            return ''
    
    @staticmethod
    def from_json(json_string: str, default: Any = None) -> Any:
        """从JSON字符串解析
        
        Args:
            json_string: JSON字符串
            default: 默认值
            
        Returns:
            解析后的对象
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return default
    
    @staticmethod
    def to_representation(value: Any, depth: int = 0) -> Any:
        """转换为可序列化表示
        
        Args:
            value: 要转换的值
            depth: 递归深度
            
        Returns:
            可序列化的表示
        """
        if depth > 100:  # 防止递归过深
            return str(value)
        
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        
        if isinstance(value, (list, tuple, set)):
            return [ConversionUtils.to_representation(item, depth + 1) for item in value]
        
        if isinstance(value, dict):
            return {str(k): ConversionUtils.to_representation(v, depth + 1) for k, v in value.items()}
        
        if hasattr(value, '__dict__'):
            return ConversionUtils.to_representation(value.__dict__, depth + 1)
        
        try:
            return str(value)
        except Exception:
            return None


class EncodingConversion:
    """编码转换类"""
    
    @staticmethod
    def to_base64(data: Union[str, bytes], urlsafe: bool = False) -> str:
        """转换为Base64编码
        
        Args:
            data: 要编码的数据
            urlsafe: 是否使用URL安全的Base64
            
        Returns:
            Base64编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if urlsafe:
            return base64.urlsafe_b64encode(data).decode('ascii')
        else:
            return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def from_base64(encoded_data: str, urlsafe: bool = False) -> bytes:
        """从Base64解码
        
        Args:
            encoded_data: Base64编码字符串
            urlsafe: 是否使用URL安全的Base64
            
        Returns:
            解码后的字节数据
        """
        if urlsafe:
            return base64.urlsafe_b64decode(encoded_data.encode('ascii'))
        else:
            return base64.b64decode(encoded_data.encode('ascii'))
    
    @staticmethod
    def to_base32(data: Union[str, bytes]) -> str:
        """转换为Base32编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base32编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b32encode(data).decode('ascii')
    
    @staticmethod
    def from_base32(encoded_data: str) -> bytes:
        """从Base32解码
        
        Args:
            encoded_data: Base32编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b32decode(encoded_data.encode('ascii'))
    
    @staticmethod
    def to_base85(data: Union[str, bytes]) -> str:
        """转换为Base85编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base85编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b85encode(data).decode('ascii')
    
    @staticmethod
    def from_base85(encoded_data: str) -> bytes:
        """从Base85解码
        
        Args:
            encoded_data: Base85编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b85decode(encoded_data.encode('ascii'))
    
    @staticmethod
    def to_url_encoding(text: str, encoding: str = 'utf-8') -> str:
        """URL编码
        
        Args:
            text: 要编码的文本
            encoding: 字符编码
            
        Returns:
            URL编码字符串
        """
        return quote(text, encoding=encoding)
    
    @staticmethod
    def from_url_encoding(encoded_text: str, encoding: str = 'utf-8') -> str:
        """URL解码
        
        Args:
            encoded_text: URL编码字符串
            encoding: 字符编码
            
        Returns:
            解码后的文本
        """
        return unquote(encoded_text, encoding=encoding)
    
    @staticmethod
    def to_url_params(params: Dict[str, Any], encoding: str = 'utf-8') -> str:
        """转换为URL参数
        
        Args:
            params: 参数字典
            encoding: 编码
            
        Returns:
            URL参数字符串
        """
        return urlencode(params, encoding=encoding)
    
    @staticmethod
    def from_url_params(query_string: str, encoding: str = 'utf-8') -> Dict[str, List[str]]:
        """从URL参数解析
        
        Args:
            query_string: URL查询字符串
            encoding: 编码
            
        Returns:
            参数字典
        """
        return parse_qs(query_string, encoding=encoding)
    
    @staticmethod
    def to_html_encoding(text: str) -> str:
        """HTML编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            HTML编码字符串
        """
        return html.escape(text, quote=True)
    
    @staticmethod
    def from_html_encoding(encoded_text: str) -> str:
        """HTML解码
        
        Args:
            encoded_text: HTML编码字符串
            
        Returns:
            解码后的文本
        """
        return html.unescape(encoded_text)
    
    @staticmethod
    def to_quoted_printable(data: Union[str, bytes]) -> str:
        """Quoted-Printable编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Quoted-Printable编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return codecs.encode(data, 'quopri').decode('ascii')
    
    @staticmethod
    def from_quoted_printable(encoded_data: str) -> bytes:
        """Quoted-Printable解码
        
        Args:
            encoded_data: Quoted-Printable编码字符串
            
        Returns:
            解码后的字节数据
        """
        return codecs.decode(encoded_data.encode('ascii'), 'quopri')
    
    @staticmethod
    def to_rot13(text: str) -> str:
        """ROT13编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            ROT13编码后的文本
        """
        return codecs.encode(text, 'rot_13')
    
    @staticmethod
    def from_rot13(encoded_text: str) -> str:
        """ROT13解码
        
        Args:
            encoded_text: ROT13编码文本
            
        Returns:
            解码后的文本
        """
        return codecs.decode(encoded_text, 'rot_13')
    
    @staticmethod
    def detect_encoding(data: Union[str, bytes]) -> Optional[str]:
        """检测字符编码
        
        Args:
            data: 要检测的数据
            
        Returns:
            检测到的编码名称，检测失败返回None
        """
        try:
            import chardet
            if isinstance(data, str):
                data = data.encode('utf-8')
            result = chardet.detect(data)
            return result.get('encoding')
        except ImportError:
            # 如果没有chardet库，尝试常见的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'ascii', 'latin1', 'cp1252', 'utf-16', 'utf-32']
            for encoding in encodings:
                try:
                    data.decode(encoding)
                    return encoding
                except (UnicodeDecodeError, LookupError):
                    continue
            return None


class DataFormatConversion:
    """数据格式转换类"""
    
    @staticmethod
    def csv_to_dict_list(csv_content: str, delimiter: str = ',', has_header: bool = True) -> List[Dict]:
        """CSV转换为字典列表
        
        Args:
            csv_content: CSV内容
            delimiter: 分隔符
            has_header: 是否有表头
            
        Returns:
            字典列表
        """
        lines = csv_content.strip().split('\n')
        if not lines:
            return []
        
        if has_header:
            reader = csv.DictReader(lines, delimiter=delimiter)
            return list(reader)
        else:
            # 无表头，使用列索引作为键
            data = []
            for line in lines:
                values = line.split(delimiter)
                row = {f"col{i}": val.strip() for i, val in enumerate(values)}
                data.append(row)
            return data
    
    @staticmethod
    def dict_list_to_csv(data: List[Dict], delimiter: str = ',', include_header: bool = True) -> str:
        """字典列表转换为CSV
        
        Args:
            data: 字典列表
            delimiter: 分隔符
            include_header: 是否包含表头
            
        Returns:
            CSV字符串
        """
        if not data:
            return ""
        
        import io
        output = io.StringIO()
        
        if include_header:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output, delimiter=delimiter)
            for row in data:
                writer.writerow(row.values())
        
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
            return DataFormatConversion._xml_element_to_dict(root)
        except ET.ParseError as e:
            print(f"XML解析错误: {e}")
            return {}
    
    @staticmethod
    def _xml_element_to_dict(element) -> Dict:
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
            child_data = DataFormatConversion._xml_element_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    @staticmethod
    def dict_to_xml(data: Dict, root_tag: str = 'root', pretty: bool = True) -> str:
        """字典转换为XML
        
        Args:
            data: 字典数据
            root_tag: 根标签名
            pretty: 是否美化输出
            
        Returns:
            XML字符串
        """
        root = ET.Element(root_tag)
        DataFormatConversion._dict_to_xml_element(root, data)
        
        if pretty:
            # 美化XML
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent='  ')
        else:
            return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def _dict_to_xml_element(parent, data: Dict):
        """内部方法：将字典转换为XML元素"""
        for key, value in data.items():
            if key == '@attributes' and isinstance(value, dict):
                parent.attrib.update({str(k): str(v) for k, v in value.items()})
            elif key == '#text':
                parent.text = str(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        child = ET.SubElement(parent, key)
                        DataFormatConversion._dict_to_xml_element(child, item)
                    else:
                        child = ET.SubElement(parent, key)
                        child.text = str(item)
            elif isinstance(value, dict):
                child = ET.SubElement(parent, key)
                DataFormatConversion._dict_to_xml_element(child, value)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)
    
    @staticmethod
    def json_to_xml(json_data: Union[str, Dict], root_tag: str = 'root') -> str:
        """JSON转换为XML
        
        Args:
            json_data: JSON数据（字符串或字典）
            root_tag: 根标签名
            
        Returns:
            XML字符串
        """
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        return DataFormatConversion.dict_to_xml(data, root_tag)
    
    @staticmethod
    def xml_to_json(xml_content: str, indent: int = 2) -> str:
        """XML转换为JSON
        
        Args:
            xml_content: XML内容
            indent: 缩进空格数
            
        Returns:
            JSON字符串
        """
        data = DataFormatConversion.xml_to_dict(xml_content)
        return json.dumps(data, ensure_ascii=False, indent=indent)
    
    @staticmethod
    def yaml_to_dict(yaml_content: str) -> Dict:
        """YAML转换为字典
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            字典
        """
        try:
            import yaml
            return yaml.safe_load(yaml_content)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")
        except Exception as e:
            print(f"YAML解析错误: {e}")
            return {}
    
    @staticmethod
    def dict_to_yaml(data: Dict, default_flow_style: bool = False) -> str:
        """字典转换为YAML
        
        Args:
            data: 字典数据
            default_flow_style: 是否使用流式风格
            
        Returns:
            YAML字符串
        """
        try:
            import yaml
            return yaml.dump(data, allow_unicode=True, default_flow_style=default_flow_style)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")
    
    @staticmethod
    def ini_to_dict(ini_content: str) -> Dict:
        """INI转换为字典
        
        Args:
            ini_content: INI内容
            
        Returns:
            字典
        """
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read_string(ini_content)
            
            result = {}
            for section in config.sections():
                result[section] = dict(config.items(section))
            
            return result
        except Exception as e:
            print(f"INI解析错误: {e}")
            return {}
    
    @staticmethod
    def dict_to_ini(data: Dict) -> str:
        """字典转换为INI
        
        Args:
            data: 字典数据
            
        Returns:
            INI字符串
        """
        try:
            import configparser
            config = configparser.ConfigParser()
            
            for section, values in data.items():
                if isinstance(values, dict):
                    config[section] = {str(k): str(v) for k, v in values.items()}
            
            import io
            output = io.StringIO()
            config.write(output)
            return output.getvalue()
        except Exception as e:
            print(f"INI转换错误: {e}")
            return ""


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
    def pickle_to_file(data: Any, file_path: str) -> bool:
        """将数据pickle到文件
        
        Args:
            data: 要序列化的数据
            file_path: 文件路径
            
        Returns:
            是否成功
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Pickle写入文件失败: {e}")
            return False
    
    @staticmethod
    def from_pickle_file(file_path: str) -> Any:
        """从文件读取pickle数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            反序列化后的对象
        """
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"从文件读取Pickle失败: {e}")
            return None


def safe_convert(value: Any, target_type: Type, 
                converter: Optional[Callable] = None,
                default: Any = None,
                **kwargs) -> Tuple[bool, Any]:
    """安全转换值（带错误处理）
    
    Args:
        value: 要转换的值
        target_type: 目标类型
        converter: 自定义转换函数
        default: 默认值
        **kwargs: 转换函数的额外参数
        
    Returns:
        (成功标志, 转换结果)
    """
    try:
        if converter:
            result = converter(value, **kwargs)
        else:
            # 使用内置转换
            if target_type == str:
                result = ConversionUtils.to_string(value, default)
            elif target_type == int:
                result = ConversionUtils.to_int(value, default, **kwargs)
            elif target_type == float:
                result = ConversionUtils.to_float(value, default)
            elif target_type == bool:
                result = ConversionUtils.to_bool(value, default, **kwargs)
            elif target_type == list:
                result = ConversionUtils.to_list(value, default, **kwargs)
            elif target_type == dict:
                result = ConversionUtils.to_dict(value, default)
            elif target_type == datetime:
                result = ConversionUtils.to_datetime(value, **kwargs)
            elif target_type == date:
                result = ConversionUtils.to_date(value, **kwargs)
            else:
                result = target_type(value)
        
        return True, result
    except Exception as e:
        return False, default if default is not None else str(e)


def convert_if_possible(value: Any, target_type: Type, default: Any = None) -> Any:
    """如果可能则转换，否则返回默认值
    
    Args:
        value: 要转换的值
        target_type: 目标类型
        default: 默认值
        
    Returns:
        转换后的值或默认值
    """
    success, result = safe_convert(value, target_type, default=default)
    return result if success else default


def safe_eval(expression: str, default: Any = None, 
             safe_globals: Optional[Dict] = None) -> Any:
    """安全执行表达式
    
    Args:
        expression: 表达式字符串
        default: 默认值
        safe_globals: 安全的全局变量
        
    Returns:
        表达式结果
    """
    try:
        # 限制可用的内置函数
        if safe_globals is None:
            safe_globals = {
                'abs': abs, 'all': all, 'any': any, 'bool': bool,
                'dict': dict, 'float': float, 'int': int, 'len': len,
                'list': list, 'max': max, 'min': min, 'set': set,
                'str': str, 'sum': sum, 'tuple': tuple
            }
        
        # 限制局部变量为空
        return eval(expression, {"__builtins__": safe_globals}, {})
    except Exception:
        return default


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """单位转换
    
    Args:
        value: 数值
        from_unit: 原单位
        to_unit: 目标单位
        
    Returns:
        转换后的值
    """
    # 长度单位转换 (米为基础)
    length_units = {
        'm': 1.0, 'km': 1000.0, 'cm': 0.01, 'mm': 0.001,
        'inch': 0.0254, 'ft': 0.3048, 'yd': 0.9144, 'mile': 1609.344
    }
    
    # 重量单位转换 (千克为基础)
    weight_units = {
        'kg': 1.0, 'g': 0.001, 'mg': 0.000001, 't': 1000.0,
        'lb': 0.45359237, 'oz': 0.0283495
    }
    
    # 时间单位转换 (秒为基础)
    time_units = {
        's': 1.0, 'ms': 0.001, 'us': 0.000001, 'ns': 1e-9,
        'min': 60.0, 'h': 3600.0, 'd': 86400.0, 'w': 604800.0
    }
    
    # 合并所有单位
    all_units = {}
    all_units.update(length_units)
    all_units.update(weight_units)
    all_units.update(time_units)
    
    if from_unit not in all_units or to_unit not in all_units:
        raise ValueError(f"不支持的单位: {from_unit} 或 {to_unit}")
    
    # 转换为基础单位，再转换为目标单位
    base_value = value * all_units[from_unit]
    return base_value / all_units[to_unit]