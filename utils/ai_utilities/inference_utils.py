"""
推理工具模块

提供AI模型推理的工具函数，包括模型包装、批量预测、推理优化、性能分析等。
"""

import os
import time
import json
import pickle
import warnings
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import torch
import torch.nn as nn
import tensorflow as tf
import onnxruntime as ort


@dataclass
class PredictionResult:
    """预测结果类"""
    predictions: np.ndarray
    probabilities: Optional[np.ndarray] = None
    inference_time: float = 0.0
    model_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelWrapper:
    """模型包装器"""
    
    def __init__(self, model: Any, model_type: str = 'auto',
                 device: str = 'cpu', name: str = None):
        """初始化模型包装器
        
        Args:
            model: 模型对象
            model_type: 模型类型 ('pytorch', 'tensorflow', 'sklearn', 'onnx', 'auto')
            device: 设备类型
            name: 模型名称
        """
        self.model = model
        self.model_type = self._detect_model_type(model) if model_type == 'auto' else model_type
        self.device = device
        self.name = name or model.__class__.__name__
        self.input_shape = None
        self.output_shape = None
        
        # 模型特定设置
        self._setup_model()
    
    def _detect_model_type(self, model: Any) -> str:
        """检测模型类型"""
        if isinstance(model, nn.Module):
            return 'pytorch'
        elif isinstance(model, tf.keras.Model):
            return 'tensorflow'
        elif hasattr(model, 'predict') and hasattr(model, 'fit'):
            return 'sklearn'
        elif isinstance(model, ort.InferenceSession):
            return 'onnx'
        elif hasattr(model, 'predict'):
            return 'custom'
        else:
            return 'unknown'
    
    def _setup_model(self):
        """设置模型"""
        if self.model_type == 'pytorch':
            self.model.to(self.device)
            self.model.eval()
            
            # 获取输入输出形状
            try:
                dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
                with torch.no_grad():
                    output = self.model(dummy_input)
                self.input_shape = dummy_input.shape
                self.output_shape = output.shape
            except:
                pass
        
        elif self.model_type == 'tensorflow':
            # 获取输入输出形状
            if hasattr(self.model, 'input_shape'):
                self.input_shape = self.model.input_shape
            if hasattr(self.model, 'output_shape'):
                self.output_shape = self.model.output_shape
    
    def predict(self, X: np.ndarray, return_prob: bool = False,
                **kwargs) -> PredictionResult:
        """预测
        
        Args:
            X: 输入数据
            return_prob: 是否返回概率
            **kwargs: 其他参数
            
        Returns:
            预测结果
        """
        start_time = time.time()
        
        if self.model_type == 'pytorch':
            predictions, probabilities = self._predict_pytorch(X, return_prob, **kwargs)
        elif self.model_type == 'tensorflow':
            predictions, probabilities = self._predict_tensorflow(X, return_prob, **kwargs)
        elif self.model_type == 'sklearn':
            predictions, probabilities = self._predict_sklearn(X, return_prob, **kwargs)
        elif self.model_type == 'onnx':
            predictions, probabilities = self._predict_onnx(X, return_prob, **kwargs)
        else:
            predictions, probabilities = self._predict_custom(X, return_prob, **kwargs)
        
        inference_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        return PredictionResult(
            predictions=predictions,
            probabilities=probabilities,
            inference_time=inference_time,
            model_name=self.name
        )
    
    def _predict_pytorch(self, X: np.ndarray, return_prob: bool,
                         **kwargs) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """PyTorch预测"""
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            output = self.model(X_tensor, **kwargs)
            
            if isinstance(output, tuple):
                output = output[0]
            
            if return_prob:
                if hasattr(torch.nn.functional, 'softmax'):
                    probabilities = torch.nn.functional.softmax(output, dim=1).cpu().numpy()
                else:
                    probabilities = output.cpu().numpy()
                
                predictions = np.argmax(probabilities, axis=1)
                return predictions, probabilities
            else:
                predictions = output.cpu().numpy()
                if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                    predictions = np.argmax(predictions, axis=1)
                return predictions, None
    
    def _predict_tensorflow(self, X: np.ndarray, return_prob: bool,
                            **kwargs) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """TensorFlow预测"""
        output = self.model.predict(X, **kwargs)
        
        if return_prob:
            if len(output.shape) > 1 and output.shape[1] > 1:
                probabilities = output
                predictions = np.argmax(output, axis=1)
            else:
                probabilities = output
                predictions = (output > 0.5).astype(int).flatten()
            
            return predictions, probabilities
        else:
            predictions = output
            if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                predictions = np.argmax(predictions, axis=1)
            return predictions, None
    
    def _predict_sklearn(self, X: np.ndarray, return_prob: bool,
                          **kwargs) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Scikit-learn预测"""
        predictions = self.model.predict(X, **kwargs)
        
        if return_prob and hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X, **kwargs)
            return predictions, probabilities
        else:
            return predictions, None
    
    def _predict_onnx(self, X: np.ndarray, return_prob: bool,
                      **kwargs) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """ONNX预测"""
        input_name = self.model.get_inputs()[0].name
        output = self.model.run(None, {input_name: X.astype(np.float32)})[0]
        
        if return_prob:
            if len(output.shape) > 1 and output.shape[1] > 1:
                probabilities = output
                predictions = np.argmax(output, axis=1)
            else:
                probabilities = output
                predictions = (output > 0.5).astype(int).flatten()
            
            return predictions, probabilities
        else:
            predictions = output
            if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                predictions = np.argmax(predictions, axis=1)
            return predictions, None
    
    def _predict_custom(self, X: np.ndarray, return_prob: bool,
                        **kwargs) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """自定义模型预测"""
        if hasattr(self.model, 'predict'):
            predictions = self.model.predict(X, **kwargs)
        else:
            predictions = self.model(X, **kwargs)
        
        if return_prob and hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X, **kwargs)
            return predictions, probabilities
        else:
            return predictions, None
    
    def predict_batch(self, X: np.ndarray, batch_size: int = 32,
                      return_prob: bool = False, **kwargs) -> PredictionResult:
        """批量预测"""
        n_samples = len(X)
        n_batches = (n_samples + batch_size - 1) // batch_size
        
        all_predictions = []
        all_probabilities = []
        
        start_time = time.time()
        
        for i in range(n_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, n_samples)
            batch_X = X[start_idx:end_idx]
            
            result = self.predict(batch_X, return_prob=return_prob, **kwargs)
            all_predictions.append(result.predictions)
            
            if return_prob and result.probabilities is not None:
                all_probabilities.append(result.probabilities)
        
        predictions = np.concatenate(all_predictions)
        probabilities = np.concatenate(all_probabilities) if all_probabilities else None
        
        inference_time = (time.time() - start_time) * 1000
        
        return PredictionResult(
            predictions=predictions,
            probabilities=probabilities,
            inference_time=inference_time,
            model_name=self.name
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            'name': self.name,
            'type': self.model_type,
            'device': self.device,
            'input_shape': self.input_shape,
            'output_shape': self.output_shape
        }
        
        if self.model_type == 'pytorch':
            info['parameters'] = sum(p.numel() for p in self.model.parameters())
        elif self.model_type == 'tensorflow':
            info['parameters'] = self.model.count_params()
        
        return info


class BatchPredictor:
    """批量预测器"""
    
    def __init__(self, model_wrapper: ModelWrapper, batch_size: int = 32,
                 num_workers: int = 1, use_threads: bool = True):
        """初始化批量预测器
        
        Args:
            model_wrapper: 模型包装器
            batch_size: 批处理大小
            num_workers: 工作线程数
            use_threads: 是否使用线程池
        """
        self.model_wrapper = model_wrapper
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.use_threads = use_threads
        
        if num_workers > 1:
            self.executor = (ThreadPoolExecutor if use_threads else ProcessPoolExecutor)(max_workers=num_workers)
        else:
            self.executor = None
    
    def predict(self, X: np.ndarray, return_prob: bool = False,
                **kwargs) -> PredictionResult:
        """预测"""
        if self.num_workers == 1:
            return self.model_wrapper.predict_batch(X, self.batch_size, return_prob, **kwargs)
        
        # 多线程/进程预测
        n_samples = len(X)
        n_batches = (n_samples + self.batch_size - 1) // self.batch_size
        
        futures = []
        for i in range(n_batches):
            start_idx = i * self.batch_size
            end_idx = min((i + 1) * self.batch_size, n_samples)
            batch_X = X[start_idx:end_idx]
            
            future = self.executor.submit(
                self.model_wrapper.predict,
                batch_X,
                return_prob=return_prob,
                **kwargs
            )
            futures.append(future)
        
        all_predictions = []
        all_probabilities = []
        
        start_time = time.time()
        
        for future in futures:
            result = future.result()
            all_predictions.append(result.predictions)
            if return_prob and result.probabilities is not None:
                all_probabilities.append(result.probabilities)
        
        predictions = np.concatenate(all_predictions)
        probabilities = np.concatenate(all_probabilities) if all_probabilities else None
        
        inference_time = (time.time() - start_time) * 1000
        
        return PredictionResult(
            predictions=predictions,
            probabilities=probabilities,
            inference_time=inference_time,
            model_name=self.model_wrapper.name
        )
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False)


class InferenceOptimizer:
    """推理优化器"""
    
    @staticmethod
    def optimize_pytorch(model: nn.Module, example_input: torch.Tensor,
                         optimization_level: str = 'o1') -> nn.Module:
        """优化PyTorch模型
        
        Args:
            model: PyTorch模型
            example_input: 示例输入
            optimization_level: 优化级别 ('o1', 'o2', 'o3')
            
        Returns:
            优化后的模型
        """
        model.eval()
        
        # TorchScript优化
        try:
            if optimization_level == 'o1':
                # 脚本化
                scripted_model = torch.jit.script(model)
            elif optimization_level == 'o2':
                # 追踪
                scripted_model = torch.jit.trace(model, example_input)
            elif optimization_level == 'o3':
                # 脚本化 + 优化
                scripted_model = torch.jit.script(model)
                scripted_model = torch.jit.optimize_for_inference(scripted_model)
            else:
                return model
            
            return scripted_model
        except Exception as e:
            warnings.warn(f"Failed to optimize PyTorch model: {e}")
            return model
    
    @staticmethod
    def optimize_tensorflow(model: tf.keras.Model,
                            optimization_level: str = 'o1') -> tf.keras.Model:
        """优化TensorFlow模型
        
        Args:
            model: TensorFlow模型
            optimization_level: 优化级别 ('o1', 'o2', 'o3')
            
        Returns:
            优化后的模型
        """
        try:
            if optimization_level == 'o1':
                # 转换为TFLite
                converter = tf.lite.TFLiteConverter.from_keras_model(model)
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                tflite_model = converter.convert()
                return tflite_model
            
            elif optimization_level == 'o2':
                # 使用XLA
                tf.config.optimizer.set_jit(True)
                return model
            
            elif optimization_level == 'o3':
                # 转换为TensorRT
                from tensorflow.python.compiler.tensorrt import trt_convert as trt
                converter = trt.TrtGraphConverterV2(input_saved_model_dir=model)
                converter.convert()
                return converter
            else:
                return model
        except Exception as e:
            warnings.warn(f"Failed to optimize TensorFlow model: {e}")
            return model
    
    @staticmethod
    def optimize_onnx(model_path: str, output_path: str,
                      optimization_level: str = 'o1') -> bool:
        """优化ONNX模型
        
        Args:
            model_path: ONNX模型路径
            output_path: 输出路径
            optimization_level: 优化级别
            
        Returns:
            是否成功
        """
        try:
            import onnx
            from onnxruntime.transformers import optimizer
            
            # 加载模型
            model = onnx.load(model_path)
            
            # 优化
            opt_options = optimizer.OptimizationOptions()
            opt_model = optimizer.optimize_model(
                model_path,
                'bert' if 'bert' in model_path.lower() else 'gpt2',
                num_heads=12,
                hidden_size=768
            )
            
            # 保存优化后的模型
            opt_model.save_model_to_file(output_path)
            
            return True
        except Exception as e:
            warnings.warn(f"Failed to optimize ONNX model: {e}")
            return False


class ModelQuantizer:
    """模型量化器"""
    
    @staticmethod
    def quantize_pytorch(model: nn.Module, calibration_data: torch.Tensor = None,
                         dtype: str = 'int8') -> nn.Module:
        """量化PyTorch模型
        
        Args:
            model: PyTorch模型
            calibration_data: 校准数据
            dtype: 数据类型 ('int8', 'fp16')
            
        Returns:
            量化后的模型
        """
        import torch.quantization as quant
        
        model.eval()
        
        if dtype == 'int8':
            # 配置量化
            model.qconfig = quant.get_default_qconfig('fbgemm')
            quant.prepare(model, inplace=True)
            
            # 校准
            if calibration_data is not None:
                with torch.no_grad():
                    model(calibration_data)
            
            # 转换
            quant.convert(model, inplace=True)
            
            return model
        
        elif dtype == 'fp16':
            # FP16量化
            return model.half()
        
        else:
            return model
    
    @staticmethod
    def quantize_tensorflow(model: tf.keras.Model,
                            calibration_data: np.ndarray = None,
                            dtype: str = 'int8') -> bytes:
        """量化TensorFlow模型
        
        Args:
            model: TensorFlow模型
            calibration_data: 校准数据
            dtype: 数据类型
            
        Returns:
            量化后的模型字节
        """
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        if dtype == 'int8':
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.uint8
            converter.inference_output_type = tf.uint8
            
            if calibration_data is not None:
                def representative_dataset():
                    for i in range(min(100, len(calibration_data))):
                        yield [calibration_data[i:i+1].astype(np.float32)]
                
                converter.representative_dataset = representative_dataset
        
        elif dtype == 'fp16':
            converter.target_spec.supported_types = [tf.float16]
        
        return converter.convert()


class ModelProfiler:
    """模型性能分析器"""
    
    def __init__(self, model_wrapper: ModelWrapper):
        """初始化性能分析器
        
        Args:
            model_wrapper: 模型包装器
        """
        self.model_wrapper = model_wrapper
    
    def profile_inference_time(self, X: np.ndarray, n_runs: int = 100,
                               warmup: int = 10) -> Dict[str, float]:
        """分析推理时间
        
        Args:
            X: 测试数据
            n_runs: 运行次数
            warmup: 预热次数
            
        Returns:
            推理时间统计
        """
        # 预热
        for _ in range(warmup):
            self.model_wrapper.predict(X[:1])
        
        # 测试推理时间
        times = []
        for _ in range(n_runs):
            start_time = time.time()
            self.model_wrapper.predict(X[:1])
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # 毫秒
        
        times = np.array(times)
        
        return {
            'mean_time_ms': float(np.mean(times)),
            'median_time_ms': float(np.median(times)),
            'min_time_ms': float(np.min(times)),
            'max_time_ms': float(np.max(times)),
            'std_time_ms': float(np.std(times)),
            'p95_time_ms': float(np.percentile(times, 95)),
            'p99_time_ms': float(np.percentile(times, 99)),
            'qps': float(1000 / np.mean(times))  # 每秒查询数
        }
    
    def profile_memory_usage(self, X: np.ndarray) -> Dict[str, float]:
        """分析内存使用
        
        Args:
            X: 测试数据
            
        Returns:
            内存使用统计
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 推理前内存
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行推理
        self.model_wrapper.predict(X)
        
        # 推理后内存
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        memory_after_gc = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'memory_before_mb': float(memory_before),
            'memory_after_mb': float(memory_after),
            'memory_after_gc_mb': float(memory_after_gc),
            'memory_increase_mb': float(memory_after - memory_before),
            'memory_peak_mb': float(memory_after)
        }
    
    def profile_throughput(self, X: np.ndarray, batch_sizes: List[int] = None) -> Dict[str, Any]:
        """分析吞吐量
        
        Args:
            X: 测试数据
            batch_sizes: 批大小列表
            
        Returns:
            吞吐量统计
        """
        if batch_sizes is None:
            batch_sizes = [1, 2, 4, 8, 16, 32, 64]
        
        results = {}
        
        for batch_size in batch_sizes:
            if batch_size > len(X):
                continue
            
            # 创建批量预测器
            predictor = BatchPredictor(self.model_wrapper, batch_size=batch_size)
            
            # 测试时间
            start_time = time.time()
            predictor.predict(X[:batch_size * 10])  # 使用10个批次
            end_time = time.time()
            
            total_time = end_time - start_time
            total_samples = batch_size * 10
            throughput = total_samples / total_time
            
            results[f'batch_{batch_size}'] = {
                'batch_size': batch_size,
                'throughput': float(throughput),
                'total_time': float(total_time),
                'samples_processed': total_samples
            }
        
        return results
    
    def generate_report(self, X: np.ndarray) -> str:
        """生成性能报告"""
        report = "\n" + "=" * 60 + "\n"
        report += "MODEL PERFORMANCE PROFILE\n"
        report += "=" * 60 + "\n\n"
        
        # 模型信息
        model_info = self.model_wrapper.get_model_info()
        report += f"Model: {model_info.get('name', 'Unknown')}\n"
        report += f"Type: {model_info.get('type', 'Unknown')}\n"
        report += f"Device: {model_info.get('device', 'Unknown')}\n"
        report += f"Parameters: {model_info.get('parameters', 0):,}\n"
        report += f"Input Shape: {model_info.get('input_shape')}\n"
        report += f"Output Shape: {model_info.get('output_shape')}\n\n"
        
        # 推理时间
        time_stats = self.profile_inference_time(X)
        report += "Inference Time (ms):\n"
        report += f"  Mean: {time_stats['mean_time_ms']:.2f}\n"
        report += f"  Median: {time_stats['median_time_ms']:.2f}\n"
        report += f"  Std: {time_stats['std_time_ms']:.2f}\n"
        report += f"  Min: {time_stats['min_time_ms']:.2f}\n"
        report += f"  Max: {time_stats['max_time_ms']:.2f}\n"
        report += f"  P95: {time_stats['p95_time_ms']:.2f}\n"
        report += f"  P99: {time_stats['p99_time_ms']:.2f}\n"
        report += f"  QPS: {time_stats['qps']:.2f}\n\n"
        
        # 内存使用
        memory_stats = self.profile_memory_usage(X)
        report += "Memory Usage (MB):\n"
        report += f"  Before: {memory_stats['memory_before_mb']:.2f}\n"
        report += f"  After: {memory_stats['memory_after_mb']:.2f}\n"
        report += f"  After GC: {memory_stats['memory_after_gc_mb']:.2f}\n"
        report += f"  Increase: {memory_stats['memory_increase_mb']:.2f}\n"
        report += f"  Peak: {memory_stats['memory_peak_mb']:.2f}\n\n"
        
        # 吞吐量
        throughput_stats = self.profile_throughput(X)
        report += "Throughput (samples/sec):\n"
        for batch_size, stats in throughput_stats.items():
            report += f"  {batch_size}: {stats['throughput']:.2f}\n"
        
        return report


