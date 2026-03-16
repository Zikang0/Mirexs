"""
模型量化器 - 模型量化优化
"""

import os
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

try:
    import torch
    from transformers import BitsAndBytesConfig
    import bitsandbytes as bnb
    QUANTIZATION_AVAILABLE = True
except ImportError:
    QUANTIZATION_AVAILABLE = False

@dataclass
class QuantizationConfig:
    """量化配置"""
    quantization_type: str  # "8bit", "4bit", "float16", "bfloat16"
    compute_dtype: str = "float16"
    use_double_quant: bool = True
    quant_type: str = "nf4"  # "nf4" or "fp4"

class ModelQuantizer:
    """模型量化器"""
    
    def __init__(self):
        self.quantization_methods = {
            "8bit": self._setup_8bit_quantization,
            "4bit": self._setup_4bit_quantization,
            "float16": self._setup_float16_quantization,
            "bfloat16": self._setup_bfloat16_quantization
        }
        
        # 性能统计
        self.stats = {
            "total_quantizations": 0,
            "successful_quantizations": 0,
            "failed_quantizations": 0,
            "memory_savings": 0.0,  # 节省的内存百分比
            "quantization_types": {}
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("ModelQuantizer")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def is_quantization_available(self) -> bool:
        """检查量化是否可用"""
        return QUANTIZATION_AVAILABLE
    
    def get_supported_quantization_types(self) -> List[str]:
        """获取支持的量化类型"""
        return list(self.quantization_methods.keys())
    
    def setup_quantization_config(self, config: QuantizationConfig) -> Optional[BitsAndBytesConfig]:
        """设置量化配置"""
        if not QUANTIZATION_AVAILABLE:
            self.logger.error("量化库不可用")
            return None
        
        try:
            quantization_type = config.quantization_type
            
            if quantization_type not in self.quantization_methods:
                self.logger.error(f"不支持的量化类型: {quantization_type}")
                return None
            
            # 调用对应的量化设置方法
            quantization_config = self.quantization_methods[quantization_type](config)
            
            self.stats["total_quantizations"] += 1
            self.stats["quantization_types"][quantization_type] = \
                self.stats["quantization_types"].get(quantization_type, 0) + 1
            
            return quantization_config
            
        except Exception as e:
            self.logger.error(f"设置量化配置失败: {e}")
            self.stats["failed_quantizations"] += 1
            return None
    
    def _setup_8bit_quantization(self, config: QuantizationConfig) -> BitsAndBytesConfig:
        """设置8位量化"""
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_enable_fp32_cpu_offload=True,
            llm_int8_skip_modules=None,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False
        )
    
    def _setup_4bit_quantization(self, config: QuantizationConfig) -> BitsAndBytesConfig:
        """设置4位量化"""
        # 设置计算数据类型
        compute_dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32
        }
        compute_dtype = compute_dtype_map.get(config.compute_dtype, torch.float16)
        
        # 设置量化类型
        quant_type_map = {
            "nf4": "nf4",
            "fp4": "fp4"
        }
        quant_type = quant_type_map.get(config.quant_type, "nf4")
        
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=config.use_double_quant,
            bnb_4bit_quant_type=quant_type,
            bnb_4bit_quant_storage_dtype=torch.uint8
        )
    
    def _setup_float16_quantization(self, config: QuantizationConfig) -> Dict[str, Any]:
        """设置float16量化"""
        return {
            "torch_dtype": torch.float16,
            "device_map": "auto" if torch.cuda.is_available() else None
        }
    
    def _setup_bfloat16_quantization(self, config: QuantizationConfig) -> Dict[str, Any]:
        """设置bfloat16量化"""
        return {
            "torch_dtype": torch.bfloat16,
            "device_map": "auto" if torch.cuda.is_available() else None
        }
    
    def quantize_model(self, model, config: QuantizationConfig) -> Dict[str, Any]:
        """量化模型"""
        if not QUANTIZATION_AVAILABLE:
            return self._error_response("量化库不可用")
        
        try:
            self.logger.info(f"开始量化模型，类型: {config.quantization_type}")
            
            # 记录原始内存使用
            original_memory = self._estimate_model_memory(model)
            
            # 设置量化配置
            quantization_config = self.setup_quantization_config(config)
            if quantization_config is None:
                return self._error_response("量化配置失败")
            
            # 应用量化
            if isinstance(quantization_config, BitsAndBytesConfig):
                # 使用BitsAndBytes量化
                from transformers import AutoModelForCausalLM
                
                # 重新加载模型应用量化
                model_config = model.config
                model_name = getattr(model_config, "_name_or_path", None)
                
                if model_name:
                    quantized_model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        quantization_config=quantization_config,
                        device_map="auto",
                        torch_dtype=torch.float16
                    )
                else:
                    return self._error_response("无法获取模型名称进行量化")
            else:
                # 使用torch dtype量化
                model = model.to(**quantization_config)
                quantized_model = model
            
            # 记录量化后内存使用
            quantized_memory = self._estimate_model_memory(quantized_model)
            
            # 计算内存节省
            memory_saving = 0.0
            if original_memory > 0:
                memory_saving = (original_memory - quantized_memory) / original_memory * 100
            
            # 更新统计
            self.stats["successful_quantizations"] += 1
            self.stats["memory_savings"] = (
                self.stats["memory_savings"] * (self.stats["successful_quantizations"] - 1) + 
                memory_saving
            ) / self.stats["successful_quantizations"]
            
            self.logger.info(f"模型量化成功，内存节省: {memory_saving:.2f}%")
            
            return {
                "success": True,
                "quantized_model": quantized_model,
                "quantization_type": config.quantization_type,
                "original_memory_mb": original_memory,
                "quantized_memory_mb": quantized_memory,
                "memory_saving_percent": memory_saving,
                "model_parameters": sum(p.numel() for p in quantized_model.parameters())
            }
            
        except Exception as e:
            self.logger.error(f"模型量化失败: {e}")
            self.stats["failed_quantizations"] += 1
            return self._error_response(str(e))
    
    def _estimate_model_memory(self, model) -> float:
        """估计模型内存使用（MB）"""
        try:
            param_size = 0
            for param in model.parameters():
                param_size += param.nelement() * param.element_size()
            
            buffer_size = 0
            for buffer in model.buffers():
                buffer_size += buffer.nelement() * buffer.element_size()
            
            total_size = param_size + buffer_size
            return total_size / (1024 ** 2)  # 转换为MB
            
        except Exception as e:
            self.logger.warning(f"估计模型内存失败: {e}")
            return 0.0
    
    def optimize_model_for_inference(self, model, **kwargs) -> Dict[str, Any]:
        """优化模型用于推理"""
        try:
            self.logger.info("开始优化模型用于推理")
            
            # 应用各种优化
            optimized_model = model
            
            # 1. 设置为评估模式
            optimized_model.eval()
            
            # 2. 应用torch.compile（如果可用）
            if hasattr(torch, 'compile') and kwargs.get("use_torch_compile", False):
                try:
                    optimized_model = torch.compile(optimized_model)
                    self.logger.info("应用torch.compile优化")
                except Exception as e:
                    self.logger.warning(f"torch.compile优化失败: {e}")
            
            # 3. 启用CPU/GPU优化
            if torch.cuda.is_available():
                # CUDA优化
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            
            # 4. 应用梯度检查点（如果支持）
            if hasattr(optimized_model, 'gradient_checkpointing_enable'):
                try:
                    optimized_model.gradient_checkpointing_enable()
                    self.logger.info("启用梯度检查点")
                except Exception as e:
                    self.logger.warning(f"启用梯度检查点失败: {e}")
            
            self.logger.info("模型推理优化完成")
            
            return {
                "success": True,
                "optimized_model": optimized_model,
                "optimizations_applied": [
                    "eval_mode",
                    "torch_compile" if kwargs.get("use_torch_compile", False) else None,
                    "cuda_optimizations" if torch.cuda.is_available() else None,
                    "gradient_checkpointing" if hasattr(optimized_model, 'gradient_checkpointing_enable') else None
                ]
            }
            
        except Exception as e:
            self.logger.error(f"模型推理优化失败: {e}")
            return self._error_response(str(e))
    
    def compare_quantization_methods(self, model, test_input) -> Dict[str, Any]:
        """比较不同量化方法的性能"""
        if not QUANTIZATION_AVAILABLE:
            return self._error_response("量化库不可用")
        
        try:
            self.logger.info("开始比较量化方法")
            
            results = {}
            quantization_configs = [
                QuantizationConfig("float16"),
                QuantizationConfig("bfloat16"),
                QuantizationConfig("8bit"),
                QuantizationConfig("4bit")
            ]
            
            for config in quantization_configs:
                self.logger.info(f"测试量化方法: {config.quantization_type}")
                
                try:
                    # 量化模型
                    quant_result = self.quantize_model(model, config)
                    
                    if quant_result["success"]:
                        quantized_model = quant_result["quantized_model"]
                        
                        # 测试推理速度
                        inference_time = self._benchmark_inference(quantized_model, test_input)
                        
                        # 记录结果
                        results[config.quantization_type] = {
                            "success": True,
                            "memory_mb": quant_result["quantized_memory_mb"],
                            "memory_saving_percent": quant_result["memory_saving_percent"],
                            "inference_time_ms": inference_time,
                            "parameters": quant_result["model_parameters"]
                        }
                    else:
                        results[config.quantization_type] = {
                            "success": False,
                            "error": quant_result.get("error", "未知错误")
                        }
                        
                except Exception as e:
                    results[config.quantization_type] = {
                        "success": False,
                        "error": str(e)
                    }
            
            self.logger.info("量化方法比较完成")
            
            return {
                "success": True,
                "comparison_results": results
            }
            
        except Exception as e:
            self.logger.error(f"量化方法比较失败: {e}")
            return self._error_response(str(e))
    
    def _benchmark_inference(self, model, test_input, num_runs: int = 10) -> float:
        """基准测试推理速度"""
        import time
        
        try:
            # 预热
            with torch.no_grad():
                _ = model(**test_input)
            
            # 正式测试
            start_time = time.time()
            for _ in range(num_runs):
                with torch.no_grad():
                    _ = model(**test_input)
            end_time = time.time()
            
            average_time = (end_time - start_time) / num_runs * 1000  # 转换为毫秒
            return average_time
            
        except Exception as e:
            self.logger.warning(f"推理基准测试失败: {e}")
            return 0.0
    
    def get_quantization_stats(self) -> Dict[str, Any]:
        """获取量化统计"""
        stats = self.stats.copy()
        
        # 计算成功率
        if stats["total_quantizations"] > 0:
            stats["success_rate"] = stats["successful_quantizations"] / stats["total_quantizations"] * 100
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error": error_msg
        }
    
    def cleanup(self):
        """清理资源"""
        # 强制垃圾回收
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.logger.info("模型量化器清理完成")

