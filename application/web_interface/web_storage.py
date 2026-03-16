"""
Web存储模块 - Mirexs Web界面

提供浏览器端数据存储功能，包括：
1. localStorage 管理
2. sessionStorage 管理
3. IndexedDB 管理
4. Cookies 管理
5. 缓存管理
6. 数据加密
"""

import logging
import time
import json
import base64
import hashlib
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class StorageType(Enum):
    """存储类型枚举"""
    LOCAL = "local"
    SESSION = "session"
    INDEXED_DB = "indexed_db"
    COOKIE = "cookie"
    CACHE = "cache"

class StorageEvent(Enum):
    """存储事件枚举"""
    SET = "set"
    GET = "get"
    DELETE = "delete"
    CLEAR = "clear"
    EXPIRED = "expired"

@dataclass
class StorageItem:
    """存储项"""
    key: str
    value: Any
    type: StorageType
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    encrypted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StorageConfig:
    """Web存储配置"""
    # 加密配置
    enable_encryption: bool = False
    encryption_key: Optional[str] = None
    
    # 过期检查
    enable_expiry: bool = True
    expiry_check_interval: int = 3600  # 1小时
    
    # 配额限制
    max_local_size: int = 5 * 1024 * 1024  # 5MB
    max_session_size: int = 5 * 1024 * 1024  # 5MB
    max_cookie_size: int = 4096  # 4KB
    
    # 默认过期时间
    default_ttl: Optional[int] = None  # 秒
    
    # 序列化
    serializer: str = "json"  # json, msgpack

