"""
数据序列化工具模块

提供各种数据格式的序列化与反序列化功能
"""

import pandas as pd
import numpy as np
import json
import pickle
import gzip
import bz2
import lzma
from typing import Dict, List, Any, Optional, Union, IO
import xml.etree.ElementTree as ET
import yaml
import csv
import logging
from pathlib import Path
import base64
import zlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSerializer:
    """数据序列化器类"""
    
    def __init__(self):
        """初始化序列化器"""
        self.compression_formats = ['gzip', 'bz2', 'lzma', 'zlib']
        self.text_formats = ['json', 'csv', 'xml', 'yaml', 'txt']
        self.binary_formats = ['pickle', 'parquet', 'feather', 'hdf5']
    
    def to_json(self, data: Union[pd.DataFrame, pd.Series, Dict, List], 
                filepath: Optional[str] = None,
                compress: bool = False,
                compression_format: str = 'gzip',
                indent: int = 2,
                ensure_ascii: bool = False) -> Optional[str]:
        """
        序列化为JSON格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径，None则返回字符串
            compress: 是否压缩
            compression_format: 压缩格式
            indent: JSON缩进
            ensure_ascii: 是否确保ASCII编码
            
        Returns:
            JSON字符串（如果filepath为None）
        """
        try:
            # 处理pandas对象
            if isinstance(data, (pd.DataFrame, pd.Series)):
                json_data = data.to_json(orient='records', force_ascii=not ensure_ascii, indent=indent)
            else:
                json_data = json.dumps(data, ensure_ascii=not ensure_ascii, indent=indent)
            
            if compress and compression_format in self.compression_formats:
                if compression_format == 'gzip':
                    json_data = gzip.compress(json_data.encode('utf-8'))
                elif compression_format == 'bz2':
                    json_data = bz2.compress(json_data.encode('utf-8'))
                elif compression_format == 'lzma':
                    json_data = lzma.compress(json_data.encode('utf-8'))
                elif compression_format == 'zlib':
                    json_data = zlib.compress(json_data.encode('utf-8'))
            
            if filepath:
                with open(filepath, 'wb' if compress else 'w', encoding='utf-8') as f:
                    if compress:
                        f.write(json_data)
                    else:
                        f.write(json_data)
                return None
            else:
                return json_data.decode('utf-8') if compress else json_data
                
        except Exception as e:
            logger.error(f"JSON序列化时出错: {e}")
            raise
    
    def from_json(self, filepath: Optional[str] = None,
                 json_string: Optional[str] = None,
                 decompress: bool = False,
                 compression_format: str = 'gzip') -> Union[pd.DataFrame, pd.Series, Dict, List]:
        """
        从JSON反序列化
        
        Args:
            filepath: 文件路径
            json_string: JSON字符串
            decompress: 是否解压缩
            compression_format: 压缩格式
            
        Returns:
            反序列化的数据
        """
        try:
            if filepath:
                with open(filepath, 'rb' if decompress else 'r', encoding='utf-8') as f:
                    if decompress:
                        compressed_data = f.read()
                        if compression_format == 'gzip':
                            json_data = gzip.decompress(compressed_data).decode('utf-8')
                        elif compression_format == 'bz2':
                            json_data = bz2.decompress(compressed_data).decode('utf-8')
                        elif compression_format == 'lzma':
                            json_data = lzma.decompress(compressed_data).decode('utf-8')
                        elif compression_format == 'zlib':
                            json_data = zlib.decompress(compressed_data).decode('utf-8')
                    else:
                        json_data = f.read()
            elif json_string:
                if decompress:
                    if compression_format == 'gzip':
                        json_data = gzip.decompress(json_string.encode('utf-8')).decode('utf-8')
                    elif compression_format == 'bz2':
                        json_data = bz2.decompress(json_string.encode('utf-8')).decode('utf-8')
                    elif compression_format == 'lzma':
                        json_data = lzma.decompress(json_string.encode('utf-8')).decode('utf-8')
                    elif compression_format == 'zlib':
                        json_data = zlib.decompress(json_string.encode('utf-8')).decode('utf-8')
                else:
                    json_data = json_string
            else:
                raise ValueError("必须提供filepath或json_string")
            
            # 尝试转换为DataFrame
            try:
                data = json.loads(json_data)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    return pd.DataFrame(data)
                elif isinstance(data, dict) and 'data' in data:
                    return pd.DataFrame(data['data'])
                else:
                    return data
            except:
                return json.loads(json_data)
                
        except Exception as e:
            logger.error(f"JSON反序列化时出错: {e}")
            raise
    
    def to_csv(self, data: Union[pd.DataFrame, pd.Series], 
               filepath: str,
               compress: bool = False,
               compression_format: str = 'gzip',
               **kwargs) -> None:
        """
        序列化为CSV格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径
            compress: 是否压缩
            compression_format: 压缩格式
            **kwargs: CSV参数
        """
        try:
            if compress:
                if compression_format == 'gzip':
                    with gzip.open(filepath, 'wt', newline='', encoding='utf-8') as f:
                        data.to_csv(f, **kwargs)
                elif compression_format == 'bz2':
                    with bz2.open(filepath, 'wt', newline='', encoding='utf-8') as f:
                        data.to_csv(f, **kwargs)
                else:
                    # 对于其他压缩格式，先保存临时文件再压缩
                    temp_path = filepath + '.tmp'
                    data.to_csv(temp_path, **kwargs)
                    
                    with open(temp_path, 'rb') as f_in:
                        with open(filepath, 'wb') as f_out:
                            if compression_format == 'lzma':
                                f_out.write(lzma.compress(f_in.read()))
                            elif compression_format == 'zlib':
                                f_out.write(zlib.compress(f_in.read()))
                    
                    Path(temp_path).unlink()  # 删除临时文件
            else:
                data.to_csv(filepath, **kwargs)
                
        except Exception as e:
            logger.error(f"CSV序列化时出错: {e}")
            raise
    
    def from_csv(self, filepath: str,
                decompress: bool = False,
                compression_format: str = 'gzip',
                **kwargs) -> pd.DataFrame:
        """
        从CSV反序列化
        
        Args:
            filepath: 文件路径
            decompress: 是否解压缩
            compression_format: 压缩格式
            **kwargs: CSV读取参数
            
        Returns:
            DataFrame
        """
        try:
            if decompress:
                if compression_format == 'gzip':
                    with gzip.open(filepath, 'rt', newline='', encoding='utf-8') as f:
                        return pd.read_csv(f, **kwargs)
                elif compression_format == 'bz2':
                    with bz2.open(filepath, 'rt', newline='', encoding='utf-8') as f:
                        return pd.read_csv(f, **kwargs)
                else:
                    # 对于其他压缩格式，先解压缩到临时文件
                    with open(filepath, 'rb') as f_in:
                        if compression_format == 'lzma':
                            decompressed_data = lzma.decompress(f_in.read())
                        elif compression_format == 'zlib':
                            decompressed_data = zlib.decompress(f_in.read())
                    
                    from io import StringIO
                    return pd.read_csv(StringIO(decompressed_data.decode('utf-8')), **kwargs)
            else:
                return pd.read_csv(filepath, **kwargs)
                
        except Exception as e:
            logger.error(f"CSV反序列化时出错: {e}")
            raise
    
    def to_xml(self, data: Union[pd.DataFrame, pd.Series, Dict, List], 
               filepath: Optional[str] = None,
               root_element: str = 'data',
               row_element: str = 'row') -> Optional[str]:
        """
        序列化为XML格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径，None则返回字符串
            root_element: 根元素名
            row_element: 行元素名
            
        Returns:
            XML字符串（如果filepath为None）
        """
        try:
            root = ET.Element(root_element)
            
            if isinstance(data, pd.DataFrame):
                for _, row in data.iterrows():
                    row_elem = ET.SubElement(root, row_element)
                    for col, val in row.items():
                        col_elem = ET.SubElement(row_elem, str(col))
                        col_elem.text = str(val) if val is not None else ''
            
            elif isinstance(data, pd.Series):
                for idx, val in data.items():
                    item_elem = ET.SubElement(root, 'item')
                    key_elem = ET.SubElement(item_elem, 'key')
                    key_elem.text = str(idx)
                    value_elem = ET.SubElement(item_elem, 'value')
                    value_elem.text = str(val) if val is not None else ''
            
            elif isinstance(data, dict):
                for key, value in data.items():
                    item_elem = ET.SubElement(root, 'item')
                    key_elem = ET.SubElement(item_elem, 'key')
                    key_elem.text = str(key)
                    value_elem = ET.SubElement(item_elem, 'value')
                    if isinstance(value, (dict, list)):
                        value_elem.text = json.dumps(value)
                    else:
                        value_elem.text = str(value) if value is not None else ''
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    item_elem = ET.SubElement(root, 'item')
                    index_elem = ET.SubElement(item_elem, 'index')
                    index_elem.text = str(i)
                    value_elem = ET.SubElement(item_elem, 'value')
                    if isinstance(item, (dict, list)):
                        value_elem.text = json.dumps(item)
                    else:
                        value_elem.text = str(item) if item is not None else ''
            
            xml_string = ET.tostring(root, encoding='unicode')
            
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(xml_string)
                return None
            else:
                return xml_string
                
        except Exception as e:
            logger.error(f"XML序列化时出错: {e}")
            raise
    
    def from_xml(self, filepath: Optional[str] = None,
                xml_string: Optional[str] = None) -> Dict:
        """
        从XML反序列化
        
        Args:
            filepath: 文件路径
            xml_string: XML字符串
            
        Returns:
            反序列化的数据
        """
        try:
            if filepath:
                tree = ET.parse(filepath)
                root = tree.getroot()
            elif xml_string:
                root = ET.fromstring(xml_string)
            else:
                raise ValueError("必须提供filepath或xml_string")
            
            result = []
            for child in root:
                if child.tag == 'row':
                    row_data = {}
                    for subchild in child:
                        row_data[subchild.tag] = subchild.text
                    result.append(row_data)
                elif child.tag == 'item':
                    item_data = {}
                    for subchild in child:
                        if subchild.tag == 'key':
                            key = subchild.text
                        elif subchild.tag == 'value':
                            try:
                                # 尝试解析JSON
                                item_data[key] = json.loads(subchild.text)
                            except:
                                item_data[key] = subchild.text
                    result.append(item_data)
            
            return result
                
        except Exception as e:
            logger.error(f"XML反序列化时出错: {e}")
            raise
    
    def to_yaml(self, data: Union[pd.DataFrame, pd.Series, Dict, List], 
                filepath: Optional[str] = None) -> Optional[str]:
        """
        序列化为YAML格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径，None则返回字符串
            
        Returns:
            YAML字符串（如果filepath为None）
        """
        try:
            # 处理pandas对象
            if isinstance(data, pd.DataFrame):
                yaml_data = data.to_dict('records')
            elif isinstance(data, pd.Series):
                yaml_data = data.to_dict()
            else:
                yaml_data = data
            
            yaml_string = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
            
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(yaml_string)
                return None
            else:
                return yaml_string
                
        except Exception as e:
            logger.error(f"YAML序列化时出错: {e}")
            raise
    
    def from_yaml(self, filepath: Optional[str] = None,
                 yaml_string: Optional[str] = None) -> Union[pd.DataFrame, Dict, List]:
        """
        从YAML反序列化
        
        Args:
            filepath: 文件路径
            yaml_string: YAML字符串
            
        Returns:
            反序列化的数据
        """
        try:
            if filepath:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            elif yaml_string:
                data = yaml.safe_load(yaml_string)
            else:
                raise ValueError("必须提供filepath或yaml_string")
            
            # 尝试转换为DataFrame
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return pd.DataFrame(data)
            else:
                return data
                
        except Exception as e:
            logger.error(f"YAML反序列化时出错: {e}")
            raise
    
    def to_pickle(self, data: Any, filepath: str, compress: bool = False) -> None:
        """
        序列化为Pickle格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径
            compress: 是否压缩
        """
        try:
            if compress:
                with gzip.open(filepath, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Pickle序列化时出错: {e}")
            raise
    
    def from_pickle(self, filepath: str, decompress: bool = False) -> Any:
        """
        从Pickle反序列化
        
        Args:
            filepath: 文件路径
            decompress: 是否解压缩
            
        Returns:
            反序列化的数据
        """
        try:
            if decompress:
                with gzip.open(filepath, 'rb') as f:
                    return pickle.load(f)
            else:
                with open(filepath, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"Pickle反序列化时出错: {e}")
            raise
    
    def to_parquet(self, data: pd.DataFrame, filepath: str, **kwargs) -> None:
        """
        序列化为Parquet格式
        
        Args:
            data: 要序列化的数据
            filepath: 文件路径
            **kwargs: Parquet参数
        """
        try:
            data.to_parquet(filepath, **kwargs)
        except Exception as e:
            logger.error(f"Parquet序列化时出错: {e}")
            raise
    
    def from_parquet(self, filepath: str, **kwargs) -> pd.DataFrame:
        """
        从Parquet反序列化
        
        Args:
            filepath: 文件路径
            **kwargs: Parquet读取参数
            
        Returns:
            DataFrame
        """
        try:
            return pd.read_parquet(filepath, **kwargs)
        except Exception as e:
            logger.error(f"Parquet反序列化时出错: {e}")
            raise
    
    def to_base64(self, data: Any) -> str:
        """
        序列化为Base64编码
        
        Args:
            data: 要序列化的数据
            
        Returns:
            Base64编码字符串
        """
        try:
            serialized_data = pickle.dumps(data)
            return base64.b64encode(serialized_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Base64序列化时出错: {e}")
            raise
    
    def from_base64(self, base64_string: str) -> Any:
        """
        从Base64反序列化
        
        Args:
            base64_string: Base64编码字符串
            
        Returns:
            反序列化的数据
        """
        try:
            serialized_data = base64.b64decode(base64_string.encode('utf-8'))
            return pickle.loads(serialized_data)
        except Exception as e:
            logger.error(f"Base64反序列化时出错: {e}")
            raise


def save_data(data: Any, filepath: str, format_type: Optional[str] = None, **kwargs) -> None:
    """
    通用数据保存函数
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
        format_type: 格式类型，None则根据文件扩展名自动判断
        **kwargs: 格式特定参数
    """
    try:
        serializer = DataSerializer()
        
        if format_type is None:
            format_type = Path(filepath).suffix.lower()[1:]  # 去掉点号
        
        if format_type == 'json':
            serializer.to_json(data, filepath, **kwargs)
        elif format_type == 'csv':
            serializer.to_csv(data, filepath, **kwargs)
        elif format_type == 'xml':
            serializer.to_xml(data, filepath, **kwargs)
        elif format_type == 'yaml' or format_type == 'yml':
            serializer.to_yaml(data, filepath, **kwargs)
        elif format_type == 'pickle' or format_type == 'pkl':
            serializer.to_pickle(data, filepath, **kwargs)
        elif format_type == 'parquet':
            serializer.to_parquet(data, filepath, **kwargs)
        else:
            raise ValueError(f"不支持的格式: {format_type}")
            
    except Exception as e:
        logger.error(f"保存数据时出错: {e}")
        raise


def load_data(filepath: str, format_type: Optional[str] = None, **kwargs) -> Any:
    """
    通用数据加载函数
    
    Args:
        filepath: 文件路径
        format_type: 格式类型，None则根据文件扩展名自动判断
        **kwargs: 格式特定参数
        
    Returns:
        加载的数据
    """
    try:
        serializer = DataSerializer()
        
        if format_type is None:
            format_type = Path(filepath).suffix.lower()[1:]  # 去掉点号
        
        if format_type == 'json':
            return serializer.from_json(filepath, **kwargs)
        elif format_type == 'csv':
            return serializer.from_csv(filepath, **kwargs)
        elif format_type == 'xml':
            return serializer.from_xml(filepath, **kwargs)
        elif format_type == 'yaml' or format_type == 'yml':
            return serializer.from_yaml(filepath, **kwargs)
        elif format_type == 'pickle' or format_type == 'pkl':
            return serializer.from_pickle(filepath, **kwargs)
        elif format_type == 'parquet':
            return serializer.from_parquet(filepath, **kwargs)
        else:
            raise ValueError(f"不支持的格式: {format_type}")
            
    except Exception as e:
        logger.error(f"加载数据时出错: {e}")
        raise


def compress_file(input_filepath: str, output_filepath: str, 
                 compression_format: str = 'gzip') -> None:
    """
    压缩文件
    
    Args:
        input_filepath: 输入文件路径
        output_filepath: 输出文件路径
        compression_format: 压缩格式
    """
    try:
        if compression_format == 'gzip':
            with open(input_filepath, 'rb') as f_in:
                with gzip.open(output_filepath, 'wb') as f_out:
                    f_out.writelines(f_in)
        elif compression_format == 'bz2':
            with open(input_filepath, 'rb') as f_in:
                with bz2.open(output_filepath, 'wb') as f_out:
                    f_out.writelines(f_in)
        elif compression_format == 'lzma':
            with open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.write(lzma.compress(f_in.read()))
        elif compression_format == 'zlib':
            with open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.write(zlib.compress(f_in.read()))
        else:
            raise ValueError(f"不支持的压缩格式: {compression_format}")
            
    except Exception as e:
        logger.error(f"压缩文件时出错: {e}")
        raise


def decompress_file(input_filepath: str, output_filepath: str, 
                   compression_format: str = 'gzip') -> None:
    """
    解压缩文件
    
    Args:
        input_filepath: 输入文件路径
        output_filepath: 输出文件路径
        compression_format: 压缩格式
    """
    try:
        if compression_format == 'gzip':
            with gzip.open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.writelines(f_in)
        elif compression_format == 'bz2':
            with bz2.open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.writelines(f_in)
        elif compression_format == 'lzma':
            with open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.write(lzma.decompress(f_in.read()))
        elif compression_format == 'zlib':
            with open(input_filepath, 'rb') as f_in:
                with open(output_filepath, 'wb') as f_out:
                    f_out.write(zlib.decompress(f_in.read()))
        else:
            raise ValueError(f"不支持的压缩格式: {compression_format}")
            
    except Exception as e:
        logger.error(f"解压缩文件时出错: {e}")
        raise


if __name__ == "__main__":
    # 示例用法
    print("数据序列化工具模块")
    
    # 创建示例数据
    sample_data = pd.DataFrame({
        'id': range(100),
        'name': [f'User_{i}' for i in range(100)],
        'value': np.random.normal(100, 15, 100),
        'category': np.random.choice(['A', 'B', 'C'], 100)
    })
    
    # 创建序列化器
    serializer = DataSerializer()
    
    # JSON序列化
    json_string = serializer.to_json(sample_data, indent=2)
    print(f"JSON序列化完成，长度: {len(json_string)}")
    
    # CSV序列化
    serializer.to_csv(sample_data, 'sample_data.csv')
    print("CSV序列化完成")
    
    # XML序列化
    xml_string = serializer.to_xml(sample_data)
    print(f"XML序列化完成，长度: {len(xml_string)}")
    
    # YAML序列化
    yaml_string = serializer.to_yaml(sample_data)
    print(f"YAML序列化完成，长度: {len(yaml_string)}")
    
    # Pickle序列化
    serializer.to_pickle(sample_data, 'sample_data.pkl', compress=True)
    print("Pickle序列化完成")
    
    # Base64序列化
    base64_string = serializer.to_base64(sample_data)
    print(f"Base64序列化完成，长度: {len(base64_string)}")
    
    # 验证反序列化
    restored_json = serializer.from_json(json_string=json_string)
    print(f"JSON反序列化验证: {len(restored_json)} 行")
    
    print("数据序列化示例完成")