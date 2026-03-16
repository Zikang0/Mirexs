"""
模型工具模块

提供AI模型管理的工具函数，包括模型注册、加载、保存、版本管理、验证、比较、部署等。
"""

import os
import json
import pickle
import joblib
import shutil
import hashlib
import tempfile
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from datetime import datetime
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import tensorflow as tf
from sklearn.base import BaseEstimator


class ModelInfo:
    """模型信息类"""
    
    def __init__(self, model_name: str, model_type: str, 
                 model_version: str = "1.0.0", 
                 metadata: Optional[Dict[str, Any]] = None):
        """初始化模型信息
        
        Args:
            model_name: 模型名称
            model_type: 模型类型 ('sklearn', 'pytorch', 'tensorflow', 'onnx', 'custom')
            model_version: 模型版本
            metadata: 模型元数据
        """
        self.model_name = model_name
        self.model_type = model_type
        self.model_version = model_version
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.model_hash = None
        self.model_size = 0
        self.parameters_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'model_version': self.model_version,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'model_hash': self.model_hash,
            'model_size': self.model_size,
            'parameters_count': self.parameters_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """从字典创建"""
        info = cls(
            model_name=data['model_name'],
            model_type=data['model_type'],
            model_version=data.get('model_version', '1.0.0'),
            metadata=data.get('metadata', {})
        )
        info.created_at = data.get('created_at', info.created_at)
        info.updated_at = data.get('updated_at', info.updated_at)
        info.model_hash = data.get('model_hash')
        info.model_size = data.get('model_size', 0)
        info.parameters_count = data.get('parameters_count', 0)
        return info


class ModelArchitecture:
    """模型架构类"""
    
    def __init__(self, architecture_name: str, 
                 architecture_config: Dict[str, Any]):
        """初始化模型架构
        
        Args:
            architecture_name: 架构名称
            architecture_config: 架构配置
        """
        self.architecture_name = architecture_name
        self.architecture_config = architecture_config
        self.input_shape = architecture_config.get('input_shape')
        self.output_shape = architecture_config.get('output_shape')
        self.layers = architecture_config.get('layers', [])
    
    def get_summary(self) -> str:
        """获取架构摘要"""
        summary = f"Architecture: {self.architecture_name}\n"
        summary += f"Input Shape: {self.input_shape}\n"
        summary += f"Output Shape: {self.output_shape}\n"
        summary += f"Layers: {len(self.layers)}\n"
        
        for i, layer in enumerate(self.layers):
            summary += f"  Layer {i+1}: {layer['type']} - {layer.get('params', {})}\n"
        
        return summary


