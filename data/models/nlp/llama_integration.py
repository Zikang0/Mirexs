"""
LLaMA集成 - LLaMA模型集成
"""

import os
import torch
import logging
from typing import Dict, Any, List, Optional
from transformers import (
    LlamaForCausalLM, 
    LlamaTokenizer,
    GenerationConfig,
    BitsAndBytesConfig
)
from .language_models import LanguageModelManager, ModelType, GenerationParameters

class LlamaIntegration:
    """LLaMA模型集成"""
    
    def __init__(self, model_cache_dir: str = "./models/llama"):
        self.model_cache_dir = model_cache_dir
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_name = None
        
        # LLaMA特定配置
        self.config = {
            "model_type": "llama",
            "max_length": 4096,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repetition_penalty": 1.1,
            "do_sample": True,
        }
        
        # 支持的LLaMA模型
        self.supported_models = {
            "llama-2-7b-chat": {
                "model_name": "meta-llama/Llama-2-7b-chat-hf",
                "description": "LLaMA 2 7B 对话模型",
                "context_length": 4096,
                "requires_auth": True
            },
            "llama-2-13b-chat": {
                "model_name": "meta-llama/Llama-2-13b-chat-hf", 
                "description": "LLaMA 2 13B 对话模型",
                "context_length": 4096,
                "requires_auth": True
            },
            "llama-2-70b-chat": {
                "model_name": "meta-llama/Llama-2-70b-chat-hf",
                "description": "LLaMA 2 70B 对话模型", 
                "context_length": 4096,
                "requires_auth": True
            },
            "llama-3-8b": {
                "model_name": "meta-llama/Meta-Llama-3-8B",
                "description": "LLaMA 3 8B 基础模型",
                "context_length": 8192,
                "requires_auth": True
            },
            "llama-3-8b-instruct": {
                "model_name": "meta-llama/Meta-Llama-3-8B-Instruct",
                "description": "LLaMA 3 8B 指导模型",
                "context_length": 8192,
                "requires_auth": True
            },
            "llama-3-70b": {
                "model_name": "meta-llama/Meta-Llama-3-70B",
                "description": "LLaMA 3 70B 基础模型",
                "context_length": 8192,
                "requires_auth": True
            },
            "llama-3-70b-instruct": {
                "model_name": "meta-llama/Meta-Llama-3-70B-Instruct", 
                "description": "LLaMA 3 70B 指导模型",
                "context_length": 8192,
                "requires_auth": True
            }
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("LlamaIntegration")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_model(self, model_key: str, **kwargs) -> bool:
        """加载LLaMA模型"""
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的LLaMA模型: {model_key}")
            return False
        
        try:
            model_info = self.supported_models[model_key]
            model_name = model_info["model_name"]
            
            self.logger.info(f"开始加载LLaMA模型: {model_key}")
            
            # 检查是否需要HuggingFace认证
            if model_info.get("requires_auth", False):
                self._check_hf_auth()
            
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
            self.logger.info("加载LLaMA tokenizer...")
            self.tokenizer = LlamaTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                trust_remote_code=True
            )
            
            # 确保有pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            self.logger.info("加载LLaMA模型...")
            self.model = LlamaForCausalLM.from_pretrained(
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
            
            self.logger.info(f"LLaMA模型加载成功: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载LLaMA模型失败: {e}")
            return False
    
    def _check_hf_auth(self):
        """检查HuggingFace认证"""
        from huggingface_hub import whoami
        try:
            user_info = whoami()
            self.logger.info(f"HuggingFace用户: {user_info.get('name', '未知')}")
        except Exception as e:
            self.logger.warning(f"HuggingFace认证检查失败: {e}")
            self.logger.warning("请设置HUGGING_FACE_HUB_TOKEN环境变量")
    
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
            # 构建LLaMA对话格式
            prompt = self._build_llama_chat_prompt(messages)
            
            # 生成回复
            result = self.generate(prompt, **kwargs)
            
            if result["success"]:
                # 提取助理回复
                assistant_response = self._extract_llama_response(result["generated_text"])
                result["assistant_response"] = assistant_response
            
            return result
            
        except Exception as e:
            self.logger.error(f"对话失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_llama_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建LLaMA对话prompt"""
        prompt = ""
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"<|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        
        # 添加助理开始标记
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
        return prompt
    
    def _extract_llama_response(self, generated_text: str) -> str:
        """提取LLaMA回复"""
        # 查找最后一个assistant标记
        assistant_marker = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        if assistant_marker in generated_text:
            parts = generated_text.split(assistant_marker)
            if len(parts) > 1:
                response = parts[-1]
                # 移除可能的结束标记
                if "<|eot_id|>" in response:
                    response = response.split("<|eot_id|>")[0]
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
        
        self.logger.info("LLaMA模型已卸载")