class WebStorage:
    """
    Web存储管理器
    
    负责浏览器端数据存储的管理，包括：
    - 多种存储类型支持
    - 数据加密
    - 过期管理
    - 配额管理
    - 事件通知
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        """
        初始化Web存储管理器
        
        Args:
            config: 存储配置
        """
        self.config = config or StorageConfig()
        
        # 存储数据
        self._local_storage: Dict[str, StorageItem] = {}
        self._session_storage: Dict[str, StorageItem] = {}
        self._indexed_db: Dict[str, StorageItem] = {}
        self._cookies: Dict[str, StorageItem] = {}
        self._cache: Dict[str, StorageItem] = {}
        
        # 监听器
        self._listeners: Dict[StorageType, List[Callable[[StorageEvent, str, Any], None]]] = {
            StorageType.LOCAL: [],
            StorageType.SESSION: [],
            StorageType.INDEXED_DB: [],
            StorageType.COOKIE: [],
            StorageType.CACHE: []
        }
        
        # 加载初始数据
        self._load_from_browser()
        
        # 启动过期检查
        if self.config.enable_expiry:
            self._start_expiry_check()
        
        logger.info("WebStorage initialized")
    
    def _load_from_browser(self):
        """从浏览器加载初始数据"""
        # 实际实现中会从window.localStorage等读取
        logger.debug("Loading data from browser storage")
    
    def _start_expiry_check(self):
        """启动过期检查"""
        import threading
        
        def check_loop():
            while True:
                try:
                    self._check_expiry()
                    time.sleep(self.config.expiry_check_interval)
                except Exception as e:
                    logger.error(f"Expiry check error: {e}")
        
        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()
        logger.debug("Expiry check started")
    
    def _check_expiry(self):
        """检查并清理过期项"""
        current_time = time.time()
        
        for storage_type, storage in self._get_storage_dicts().items():
            expired_keys = []
            
            for key, item in storage.items():
                if item.expires_at and item.expires_at < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del storage[key]
                self._notify_listeners(storage_type, StorageEvent.EXPIRED, key, None)
                logger.debug(f"Expired item removed: {storage_type.value}.{key}")
    
    def _get_storage_dicts(self) -> Dict[StorageType, Dict[str, StorageItem]]:
        """获取所有存储字典"""
        return {
            StorageType.LOCAL: self._local_storage,
            StorageType.SESSION: self._session_storage,
            StorageType.INDEXED_DB: self._indexed_db,
            StorageType.COOKIE: self._cookies,
            StorageType.CACHE: self._cache
        }
    
    def _get_storage(self, storage_type: StorageType) -> Dict[str, StorageItem]:
        """获取指定类型的存储字典"""
        storages = self._get_storage_dicts()
        return storages.get(storage_type, {})
    
    def _encrypt(self, data: Any) -> str:
        """加密数据"""
        if not self.config.enable_encryption:
            return json.dumps(data)
        
        # 简化加密实现
        json_str = json.dumps(data)
        if self.config.encryption_key:
            # 使用密钥进行简单混淆
            key = self.config.encryption_key
            result = []
            for i, c in enumerate(json_str):
                key_char = key[i % len(key)]
                result.append(chr(ord(c) ^ ord(key_char)))
            return base64.b64encode(''.join(result).encode()).decode()
        
        return base64.b64encode(json_str.encode()).decode()
    
    def _decrypt(self, data: str) -> Any:
        """解密数据"""
        try:
            if not self.config.enable_encryption:
                return json.loads(data)
            
            # 简化解密实现
            decoded = base64.b64decode(data).decode()
            if self.config.encryption_key:
                key = self.config.encryption_key
                result = []
                for i, c in enumerate(decoded):
                    key_char = key[i % len(key)]
                    result.append(chr(ord(c) ^ ord(key_char)))
                return json.loads(''.join(result))
            
            return json.loads(decoded)
        except:
            return data
    
    def set(self, key: str, value: Any, storage_type: StorageType = StorageType.LOCAL,
            ttl: Optional[int] = None, encrypt: Optional[bool] = None):
        """
        设置存储项
        
        Args:
            key: 键名
            value: 值
            storage_type: 存储类型
            ttl: 存活时间（秒）
            encrypt: 是否加密
        """
        storage = self._get_storage(storage_type)
        
        # 计算过期时间
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        elif self.config.default_ttl is not None:
            expires_at = time.time() + self.config.default_ttl
        
        # 是否加密
        should_encrypt = encrypt if encrypt is not None else self.config.enable_encryption
        
        # 创建存储项
        item = StorageItem(
            key=key,
            value=self._encrypt(value) if should_encrypt else value,
            type=storage_type,
            expires_at=expires_at,
            encrypted=should_encrypt
        )
        
        # 检查配额
        if not self._check_quota(storage_type, item):
            logger.warning(f"Storage quota exceeded for {storage_type.value}")
            return
        
        storage[key] = item
        
        # 同步到浏览器
        self._sync_to_browser(storage_type, key, item)
        
        self._notify_listeners(storage_type, StorageEvent.SET, key, value)
        logger.debug(f"Item set: {storage_type.value}.{key}")
    
    def get(self, key: str, storage_type: StorageType = StorageType.LOCAL,
            default: Any = None) -> Any:
        """
        获取存储项
        
        Args:
            key: 键名
            storage_type: 存储类型
            default: 默认值
        
        Returns:
            存储的值
        """
        storage = self._get_storage(storage_type)
        
        if key not in storage:
            return default
        
        item = storage[key]
        
        # 检查过期
        if item.expires_at and item.expires_at < time.time():
            self.delete(key, storage_type)
            return default
        
        # 解密
        value = self._decrypt(item.value) if item.encrypted else item.value
        
        self._notify_listeners(storage_type, StorageEvent.GET, key, value)
        
        return value
    
    def delete(self, key: str, storage_type: StorageType = StorageType.LOCAL):
        """
        删除存储项
        
        Args:
            key: 键名
            storage_type: 存储类型
        """
        storage = self._get_storage(storage_type)
        
        if key in storage:
            del storage[key]
            self._sync_to_browser(storage_type, key, None, delete=True)
            self._notify_listeners(storage_type, StorageEvent.DELETE, key, None)
            logger.debug(f"Item deleted: {storage_type.value}.{key}")
    
    def clear(self, storage_type: Optional[StorageType] = None):
        """
        清空存储
        
        Args:
            storage_type: 存储类型，None表示清空所有
        """
        if storage_type:
            storages = {storage_type: self._get_storage(storage_type)}
        else:
            storages = self._get_storage_dicts()
        
        for stype, storage in storages.items():
            storage.clear()
            self._sync_to_browser(stype, None, None, clear=True)
            self._notify_listeners(stype, StorageEvent.CLEAR, None, None)
            logger.debug(f"Storage cleared: {stype.value}")
    
    def has(self, key: str, storage_type: StorageType = StorageType.LOCAL) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            storage_type: 存储类型
        
        Returns:
            是否存在
        """
        storage = self._get_storage(storage_type)
        return key in storage
    
    def keys(self, storage_type: StorageType = StorageType.LOCAL) -> List[str]:
        """
        获取所有键名
        
        Args:
            storage_type: 存储类型
        
        Returns:
            键名列表
        """
        storage = self._get_storage(storage_type)
        return list(storage.keys())
    
    def size(self, storage_type: StorageType = StorageType.LOCAL) -> int:
        """
        获取存储项数量
        
        Args:
            storage_type: 存储类型
        
        Returns:
            数量
        """
        storage = self._get_storage(storage_type)
        return len(storage)
    
    def _check_quota(self, storage_type: StorageType, item: StorageItem) -> bool:
        """检查配额"""
        # 估算大小
        size = len(json.dumps(item.__dict__))
        
        if storage_type == StorageType.LOCAL:
            current_size = sum(len(json.dumps(i.__dict__)) for i in self._local_storage.values())
            return current_size + size <= self.config.max_local_size
        elif storage_type == StorageType.SESSION:
            current_size = sum(len(json.dumps(i.__dict__)) for i in self._session_storage.values())
            return current_size + size <= self.config.max_session_size
        elif storage_type == StorageType.COOKIE:
            current_size = sum(len(json.dumps(i.__dict__)) for i in self._cookies.values())
            return current_size + size <= self.config.max_cookie_size
        
        return True
    
    def _sync_to_browser(self, storage_type: StorageType, key: Optional[str],
                        item: Optional[StorageItem], delete: bool = False,
                        clear: bool = False):
        """同步到浏览器存储"""
        # 实际实现中会调用浏览器API
        pass
    
    def _notify_listeners(self, storage_type: StorageType, event: StorageEvent,
                         key: Optional[str], value: Any):
        """通知监听器"""
        for listener in self._listeners.get(storage_type, []):
            try:
                listener(event, key, value)
            except Exception as e:
                logger.error(f"Error in storage listener: {e}")
    
    def add_listener(self, storage_type: StorageType, 
                    listener: Callable[[StorageEvent, Optional[str], Any], None]):
        """
        添加监听器
        
        Args:
            storage_type: 存储类型
            listener: 监听函数
        """
        if storage_type in self._listeners:
            self._listeners[storage_type].append(listener)
    
    def remove_listener(self, storage_type: StorageType,
                       listener: Callable[[StorageEvent, Optional[str], Any], None]):
        """
        移除监听器
        
        Args:
            storage_type: 存储类型
            listener: 监听函数
        """
        if storage_type in self._listeners and listener in self._listeners[storage_type]:
            self._listeners[storage_type].remove(listener)
    
    def get_storage_info(self, storage_type: Optional[StorageType] = None) -> Dict[str, Any]:
        """
        获取存储信息
        
        Args:
            storage_type: 存储类型
        
        Returns:
            存储信息
        """
        if storage_type:
            storages = {storage_type: self._get_storage(storage_type)}
        else:
            storages = self._get_storage_dicts()
        
        info = {}
        for stype, storage in storages.items():
            total_size = sum(len(json.dumps(i.__dict__)) for i in storage.values())
            info[stype.value] = {
                "count": len(storage),
                "size": total_size,
                "keys": list(storage.keys())[:10]  # 只显示前10个
            }
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Web存储管理器状态
        
        Returns:
            状态字典
        """
        return {
            "config": {
                "enable_encryption": self.config.enable_encryption,
                "enable_expiry": self.config.enable_expiry,
                "default_ttl": self.config.default_ttl
            },
            "storage_info": self.get_storage_info(),
            "listeners": {
                stype.value: len(listeners)
                for stype, listeners in self._listeners.items()
            }
        }
    
    def shutdown(self):
        """关闭Web存储管理器"""
        logger.info("Shutting down WebStorage...")
        
        # 清空所有监听器
        self._listeners.clear()
        
        # 可选：保存所有数据
        for storage_type in StorageType:
            self._sync_to_browser(storage_type, None, None, clear=False)
        
        logger.info("WebStorage shutdown completed")

# 单例模式实现
_web_storage_instance: Optional[WebStorage] = None

def get_web_storage(config: Optional[StorageConfig] = None) -> WebStorage:
    """
    获取Web存储管理器单例
    
    Args:
        config: 存储配置
    
    Returns:
        Web存储管理器实例
    """
    global _web_storage_instance
    if _web_storage_instance is None:
        _web_storage_instance = WebStorage(config)
    return _web_storage_instance

