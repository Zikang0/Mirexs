"""
编码工具模块

提供各种编码解码操作的实用工具函数，包括字符编码、进制编码、加密编码等。
"""

import base64
import binascii
import codecs
import html
import urllib.parse
import quopri
import hashlib
import json
from typing import Union, Optional, Dict, Any, List, Tuple
import chardet
import re


class EncodingUtils:
    """编码工具类"""
    
    # 常见编码名称
    ENCODINGS = [
        'utf-8', 'ascii', 'latin-1', 'cp1252', 'gbk', 'gb2312', 'big5',
        'utf-16', 'utf-16le', 'utf-16be', 'utf-32', 'utf-32le', 'utf-32be',
        'iso-8859-1', 'iso-8859-15', 'koi8-r', 'koi8-u', 'mac-roman'
    ]
    
    @staticmethod
    def encode_base64(data: Union[str, bytes], urlsafe: bool = False) -> str:
        """Base64编码
        
        Args:
            data: 要编码的数据
            urlsafe: 是否使用URL安全的Base64（将+和/替换为-和_）
            
        Returns:
            Base64编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if urlsafe:
            encoded = base64.urlsafe_b64encode(data)
        else:
            encoded = base64.b64encode(data)
        
        return encoded.decode('ascii')
    
    @staticmethod
    def decode_base64(encoded_data: str, urlsafe: bool = False) -> bytes:
        """Base64解码
        
        Args:
            encoded_data: Base64编码字符串
            urlsafe: 是否使用URL安全的Base64
            
        Returns:
            解码后的字节数据
        """
        # 处理可能缺少填充的情况
        missing_padding = len(encoded_data) % 4
        if missing_padding:
            encoded_data += '=' * (4 - missing_padding)
        
        if urlsafe:
            return base64.urlsafe_b64decode(encoded_data)
        else:
            return base64.b64decode(encoded_data)
    
    @staticmethod
    def encode_base32(data: Union[str, bytes]) -> str:
        """Base32编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base32编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b32encode(data).decode('ascii')
    
    @staticmethod
    def decode_base32(encoded_data: str) -> bytes:
        """Base32解码
        
        Args:
            encoded_data: Base32编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b32decode(encoded_data.upper())
    
    @staticmethod
    def encode_base16(data: Union[str, bytes]) -> str:
        """Base16编码（十六进制）
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base16编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b16encode(data).decode('ascii')
    
    @staticmethod
    def decode_base16(encoded_data: str) -> bytes:
        """Base16解码
        
        Args:
            encoded_data: Base16编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b16decode(encoded_data.upper())
    
    @staticmethod
    def encode_base85(data: Union[str, bytes]) -> str:
        """Base85编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base85编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b85encode(data).decode('ascii')
    
    @staticmethod
    def decode_base85(encoded_data: str) -> bytes:
        """Base85解码
        
        Args:
            encoded_data: Base85编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.b85decode(encoded_data)
    
    @staticmethod
    def encode_ascii85(data: Union[str, bytes]) -> str:
        """ASCII85编码（Adobe版本）
        
        Args:
            data: 要编码的数据
            
        Returns:
            ASCII85编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Python没有内置ASCII85，使用base64.a85encode
        return base64.a85encode(data).decode('ascii')
    
    @staticmethod
    def decode_ascii85(encoded_data: str) -> bytes:
        """ASCII85解码
        
        Args:
            encoded_data: ASCII85编码字符串
            
        Returns:
            解码后的字节数据
        """
        return base64.a85decode(encoded_data)
    
    @staticmethod
    def encode_url(text: str, encoding: str = 'utf-8') -> str:
        """URL编码
        
        Args:
            text: 要编码的文本
            encoding: 字符编码
            
        Returns:
            URL编码字符串
        """
        return urllib.parse.quote(text, encoding=encoding)
    
    @staticmethod
    def encode_url_component(text: str, encoding: str = 'utf-8') -> str:
        """URL组件编码（编码所有特殊字符）
        
        Args:
            text: 要编码的文本
            encoding: 字符编码
            
        Returns:
            URL编码字符串
        """
        return urllib.parse.quote(text, safe='', encoding=encoding)
    
    @staticmethod
    def decode_url(encoded_text: str, encoding: str = 'utf-8') -> str:
        """URL解码
        
        Args:
            encoded_text: URL编码字符串
            encoding: 字符编码
            
        Returns:
            解码后的文本
        """
        return urllib.parse.unquote(encoded_text, encoding=encoding)
    
    @staticmethod
    def encode_url_params(params: Dict[str, Any], encoding: str = 'utf-8') -> str:
        """编码URL参数
        
        Args:
            params: 参数字典
            encoding: 编码
            
        Returns:
            URL参数字符串（如 key1=value1&key2=value2）
        """
        return urllib.parse.urlencode(params, encoding=encoding)
    
    @staticmethod
    def decode_url_params(query_string: str, encoding: str = 'utf-8') -> Dict[str, List[str]]:
        """解码URL参数
        
        Args:
            query_string: URL查询字符串
            encoding: 编码
            
        Returns:
            参数字典（值可能为列表）
        """
        return urllib.parse.parse_qs(query_string, encoding=encoding)
    
    @staticmethod
    def encode_html(text: str, quote: bool = True) -> str:
        """HTML编码
        
        Args:
            text: 要编码的文本
            quote: 是否编码引号
            
        Returns:
            HTML编码字符串
        """
        return html.escape(text, quote=quote)
    
    @staticmethod
    def decode_html(encoded_text: str) -> str:
        """HTML解码
        
        Args:
            encoded_text: HTML编码字符串
            
        Returns:
            解码后的文本
        """
        return html.unescape(encoded_text)
    
    @staticmethod
    def encode_xml(text: str) -> str:
        """XML编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            XML编码字符串
        """
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text
    
    @staticmethod
    def decode_xml(encoded_text: str) -> str:
        """XML解码
        
        Args:
            encoded_text: XML编码字符串
            
        Returns:
            解码后的文本
        """
        text = encoded_text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&apos;', "'")
        return text
    
    @staticmethod
    def encode_json(data: Any, ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
        """JSON编码
        
        Args:
            data: 要编码的数据
            ensure_ascii: 是否确保ASCII
            indent: 缩进空格数
            
        Returns:
            JSON字符串
        """
        return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
    
    @staticmethod
    def decode_json(json_string: str) -> Any:
        """JSON解码
        
        Args:
            json_string: JSON字符串
            
        Returns:
            解码后的数据
        """
        return json.loads(json_string)
    
    @staticmethod
    def encode_hex(data: Union[str, bytes, int], prefix: bool = False, upper: bool = False) -> str:
        """十六进制编码
        
        Args:
            data: 要编码的数据
            prefix: 是否添加 0x 前缀
            upper: 是否使用大写字母
            
        Returns:
            十六进制字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if isinstance(data, bytes):
            hex_str = binascii.hexlify(data).decode('ascii')
        elif isinstance(data, int):
            hex_str = format(data, 'x')
        else:
            hex_str = ''
        
        if upper:
            hex_str = hex_str.upper()
        
        if prefix and hex_str:
            return f"0x{hex_str}"
        return hex_str
    
    @staticmethod
    def decode_hex(hex_string: str) -> bytes:
        """十六进制解码
        
        Args:
            hex_string: 十六进制字符串
            
        Returns:
            解码后的字节数据
        """
        # 移除可能的前缀
        hex_string = hex_string.replace('0x', '').replace('0X', '')
        return binascii.unhexlify(hex_string)
    
    @staticmethod
    def encode_binary(value: int, bits: int = 8, prefix: bool = False) -> str:
        """二进制编码
        
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
    def decode_binary(bin_string: str) -> int:
        """二进制解码
        
        Args:
            bin_string: 二进制字符串
            
        Returns:
            整数值
        """
        bin_string = bin_string.replace('0b', '').replace('0B', '')
        return int(bin_string, 2)
    
    @staticmethod
    def encode_octal(value: int, prefix: bool = False) -> str:
        """八进制编码
        
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
    def decode_octal(oct_string: str) -> int:
        """八进制解码
        
        Args:
            oct_string: 八进制字符串
            
        Returns:
            整数值
        """
        oct_string = oct_string.replace('0o', '').replace('0O', '')
        return int(oct_string, 8)
    
    @staticmethod
    def encode_quoted_printable(data: Union[str, bytes], header: bool = False) -> str:
        """Quoted-Printable编码
        
        Args:
            data: 要编码的数据
            header: 是否为邮件头编码
            
        Returns:
            Quoted-Printable编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if header:
            return codecs.encode(data, 'quopri').decode('ascii').replace('=', '?=')
        else:
            return codecs.encode(data, 'quopri').decode('ascii')
    
    @staticmethod
    def decode_quoted_printable(encoded_data: str) -> bytes:
        """Quoted-Printable解码
        
        Args:
            encoded_data: Quoted-Printable编码字符串
            
        Returns:
            解码后的字节数据
        """
        return codecs.decode(encoded_data.encode('ascii'), 'quopri')
    
    @staticmethod
    def encode_uuencode(data: Union[str, bytes]) -> str:
        """UUencode编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            UUencode编码字符串
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return codecs.encode(data, 'uu').decode('ascii')
    
    @staticmethod
    def decode_uuencode(encoded_data: str) -> bytes:
        """UUencode解码
        
        Args:
            encoded_data: UUencode编码字符串
            
        Returns:
            解码后的字节数据
        """
        return codecs.decode(encoded_data.encode('ascii'), 'uu')
    
    @staticmethod
    def encode_rot13(text: str) -> str:
        """ROT13编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            ROT13编码后的文本
        """
        return codecs.encode(text, 'rot_13')
    
    @staticmethod
    def decode_rot13(encoded_text: str) -> str:
        """ROT13解码
        
        Args:
            encoded_text: ROT13编码文本
            
        Returns:
            解码后的文本
        """
        return codecs.decode(encoded_text, 'rot_13')
    
    @staticmethod
    def encode_rot5(text: str) -> str:
        """ROT5编码（只编码数字）
        
        Args:
            text: 要编码的文本
            
        Returns:
            ROT5编码后的文本
        """
        result = []
        for char in text:
            if char.isdigit():
                result.append(str((int(char) + 5) % 10))
            else:
                result.append(char)
        return ''.join(result)
    
    @staticmethod
    def decode_rot5(encoded_text: str) -> str:
        """ROT5解码
        
        Args:
            encoded_text: ROT5编码文本
            
        Returns:
            解码后的文本
        """
        result = []
        for char in encoded_text:
            if char.isdigit():
                result.append(str((int(char) - 5) % 10))
            else:
                result.append(char)
        return ''.join(result)
    
    @staticmethod
    def encode_rot13_rot5(text: str) -> str:
        """ROT13+ROT5编码（字母ROT13，数字ROT5）
        
        Args:
            text: 要编码的文本
            
        Returns:
            编码后的文本
        """
        rot13 = EncodingUtils.encode_rot13(text)
        return EncodingUtils.encode_rot5(rot13)
    
    @staticmethod
    def decode_rot13_rot5(encoded_text: str) -> str:
        """ROT13+ROT5解码
        
        Args:
            encoded_text: 编码文本
            
        Returns:
            解码后的文本
        """
        rot5_decoded = EncodingUtils.decode_rot5(encoded_text)
        return EncodingUtils.decode_rot13(rot5_decoded)
    
    @staticmethod
    def encode_atbash(text: str) -> str:
        """Atbash编码（字母反转）
        
        Args:
            text: 要编码的文本
            
        Returns:
            Atbash编码后的文本
        """
        result = []
        for char in text:
            if 'a' <= char <= 'z':
                result.append(chr(ord('a') + (25 - (ord(char) - ord('a')))))
            elif 'A' <= char <= 'Z':
                result.append(chr(ord('A') + (25 - (ord(char) - ord('A')))))
            else:
                result.append(char)
        return ''.join(result)
    
    @staticmethod
    def decode_atbash(encoded_text: str) -> str:
        """Atbash解码（与编码相同）
        
        Args:
            encoded_text: Atbash编码文本
            
        Returns:
            解码后的文本
        """
        return EncodingUtils.encode_atbash(encoded_text)
    
    @staticmethod
    def encode_punycode(text: str) -> str:
        """Punycode编码（用于国际化域名）
        
        Args:
            text: 要编码的文本
            
        Returns:
            Punycode编码字符串
        """
        return text.encode('punycode').decode('ascii')
    
    @staticmethod
    def decode_punycode(encoded_text: str) -> str:
        """Punycode解码
        
        Args:
            encoded_text: Punycode编码字符串
            
        Returns:
            解码后的文本
        """
        return encoded_text.encode('ascii').decode('punycode')
    
    @staticmethod
    def encode_morse(text: str) -> str:
        """莫尔斯电码编码
        
        Args:
            text: 要编码的文本
            
        Returns:
            莫尔斯电码字符串
        """
        morse_dict = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
            'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
            'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
            'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
            'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
            'Z': '--..',
            '0': '-----', '1': '.----', '2': '..---', '3': '...--',
            '4': '....-', '5': '.....', '6': '-....', '7': '--...',
            '8': '---..', '9': '----.',
            '.': '.-.-.-', ',': '--..--', '?': '..--..', '!': '-.-.--',
            '/': '-..-.', '(': '-.--.', ')': '-.--.-', '&': '.-...',
            ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.',
            '-': '-....-', '_': '..--.-', '"': '.-..-.', '$': '...-..-',
            '@': '.--.-.', ' ': '/'
        }
        
        result = []
        text = text.upper()
        for char in text:
            if char in morse_dict:
                result.append(morse_dict[char])
            else:
                result.append(char)
        
        return ' '.join(result)
    
    @staticmethod
    def decode_morse(morse_code: str) -> str:
        """莫尔斯电码解码
        
        Args:
            morse_code: 莫尔斯电码字符串
            
        Returns:
            解码后的文本
        """
        morse_dict = {
            '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
            '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
            '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
            '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
            '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
            '--..': 'Z',
            '-----': '0', '.----': '1', '..---': '2', '...--': '3',
            '....-': '4', '.....': '5', '-....': '6', '--...': '7',
            '---..': '8', '----.': '9',
            '.-.-.-': '.', '--..--': ',', '..--..': '?', '-.-.--': '!',
            '-..-.': '/', '-.--.': '(', '-.--.-': ')', '.-...': '&',
            '---...': ':', '-.-.-.': ';', '-...-': '=', '.-.-.': '+',
            '-....-': '-', '..--.-': '_', '.-..-.': '"', '...-..-': '$',
            '.--.-.': '@', '/': ' '
        }
        
        result = []
        codes = morse_code.split(' ')
        
        for code in codes:
            if code in morse_dict:
                result.append(morse_dict[code])
            elif code == '':
                result.append(' ')
            else:
                result.append(code)
        
        return ''.join(result)


class CharsetUtils:
    """字符集检测和转换工具类"""
    
    @staticmethod
    def detect_encoding(data: Union[str, bytes]) -> Optional[Dict[str, Any]]:
        """检测字符编码
        
        Args:
            data: 要检测的数据
            
        Returns:
            包含编码信息的字典，检测失败返回None
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        try:
            result = chardet.detect(data)
            return {
                'encoding': result.get('encoding'),
                'confidence': result.get('confidence', 0.0),
                'language': result.get('language')
            }
        except Exception:
            return None
    
    @staticmethod
    def detect_encoding_with_fallback(data: bytes) -> str:
        """检测编码，失败时返回默认编码
        
        Args:
            data: 字节数据
            
        Returns:
            编码名称
        """
        result = CharsetUtils.detect_encoding(data)
        if result and result['encoding'] and result['confidence'] > 0.5:
            return result['encoding']
        
        # 尝试常见编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']:
            try:
                data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        
        return 'utf-8'  # 默认
    
    @staticmethod
    def convert_encoding(data: Union[str, bytes],
                        from_encoding: Optional[str] = None,
                        to_encoding: str = 'utf-8') -> str:
        """转换字符编码
        
        Args:
            data: 要转换的数据
            from_encoding: 原始编码，None则自动检测
            to_encoding: 目标编码
            
        Returns:
            转换后的字符串
        """
        if isinstance(data, str):
            if from_encoding:
                # 如果提供了原始编码，先编码再解码
                data = data.encode(from_encoding, errors='ignore')
            else:
                # 已经是字符串，直接返回
                return data
        
        if from_encoding is None:
            from_encoding = CharsetUtils.detect_encoding_with_fallback(data)
        
        try:
            return data.decode(from_encoding, errors='ignore').encode(to_encoding).decode(to_encoding)
        except Exception:
            # 失败时尝试使用UTF-8
            return data.decode('utf-8', errors='ignore')
    
    @staticmethod
    def normalize_encoding(encoding: str) -> str:
        """标准化编码名称
        
        Args:
            encoding: 编码名称
            
        Returns:
            标准化的编码名称
        """
        encoding = encoding.lower().replace('-', '').replace('_', '')
        
        # 常见编码映射
        encoding_map = {
            'utf8': 'utf-8',
            'utf16': 'utf-16',
            'utf16le': 'utf-16le',
            'utf16be': 'utf-16be',
            'gb2312': 'gbk',
            'gbk': 'gbk',
            'big5': 'big5',
            'latin1': 'latin-1',
            'iso88591': 'iso-8859-1',
            'ascii': 'ascii',
        }
        
        return encoding_map.get(encoding, encoding)
    
    @staticmethod
    def is_supported_encoding(encoding: str) -> bool:
        """检查是否支持指定的编码
        
        Args:
            encoding: 编码名称
            
        Returns:
            是否支持
        """
        try:
            codecs.lookup(encoding)
            return True
        except LookupError:
            return False
    
    @staticmethod
    def get_system_encoding() -> str:
        """获取系统默认编码
        
        Returns:
            系统默认编码
        """
        import locale
        return locale.getpreferredencoding()


class HashUtils:
    """哈希工具类"""
    
    @staticmethod
    def md5(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """MD5哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.md5(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def sha1(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """SHA1哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.sha1(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def sha256(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """SHA256哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.sha256(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def sha512(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """SHA512哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.sha512(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def blake2b(data: Union[str, bytes], digest_size: int = 64, hexdigest: bool = True) -> str:
        """BLAKE2b哈希
        
        Args:
            data: 要哈希的数据
            digest_size: 摘要大小（1-64）
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.blake2b(data, digest_size=digest_size)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def blake2s(data: Union[str, bytes], digest_size: int = 32, hexdigest: bool = True) -> str:
        """BLAKE2s哈希
        
        Args:
            data: 要哈希的数据
            digest_size: 摘要大小（1-32）
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.blake2s(data, digest_size=digest_size)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def sha3_256(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """SHA3-256哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.sha3_256(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def sha3_512(data: Union[str, bytes], hexdigest: bool = True) -> str:
        """SHA3-512哈希
        
        Args:
            data: 要哈希的数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        h = hashlib.sha3_512(data)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def hmac_md5(key: Union[str, bytes], data: Union[str, bytes], hexdigest: bool = True) -> str:
        """HMAC-MD5
        
        Args:
            key: 密钥
            data: 数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            HMAC值
        """
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        import hmac
        h = hmac.new(key, data, hashlib.md5)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def hmac_sha256(key: Union[str, bytes], data: Union[str, bytes], hexdigest: bool = True) -> str:
        """HMAC-SHA256
        
        Args:
            key: 密钥
            data: 数据
            hexdigest: 是否返回十六进制字符串
            
        Returns:
            HMAC值
        """
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        import hmac
        h = hmac.new(key, data, hashlib.sha256)
        return h.hexdigest() if hexdigest else h.digest()
    
    @staticmethod
    def crc32(data: Union[str, bytes]) -> int:
        """CRC32校验
        
        Args:
            data: 数据
            
        Returns:
            CRC32值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return binascii.crc32(data) & 0xffffffff
    
    @staticmethod
    def adler32(data: Union[str, bytes]) -> int:
        """Adler-32校验
        
        Args:
            data: 数据
            
        Returns:
            Adler-32值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return binascii.adler32(data) & 0xffffffff


def detect_encoding(data: Union[str, bytes]) -> Optional[str]:
    """检测字符编码（便捷函数）
    
    Args:
        data: 要检测的数据
        
    Returns:
        编码名称
    """
    result = CharsetUtils.detect_encoding(data)
    return result['encoding'] if result else None


def to_unicode(data: Union[str, bytes], encoding: Optional[str] = None) -> str:
    """转换为Unicode字符串
    
    Args:
        data: 要转换的数据
        encoding: 原始编码，None则自动检测
        
    Returns:
        Unicode字符串
    """
    if isinstance(data, str):
        return data
    
    if encoding is None:
        encoding = detect_encoding(data) or 'utf-8'
    
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        # 失败时尝试使用UTF-8
        return data.decode('utf-8', errors='ignore')


def to_bytes(data: Union[str, bytes], encoding: str = 'utf-8') -> bytes:
    """转换为字节数据
    
    Args:
        data: 要转换的数据
        encoding: 目标编码
        
    Returns:
        字节数据
    """
    if isinstance(data, bytes):
        return data
    
    return data.encode(encoding)


def is_base64(data: str) -> bool:
    """检查是否为Base64编码
    
    Args:
        data: 要检查的字符串
        
    Returns:
        是否为Base64编码
    """
    # 检查长度
    if len(data) % 4 != 0:
        return False
    
    # 检查字符
    pattern = r'^[A-Za-z0-9+/]+=*$'
    if not re.match(pattern, data):
        return False
    
    # 尝试解码
    try:
        base64.b64decode(data)
        return True
    except Exception:
        return False


def is_hex(data: str) -> bool:
    """检查是否为十六进制编码
    
    Args:
        data: 要检查的字符串
        
    Returns:
        是否为十六进制编码
    """
    data = data.replace('0x', '').replace('0X', '')
    pattern = r'^[0-9A-Fa-f]+$'
    return bool(re.match(pattern, data))


def is_ascii(text: str) -> bool:
    """检查是否全部为ASCII字符
    
    Args:
        text: 要检查的文本
        
    Returns:
        是否全部为ASCII
    """
    return all(ord(char) < 128 for char in text)


def get_unicode_escape(text: str) -> str:
    """获取Unicode转义表示
    
    Args:
        text: 原始文本
        
    Returns:
        Unicode转义字符串（如 \u4e2d\u6587）
    """
    return text.encode('unicode_escape').decode('ascii')


def from_unicode_escape(escaped: str) -> str:
    """从Unicode转义恢复
    
    Args:
        escaped: Unicode转义字符串
        
    Returns:
        原始文本
    """
    return escaped.encode('ascii').decode('unicode_escape')


def encode_rot(text: str, shift: int) -> str:
    """ROT-N编码（通用）
    
    Args:
        text: 要编码的文本
        shift: 移位数量
        
    Returns:
        ROT-N编码后的文本
    """
    shift = shift % 26
    result = []
    
    for char in text:
        if 'a' <= char <= 'z':
            result.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
        elif 'A' <= char <= 'Z':
            result.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
        else:
            result.append(char)
    
    return ''.join(result)


def decode_rot(encoded: str, shift: int) -> str:
    """ROT-N解码
    
    Args:
        encoded: 编码文本
        shift: 移位数量
        
    Returns:
        解码后的文本
    """
    return encode_rot(encoded, -shift)


def encode_caesar(text: str, shift: int) -> str:
    """凯撒密码编码（ROT-N的别名）
    
    Args:
        text: 要编码的文本
        shift: 移位数量
        
    Returns:
        编码后的文本
    """
    return encode_rot(text, shift)


def decode_caesar(encoded: str, shift: int) -> str:
    """凯撒密码解码
    
    Args:
        encoded: 编码文本
        shift: 移位数量
        
    Returns:
        解码后的文本
    """
    return encode_rot(encoded, -shift)