class ONNXInferenceEngine:
    """ONNX推理引擎"""
    
    def __init__(self, model_path: str, providers: List[str] = None):
        """初始化ONNX推理引擎
        
        Args:
            model_path: ONNX模型路径
            providers: 执行提供者列表
        """
        self.model_path = model_path
        self.providers = providers or ['CPUExecutionProvider']
        self.session = ort.InferenceSession(model_path, providers=self.providers)
        
        # 获取输入输出信息
        self.inputs = self.session.get_inputs()
        self.outputs = self.session.get_outputs()
        self.input_names = [input.name for input in self.inputs]
        self.output_names = [output.name for output in self.outputs]
    
    def predict(self, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """预测"""
        outputs = self.session.run(self.output_names, inputs)
        return {name: output for name, output in zip(self.output_names, outputs)}
    
    def predict_single(self, input_name: str, input_data: np.ndarray) -> np.ndarray:
        """单输入预测"""
        return self.session.run(self.output_names, {input_name: input_data})[0]


class TensorRTInferenceEngine:
    """TensorRT推理引擎"""
    
    def __init__(self, engine_path: str):
        """初始化TensorRT推理引擎
        
        Args:
            engine_path: TensorRT引擎路径
        """
        try:
            import tensorrt as trt
            
            self.logger = trt.Logger(trt.Logger.INFO)
            with open(engine_path, 'rb') as f:
                self.engine_data = f.read()
            
            self.runtime = trt.Runtime(self.logger)
            self.engine = self.runtime.deserialize_cuda_engine(self.engine_data)
            self.context = self.engine.create_execution_context()
            
            self.inputs = []
            self.outputs = []
            self.allocations = []
            
        except ImportError:
            raise ImportError("TensorRT not installed. Please install tensorrt.")
    
    def predict(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """预测"""
        # 简化实现，实际需要处理GPU内存和流
        import pycuda.driver as cuda
        import pycuda.autoinit
        
        # 分配内存
        for i, input_data in enumerate(inputs):
            input_data = input_data.astype(np.float32)
            cuda.memcpy_htod(self.allocations[i], input_data)
        
        # 执行推理
        self.context.execute_v2(self.allocations)
        
        # 获取输出
        outputs = []
        for i, output in enumerate(self.outputs):
            output_data = np.empty(output.shape, dtype=np.float32)
            cuda.memcpy_dtoh(output_data, self.allocations[len(inputs) + i])
            outputs.append(output_data)
        
        return outputs


class OpenVINOInferenceEngine:
    """OpenVINO推理引擎"""
    
    def __init__(self, model_path: str, device: str = 'CPU'):
        """初始化OpenVINO推理引擎
        
        Args:
            model_path: OpenVINO模型路径（不带扩展名）
            device: 设备类型
        """
        try:
            from openvino.inference_engine import IECore
            
            self.ie = IECore()
            self.net = self.ie.read_network(f"{model_path}.xml", f"{model_path}.bin")
            self.exec_net = self.ie.load_network(network=self.net, device_name=device)
            
            self.input_blob = next(iter(self.net.input_info))
            self.output_blob = next(iter(self.net.outputs))
            
        except ImportError:
            raise ImportError("OpenVINO not installed. Please install openvino.")
    
    def predict(self, input_data: np.ndarray) -> np.ndarray:
        """预测"""
        result = self.exec_net.infer(inputs={self.input_blob: input_data})
        return result[self.output_blob]


class PredictionExplainer:
    """预测解释器"""
    
    def __init__(self, model_wrapper: ModelWrapper):
        """初始化预测解释器
        
        Args:
            model_wrapper: 模型包装器
        """
        self.model_wrapper = model_wrapper
    
    def explain_shap(self, X: np.ndarray, background: np.ndarray = None,
                     n_samples: int = 100) -> Dict[str, Any]:
        """SHAP解释
        
        Args:
            X: 要解释的样本
            background: 背景数据
            n_samples: 样本数
            
        Returns:
            SHAP值
        """
        try:
            import shap
            
            if background is None:
                background = X[:100]
            
            # 创建解释器
            if self.model_wrapper.model_type == 'sklearn':
                explainer = shap.TreeExplainer(self.model_wrapper.model)
            elif self.model_wrapper.model_type in ['pytorch', 'tensorflow']:
                def predict_fn(x):
                    return self.model_wrapper.predict(x).predictions
                explainer = shap.KernelExplainer(predict_fn, background)
            else:
                explainer = shap.KernelExplainer(self.model_wrapper.model.predict, background)
            
            # 计算SHAP值
            shap_values = explainer.shap_values(X[:n_samples])
            
            return {
                'shap_values': shap_values,
                'base_value': explainer.expected_value,
                'data': X[:n_samples]
            }
        except ImportError:
            warnings.warn("SHAP not installed. Please install shap.")
            return {}
    
    def explain_lime(self, X: np.ndarray, feature_names: List[str] = None,
                     class_names: List[str] = None, n_samples: int = 500) -> Dict[str, Any]:
        """LIME解释
        
        Args:
            X: 要解释的样本
            feature_names: 特征名称
            class_names: 类别名称
            n_samples: 采样数
            
        Returns:
            LIME解释
        """
        try:
            from lime import lime_tabular
            
            if feature_names is None:
                feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            
            # 创建解释器
            explainer = lime_tabular.LimeTabularExplainer(
                X,
                feature_names=feature_names,
                class_names=class_names,
                mode='classification'
            )
            
            # 解释单个样本
            exp = explainer.explain_instance(
                X[0],
                self.model_wrapper.model.predict_proba if hasattr(self.model_wrapper.model, 'predict_proba') else self.model_wrapper.model.predict,
                num_features=10,
                num_samples=n_samples
            )
            
            return {
                'explanation': exp,
                'feature_importance': exp.as_list(),
                'local_pred': exp.local_pred
            }
        except ImportError:
            warnings.warn("LIME not installed. Please install lime.")
            return {}


class ModelServer:
    """模型服务器"""
    
    def __init__(self, model_wrapper: ModelWrapper, port: int = 8000):
        """初始化模型服务器
        
        Args:
            model_wrapper: 模型包装器
            port: 服务端口
        """
        self.model_wrapper = model_wrapper
        self.port = port
        self.app = None
    
    def start_rest_server(self, host: str = '0.0.0.0'):
        """启动REST服务器"""
        try:
            from flask import Flask, request, jsonify
            
            self.app = Flask(__name__)
            
            @self.app.route('/predict', methods=['POST'])
            def predict():
                data = request.json
                X = np.array(data['features'])
                
                result = self.model_wrapper.predict(X)
                
                response = {
                    'predictions': result.predictions.tolist(),
                    'inference_time_ms': result.inference_time
                }
                
                if result.probabilities is not None:
                    response['probabilities'] = result.probabilities.tolist()
                
                return jsonify(response)
            
            @self.app.route('/info', methods=['GET'])
            def info():
                return jsonify(self.model_wrapper.get_model_info())
            
            self.app.run(host=host, port=self.port)
            
        except ImportError:
            raise ImportError("Flask not installed. Please install flask.")
    
    def start_grpc_server(self):
        """启动gRPC服务器"""
        # 简化实现，需要生成gRPC代码
        pass


class InferencePipeline:
    """推理流水线"""
    
    def __init__(self, steps: List[Tuple[str, Any]]):
        """初始化推理流水线
        
        Args:
            steps: 流水线步骤 [(名称, 处理器), ...]
        """
        self.steps = steps
    
    def predict(self, X: np.ndarray) -> PredictionResult:
        """预测"""
        current_data = X
        
        for name, step in self.steps:
            if hasattr(step, 'transform'):
                current_data = step.transform(current_data)
            elif hasattr(step, 'predict'):
                current_data = step.predict(current_data)
            elif callable(step):
                current_data = step(current_data)
        
        if isinstance(current_data, PredictionResult):
            return current_data
        else:
            return PredictionResult(predictions=current_data)


def create_model_from_config(config: Dict[str, Any]) -> ModelWrapper:
    """从配置创建模型包装器
    
    Args:
        config: 模型配置字典
        
    Returns:
        模型包装器
    """
    model_path = config.get('path')
    model_type = config.get('type', 'auto')
    device = config.get('device', 'cpu')
    name = config.get('name')
    
    if model_path:
        if model_type == 'pytorch':
            import torch
            model = torch.load(model_path, map_location=device)
        elif model_type == 'tensorflow':
            import tensorflow as tf
            model = tf.keras.models.load_model(model_path)
        elif model_type == 'sklearn':
            import joblib
            model = joblib.load(model_path)
        elif model_type == 'onnx':
            import onnxruntime as ort
            model = ort.InferenceSession(model_path)
        else:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
    else:
        model = config.get('model')
    
    return ModelWrapper(model, model_type, device, name)