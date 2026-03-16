"""
语言模型 - 大语言模型管理
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

try:
    import torch
    import transformers
    from transformers import (
        AutoModelForCausalLM,
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        GenerationConfig,
        StoppingCriteria,
        StoppingCriteriaList
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class ModelType(Enum):
    """模型类型枚举"""
    CAUSAL_LM = "causal_lm"  # 因果语言模型
    SEQ2SEQ_LM = "seq2seq_lm"  # 序列到序列模型
    CHAT_MODEL = "chat_model"  # 对话模型

@dataclass
class GenerationParameters:
    """生成参数配置"""
    max_length: int = 2048
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    num_beams: int = 1
    early_stopping: bool = True
    num_return_sequences: int = 1

class StopTokensCriteria(StoppingCriteria):
    """停止词标准"""
    def __init__(self, stop_token_ids: List[int]):
        self.stop_token_ids = stop_token_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_id in self.stop_token_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False

class LanguageModelManager:
    """大语言模型管理器"""
    
    def __init__(self, model_cache_dir: str = "./models"):
        self.model_cache_dir = model_cache_dir
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, Dict] = {}
        self.active_model: Optional[str] = None
        
        # 支持的模型配置
        self.supported_models = {
            "llama-2-7b": {
                "type": ModelType.CAUSAL_LM,
                "model_name": "meta-llama/Llama-2-7b-chat-hf",
                "description": "LLaMA 2 7B 对话模型",
                "context_length": 4096
            },
            "qwen-7b": {
                "type": ModelType.CAUSAL_LM, 
                "model_name": "Qwen/Qwen-7B-Chat",
                "description": "通义千问 7B 对话模型",
                "context_length": 8192
            },
            "mistral-7b": {
                "type": ModelType.CAUSAL_LM,
                "model_name": "mistralai/Mistral-7B-Instruct-v0.1",
                "description": "Mistral 7B 指导模型",
                "context_length": 32768
            },
            "bloom-7b": {
                "type": ModelType.CAUSAL_LM,
                "model_name": "bigscience/bloom-7b1",
                "description": "BLOOM 7B 多语言模型",
                "context_length": 2048
            }
        }
        
        # 默认生成参数
        self.default_generation_params = GenerationParameters()
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "average_response_time": 0.0,
            "model_usage": {},
            "error_count": 0
        }
        
        # 创建缓存目录
        os.makedirs(model_cache_dir, exist_ok=True)
        
        # 加载模型配置
        self._load_model_configs()
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("LanguageModelManager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_model_configs(self):
        """加载模型配置"""
        config_path = os.path.join(self.model_cache_dir, "model_configs.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.model_configs = json.load(f)
                self.logger.info("模型配置加载成功")
            except Exception as e:
                self.logger.warning(f"加载模型配置失败: {e}")
    
    def _save_model_configs(self):
        """保存模型配置"""
        config_path = os.path.join(self.model_cache_dir, "model_configs.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.model_configs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存模型配置失败: {e}")
    
    def load_model(self, model_key: str, **kwargs) -> bool:
        """加载指定模型"""
        if not TRANSFORMERS_AVAILABLE:
            self.logger.error("transformers库不可用，无法加载模型")
            return False
        
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的模型: {model_key}")
            return False
        
        try:
            model_config = self.supported_models[model_key]
            model_name = model_config["model_name"]
            
            self.logger.info(f"开始加载模型: {model_key} ({model_name})")
            start_time = time.time()
            
            # 设置设备
            device = kwargs.get("device", "cuda" if torch.cuda.is_available() else "cpu")
            torch_dtype = kwargs.get("torch_dtype", torch.float16 if device == "cuda" else torch.float32)
            
            # 加载tokenizer
            self.logger.info("加载tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                trust_remote_code=True
            )
            
            # 设置pad_token（如果需要）
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # 加载模型
            self.logger.info("加载模型...")
            if model_config["type"] == ModelType.CAUSAL_LM:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    torch_dtype=torch_dtype,
                    device_map="auto" if device == "cuda" else None,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
            elif model_config["type"] == ModelType.SEQ2SEQ_LM:
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    torch_dtype=torch_dtype,
                    device_map="auto" if device == "cuda" else None,
                    trust_remote_code=True
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    torch_dtype=torch_dtype,
                    device_map="auto" if device == "cuda" else None,
                    trust_remote_code=True
                )
            
            # 移动到设备
            if device != "cuda" or not hasattr(model, "device_map"):
                model = model.to(device)
            
            # 设置模型配置
            model_info = {
                "model": model,
                "tokenizer": tokenizer,
                "config": model_config,
                "device": device,
                "loaded_time": time.time()
            }
            
            self.loaded_models[model_key] = model_info
            self.active_model = model_key
            
            load_time = time.time() - start_time
            self.logger.info(f"模型加载完成，耗时: {load_time:.2f}秒")
            
            # 更新模型配置
            if model_key not in self.model_configs:
                self.model_configs[model_key] = {}
            self.model_configs[model_key]["last_loaded"] = time.time()
            self.model_configs[model_key]["load_time"] = load_time
            self._save_model_configs()
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            self.stats["error_count"] += 1
            return False
    
    def unload_model(self, model_key: str) -> bool:
        """卸载模型"""
        if model_key not in self.loaded_models:
            self.logger.warning(f"模型未加载: {model_key}")
            return False
        
        try:
            # 清理模型资源
            model_info = self.loaded_models[model_key]
            model_info["model"].cpu()
            if hasattr(model_info["model"], 'device_map'):
                del model_info["model"]
            del self.loaded_models[model_key]
            
            # 如果卸载的是当前激活模型，清空激活模型
            if self.active_model == model_key:
                self.active_model = None
            
            # 强制垃圾回收
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info(f"模型已卸载: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载模型失败: {e}")
            return False
    
    def generate_text(self, 
                     prompt: str, 
                     model_key: Optional[str] = None,
                     generation_params: Optional[GenerationParameters] = None,
                     **kwargs) -> Dict[str, Any]:
        """生成文本"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        model_key = model_key or self.active_model
        if model_key is None:
            return self._error_response("没有激活的模型")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        try:
            start_time = time.time()
            model_info = self.loaded_models[model_key]
            model = model_info["model"]
            tokenizer = model_info["tokenizer"]
            device = model_info["device"]
            
            # 准备生成参数
            params = generation_params or self.default_generation_params
            gen_config = GenerationConfig(
                max_length=params.max_length,
                max_new_tokens=params.max_new_tokens,
                temperature=params.temperature,
                top_p=params.top_p,
                top_k=params.top_k,
                repetition_penalty=params.repetition_penalty,
                do_sample=params.do_sample,
                num_beams=params.num_beams,
                early_stopping=params.early_stopping,
                num_return_sequences=params.num_return_sequences,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
            # 编码输入
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=params.max_length)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # 生成文本
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    generation_config=gen_config,
                    **kwargs
                )
            
            # 解码输出
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 计算统计信息
            processing_time = time.time() - start_time
            input_tokens = inputs["input_ids"].shape[1]
            output_tokens = outputs.shape[1] - input_tokens
            
            # 更新统计
            self._update_stats(model_key, processing_time, input_tokens + output_tokens)
            
            return {
                "success": True,
                "generated_text": generated_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"文本生成失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def chat(self, 
            messages: List[Dict[str, str]],
            model_key: Optional[str] = None,
            generation_params: Optional[GenerationParameters] = None,
            **kwargs) -> Dict[str, Any]:
        """对话接口"""
        # 构建对话prompt
        prompt = self._build_chat_prompt(messages, model_key)
        
        # 生成回复
        result = self.generate_text(prompt, model_key, generation_params, **kwargs)
        
        if result["success"]:
            # 提取助理回复
            assistant_response = self._extract_assistant_response(
                result["generated_text"], 
                model_key
            )
            result["assistant_response"] = assistant_response
        
        return result
    
    def _build_chat_prompt(self, messages: List[Dict[str, str]], model_key: str) -> str:
        """构建对话prompt"""
        if model_key.startswith("llama"):
            return self._build_llama_chat_prompt(messages)
        elif model_key.startswith("qwen"):
            return self._build_qwen_chat_prompt(messages)
        elif model_key.startswith("mistral"):
            return self._build_mistral_chat_prompt(messages)
        else:
            return self._build_default_chat_prompt(messages)
    
    def _build_llama_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建LLaMA对话prompt"""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"<|system|>\n{content}</s>\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}</s>\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}</s>\n"
        prompt += "<|assistant|>\n"
        return prompt
    
    def _build_qwen_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建Qwen对话prompt"""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        prompt += "Assistant: "
        return prompt
    
    def _build_mistral_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建Mistral对话prompt"""
        prompt = "<s>"
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"[INST] {content} [/INST]"
            elif role == "assistant":
                prompt += f" {content}</s>"
        return prompt
    
    def _build_default_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建默认对话prompt"""
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt += f"{role}: {content}\n"
        prompt += "assistant: "
        return prompt
    
    def _extract_assistant_response(self, generated_text: str, model_key: str) -> str:
        """提取助理回复"""
        if model_key.startswith("llama"):
            return self._extract_llama_response(generated_text)
        elif model_key.startswith("qwen"):
            return self._extract_qwen_response(generated_text)
        elif model_key.startswith("mistral"):
            return self._extract_mistral_response(generated_text)
        else:
            return self._extract_default_response(generated_text)
    
    def _extract_llama_response(self, text: str) -> str:
        """提取LLaMA回复"""
        if "<|assistant|>" in text:
            parts = text.split("<|assistant|>")
            return parts[-1].replace("</s>", "").strip()
        return text
    
    def _extract_qwen_response(self, text: str) -> str:
        """提取Qwen回复"""
        if "Assistant:" in text:
            parts = text.split("Assistant:")
            return parts[-1].strip()
        return text
    
    def _extract_mistral_response(self, text: str) -> str:
        """提取Mistral回复"""
        if "[/INST]" in text:
            parts = text.split("[/INST]")
            return parts[-1].replace("</s>", "").strip()
        return text
    
    def _extract_default_response(self, text: str) -> str:
        """提取默认回复"""
        if "assistant:" in text.lower():
            parts = text.lower().split("assistant:")
            return parts[-1].strip()
        return text
    
    def _update_stats(self, model_key: str, processing_time: float, token_count: int):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        self.stats["total_tokens"] += token_count
        
        # 更新平均响应时间（指数移动平均）
        alpha = 0.1
        self.stats["average_response_time"] = (
            alpha * processing_time + (1 - alpha) * self.stats["average_response_time"]
        )
        
        # 更新模型使用统计
        if model_key not in self.stats["model_usage"]:
            self.stats["model_usage"][model_key] = {
                "requests": 0,
                "tokens": 0,
                "total_time": 0.0
            }
        
        self.stats["model_usage"][model_key]["requests"] += 1
        self.stats["model_usage"][model_key]["tokens"] += token_count
        self.stats["model_usage"][model_key]["total_time"] += processing_time
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error": error_msg,
            "generated_text": "",
            "processing_time": 0.0,
            "total_tokens": 0
        }
    
    def get_loaded_models(self) -> List[str]:
        """获取已加载的模型列表"""
        return list(self.loaded_models.keys())
    
    def get_model_info(self, model_key: str) -> Dict[str, Any]:
        """获取模型信息"""
        if model_key not in self.supported_models:
            return {"error": f"不支持的模型: {model_key}"}
        
        info = self.supported_models[model_key].copy()
        info["is_loaded"] = model_key in self.loaded_models
        
        if model_key in self.loaded_models:
            model_info = self.loaded_models[model_key]
            info["device"] = model_info["device"]
            info["loaded_time"] = model_info["loaded_time"]
        
        return info
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()
        
        # 计算每个模型的平均响应时间
        for model_key, usage in stats["model_usage"].items():
            if usage["requests"] > 0:
                usage["average_time"] = usage["total_time"] / usage["requests"]
            else:
                usage["average_time"] = 0.0
        
        return stats
    
    def set_active_model(self, model_key: str) -> bool:
        """设置激活模型"""
        if model_key not in self.loaded_models:
            self.logger.error(f"模型未加载: {model_key}")
            return False
        
        self.active_model = model_key
        self.logger.info(f"激活模型: {model_key}")
        return True
    
    def cleanup(self):
        """清理资源"""
        for model_key in list(self.loaded_models.keys()):
            self.unload_model(model_key)
        
        self.logger.info("语言模型管理器清理完成")
        