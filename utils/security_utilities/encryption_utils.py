"""
加密工具模块

提供数据加密和解密工具。
"""

from typing import Union, Optional, Dict, Any
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import secrets


class EncryptionUtils:
    """加密工具类"""
    
    @staticmethod
    def generate_key(password: str, salt: bytes = None) -> bytes:
        """生成加密密钥
        
        Args:
            password: 密码
            salt: 盐值，如果为None则生成随机盐值
            
        Returns:
            加密密钥和盐值
        """
        if salt is None:
            salt = os.urandom(16)
        
        # 使用PBKDF2生成密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        return key, salt
    
    @staticmethod
    def encrypt_data(data: Union[str, bytes], password: str) -> Dict[str, str]:
        """加密数据
        
        Args:
            data: 要加密的数据
            password: 密码
            
        Returns:
            包含加密数据和元信息的字典
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 生成密钥和盐值
        key, salt = EncryptionUtils.generate_key(password)
        
        # 加密数据
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'algorithm': 'Fernet'
        }
    
    @staticmethod
    def decrypt_data(encrypted_data: str, password: str, salt: str) -> bytes:
        """解密数据
        
        Args:
            encrypted_data: 加密的数据
            password: 密码
            salt: 盐值
            
        Returns:
            解密后的数据
        """
        # 解码
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        salt_bytes = base64.b64decode(salt.encode('utf-8'))
        
        # 重新生成密钥
        key, _ = EncryptionUtils.generate_key(password, salt_bytes)
        
        # 解密数据
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_bytes)
        
        return decrypted_data
    
    @staticmethod
    def encrypt_file(file_path: str, password: str, output_path: str = None) -> str:
        """加密文件
        
        Args:
            file_path: 文件路径
            password: 密码
            output_path: 输出文件路径
            
        Returns:
            加密后的文件路径
        """
        if output_path is None:
            output_path = file_path + '.encrypted'
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 加密数据
        encrypted_result = EncryptionUtils.encrypt_data(file_data, password)
        
        # 保存加密结果
        with open(output_path, 'w') as f:
            import json
            json.dump(encrypted_result, f)
        
        return output_path
    
    @staticmethod
    def decrypt_file(encrypted_file_path: str, password: str, output_path: str = None) -> str:
        """解密文件
        
        Args:
            encrypted_file_path: 加密文件路径
            password: 密码
            output_path: 输出文件路径
            
        Returns:
            解密后的文件路径
        """
        if output_path is None:
            output_path = encrypted_file_path.replace('.encrypted', '')
        
        # 读取加密文件
        with open(encrypted_file_path, 'r') as f:
            import json
            encrypted_result = json.load(f)
        
        # 解密数据
        decrypted_data = EncryptionUtils.decrypt_data(
            encrypted_result['encrypted_data'],
            password,
            encrypted_result['salt']
        )
        
        # 保存解密文件
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return output_path


class HashUtils:
    """哈希工具类"""
    
    @staticmethod
    def sha256_hash(data: Union[str, bytes]) -> str:
        """计算SHA256哈希值
        
        Args:
            data: 要哈希的数据
            
        Returns:
            SHA256哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_object = hashlib.sha256(data)
        return hash_object.hexdigest()
    
    @staticmethod
    def sha512_hash(data: Union[str, bytes]) -> str:
        """计算SHA512哈希值
        
        Args:
            data: 要哈希的数据
            
        Returns:
            SHA512哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_object = hashlib.sha512(data)
        return hash_object.hexdigest()
    
    @staticmethod
    def md5_hash(data: Union[str, bytes]) -> str:
        """计算MD5哈希值
        
        Args:
            data: 要哈希的数据
            
        Returns:
            MD5哈希值
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_object = hashlib.md5(data)
        return hash_object.hexdigest()
    
    @staticmethod
    def hash_file(file_path: str, algorithm: str = 'sha256') -> str:
        """计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法 ('sha256', 'sha512', 'md5')
            
        Returns:
            文件哈希值
        """
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def generate_salt(length: int = 32) -> str:
        """生成随机盐值
        
        Args:
            length: 盐值长度
            
        Returns:
            随机盐值
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成安全令牌
        
        Args:
            length: 令牌长度
            
        Returns:
            安全令牌
        """
        return secrets.token_urlsafe(length)


