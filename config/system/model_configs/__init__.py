# config/system/model_configs/__init__.py
"""
模型配置模块
管理所有AI模型配置，包括语音、视觉、NLP、3D等
"""

import os
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml

from .. import config_manager

class ModelType(Enum):
    """模型类型枚举"""
    SPEECH = "speech"
    VISION = "vision"
    NLP = "nlp"
    THREED = "3d"
    REASONING = "reasoning"

class ModelFramework(Enum):
    """模型框架枚举"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    ONNX = "onnx"
    JAX = "jax"
    TRT = "tensorrt"

class ModelDevice(Enum):
    """模型运行设备枚举"""
    CPU = "cpu"
    GPU = "gpu"
    AUTO = "auto"
    MULTI_GPU = "multi_gpu"

@dataclass
class ModelConfig:
    """基础模型配置"""
    name: str
    type: ModelType
    framework: ModelFramework
    device: ModelDevice = ModelDevice.AUTO
    path: Optional[str] = None
    url: Optional[str] = None
    version: str = "latest"
    enabled: bool = True
    priority: int = 1
    memory_mb: int = 1024
    requires_gpu: bool = False
    parameters: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        # 自动确定设备要求
        if self.requires_gpu and self.device == ModelDevice.CPU:
            self.device = ModelDevice.GPU
        elif self.device == ModelDevice.AUTO:
            self.device = ModelDevice.GPU if self.requires_gpu else ModelDevice.CPU

class ModelManager:
    """模型配置管理器"""
    
    def __init__(self):
        self.model_registry = {}
        self._load_all_model_configs()
    
    def _load_all_model_configs(self):
        """加载所有模型配置"""
        model_types = ["speech", "vision", "nlp", "3d"]
        
        for model_type in model_types:
            try:
                config = config_manager.get_model_config(model_type)
                self.model_registry[model_type] = config
            except Exception as e:
                print(f"加载{model_type}模型配置失败: {e}")
    
    def get_model(self, model_type: Union[str, ModelType], model_name: str = None) -> Dict:
        """获取模型配置
        
        Args:
            model_type: 模型类型
            model_name: 模型名称，为None时返回该类型所有模型
            
        Returns:
            Dict: 模型配置
        """
        if isinstance(model_type, ModelType):
            model_type = model_type.value
        
        if model_type not in self.model_registry:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        if model_name is None:
            return self.model_registry[model_type]
        
        # 查找指定名称的模型
        models = self.model_registry[model_type].get('models', [])
        for model in models:
            if model.get('name') == model_name:
                return model
        
        raise ValueError(f"未找到模型: {model_type}/{model_name}")
    
    def get_active_models(self, model_type: Union[str, ModelType] = None) -> List[Dict]:
        """获取启用的模型配置
        
        Args:
            model_type: 模型类型，为None时返回所有启用的模型
            
        Returns:
            List[Dict]: 启用的模型配置列表
        """
        active_models = []
        
        if model_type is not None:
            if isinstance(model_type, ModelType):
                model_type = model_type.value
            
            if model_type in self.model_registry:
                models = self.model_registry[model_type].get('models', [])
                active_models.extend([m for m in models if m.get('enabled', True)])
        else:
            # 返回所有类型的启用模型
            for mt in self.model_registry.values():
                models = mt.get('models', [])
                active_models.extend([m for m in models if m.get('enabled', True)])
        
        return active_models
    
    def get_model_path(self, model_type: str, model_name: str) -> Path:
        """获取模型文件路径
        
        Args:
            model_type: 模型类型
            model_name: 模型名称
            
        Returns:
            Path: 模型文件路径
        """
        model_config = self.get_model(model_type, model_name)
        
        # 优先使用本地路径
        if 'path' in model_config and model_config['path']:
            return Path(model_config['path'])
        
        # 检查默认模型目录
        main_config = config_manager.get_system_config()
        models_dir = Path(main_config.get('paths', {}).get('models_dir', 'data/models'))
        
        # 构建模型路径
        model_path = models_dir / model_type / f"{model_name}.pth"
        if model_path.exists():
            return model_path
        
        # 检查是否有其他扩展名
        for ext in ['.pth', '.pt', '.onnx', '.h5', '.pb']:
            alt_path = models_dir / model_type / f"{model_name}{ext}"
            if alt_path.exists():
                return alt_path
        
        # 如果没有找到本地文件，返回默认路径
        return models_dir / model_type / f"{model_name}.pth"

# 全局模型管理器实例
model_manager = ModelManager()

__all__ = [
    'ModelType',
    'ModelFramework',
    'ModelDevice',
    'ModelConfig',
    'ModelManager',
    'model_manager'
]