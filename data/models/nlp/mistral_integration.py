"""
Mistral集成 - Mistral模型集成
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

class MistralIntegration:
    """Mistral模型集成"""
    
    def __init__(self, model_cache_dir: str = "./models/mistral"):
        self.model_cache_dir = model_cache_dir
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_name = None
        
        # Mistral特定配置
        self.config = {
            "model_type": "mistral",
            "max_length": 32768,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repetition_penalty": 1.1,
            "do_sample": True,
        }
        
        # 支持的Mistral模型
        self.supported_models = {
            "mistral-7b": {
                "model_name": "mistralai/Mistral-7B-v0.1",
                "description": "Mistral 7B 基础模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "mistral-7b-instruct": {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.1",
                "description": "Mistral 7B 指导模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "mistral-7b-instruct-v0.2": {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.2",
                "description": "Mistral 7B 指导模型 v0.2",
                "context_length": 32768,
                "requires_auth": False
            },
            "mistral-7b-instruct-v0.3": {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.3",
                "description": "Mistral 7B 指导模型 v0.3",
                "context_length": 32768,
                "requires_auth": False
            },
            "mixtral-8x7b": {
                "model_name": "mistralai/Mixtral-8x7B-v0.1",
                "description": "Mixtral 8x7B 基础模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "mixtral-8x7b-instruct": {
                "model_name": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "description": "Mixtral 8x7B 指导模型",
                "context_length": 32768,
                "requires_auth": False
            },
            "mixtral-8x22b": {
                "model_name": "mistralai/Mixtral-8x22B-v0.1",
                "description": "Mixtral 8x22B 基础模型",
                "context_length": 65536,
                "requires_auth": False
            },
            "mixtral-8x22b-instruct": {
                "model_name": "mistralai/Mixtral-8x22B-Instruct-v0.1",
                "description": "Mixtral 8x22B 指导模型",
                "context_length": 65536,
                "requires_auth": False
            }
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("MistralIntegration")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_model(self, model_key: str, **kwargs) -> bool:
        """加载Mistral模型"""
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的Mistral模型: {model_key}")
            return False
        
        try:
            model_info = self.supported_models[model_key]
            model_name = model_info["model_name"]
            
            self.logger.info(f"开始加载Mistral模型: {model_key}")
            
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
            self.logger.info("加载Mistral tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                trust_remote_code=True
            )
            
            # Mistral模型需要设置pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            self.logger.info("加载Mistral模型...")
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
            
            self.logger.info(f"Mistral模型加载成功: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载Mistral模型失败: {e}")
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
            # 构建Mistral对话格式
            prompt = self._build_mistral_chat_prompt(messages)
            
            # 生成回复
            result = self.generate(prompt, **kwargs)
            
            if result["success"]:
                # 提取助理回复
                assistant_response = self._extract_mistral_response(result["generated_text"])
                result["assistant_response"] = assistant_response
            
            return result
            
        except Exception as e:
            self.logger.error(f"对话失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_mistral_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建Mistral对话prompt"""
        prompt = "<s>"
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"[INST] {content} [/INST]"
            elif role == "user":
                prompt += f"[INST] {content} [/INST]"
            elif role == "assistant":
                prompt += f" {content}</s>"
        
        return prompt
    
    def _extract_mistral_response(self, generated_text: str) -> str:
        """提取Mistral回复"""
        # 查找最后一个[/INST]标记
        inst_marker = "[/INST]"
        if inst_marker in generated_text:
            parts = generated_text.split(inst_marker)
            if len(parts) > 1:
                response = parts[-1]
                # 移除可能的结束标记
                if "</s>" in response:
                    response = response.split("</s>")[0]
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
        
        self.logger.info("Mistral模型已卸载")

