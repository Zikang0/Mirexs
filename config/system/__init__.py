# config/system/__init__.py
"""
系统配置模块
管理Mirexs所有系统级配置，包括模型、服务、平台等
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, validator, Field

class ConfigError(Exception):
    """配置相关异常"""
    pass

logger = logging.getLogger("mirexs.config.system")

class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_dir: str = None):
        """初始化配置管理器

        Args:
            config_dir: 配置目录路径，默认为项目config目录
        """
        if config_dir is None:
            # 从环境变量或默认路径获取配置目录
            config_dir = os.environ.get('MIREXS_CONFIG_DIR',
                                       str(Path(__file__).parent.parent))

        self.config_dir = Path(config_dir)
        self._config_cache = {}
        self._watchers = []

        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)

    def load_config(self, config_path: str, reload: bool = False) -> Dict:
        """加载配置文件

        Args:
            config_path: 配置文件相对路径
            reload: 是否强制重新加载

        Returns:
            Dict: 配置字典
        """
        cache_key = str(config_path)

        if not reload and cache_key in self._config_cache:
            return self._config_cache[cache_key]

        full_path = self.config_dir / config_path

        if not full_path.exists():
            raise ConfigError(f"配置文件不存在: {full_path}")

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                if full_path.suffix in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif full_path.suffix == '.json':
                    import json
                    config = json.load(f)
                else:
                    # 尝试作为Python配置文件加载
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        config_path.stem, full_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 提取所有大写配置
                    config = {
                        k: v for k, v in module.__dict__.items()
                        if not k.startswith('_') and k.isupper()
                    }

            self._config_cache[cache_key] = config
            return config

        except Exception as e:
                raise ConfigError(f"加载配置文件失败 {full_path}: {str(e)}")

    def get_config(self, config_name: str, default: Optional[Dict[str, Any]] = None,
                   reload: bool = False) -> Dict[str, Any]:
        """
        获取配置（v2 推荐入口）。

        该方法用于支持各子系统使用统一调用方式：
        - `get_config("text_input_config")`
        - `get_config("auto_correction_config")`

        查找策略（从高到低）：
        1) 若 `config_name` 看起来像路径（包含 `/` 或后缀），则直接按路径加载
        2) `system/component_configs/{name}.yaml`
        3) `system/service_configs/{name}.yaml`
        4) `system/model_configs/{name}.yaml`
        5) `system/platform_configs/{name}.yaml`
        6) `system/{name}.yaml`

        Args:
            config_name: 配置名称或相对路径
            default: 默认返回值（默认 `{}`）
            reload: 是否强制重新加载

        Returns:
            Dict[str, Any]: 配置字典；找不到时返回 default
        """
        if default is None:
            default = {}

        name = str(config_name or "").strip()
        if not name:
            return default

        # 1) 直接路径加载
        if ("/" in name) or ("\\" in name) or name.endswith((".yaml", ".yml", ".json", ".py")):
            try:
                return self.load_config(name, reload=reload) or default
            except Exception:
                return default

        # 2) 按约定目录查找
        candidates = [
            f"system/component_configs/{name}.yaml",
            f"system/component_configs/{name}.yml",
            f"system/service_configs/{name}.yaml",
            f"system/service_configs/{name}.yml",
            f"system/model_configs/{name}.yaml",
            f"system/model_configs/{name}.yml",
            f"system/platform_configs/{name}.yaml",
            f"system/platform_configs/{name}.yml",
            f"system/{name}.yaml",
            f"system/{name}.yml",
        ]

        for rel_path in candidates:
            try:
                return self.load_config(rel_path, reload=reload) or default
            except Exception:
                continue

        return default

    def save_config(self, config_path: str, config: Dict):
        """保存配置文件

        Args:
            config_path: 配置文件相对路径
            config: 配置字典
        """
        full_path = self.config_dir / config_path

        try:
            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                if full_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False,
                              allow_unicode=True, indent=2)
                elif full_path.suffix == '.json':
                    import json
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    # 保存为Python配置文件
                    config_str = "# Auto-generated configuration file\n\n"
                    for key, value in config.items():
                        if key.isupper():
                            if isinstance(value, str):
                                config_str += f"{key} = '{value}'\n"
                            else:
                                config_str += f"{key} = {value}\n"
                    f.write(config_str)

            # 清除缓存并通知观察者
            cache_key = str(config_path)
            if cache_key in self._config_cache:
                del self._config_cache[cache_key]

            self._notify_watchers(config_path)

        except Exception as e:
            raise ConfigError(f"保存配置文件失败 {full_path}: {str(e)}")

    def get_system_config(self, reload: bool = False) -> Dict[str, Any]:
        """获取系统主配置"""
        config = self.load_config('system/main_config.yaml', reload=reload)
        self._validate_main_config_v2(config)
        return config

    def _validate_main_config_v2(self, config: Any) -> None:
        """
        v2 主配置最小校验。

        说明：此处只做“版本与必需字段”的最小校验，避免把业务运行绑死在过度复杂的 schema 上。
        """
        if not isinstance(config, dict):
            raise ConfigError("system/main_config.yaml 解析结果不是 dict；请检查 YAML 格式是否正确。")

        meta = config.get("meta") or {}
        schema_version = str(meta.get("schema_version") or "").strip()
        if not schema_version:
            raise ConfigError("system/main_config.yaml 缺少 meta.schema_version（v2 必填）。")
        if not schema_version.startswith("2."):
            raise ConfigError(f"system/main_config.yaml schema_version={schema_version} 不受支持（期望 2.x）。")

        required_top = ["system", "mode", "logging", "paths"]
        missing = [k for k in required_top if k not in config]
        if missing:
            raise ConfigError(f"system/main_config.yaml 缺少必需字段: {missing}")

    def get_model_config(self, model_type: str) -> Dict:
        """获取指定模型类型配置

        Args:
            model_type: 模型类型，如 'speech', 'vision', 'nlp', '3d'
        """
        config_file = f'system/model_configs/{model_type}_models.yaml'
        return self.load_config(config_file)

    def get_service_config(self) -> Dict:
        """获取服务配置"""
        return self.load_config('system/service_configs/api_config.yaml')

    def get_platform_config(self, platform: str = None) -> Dict:
        """获取平台配置

        Args:
            platform: 平台名称，如 'windows', 'linux', 'macos', 'mobile'
                     为None时返回跨平台配置
        """
        if platform is None:
            return self.load_config('system/platform_configs/cross_platform.yaml')
        else:
            config_file = f'system/platform_configs/{platform}_config.yaml'
            return self.load_config(config_file)

    def register_watcher(self, callback):
        """注册配置变更观察者

        Args:
            callback: 回调函数，接收(config_path)参数
        """
        self._watchers.append(callback)

    def _notify_watchers(self, config_path: str):
        """通知配置变更观察者"""
        for callback in self._watchers:
            try:
                callback(config_path)
            except Exception as e:
                print(f"配置观察者回调失败: {e}")

# 全局配置管理器实例
config_manager = ConfigManager()

# 配置验证模型
class SystemConfig(BaseModel):
    """系统主配置验证模型"""
    version: str = Field(..., description="系统版本")
    debug: bool = Field(False, description="调试模式")
    log_level: str = Field("INFO", description="日志级别")
    data_dir: str = Field("data", description="数据目录")
    cache_dir: str = Field("cache", description="缓存目录")

    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'日志级别必须是 {valid_levels} 之一')
        return v.upper()

# 导出主要功能
__all__ = [
    'ConfigError',
    'ConfigManager',
    'config_manager',
    'SystemConfig'
]
