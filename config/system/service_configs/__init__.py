# config/system/service_configs/__init__.py
"""
服务配置模块
管理所有微服务配置，包括API、数据库、缓存、网络等
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .. import config_manager


class ServiceType(Enum):
    """服务类型枚举"""
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    NETWORK = "network"
    DISCOVERY = "discovery"
    MESSAGE = "message"
    MODEL = "model"


class ServiceStatus(Enum):
    """服务状态枚举"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    type: ServiceType
    host: str
    port: int
    enabled: bool = True
    ssl_enabled: bool = False
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    health_check_path: Optional[str] = None
    authentication: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)

    def get_url(self) -> str:
        """获取服务URL"""
        protocol = "https" if self.ssl_enabled else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def get_health_url(self) -> Optional[str]:
        """获取健康检查URL"""
        if self.health_check_path:
            return f"{self.get_url()}{self.health_check_path}"
        return None


class ServiceManager:
    """服务管理器"""

    def __init__(self):
        self.services = {}
        self._load_all_service_configs()

    def _load_all_service_configs(self):
        """加载所有服务配置"""
        # 加载API配置
        api_config = config_manager.load_config('system/service_configs/api_config.yaml')
        self.services[ServiceType.API.value] = api_config

        # 加载数据库配置
        db_config = config_manager.load_config('system/service_configs/database_config.yaml')
        self.services[ServiceType.DATABASE.value] = db_config

        # 加载缓存配置
        cache_config = config_manager.load_config('system/service_configs/cache_config.yaml')
        self.services[ServiceType.CACHE.value] = cache_config

        # 加载网络配置
        network_config = config_manager.load_config('system/service_configs/network_config.yaml')
        self.services[ServiceType.NETWORK.value] = network_config

        # 加载服务发现配置
        discovery_config = config_manager.load_config('system/service_configs/service_discovery.yaml')
        self.services[ServiceType.DISCOVERY.value] = discovery_config

    def get_service_config(self, service_type: ServiceType) -> Dict:
        """获取指定类型的服务配置"""
        return self.services.get(service_type.value, {})

    def get_database_connection_string(self, db_type: str = "postgresql") -> str:
        """获取数据库连接字符串"""
        db_config = self.get_service_config(ServiceType.DATABASE)
        databases = db_config.get('databases', {})

        if db_type not in databases:
            raise ValueError(f"未知的数据库类型: {db_type}")

        db_info = databases[db_type]

        if db_type == "postgresql":
            return f"postgresql://{db_info['username']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/{db_info['database']}"
        elif db_type == "redis":
            return f"redis://{db_info['host']}:{db_info['port']}/{db_info.get('database', 0)}"
        elif db_type == "neo4j":
            return f"bolt://{db_info['host']}:{db_info['port']}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    def get_api_endpoint(self, api_name: str) -> str:
        """获取API端点URL"""
        api_config = self.get_service_config(ServiceType.API)
        endpoints = api_config.get('endpoints', {})

        if api_name not in endpoints:
            raise ValueError(f"未知的API端点: {api_name}")

        endpoint = endpoints[api_name]
        protocol = "https" if endpoint.get('ssl', False) else "http"
        host = endpoint.get('host', 'localhost')
        port = endpoint.get('port', 80)
        path = endpoint.get('path', '')

        return f"{protocol}://{host}:{port}{path}"


# 全局服务管理器实例
service_manager = ServiceManager()

__all__ = [
    'ServiceType',
    'ServiceStatus',
    'ServiceConfig',
    'ServiceManager',
    'service_manager'
]