"""
证书工具模块

提供SSL/TLS证书管理、生成、验证、转换等功能。
"""

import logging
import ssl
import socket
import hashlib
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import subprocess
import re
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import OpenSSL
from cryptography.hazmat.primitives.serialization import pkcs12


class CertificateType(Enum):
    """证书类型枚举"""
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    SERVER_CERT = "server_cert"
    CLIENT_CERT = "client_cert"
    CODE_SIGNING = "code_signing"
    EMAIL = "email"


class CertificateStatus(Enum):
    """证书状态枚举"""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"
    INVALID = "invalid"


@dataclass
class CertificateInfo:
    """证书信息数据类"""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    public_key: str
    signature_algorithm: str
    fingerprint_sha256: str
    fingerprint_sha1: str
    san: List[str] = field(default_factory=list)
    key_usage: List[str] = field(default_factory=list)
    extended_key_usage: List[str] = field(default_factory=list)
    status: CertificateStatus = CertificateStatus.VALID


@dataclass
class CertificateChain:
    """证书链数据类"""
    certificates: List[CertificateInfo]
    root_ca: Optional[CertificateInfo] = None
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


class CertificateError(Exception):
    """证书异常"""
    pass


class CertificateValidationError(Exception):
    """证书验证异常"""
    pass


class CertificateGenerator:
    """证书生成器"""
    
    def __init__(self):
        """初始化证书生成器"""
        self.key_size = 2048
        self.hash_algorithm = hashes.SHA256()
        
    def generate_rsa_key(self, key_size: int = 2048) -> rsa.RSAPrivateKey:
        """生成RSA私钥
        
        Args:
            key_size: 密钥大小
            
        Returns:
            rsa.RSAPrivateKey: RSA私钥对象
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        return private_key
        
    def generate_ec_key(self, curve: ec.SECP256R1 = ec.SECP256R1()) -> ec.EllipticCurvePrivateKey:
        """生成椭圆曲线私钥
        
        Args:
            curve: 椭圆曲线
            
        Returns:
            ec.EllipticCurvePrivateKey: 椭圆曲线私钥对象
        """
        private_key = ec.generate_private_key(
            curve=curve,
            backend=default_backend()
        )
        return private_key
        
    def create_certificate_request(self, private_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
                                  subject_info: Dict[str, str],
                                  san: Optional[List[str]] = None) -> x509.CertificateSigningRequest:
        """创建证书签名请求
        
        Args:
            private_key: 私钥对象
            subject_info: 主题信息字典
            san: 主题备用名称列表
            
        Returns:
            x509.CertificateSigningRequest: 证书签名请求
        """
        # 构建主题
        subject_components = []
        for key, value in subject_info.items():
            if key.lower() == 'country':
                subject_components.append(x509.NameAttribute(NameOID.COUNTRY_NAME, value))
            elif key.lower() == 'state':
                subject_components.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, value))
            elif key.lower() == 'locality':
                subject_components.append(x509.NameAttribute(NameOID.LOCALITY_NAME, value))
            elif key.lower() == 'organization':
                subject_components.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, value))
            elif key.lower() == 'organizational_unit':
                subject_components.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, value))
            elif key.lower() == 'common_name':
                subject_components.append(x509.NameAttribute(NameOID.COMMON_NAME, value))
            elif key.lower() == 'email':
                subject_components.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, value))
                
        subject = x509.Name(subject_components)
        
        # 构建证书请求
        builder = x509.CertificateSigningRequestBuilder().subject_name(subject)
        
        # 添加SAN扩展
        if san:
            san_list = [x509.DNSName(name) for name in san]
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
            
        # 签名证书请求
        csr = builder.sign(private_key, self.hash_algorithm, default_backend())
        return csr
        
    def sign_certificate(self, csr: x509.CertificateSigningRequest,
                        issuer_private_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
                        issuer_cert: Optional[x509.Certificate] = None,
                        validity_days: int = 365,
                        certificate_type: CertificateType = CertificateType.SERVER_CERT) -> x509.Certificate:
        """签署证书
        
        Args:
            csr: 证书签名请求
            issuer_private_key: 颁发者私钥
            issuer_cert: 颁发者证书（自签名证书时为None）
            validity_days: 有效期天数
            certificate_type: 证书类型
            
        Returns:
            x509.Certificate: 签署的证书
        """
        # 确定颁发者
        if issuer_cert:
            issuer_name = issuer_cert.subject
        else:
            issuer_name = csr.subject
            
        # 构建证书
        builder = (x509.CertificateBuilder()
                  .subject_name(csr.subject)
                  .issuer_name(issuer_name)
                  .public_key(csr.public_key())
                  .serial_number(x509.random_serial_number())
                  .not_valid_before(datetime.utcnow())
                  .not_valid_after(datetime.utcnow() + timedelta(days=validity_days)))
        
        # 添加基础约束
        if certificate_type in [CertificateType.ROOT_CA, CertificateType.INTERMEDIATE_CA]:
            builder = builder.add_extension(
                x509.BasicConstraints(ca=True, path_length=None if certificate_type == CertificateType.ROOT_CA else 0),
                critical=True
            )
        else:
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
        
        # 添加密钥用法
        if certificate_type == CertificateType.SERVER_CERT:
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            )
        elif certificate_type == CertificateType.CLIENT_CERT:
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=True,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            )
            
        # 添加扩展密钥用法
        if certificate_type == CertificateType.SERVER_CERT:
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False
            )
        elif certificate_type == CertificateType.CLIENT_CERT:
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=False
            )
        elif certificate_type == CertificateType.EMAIL:
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.EMAIL_PROTECTION]),
                critical=False
            )
            
        # 复制SAN扩展
        san_extension = csr.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        if san_extension:
            builder = builder.add_extension(
                san_extension.value,
                critical=False
            )
            
        # 签署证书
        certificate = builder.sign(issuer_private_key, self.hash_algorithm, default_backend())
        return certificate
        
    def generate_self_signed_certificate(self, subject_info: Dict[str, str],
                                        validity_days: int = 365,
                                        san: Optional[List[str]] = None,
                                        key_size: int = 2048) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """生成自签名证书
        
        Args:
            subject_info: 主题信息
            validity_days: 有效期天数
            san: 主题备用名称
            key_size: 密钥大小
            
        Returns:
            Tuple: (证书, 私钥)
        """
        # 生成私钥
        private_key = self.generate_rsa_key(key_size)
        
        # 创建证书请求
        csr = self.create_certificate_request(private_key, subject_info, san)
        
        # 签署证书
        certificate = self.sign_certificate(
            csr, private_key, None, validity_days, CertificateType.ROOT_CA
        )
        
        return certificate, private_key
        
    def generate_certificate_chain(self, ca_info: Dict[str, str],
                                  server_info: Dict[str, str],
                                  validity_days: int = 365,
                                  san: Optional[List[str]] = None) -> Tuple[x509.Certificate, x509.Certificate, rsa.RSAPrivateKey]:
        """生成证书链（CA证书 + 服务器证书）
        
        Args:
            ca_info: CA证书主题信息
            server_info: 服务器证书主题信息
            validity_days: 有效期天数
            san: 服务器证书SAN
            
        Returns:
            Tuple: (CA证书, 服务器证书, CA私钥)
        """
        # 生成CA私钥和证书
        ca_private_key = self.generate_rsa_key(2048)
        ca_csr = self.create_certificate_request(ca_private_key, ca_info)
        ca_certificate = self.sign_certificate(
            ca_csr, ca_private_key, None, validity_days, CertificateType.ROOT_CA
        )
        
        # 生成服务器私钥和证书
        server_private_key = self.generate_rsa_key(2048)
        server_csr = self.create_certificate_request(server_private_key, server_info, san)
        server_certificate = self.sign_certificate(
            server_csr, ca_private_key, ca_certificate, validity_days, CertificateType.SERVER_CERT
        )
        
        return ca_certificate, server_certificate, ca_private_key


class CertificateValidator:
    """证书验证器"""
    
    def __init__(self):
        """初始化证书验证器"""
        pass
        
    def parse_certificate(self, cert_data: Union[str, bytes]) -> CertificateInfo:
        """解析证书数据
        
        Args:
            cert_data: 证书数据（ PEM格式字符串或字节）
            
        Returns:
            CertificateInfo: 证书信息对象
            
        Raises:
            CertificateError: 证书解析失败
        """
        try:
            if isinstance(cert_data, str):
                cert_data = cert_data.encode('utf-8')
                
            certificate = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # 提取主题信息
            subject = certificate.subject.rfc4514_string()
            issuer = certificate.issuer.rfc4514_string()
            
            # 计算指纹
            fingerprint_sha256 = certificate.fingerprint(hashes.SHA256()).hex()
            fingerprint_sha1 = certificate.fingerprint(hashes.SHA1()).hex()
            
            # 提取SAN
            san_list = []
            try:
                san_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                for name in san_ext.value:
                    if isinstance(name, x509.DNSName):
                        san_list.append(name.value)
                    elif isinstance(name, x509.IPAddress):
                        san_list.append(str(name.value))
            except x509.ExtensionNotFound:
                pass
                
            # 提取密钥用法
            key_usage_list = []
            try:
                key_usage_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
                for attr_name in dir(key_usage_ext.value):
                    if attr_name.startswith('_') or callable(getattr(key_usage_ext.value, attr_name)):
                        continue
                    if getattr(key_usage_ext.value, attr_name):
                        key_usage_list.append(attr_name)
            except x509.ExtensionNotFound:
                pass
                
            # 提取扩展密钥用法
            extended_key_usage_list = []
            try:
                eku_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
                for eku in eku_ext.value:
                    extended_key_usage_list.append(eku.dotted_string)
            except x509.ExtensionNotFound:
                pass
                
            # 确定证书状态
            now = datetime.utcnow()
            if now < certificate.not_valid_before:
                status = CertificateStatus.PENDING
            elif now > certificate.not_valid_after:
                status = CertificateStatus.EXPIRED
            else:
                status = CertificateStatus.VALID
                
            return CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=str(certificate.serial_number),
                not_before=certificate.not_valid_before,
                not_after=certificate.not_valid_after,
                public_key=certificate.public_key().__class__.__name__,
                signature_algorithm=certificate.signature_algorithm_oid._name,
                fingerprint_sha256=fingerprint_sha256,
                fingerprint_sha1=fingerprint_sha1,
                san=san_list,
                key_usage=key_usage_list,
                extended_key_usage=extended_key_usage_list,
                status=status
            )
            
        except Exception as e:
            raise CertificateError(f"证书解析失败: {str(e)}")
            
    def validate_certificate_chain(self, cert_chain: List[Union[str, bytes]]) -> CertificateChain:
        """验证证书链
        
        Args:
            cert_chain: 证书链列表
            
        Returns:
            CertificateChain: 证书链验证结果
        """
        certificates = []
        validation_errors = []
        
        # 解析所有证书
        for i, cert_data in enumerate(cert_chain):
            try:
                cert_info = self.parse_certificate(cert_data)
                certificates.append(cert_info)
            except Exception as e:
                validation_errors.append(f"证书 {i} 解析失败: {str(e)}")
                continue
                
        if not certificates:
            return CertificateChain([], is_valid=False, validation_errors=validation_errors)
            
        # 验证证书链
        is_valid = True
        
        # 检查证书有效期
        now = datetime.utcnow()
        for cert in certificates:
            if now < cert.not_before:
                validation_errors.append(f"证书尚未生效: {cert.subject}")
                is_valid = False
            elif now > cert.not_after:
                validation_errors.append(f"证书已过期: {cert.subject}")
                is_valid = False
                
        # 验证证书链关系
        for i in range(len(certificates) - 1):
            issuer = certificates[i + 1]
            subject = certificates[i]
            
            if subject.issuer != issuer.subject:
                validation_errors.append(f"证书链不匹配: {subject.subject} 的颁发者不是 {issuer.subject}")
                is_valid = False
                
        # 识别根证书
        root_ca = None
        if certificates:
            last_cert = certificates[-1]
            if last_cert.subject == last_cert.issuer:
                root_ca = last_cert
                
        return CertificateChain(
            certificates=certificates,
            root_ca=root_ca,
            is_valid=is_valid,
            validation_errors=validation_errors
        )
        
    def verify_certificate_signature(self, cert_data: Union[str, bytes],
                                   issuer_cert_data: Union[str, bytes]) -> bool:
        """验证证书签名
        
        Args:
            cert_data: 证书数据
            issuer_cert_data: 颁发者证书数据
            
        Returns:
            bool: 签名验证结果
        """
        try:
            if isinstance(cert_data, str):
                cert_data = cert_data.encode('utf-8')
            if isinstance(issuer_cert_data, str):
                issuer_cert_data = issuer_cert_data.encode('utf-8')
                
            certificate = x509.load_pem_x509_certificate(cert_data, default_backend())
            issuer_certificate = x509.load_pem_x509_certificate(issuer_cert_data, default_backend())
            
            # 使用颁发者公钥验证证书签名
            issuer_public_key = issuer_certificate.public_key()
            issuer_public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                certificate.signature_algorithm_oid
            )
            
            return True
            
        except Exception:
            return False
            
    def check_certificate_revocation(self, cert_info: CertificateInfo,
                                   crl_data: Optional[Union[str, bytes]] = None) -> bool:
        """检查证书吊销状态
        
        Args:
            cert_info: 证书信息
            crl_data: CRL数据
            
        Returns:
            bool: 是否被吊销
        """
        # TODO: 实现CRL检查逻辑
        # 这里需要根据具体的CRL格式进行解析和验证
        return False
        
    def get_certificate_from_host(self, hostname: str, port: int = 443) -> Optional[CertificateInfo]:
        """从主机获取证书
        
        Args:
            hostname: 主机名
            port: 端口号
            
        Returns:
            CertificateInfo: 证书信息，获取失败返回None
        """
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(True)
                    cert_pem = ssl.DER_cert_to_PEM_cert(cert_der)
                    return self.parse_certificate(cert_pem)
                    
        except Exception as e:
            logging.error(f"从主机 {hostname}:{port} 获取证书失败: {str(e)}")
            return None


class CertificateManager:
    """证书管理器"""
    
    def __init__(self, cert_dir: str = "./certificates"):
        """初始化证书管理器
        
        Args:
            cert_dir: 证书存储目录
        """
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)
        
        self.generator = CertificateGenerator()
        self.validator = CertificateValidator()
        
    def save_certificate(self, certificate: x509.Certificate, 
                        filename: str, format: str = "pem") -> bool:
        """保存证书到文件
        
        Args:
            certificate: 证书对象
            filename: 文件名
            format: 文件格式（pem, der）
            
        Returns:
            bool: 保存成功返回True
        """
        try:
            file_path = self.cert_dir / filename
            
            if format.lower() == "pem":
                cert_data = certificate.public_bytes(serialization.Encoding.PEM)
            elif format.lower() == "der":
                cert_data = certificate.public_bytes(serialization.Encoding.DER)
            else:
                raise ValueError(f"不支持的格式: {format}")
                
            with open(file_path, 'wb') as f:
                f.write(cert_data)
                
            logging.info(f"证书保存成功: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"保存证书失败: {str(e)}")
            return False
            
    def save_private_key(self, private_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
                        filename: str, format: str = "pem", password: Optional[bytes] = None) -> bool:
        """保存私钥到文件
        
        Args:
            private_key: 私钥对象
            filename: 文件名
            format: 文件格式（pem, der）
            password: 加密密码
            
        Returns:
            bool: 保存成功返回True
        """
        try:
            file_path = self.cert_dir / filename
            
            encryption = serialization.NoEncryption()
            if password:
                encryption = serialization.BestAvailableEncryption(password)
                
            if format.lower() == "pem":
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=encryption
                )
            elif format.lower() == "der":
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=encryption
                )
            else:
                raise ValueError(f"不支持的格式: {format}")
                
            with open(file_path, 'wb') as f:
                f.write(key_data)
                
            logging.info(f"私钥保存成功: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"保存私钥失败: {str(e)}")
            return False
            
    def load_certificate(self, filename: str) -> Optional[x509.Certificate]:
        """从文件加载证书
        
        Args:
            filename: 文件名
            
        Returns:
            x509.Certificate: 证书对象，加载失败返回None
        """
        try:
            file_path = self.cert_dir / filename
            
            with open(file_path, 'rb') as f:
                cert_data = f.read()
                
            # 尝试PEM格式
            try:
                return x509.load_pem_x509_certificate(cert_data, default_backend())
            except ValueError:
                pass
                
            # 尝试DER格式
            try:
                return x509.load_der_x509_certificate(cert_data, default_backend())
            except ValueError:
                pass
                
            raise ValueError("不支持的证书格式")
            
        except Exception as e:
            logging.error(f"加载证书失败: {str(e)}")
            return None
            
    def load_private_key(self, filename: str, password: Optional[bytes] = None) -> Optional[Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey]]:
        """从文件加载私钥
        
        Args:
            filename: 文件名
            password: 解密密码
            
        Returns:
            私钥对象，加载失败返回None
        """
        try:
            file_path = self.cert_dir / filename
            
            with open(file_path, 'rb') as f:
                key_data = f.read()
                
            # 尝试PEM格式
            try:
                return serialization.load_pem_private_key(
                    key_data, password=password, backend=default_backend()
                )
            except ValueError:
                pass
                
            # 尝试DER格式
            try:
                return serialization.load_der_private_key(
                    key_data, password=password, backend=default_backend()
                )
            except ValueError:
                pass
                
            raise ValueError("不支持的私钥格式")
            
        except Exception as e:
            logging.error(f"加载私钥失败: {str(e)}")
            return None
            
    def create_pkcs12_bundle(self, certificate: x509.Certificate,
                           private_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
                           filename: str, password: Optional[bytes] = None) -> bool:
        """创建PKCS#12包
        
        Args:
            certificate: 证书对象
            private_key: 私钥对象
            filename: 文件名
            password: 保护密码
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            file_path = self.cert_dir / filename
            
            # 创建PKCS#12包
            p12 = pkcs12.serialize_key_and_certificates(
                name=b"certificate",
                key=private_key,
                cert=certificate,
                cas=None,
                encryption_algorithm=serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
            )
            
            with open(file_path, 'wb') as f:
                f.write(p12)
                
            logging.info(f"PKCS#12包创建成功: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"创建PKCS#12包失败: {str(e)}")
            return False
            
    def get_certificate_info(self, certificate: x509.Certificate) -> Dict[str, Any]:
        """获取证书详细信息
        
        Args:
            certificate: 证书对象
            
        Returns:
            Dict: 证书信息字典
        """
        return self.validator.parse_certificate(
            certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        ).__dict__


# 全局证书管理器实例
cert_manager = CertificateManager()


def generate_self_signed_certificate(subject_info: Dict[str, str],
                                   validity_days: int = 365,
                                   san: Optional[List[str]] = None,
                                   key_size: int = 2048) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """生成自签名证书便捷函数"""
    return cert_manager.generator.generate_self_signed_certificate(
        subject_info, validity_days, san, key_size
    )


def parse_certificate(cert_data: Union[str, bytes]) -> CertificateInfo:
    """解析证书便捷函数"""
    return cert_manager.validator.parse_certificate(cert_data)


def validate_certificate_chain(cert_chain: List[Union[str, bytes]]) -> CertificateChain:
    """验证证书链便捷函数"""
    return cert_manager.validator.validate_certificate_chain(cert_chain)


def get_certificate_from_host(hostname: str, port: int = 443) -> Optional[CertificateInfo]:
    """从主机获取证书便捷函数"""
    return cert_manager.validator.get_certificate_from_host(hostname, port)


def save_certificate(certificate: x509.Certificate, filename: str, format: str = "pem") -> bool:
    """保存证书便捷函数"""
    return cert_manager.save_certificate(certificate, filename, format)


def load_certificate(filename: str) -> Optional[x509.Certificate]:
    """加载证书便捷函数"""
    return cert_manager.load_certificate(filename)


def create_pkcs12_bundle(certificate: x509.Certificate,
                        private_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
                        filename: str, password: Optional[bytes] = None) -> bool:
    """创建PKCS#12包便捷函数"""
    return cert_manager.create_pkcs12_bundle(certificate, private_key, filename, password)


def verify_certificate_signature(cert_data: Union[str, bytes],
                               issuer_cert_data: Union[str, bytes]) -> bool:
    """验证证书签名便捷函数"""
    return cert_manager.validator.verify_certificate_signature(cert_data, issuer_cert_data)