class ModelLoader:
    """模型加载器"""
    
    @staticmethod
    def load_model(model_path: str, model_type: str = None,
                   device: str = 'cpu', **kwargs) -> Any:
        """加载模型
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型 (自动检测如果为None)
            device: 设备类型 (for pytorch)
            **kwargs: 其他参数
            
        Returns:
            加载的模型
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # 自动检测模型类型
        if model_type is None:
            model_type = ModelLoader._detect_model_type(model_path)
        
        if model_type == 'sklearn':
            return ModelLoader._load_sklearn(model_path, **kwargs)
        elif model_type == 'pytorch':
            return ModelLoader._load_pytorch(model_path, device, **kwargs)
        elif model_type == 'tensorflow':
            return ModelLoader._load_tensorflow(model_path, **kwargs)
        elif model_type == 'onnx':
            return ModelLoader._load_onnx(model_path, **kwargs)
        elif model_type == 'pickle':
            return ModelLoader._load_pickle(model_path, **kwargs)
        elif model_type == 'joblib':
            return ModelLoader._load_joblib(model_path, **kwargs)
        elif model_type == 'h5':
            return ModelLoader._load_h5(model_path, **kwargs)
        elif model_type == 'keras':
            return ModelLoader._load_keras(model_path, **kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    @staticmethod
    def _detect_model_type(model_path: str) -> str:
        """检测模型类型"""
        ext = os.path.splitext(model_path)[1].lower()
        
        if ext == '.pkl' or ext == '.pickle':
            return 'pickle'
        elif ext == '.joblib':
            return 'joblib'
        elif ext == '.pth' or ext == '.pt':
            return 'pytorch'
        elif ext == '.h5':
            return 'h5'
        elif ext == '.keras':
            return 'keras'
        elif ext == '.onnx':
            return 'onnx'
        elif ext == '.pb' or ext == '.hdf5':
            return 'tensorflow'
        else:
            # 尝试读取文件头
            try:
                with open(model_path, 'rb') as f:
                    header = f.read(10)
                
                if header.startswith(b'PK'):
                    return 'pickle'
                elif header.startswith(b'\x80'):
                    return 'pickle'
                elif header.startswith(b'\x89PK'):
                    return 'joblib'
                elif header.startswith(b'\x7fELF'):
                    return 'pytorch'
                elif header.startswith(b'\x1f\x8b'):
                    return 'tensorflow'
            except:
                pass
            
            return 'unknown'
    
    @staticmethod
    def _load_sklearn(model_path: str, **kwargs) -> BaseEstimator:
        """加载scikit-learn模型"""
        try:
            return joblib.load(model_path)
        except:
            with open(model_path, 'rb') as f:
                return pickle.load(f)
    
    @staticmethod
    def _load_pytorch(model_path: str, device: str = 'cpu', 
                     model_class: Optional[type] = None, **kwargs) -> nn.Module:
        """加载PyTorch模型"""
        if model_class:
            model = model_class(**kwargs)
            state_dict = torch.load(model_path, map_location=device)
            model.load_state_dict(state_dict)
        else:
            model = torch.load(model_path, map_location=device)
        
        model.eval()
        return model
    
    @staticmethod
    def _load_tensorflow(model_path: str, **kwargs) -> tf.keras.Model:
        """加载TensorFlow模型"""
        return tf.keras.models.load_model(model_path, **kwargs)
    
    @staticmethod
    def _load_onnx(model_path: str, **kwargs):
        """加载ONNX模型"""
        import onnxruntime as ort
        return ort.InferenceSession(model_path, **kwargs)
    
    @staticmethod
    def _load_pickle(model_path: str, **kwargs) -> Any:
        """加载pickle模型"""
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    @staticmethod
    def _load_joblib(model_path: str, **kwargs) -> Any:
        """加载joblib模型"""
        return joblib.load(model_path)
    
    @staticmethod
    def _load_h5(model_path: str, **kwargs) -> tf.keras.Model:
        """加载H5模型"""
        return tf.keras.models.load_model(model_path, **kwargs)
    
    @staticmethod
    def _load_keras(model_path: str, **kwargs) -> tf.keras.Model:
        """加载Keras模型"""
        return tf.keras.models.load_model(model_path, **kwargs)


class ModelSaver:
    """模型保存器"""
    
    @staticmethod
    def save_model(model: Any, model_path: str, model_type: str = None,
                   overwrite: bool = True, **kwargs) -> bool:
        """保存模型
        
        Args:
            model: 模型对象
            model_path: 保存路径
            model_type: 模型类型
            overwrite: 是否覆盖已存在文件
            **kwargs: 其他参数
            
        Returns:
            是否保存成功
        """
        if os.path.exists(model_path) and not overwrite:
            return False
        
        os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
        
        if model_type is None:
            model_type = ModelSaver._detect_model_type(model)
        
        try:
            if model_type == 'sklearn':
                ModelSaver._save_sklearn(model, model_path, **kwargs)
            elif model_type == 'pytorch':
                ModelSaver._save_pytorch(model, model_path, **kwargs)
            elif model_type == 'tensorflow':
                ModelSaver._save_tensorflow(model, model_path, **kwargs)
            elif model_type == 'onnx':
                ModelSaver._save_onnx(model, model_path, **kwargs)
            elif model_type == 'pickle':
                ModelSaver._save_pickle(model, model_path, **kwargs)
            elif model_type == 'joblib':
                ModelSaver._save_joblib(model, model_path, **kwargs)
            elif model_type == 'h5':
                ModelSaver._save_h5(model, model_path, **kwargs)
            elif model_type == 'keras':
                ModelSaver._save_keras(model, model_path, **kwargs)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            return True
        except Exception as e:
            print(f"Failed to save model: {e}")
            return False
    
    @staticmethod
    def _detect_model_type(model: Any) -> str:
        """检测模型类型"""
        if hasattr(model, 'predict') and hasattr(model, 'fit'):
            if hasattr(model, 'classes_'):
                return 'sklearn'
        
        if isinstance(model, nn.Module):
            return 'pytorch'
        
        if isinstance(model, tf.keras.Model):
            return 'tensorflow'
        
        return 'pickle'
    
    @staticmethod
    def _save_sklearn(model: BaseEstimator, model_path: str, **kwargs):
        """保存scikit-learn模型"""
        joblib.dump(model, model_path)
    
    @staticmethod
    def _save_pytorch(model: nn.Module, model_path: str, 
                     save_state_dict: bool = True, **kwargs):
        """保存PyTorch模型"""
        if save_state_dict:
            torch.save(model.state_dict(), model_path)
        else:
            torch.save(model, model_path)
    
    @staticmethod
    def _save_tensorflow(model: tf.keras.Model, model_path: str, **kwargs):
        """保存TensorFlow模型"""
        model.save(model_path, **kwargs)
    
    @staticmethod
    def _save_onnx(model, model_path: str, **kwargs):
        """保存ONNX模型"""
        # ONNX模型通常已经是文件，这里只是复制
        if isinstance(model, str):
            shutil.copy2(model, model_path)
        elif hasattr(model, 'SerializeToString'):
            with open(model_path, 'wb') as f:
                f.write(model.SerializeToString())
    
    @staticmethod
    def _save_pickle(model: Any, model_path: str, **kwargs):
        """保存pickle模型"""
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
    
    @staticmethod
    def _save_joblib(model: Any, model_path: str, **kwargs):
        """保存joblib模型"""
        joblib.dump(model, model_path)
    
    @staticmethod
    def _save_h5(model: tf.keras.Model, model_path: str, **kwargs):
        """保存H5模型"""
        model.save(model_path, save_format='h5', **kwargs)
    
    @staticmethod
    def _save_keras(model: tf.keras.Model, model_path: str, **kwargs):
        """保存Keras模型"""
        model.save(model_path, **kwargs)


class ModelVersionManager:
    """模型版本管理器"""
    
    def __init__(self, base_path: str):
        """初始化版本管理器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = base_path
        self.models_path = os.path.join(base_path, 'models')
        self.versions_path = os.path.join(base_path, 'versions.json')
        
        os.makedirs(self.models_path, exist_ok=True)
        self._init_versions()
    
    def _init_versions(self):
        """初始化版本文件"""
        if not os.path.exists(self.versions_path):
            self._save_versions({})
    
    def _load_versions(self) -> Dict[str, Any]:
        """加载版本信息"""
        with open(self.versions_path, 'r') as f:
            return json.load(f)
    
    def _save_versions(self, versions: Dict[str, Any]):
        """保存版本信息"""
        with open(self.versions_path, 'w') as f:
            json.dump(versions, f, indent=2)
    
    def _generate_version(self, model_name: str, versions: Dict) -> str:
        """生成版本号"""
        if model_name not in versions:
            return "1.0.0"
        
        existing_versions = list(versions[model_name].keys())
        if not existing_versions:
            return "1.0.0"
        
        # 获取最新版本并递增patch
        latest = max(existing_versions, key=lambda x: tuple(map(int, x.split('.'))))
        major, minor, patch = map(int, latest.split('.'))
        patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def save_version(self, model: Any, model_name: str, 
                    model_type: str, metadata: Optional[Dict] = None) -> str:
        """保存模型版本
        
        Args:
            model: 模型对象
            model_name: 模型名称
            model_type: 模型类型
            metadata: 元数据
            
        Returns:
            版本号
        """
        versions = self._load_versions()
        version = self._generate_version(model_name, versions)
        
        # 保存模型
        model_filename = f"{model_name}_v{version}.pkl"
        model_path = os.path.join(self.models_path, model_filename)
        ModelSaver.save_model(model, model_path, model_type)
        
        # 计算模型哈希
        model_hash = self._calculate_file_hash(model_path)
        model_size = os.path.getsize(model_path)
        params_count = count_parameters(model)
        
        # 更新版本信息
        if model_name not in versions:
            versions[model_name] = {}
        
        versions[model_name][version] = {
            'path': model_path,
            'type': model_type,
            'hash': model_hash,
            'size': model_size,
            'parameters': params_count,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self._save_versions(versions)
        return version
    
    def load_version(self, model_name: str, version: Optional[str] = None) -> Any:
        """加载模型版本
        
        Args:
            model_name: 模型名称
            version: 版本号，None表示最新版本
            
        Returns:
            模型对象
        """
        versions = self._load_versions()
        
        if model_name not in versions:
            raise ValueError(f"Model {model_name} not found")
        
        if version is None:
            # 获取最新版本
            version = max(versions[model_name].keys(), 
                         key=lambda x: tuple(map(int, x.split('.'))))
        
        if version not in versions[model_name]:
            raise ValueError(f"Version {version} not found for model {model_name}")
        
        model_info = versions[model_name][version]
        return ModelLoader.load_model(model_info['path'], model_info['type'])
    
    def list_versions(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """列出版本
        
        Args:
            model_name: 模型名称，None表示所有模型
            
        Returns:
            版本信息
        """
        versions = self._load_versions()
        
        if model_name:
            return {model_name: versions.get(model_name, {})}
        
        return versions
    
    def delete_version(self, model_name: str, version: str) -> bool:
        """删除版本
        
        Args:
            model_name: 模型名称
            version: 版本号
            
        Returns:
            是否成功
        """
        versions = self._load_versions()
        
        if model_name not in versions or version not in versions[model_name]:
            return False
        
        # 删除模型文件
        model_path = versions[model_name][version]['path']
        if os.path.exists(model_path):
            os.remove(model_path)
        
        # 删除版本信息
        del versions[model_name][version]
        
        if not versions[model_name]:
            del versions[model_name]
        
        self._save_versions(versions)
        return True
    
    def get_model_info(self, model_name: str, version: str) -> Dict[str, Any]:
        """获取模型信息
        
        Args:
            model_name: 模型名称
            version: 版本号
            
        Returns:
            模型信息
        """
        versions = self._load_versions()
        
        if model_name in versions and version in versions[model_name]:
            return versions[model_name][version]
        
        return {}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


class ModelValidator:
    """模型验证器"""
    
    @staticmethod
    def validate_model(model: Any, X_sample: np.ndarray, 
                      y_sample: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """验证模型
        
        Args:
            model: 模型对象
            X_sample: 样本输入
            y_sample: 样本输出（可选）
            
        Returns:
            验证结果
        """
        results = {
            'is_valid': False,
            'model_type': None,
            'has_predict': False,
            'has_predict_proba': False,
            'has_fit': False,
            'input_compatible': False,
            'output_compatible': False,
            'errors': [],
            'warnings': []
        }
        
        # 检查模型类型
        if isinstance(model, nn.Module):
            results['model_type'] = 'pytorch'
        elif isinstance(model, tf.keras.Model):
            results['model_type'] = 'tensorflow'
        elif hasattr(model, 'predict') and hasattr(model, 'fit'):
            results['model_type'] = 'sklearn'
        else:
            results['model_type'] = 'unknown'
        
        # 检查必要方法
        results['has_predict'] = hasattr(model, 'predict')
        results['has_predict_proba'] = hasattr(model, 'predict_proba')
        results['has_fit'] = hasattr(model, 'fit')
        
        # 验证输入兼容性
        try:
            if results['model_type'] == 'pytorch':
                import torch
                X_tensor = torch.FloatTensor(X_sample[:1])
                with torch.no_grad():
                    output = model(X_tensor)
                results['input_compatible'] = True
                results['output_compatible'] = output is not None
            
            elif results['model_type'] == 'tensorflow':
                output = model.predict(X_sample[:1])
                results['input_compatible'] = True
                results['output_compatible'] = output is not None
            
            elif results['model_type'] == 'sklearn' and results['has_predict']:
                output = model.predict(X_sample[:1])
                results['input_compatible'] = True
                results['output_compatible'] = output is not None
            
        except Exception as e:
            results['errors'].append(f"Input/Output validation failed: {str(e)}")
        
        results['is_valid'] = (results['input_compatible'] and 
                              results['output_compatible'] and
                              len(results['errors']) == 0)
        
        return results
    
    @staticmethod
    def validate_model_consistency(model1: Any, model2: Any, 
                                  X_test: np.ndarray) -> Dict[str, Any]:
        """验证模型一致性
        
        Args:
            model1: 第一个模型
            model2: 第二个模型
            X_test: 测试数据
            
        Returns:
            一致性验证结果
        """
        try:
            # 获取预测结果
            if hasattr(model1, 'predict'):
                pred1 = model1.predict(X_test)
            else:
                pred1 = None
            
            if hasattr(model2, 'predict'):
                pred2 = model2.predict(X_test)
            else:
                pred2 = None
            
            # 比较预测结果
            if pred1 is not None and pred2 is not None:
                if np.array_equal(pred1, pred2):
                    consistency = 1.0
                else:
                    # 计算一致性比例
                    if len(pred1.shape) > 1:
                        # 对于概率输出，使用相关性
                        from scipy.stats import pearsonr
                        corrs = []
                        for i in range(pred1.shape[1]):
                            if len(pred1) > 1:
                                corr, _ = pearsonr(pred1[:, i], pred2[:, i])
                                corrs.append(abs(corr))
                        consistency = np.mean(corrs) if corrs else 0
                    else:
                        # 对于分类输出，使用准确率
                        consistency = np.mean(pred1 == pred2)
            else:
                consistency = 0
            
            return {
                'is_consistent': consistency > 0.95,
                'consistency_score': float(consistency),
                'predictions_match': np.array_equal(pred1, pred2) if pred1 is not None else False
            }
        except Exception as e:
            return {
                'is_consistent': False,
                'consistency_score': 0,
                'error': str(e)
            }


class ModelMetrics:
    """模型指标类"""
    
    def __init__(self, model_name: str = None):
        """初始化模型指标
        
        Args:
            model_name: 模型名称
        """
        self.model_name = model_name
        self.metrics = {}
        self.training_history = {}
        self.evaluation_results = {}
    
    def add_metric(self, metric_name: str, value: float, 
                  metadata: Optional[Dict] = None):
        """添加指标"""
        self.metrics[metric_name] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
    
    def add_training_history(self, epoch: int, **kwargs):
        """添加训练历史"""
        if epoch not in self.training_history:
            self.training_history[epoch] = {}
        self.training_history[epoch].update(kwargs)
    
    def add_evaluation_result(self, dataset_name: str, **kwargs):
        """添加评估结果"""
        self.evaluation_results[dataset_name] = kwargs
    
    def get_best_metric(self, metric_name: str, mode: str = 'max') -> Tuple[float, int]:
        """获取最佳指标
        
        Args:
            metric_name: 指标名称
            mode: 'max' 或 'min'
            
        Returns:
            (最佳值, 对应轮次)
        """
        if not self.training_history:
            return 0, 0
        
        values = [(epoch, data.get(metric_name, 0)) 
                 for epoch, data in self.training_history.items()
                 if metric_name in data]
        
        if not values:
            return 0, 0
        
        if mode == 'max':
            best = max(values, key=lambda x: x[1])
        else:
            best = min(values, key=lambda x: x[1])
        
        return best[1], best[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_name': self.model_name,
            'metrics': self.metrics,
            'training_history': self.training_history,
            'evaluation_results': self.evaluation_results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetrics':
        """从字典创建"""
        metrics = cls(data.get('model_name'))
        metrics.metrics = data.get('metrics', {})
        metrics.training_history = data.get('training_history', {})
        metrics.evaluation_results = data.get('evaluation_results', {})
        return metrics


class ModelComparison:
    """模型比较器"""
    
    def __init__(self, models: Dict[str, Any]):
        """初始化模型比较器
        
        Args:
            models: 模型字典 {模型名: 模型对象}
        """
        self.models = models
        self.results = {}
    
    def compare_on_data(self, X_test: np.ndarray, y_test: np.ndarray,
                       metrics: List[str] = None) -> Dict[str, Dict[str, float]]:
        """在数据上比较模型
        
        Args:
            X_test: 测试特征
            y_test: 测试标签
            metrics: 比较指标列表
            
        Returns:
            比较结果
        """
        if metrics is None:
            metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        results = {}
        
        for name, model in self.models.items():
            model_results = {}
            y_pred = model.predict(X_test)
            
            if 'accuracy' in metrics:
                model_results['accuracy'] = accuracy_score(y_test, y_pred)
            
            if 'precision' in metrics:
                try:
                    model_results['precision'] = precision_score(y_test, y_pred, average='weighted', zero_division=0)
                except:
                    model_results['precision'] = 0
            
            if 'recall' in metrics:
                try:
                    model_results['recall'] = recall_score(y_test, y_pred, average='weighted', zero_division=0)
                except:
                    model_results['recall'] = 0
            
            if 'f1_score' in metrics:
                try:
                    model_results['f1_score'] = f1_score(y_test, y_pred, average='weighted', zero_division=0)
                except:
                    model_results['f1_score'] = 0
            
            results[name] = model_results
        
        self.results = results
        return results
    
    def compare_on_time(self, X_test: np.ndarray, n_runs: int = 10) -> Dict[str, Dict[str, float]]:
        """比较推理时间
        
        Args:
            X_test: 测试数据
            n_runs: 运行次数
            
        Returns:
            时间比较结果
        """
        import time
        
        results = {}
        
        for name, model in self.models.items():
            times = []
            
            for _ in range(n_runs):
                start = time.time()
                model.predict(X_test[:1])
                end = time.time()
                times.append((end - start) * 1000)  # 转换为毫秒
            
            results[name] = {
                'mean_time_ms': np.mean(times),
                'std_time_ms': np.std(times),
                'min_time_ms': np.min(times),
                'max_time_ms': np.max(times),
                'p95_time_ms': np.percentile(times, 95)
            }
        
        self.results['timing'] = results
        return results
    
    def compare_on_size(self) -> Dict[str, Dict[str, float]]:
        """比较模型大小
        
        Returns:
            大小比较结果
        """
        results = {}
        
        for name, model in self.models.items():
            size_bytes = 0
            params_count = count_parameters(model)
            
            # 尝试估算模型大小
            if isinstance(model, nn.Module):
                size_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
            elif isinstance(model, tf.keras.Model):
                size_bytes = model.count_params() * 4  # 假设float32
            
            results[name] = {
                'size_bytes': size_bytes,
                'size_mb': size_bytes / (1024 * 1024),
                'parameters': params_count
            }
        
        self.results['size'] = results
        return results
    
    def get_best_model(self, metric: str = 'accuracy', 
                      higher_is_better: bool = True) -> Optional[str]:
        """获取最佳模型
        
        Args:
            metric: 比较指标
            higher_is_better: 指标是否越高越好
            
        Returns:
            最佳模型名称
        """
        if not self.results:
            return None
        
        best_model = None
        best_value = float('-inf') if higher_is_better else float('inf')
        
        for name, metrics in self.results.items():
            if name == 'timing' or name == 'size':
                continue
            
            if metric in metrics:
                value = metrics[metric]
                if higher_is_better and value > best_value:
                    best_value = value
                    best_model = name
                elif not higher_is_better and value < best_value:
                    best_value = value
                    best_model = name
        
        return best_model
    
    def generate_report(self) -> str:
        """生成比较报告"""
        report = "\n" + "=" * 60 + "\n"
        report += "MODEL COMPARISON REPORT\n"
        report += "=" * 60 + "\n\n"
        
        for name, metrics in self.results.items():
            if name == 'timing' or name == 'size':
                continue
            
            report += f"Model: {name}\n"
            report += "-" * 40 + "\n"
            
            for metric, value in metrics.items():
                report += f"  {metric}: {value:.4f}\n"
            
            report += "\n"
        
        if 'timing' in self.results:
            report += "Inference Time (ms):\n"
            report += "-" * 40 + "\n"
            for name, times in self.results['timing'].items():
                report += f"  {name}: {times['mean_time_ms']:.2f} ± {times['std_time_ms']:.2f}\n"
            report += "\n"
        
        if 'size' in self.results:
            report += "Model Size:\n"
            report += "-" * 40 + "\n"
            for name, size_info in self.results['size'].items():
                report += f"  {name}: {size_info['size_mb']:.2f} MB ({size_info['parameters']:,} params)\n"
            report += "\n"
        
        best_model = self.get_best_model()
        if best_model:
            report += f"Best Model: {best_model}\n"
        
        return report


class ModelDeployment:
    """模型部署类"""
    
    def __init__(self, model: Any, model_name: str, version: str = "1.0.0"):
        """初始化模型部署
        
        Args:
            model: 模型对象
            model_name: 模型名称
            version: 版本号
        """
        self.model = model
        self.model_name = model_name
        self.version = version
        self.deployment_config = {}
        self.endpoints = []
        self.status = "pending"
    
    def export_to_onnx(self, output_path: str, input_shape: Tuple) -> bool:
        """导出为ONNX格式
        
        Args:
            output_path: 输出路径
            input_shape: 输入形状
            
        Returns:
            是否成功
        """
        try:
            if isinstance(self.model, nn.Module):
                import torch.onnx
                self.model.eval()
                dummy_input = torch.randn(*input_shape)
                torch.onnx.export(self.model, dummy_input, output_path,
                                 input_names=['input'], output_names=['output'])
                return True
            
            elif isinstance(self.model, tf.keras.Model):
                import tf2onnx
                import onnx
                spec = (tf.TensorSpec(input_shape, tf.float32, name="input"),)
                output_path = output_path.replace('.onnx', '')
                model_proto, _ = tf2onnx.convert.from_keras(self.model, 
                                                           input_signature=spec,
                                                           output_path=output_path)
                return True
            
            return False
        except Exception as e:
            print(f"Failed to export to ONNX: {e}")
            return False
    
    def export_to_tensorrt(self, output_path: str, input_shape: Tuple,
                          precision: str = 'fp32') -> bool:
        """导出为TensorRT格式
        
        Args:
            output_path: 输出路径
            input_shape: 输入形状
            precision: 精度 ('fp32', 'fp16', 'int8')
            
        Returns:
            是否成功
        """
        try:
            import tensorrt as trt
            
            # 创建TensorRT构建器
            logger = trt.Logger(trt.Logger.INFO)
            builder = trt.Builder(logger)
            
            # 创建网络
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            
            # 这里需要更复杂的转换逻辑
            # 通常需要先将模型转换为ONNX，然后用trtexec转换
            
            print("TensorRT export requires ONNX model first")
            return False
        except Exception as e:
            print(f"Failed to export to TensorRT: {e}")
            return False
    
    def create_endpoint(self, endpoint_name: str, protocol: str = 'http',
                       port: int = 8000, **kwargs) -> Dict[str, Any]:
        """创建服务端点
        
        Args:
            endpoint_name: 端点名称
            protocol: 协议
            port: 端口
            **kwargs: 其他参数
            
        Returns:
            端点信息
        """
        endpoint = {
            'name': endpoint_name,
            'protocol': protocol,
            'port': port,
            'url': f"{protocol}://localhost:{port}/{endpoint_name}",
            'created_at': datetime.now().isoformat(),
            'config': kwargs
        }
        
        self.endpoints.append(endpoint)
        return endpoint
    
    def deploy_to_docker(self, image_name: str, **kwargs) -> bool:
        """部署到Docker
        
        Args:
            image_name: Docker镜像名
            **kwargs: 其他参数
            
        Returns:
            是否成功
        """
        try:
            # 创建Dockerfile
            dockerfile = self._generate_dockerfile()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # 保存Dockerfile
                with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
                    f.write(dockerfile)
                
                # 保存模型
                model_path = os.path.join(tmpdir, 'model.pkl')
                ModelSaver.save_model(self.model, model_path)
                
                # 保存配置
                config = {
                    'model_name': self.model_name,
                    'version': self.version,
                    'endpoints': self.endpoints
                }
                with open(os.path.join(tmpdir, 'config.json'), 'w') as f:
                    json.dump(config, f, indent=2)
                
                # 构建Docker镜像
                import subprocess
                result = subprocess.run(['docker', 'build', '-t', image_name, tmpdir],
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.status = "deployed"
                    return True
                else:
                    print(f"Docker build failed: {result.stderr}")
                    return False
        except Exception as e:
            print(f"Failed to deploy to Docker: {e}")
            return False
    
    def _generate_dockerfile(self) -> str:
        """生成Dockerfile"""
        return """
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "serve.py"]
"""
    
    def get_deployment_info(self) -> Dict[str, Any]:
        """获取部署信息"""
        return {
            'model_name': self.model_name,
            'version': self.version,
            'status': self.status,
            'endpoints': self.endpoints,
            'config': self.deployment_config,
            'deployed_at': datetime.now().isoformat() if self.status == 'deployed' else None
        }


class ModelConverter:
    """模型转换器"""
    
    @staticmethod
    def sklearn_to_onnx(model: BaseEstimator, output_path: str,
                       input_shape: Tuple, **kwargs) -> bool:
        """将scikit-learn模型转换为ONNX"""
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            
            initial_type = [('float_input', FloatTensorType(input_shape))]
            onx = convert_sklearn(model, initial_types=initial_type, **kwargs)
            
            with open(output_path, 'wb') as f:
                f.write(onx.SerializeToString())
            
            return True
        except Exception as e:
            print(f"Failed to convert sklearn to ONNX: {e}")
            return False
    
    @staticmethod
    def pytorch_to_onnx(model: nn.Module, output_path: str,
                        input_shape: Tuple, **kwargs) -> bool:
        """将PyTorch模型转换为ONNX"""
        try:
            model.eval()
            dummy_input = torch.randn(*input_shape)
            torch.onnx.export(model, dummy_input, output_path,
                            input_names=['input'], output_names=['output'],
                            **kwargs)
            return True
        except Exception as e:
            print(f"Failed to convert PyTorch to ONNX: {e}")
            return False
    
    @staticmethod
    def tensorflow_to_onnx(model: tf.keras.Model, output_path: str,
                          **kwargs) -> bool:
        """将TensorFlow模型转换为ONNX"""
        try:
            import tf2onnx
            spec = (tf.TensorSpec(model.input_shape, tf.float32, name="input"),)
            model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec,
                                                       output_path=output_path, **kwargs)
            return True
        except Exception as e:
            print(f"Failed to convert TensorFlow to ONNX: {e}")
            return False
    
    @staticmethod
    def onnx_to_tensorrt(onnx_path: str, output_path: str,
                        precision: str = 'fp32', **kwargs) -> bool:
        """将ONNX模型转换为TensorRT"""
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.INFO)
            builder = trt.Builder(logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, logger)
            
            with open(onnx_path, 'rb') as f:
                if not parser.parse(f.read()):
                    for error in range(parser.num_errors):
                        print(parser.get_error(error))
                    return False
            
            config = builder.create_builder_config()
            
            if precision == 'fp16':
                config.set_flag(trt.BuilderFlag.FP16)
            elif precision == 'int8':
                config.set_flag(trt.BuilderFlag.INT8)
            
            engine = builder.build_engine(network, config)
            with open(output_path, 'wb') as f:
                f.write(engine.serialize())
            
            return True
        except Exception as e:
            print(f"Failed to convert ONNX to TensorRT: {e}")
            return False


class ModelOptimizer:
    """模型优化器"""
    
    @staticmethod
    def quantize_model(model: Any, model_type: str,
                      calibration_data: Optional[np.ndarray] = None) -> Any:
        """量化模型"""
        if model_type == 'tensorflow':
            import tensorflow as tf
            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            
            if calibration_data is not None:
                def representative_dataset():
                    for i in range(min(100, len(calibration_data))):
                        yield [calibration_data[i:i+1].astype(np.float32)]
                
                converter.representative_dataset = representative_dataset
                converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
                converter.inference_input_type = tf.uint8
                converter.inference_output_type = tf.uint8
            
            return converter.convert()
        
        elif model_type == 'pytorch':
            # PyTorch量化
            import torch.quantization as quant
            model.eval()
            model.qconfig = quant.get_default_qconfig('fbgemm')
            quant.prepare(model, inplace=True)
            
            if calibration_data is not None:
                # 校准
                pass
            
            quant.convert(model, inplace=True)
            return model
        
        else:
            raise ValueError(f"Quantization not supported for {model_type}")
    
    @staticmethod
    def prune_model(model: nn.Module, amount: float = 0.3) -> nn.Module:
        """剪枝模型"""
        import torch.nn.utils.prune as prune
        
        for name, module in model.named_modules():
            if isinstance(module, nn.Conv2d) or isinstance(module, nn.Linear):
                prune.l1_unstructured(module, name='weight', amount=amount)
                prune.remove(module, 'weight')
        
        return model
    
    @staticmethod
    def distill_model(teacher_model: Any, student_model: Any,
                     X_train: np.ndarray, y_train: np.ndarray,
                     temperature: float = 3.0, alpha: float = 0.5) -> Any:
        """知识蒸馏"""
        # 简化实现
        if hasattr(student_model, 'fit'):
            student_model.fit(X_train, y_train)
        
        return student_model


def count_parameters(model: Any) -> int:
    """计算模型参数量"""
    if isinstance(model, nn.Module):
        return sum(p.numel() for p in model.parameters())
    elif isinstance(model, tf.keras.Model):
        return model.count_params()
    elif hasattr(model, 'coef_') and hasattr(model, 'intercept_'):
        # sklearn linear model
        coef_size = model.coef_.size if hasattr(model.coef_, 'size') else 0
        intercept_size = model.intercept_.size if hasattr(model.intercept_, 'size') else 0
        return coef_size + intercept_size
    else:
        return 0


def get_model_size(model: Any) -> float:
    """获取模型大小（MB）"""
    if isinstance(model, nn.Module):
        param_size = sum(p.numel() * p.element_size() for p in model.parameters())
        buffer_size = sum(b.numel() * b.element_size() for b in model.buffers())
        return (param_size + buffer_size) / (1024 * 1024)
    elif isinstance(model, tf.keras.Model):
        return model.count_params() * 4 / (1024 * 1024)  # 假设float32
    else:
        return 0


def create_model_summary(model: Any, model_name: str = None) -> Dict[str, Any]:
    """创建模型摘要"""
    summary = {
        'model_name': model_name or model.__class__.__name__,
        'parameters': count_parameters(model),
        'size_mb': get_model_size(model),
        'type': model.__class__.__name__
    }
    
    # 获取模型结构
    if isinstance(model, nn.Module):
        summary['architecture'] = str(model)
        summary['num_layers'] = len(list(model.modules()))
    elif isinstance(model, tf.keras.Model):
        summary['num_layers'] = len(model.layers)
    
    return summary