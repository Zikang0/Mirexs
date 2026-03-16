"""
Qwen集成 - 通义千问模型集成
"""

import os
import torch
import logging
from typing import Dict, Any, List, Optional
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GenerationConfig,
    BitsAndBytesConfig
)

class QwenIntegration:
    """通义千问模型集成"""
    
    def __init__(self, model_cache_dir: str = "./models/qwen"):
        self.model_cache_dir = model_cache_dir
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_name = None
        
        # Qwen特定配置
        self.config = {
            "model_type": "qwen",
            "max_length": 8192,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "repetition_penalty": 1.1,
            "do_sample": True,
        }
        
        # 支持的Qwen模型
        self.supported_models = {
            "qwen-1.8b": {
                "model_name": "Qwen/Qwen-1_8B",
                "description": "Qwen 1.8B 基础模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-1.8b-chat": {
                "model_name": "Qwen/Qwen-1_8B-Chat",
                "description": "Qwen 1.8B 对话模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-7b": {
                "model_name": "Qwen/Qwen-7B",
                "description": "Qwen 7B 基础模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-7b-chat": {
                "model_name": "Qwen/Qwen-7B-Chat",
                "description": "Qwen 7B 对话模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-14b": {
                "model_name": "Qwen/Qwen-14B",
                "description": "Qwen 14B 基础模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-14b-chat": {
                "model_name": "Qwen/Qwen-14B-Chat",
                "description": "Qwen 14B 对话模型",
                "context_length": 8192,
                "requires_auth": False
            },
            "qwen-72b": {
                "model_name": "Qwen/Qwen-72B",
                "description": "Qwen 72B 基础模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "qwen-72b-chat": {
                "model_name": "Qwen/Qwen-72B-Chat",
                "description": "Qwen 72B 对话模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "qwen-2-7b": {
                "model_name": "Qwen/Qwen2-7B",
                "description": "Qwen2 7B 基础模型",
                "context_length": 131072,
                "requires_auth": False
            },
            "qwen-2-7b-instruct": {
                "model_name": "Qwen/Qwen2-7B-Instruct",
                "description": "Qwen2 7B 指导模型",
                "context_length": 131072,
                "requires_auth": False
            }
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("QwenIntegration")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_model(self, model_key: str, **kwargs) -> bool:
        """加载Qwen模型"""
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的Qwen模型: {model_key}")
            return False
        
        try:
            model_info = self.supported_models[model_key]
            model_name = model_info["model_name"]
            
            self.logger.info(f"开始加载Qwen模型: {model_key}")
            
            # 设置设备
            device = kwargs.get("device", "cuda" if torch.cuda.is_available() else "cpu")
            torch_dtype = kwargs.get("torch_dtype", torch.float16 if device == "cuda" else torch.float32)
            
            # 量化配置
            quantization_config = None
            if kwargs.get("load_in_8bit", False):
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            elif kwargs.get("load_in_4bit", False):
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch_dtype,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            
            # 加载tokenizer
            self.logger.info("加载Qwen tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                trust_remote_code=True
            )
            
            # Qwen模型需要设置pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            self.logger.info("加载Qwen模型...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                torch_dtype=torch_dtype,
                device_map="auto" if device == "cuda" else None,
                quantization_config=quantization_config,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.is_loaded = True
            self.model_name = model_key
            
            self.logger.info(f"Qwen模型加载成功: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载Qwen模型失败: {e}")
            return False
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本"""
        if not self.is_loaded:
            return {"success": False, "error": "模型未加载"}
        
        try:
            # 准备生成参数
            generation_config = GenerationConfig(
                max_length=kwargs.get("max_length", self.config["max_length"]),
                max_new_tokens=kwargs.get("max_new_tokens", self.config["max_new_tokens"]),
                temperature=kwargs.get("temperature", self.config["temperature"]),
                top_p=kwargs.get("top_p", self.config["top_p"]),
                top_k=kwargs.get("top_k", self.config["top_k"]),
                repetition_penalty=kwargs.get("repetition_penalty", self.config["repetition_penalty"]),
                do_sample=kwargs.get("do_sample", self.config["do_sample"]),
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
            
            # 编码输入
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, 
                                  max_length=self.config["max_length"])
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # 生成文本
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    generation_config=generation_config,
                    **{k: v for k, v in kwargs.items() if k not in [
                        "max_length", "max_new_tokens", "temperature", "top_p", 
                        "top_k", "repetition_penalty", "do_sample"
                    ]}
                )
            
            # 解码输出
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return {
                "success": True,
                "generated_text": generated_text,
                "input_length": len(prompt),
                "output_length": len(generated_text) - len(prompt)
            }
            
        except Exception as e:
            self.logger.error(f"文本生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """对话接口"""
        if not self.is_loaded:
            return {"success": False, "error": "模型未加载"}
        
        try:
            # 构建Qwen对话格式
            prompt = self._build_qwen_chat_prompt(messages)
            
            # 生成回复
            result = self.generate(prompt, **kwargs)
            
            if result["success"]:
                # 提取助理回复
                assistant_response = self._extract_qwen_response(result["generated_text"])
                result["assistant_response"] = assistant_response
            
            return result
            
        except Exception as e:
            self.logger.error(f"对话失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_qwen_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建Qwen对话prompt"""
        prompt = ""
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        # 添加助理开始标记
        prompt += "<|im_start|>assistant\n"
        
        return prompt
    
    def _extract_qwen_response(self, generated_text: str) -> str:
        """提取Qwen回复"""
        # 查找最后一个assistant标记
        assistant_marker = "<|im_start|>assistant\n"
        if assistant_marker in generated_text:
            parts = generated_text.split(assistant_marker)
            if len(parts) > 1:
                response = parts[-1]
                # 移除可能的结束标记
                if "<|im_end|>" in response:
                    response = response.split("<|im_end|>")[0]
                return response.strip()
        
        return generated_text
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "config": self.config,
            "supported_models": list(self.supported_models.keys())
        }
        
        if self.is_loaded:
            info["device"] = str(self.model.device)
            info["dtype"] = str(next(self.model.parameters()).dtype)
        
        return info
    
    def unload_model(self):
        """卸载模型"""
        if self.model:
            self.model.cpu()
            del self.model
            self.model = None
        
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        
        self.is_loaded = False
        self.model_name = None
        
        # 清理GPU内存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.logger.info("Qwen模型已卸载")

        