class PasswordUtils:
    """密码工具类"""
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Dict[str, str]:
        """哈希密码
        
        Args:
            password: 原始密码
            salt: 盐值，如果为None则生成随机盐值
            
        Returns:
            包含哈希密码和盐值的字典
        """
        if salt is None:
            salt = PasswordUtils.generate_salt()
        
        # 使用PBKDF2哈希密码
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)
        
        return {
            'password_hash': base64.b64encode(password_hash).decode('utf-8'),
            'salt': salt,
            'algorithm': 'PBKDF2-SHA256',
            'iterations': 100000
        }
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """验证密码
        
        Args:
            password: 原始密码
            password_hash: 存储的密码哈希
            salt: 盐值
            
        Returns:
            密码是否正确
        """
        # 重新计算哈希
        computed_hash = hashlib.pbkdf2_hmac('sha256',
                                          password.encode('utf-8'),
                                          salt.encode('utf-8'),
                                          100000)
        
        # 比较哈希值
        stored_hash = base64.b64decode(password_hash.encode('utf-8'))
        return secrets.compare_digest(computed_hash, stored_hash)
    
    @staticmethod
    def generate_secure_password(length: int = 16, 
                               include_symbols: bool = True,
                               include_numbers: bool = True,
                               include_uppercase: bool = True,
                               include_lowercase: bool = True) -> str:
        """生成安全密码
        
        Args:
            length: 密码长度
            include_symbols: 是否包含符号
            include_numbers: 是否包含数字
            include_uppercase: 是否包含大写字母
            include_lowercase: 是否包含小写字母
            
        Returns:
            安全密码
        """
        characters = ""
        
        if include_lowercase:
            characters += "abcdefghijklmnopqrstuvwxyz"
        if include_uppercase:
            characters += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if include_numbers:
            characters += "0123456789"
        if include_symbols:
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if not characters:
            characters = "abcdefghijklmnopqrstuvwxyz"  # 默认包含小写字母
        
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """检查密码强度
        
        Args:
            password: 密码
            
        Returns:
            密码强度分析结果
        """
        score = 0
        feedback = []
        
        # 长度检查
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("密码长度至少8位，建议12位以上")
        
        # 字符类型检查
        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_numbers = any(c.isdigit() for c in password)
        has_symbols = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        char_types = sum([has_lowercase, has_uppercase, has_numbers, has_symbols])
        score += char_types
        
        if not has_lowercase:
            feedback.append("建议包含小写字母")
        if not has_uppercase:
            feedback.append("建议包含大写字母")
        if not has_numbers:
            feedback.append("建议包含数字")
        if not has_symbols:
            feedback.append("建议包含特殊符号")
        
        # 常见密码检查
        common_passwords = [
            "password", "123456", "qwerty", "abc123", "password123",
            "admin", "letmein", "welcome", "monkey", "1234567890"
        ]
        
        if password.lower() in common_passwords:
            score = 0
            feedback.append("密码过于常见，请使用更复杂的密码")
        
        # 确定强度等级
        if score >= 6:
            strength = "强"
        elif score >= 4:
            strength = "中等"
        elif score >= 2:
            strength = "弱"
        else:
            strength = "很弱"
        
        return {
            'score': score,
            'strength': strength,
            'feedback': feedback,
            'has_lowercase': has_lowercase,
            'has_uppercase': has_uppercase,
            'has_numbers': has_numbers,
            'has_symbols': has_symbols,
            'length': len(password)
        }


class CryptographicUtils:
    """加密工具类"""
    
    @staticmethod
    def generate_key_pair() -> Dict[str, str]:
        """生成RSA密钥对
        
        Returns:
            包含公钥和私钥的字典
        """
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # 生成公钥
        public_key = private_key.public_key()
        
        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'private_key': private_pem.decode('utf-8'),
            'public_key': public_pem.decode('utf-8')
        }
    
    @staticmethod
    def encrypt_with_public_key(data: Union[str, bytes], public_key_pem: str) -> str:
        """使用公钥加密数据
        
        Args:
            data: 要加密的数据
            public_key_pem: PEM格式的公钥
            
        Returns:
            加密后的数据（Base64编码）
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 加载公钥
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # 加密数据
        encrypted = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode('utf-8')
    
    @staticmethod
    def decrypt_with_private_key(encrypted_data: str, private_key_pem: str) -> bytes:
        """使用私钥解密数据
        
        Args:
            encrypted_data: 加密的数据（Base64编码）
            private_key_pem: PEM格式的私钥
            
        Returns:
            解密后的数据
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # 加载私钥
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
        )
        
        # 解密数据
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted
    
    @staticmethod
    def sign_data(data: Union[str, bytes], private_key_pem: str) -> str:
        """使用私钥签名数据
        
        Args:
            data: 要签名的数据
            private_key_pem: PEM格式的私钥
            
        Returns:
            签名（Base64编码）
        """
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 加载私钥
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
        )
        
        # 签名数据
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_signature(data: Union[str, bytes], signature: str, public_key_pem: str) -> bool:
        """验证签名
        
        Args:
            data: 原始数据
            signature: 签名（Base64编码）
            public_key_pem: PEM格式的公钥
            
        Returns:
            签名是否有效
        """
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 加载公钥
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # 验证签名
        try:
            public_key.verify(
                base64.b64decode(signature.encode('utf-8')),
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


def secure_compare(a: str, b: str) -> bool:
    """安全比较两个字符串（防止时序攻击）
    
    Args:
        a: 第一个字符串
        b: 第二个字符串
        
    Returns:
        字符串是否相等
    """
    return secrets.compare_digest(a, b)


def generate_secure_random_bytes(length: int) -> bytes:
    """生成安全随机字节
    
    Args:
        length: 字节长度
        
    Returns:
        随机字节
    """
    return secrets.token_bytes(length)


def mask_sensitive_data(data: str, mask_char: str = '*', 
                       show_first: int = 2, show_last: int = 2) -> str:
    """遮盖敏感数据
    
    Args:
        data: 原始数据
        mask_char: 遮盖字符
        show_first: 显示前几位
        show_last: 显示后几位
        
    Returns:
        遮盖后的数据
    """
    if len(data) <= show_first + show_last:
        return mask_char * len(data)
    
    return (data[:show_first] + 
            mask_char * (len(data) - show_first - show_last) + 
            data[-show_last:])