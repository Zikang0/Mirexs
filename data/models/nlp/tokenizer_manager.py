"""
分词器管理 - 统一分词器管理
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    from transformers import AutoTokenizer, PreTrainedTokenizer, PreTrainedTokenizerFast
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

@dataclass
class TokenizerConfig:
    """分词器配置"""
    model_name: str
    use_fast: bool = True
    trust_remote_code: bool = True
    padding_side: str = "right"
    truncation_side: str = "right"

class TokenizerManager:
    """分词器管理器"""
    
    def __init__(self, tokenizer_cache_dir: str = "./models/tokenizers"):
        self.tokenizer_cache_dir = tokenizer_cache_dir
        self.loaded_tokenizers: Dict[str, Any] = {}
        
        # 常用分词器配置
        self.tokenizer_configs = {
            "llama": {
                "model_name": "meta-llama/Llama-2-7b-hf",
                "use_fast": True,
                "padding_side": "right",
                "special_tokens": {"pad_token": "</s>"}
            },
            "qwen": {
                "model_name": "Qwen/Qwen-7B",
                "use_fast": True,
                "padding_side": "right",
                "trust_remote_code": True
            },
            "mistral": {
                "model_name": "mistralai/Mistral-7B-v0.1",
                "use_fast": True,
                "padding_side": "left"
            },
            "bert": {
                "model_name": "bert-base-uncased",
                "use_fast": True,
                "padding_side": "right"
            },
            "roberta": {
                "model_name": "roberta-base",
                "use_fast": True,
                "padding_side": "right"
            },
            "gpt2": {
                "model_name": "gpt2",
                "use_fast": True,
                "padding_side": "right"
            },
            "t5": {
                "model_name": "t5-base",
                "use_fast": True,
                "padding_side": "right"
            },
            "bloom": {
                "model_name": "bigscience/bloom-560m",
                "use_fast": True,
                "padding_side": "left",
                "trust_remote_code": True
            },
            "chatglm": {
                "model_name": "THUDM/chatglm-6b",
                "use_fast": False,
                "padding_side": "left",
                "trust_remote_code": True
            },
            "baichuan": {
                "model_name": "baichuan-inc/Baichuan2-7B-Base",
                "use_fast": False,
                "padding_side": "left",
                "trust_remote_code": True
            }
        }
        
        # 性能统计
        self.stats = {
            "total_tokenizations": 0,
            "total_detokenizations": 0,
            "total_tokens": 0,
            "tokenizer_usage": {},
            "error_count": 0
        }
        
        # 创建缓存目录
        os.makedirs(tokenizer_cache_dir, exist_ok=True)
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("TokenizerManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_tokenizer(self, tokenizer_key: str, config: Optional[TokenizerConfig] = None) -> bool:
        """加载分词器"""
        if not TRANSFORMERS_AVAILABLE:
            self.logger.error("transformers库不可用")
            return False
        
        if tokenizer_key in self.loaded_tokenizers:
            self.logger.info(f"分词器已加载: {tokenizer_key}")
            return True
        
        try:
            # 获取配置
            if config:
                tokenizer_config = {
                    "model_name": config.model_name,
                    "use_fast": config.use_fast,
                    "trust_remote_code": config.trust_remote_code
                }
            elif tokenizer_key in self.tokenizer_configs:
                tokenizer_config = self.tokenizer_configs[tokenizer_key]
            else:
                self.logger.error(f"未知的分词器类型: {tokenizer_key}")
                return False
            
            model_name = tokenizer_config["model_name"]
            use_fast = tokenizer_config.get("use_fast", True)
            trust_remote_code = tokenizer_config.get("trust_remote_code", True)
            
            self.logger.info(f"开始加载分词器: {tokenizer_key} ({model_name})")
            
            # 加载分词器
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.tokenizer_cache_dir,
                use_fast=use_fast,
                trust_remote_code=trust_remote_code
            )
            
            # 应用特殊配置
            if "padding_side" in tokenizer_config:
                tokenizer.padding_side = tokenizer_config["padding_side"]
            
            if "truncation_side" in tokenizer_config:
                tokenizer.truncation_side = tokenizer_config["truncation_side"]
            
            # 处理特殊token
            special_tokens = tokenizer_config.get("special_tokens", {})
            for token_type, token_value in special_tokens.items():
                if hasattr(tokenizer, token_type) and getattr(tokenizer, token_type) is None:
                    setattr(tokenizer, token_type, token_value)
            
            # 确保有pad_token
            if tokenizer.pad_token is None:
                if tokenizer.eos_token is not None:
                    tokenizer.pad_token = tokenizer.eos_token
                else:
                    tokenizer.add_special_tokens({'pad_token': '[PAD]'})
            
            # 保存分词器
            self.loaded_tokenizers[tokenizer_key] = {
                "tokenizer": tokenizer,
                "config": tokenizer_config,
                "vocab_size": tokenizer.vocab_size,
                "model_max_length": tokenizer.model_max_length
            }
            
            self.logger.info(f"分词器加载成功: {tokenizer_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载分词器失败: {e}")
            self.stats["error_count"] += 1
            return False
    
    def tokenize(self, text: str, tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """分词"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            # 分词
            tokens = tokenizer.tokenize(text, **kwargs)
            token_ids = tokenizer.encode(text, **kwargs)
            
            # 更新统计
            self._update_stats(tokenizer_key, "tokenize", len(token_ids))
            
            return {
                "success": True,
                "tokens": tokens,
                "token_ids": token_ids,
                "token_count": len(tokens),
                "text_length": len(text),
                "tokenizer_used": tokenizer_key
            }
            
        except Exception as e:
            self.logger.error(f"分词失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def batch_tokenize(self, texts: List[str], tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """批量分词"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            results = []
            total_tokens = 0
            
            for text in texts:
                tokens = tokenizer.tokenize(text, **kwargs)
                token_ids = tokenizer.encode(text, **kwargs)
                
                results.append({
                    "text": text,
                    "tokens": tokens,
                    "token_ids": token_ids,
                    "token_count": len(tokens)
                })
                
                total_tokens += len(tokens)
            
            # 更新统计
            self._update_stats(tokenizer_key, "tokenize", total_tokens)
            
            return {
                "success": True,
                "results": results,
                "total_texts": len(texts),
                "total_tokens": total_tokens,
                "tokenizer_used": tokenizer_key
            }
            
        except Exception as e:
            self.logger.error(f"批量分词失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def encode(self, text: str, tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """编码文本为token IDs"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            # 编码
            encoding = tokenizer.encode_plus(
                text,
                **kwargs
            )
            
            token_ids = encoding["input_ids"]
            attention_mask = encoding.get("attention_mask", [1] * len(token_ids))
            token_type_ids = encoding.get("token_type_ids")
            
            # 更新统计
            self._update_stats(tokenizer_key, "encode", len(token_ids))
            
            result = {
                "success": True,
                "token_ids": token_ids,
                "attention_mask": attention_mask,
                "token_count": len(token_ids),
                "text_length": len(text),
                "tokenizer_used": tokenizer_key
            }
            
            if token_type_ids is not None:
                result["token_type_ids"] = token_type_ids
            
            return result
            
        except Exception as e:
            self.logger.error(f"编码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def batch_encode(self, texts: List[str], tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """批量编码"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            # 批量编码
            encodings = tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt" if kwargs.get("return_tensors") == "pt" else None,
                **{k: v for k, v in kwargs.items() if k != "return_tensors"}
            )
            
            # 更新统计
            total_tokens = sum(len(ids) for ids in encodings["input_ids"])
            self._update_stats(tokenizer_key, "encode", total_tokens)
            
            # 转换为列表格式
            result = {
                "success": True,
                "input_ids": encodings["input_ids"].tolist() if hasattr(encodings["input_ids"], 'tolist') else encodings["input_ids"],
                "attention_mask": encodings["attention_mask"].tolist() if hasattr(encodings["attention_mask"], 'tolist') else encodings["attention_mask"],
                "total_texts": len(texts),
                "total_tokens": total_tokens,
                "tokenizer_used": tokenizer_key
            }
            
            if "token_type_ids" in encodings:
                result["token_type_ids"] = encodings["token_type_ids"].tolist() if hasattr(encodings["token_type_ids"], 'tolist') else encodings["token_type_ids"]
            
            return result
            
        except Exception as e:
            self.logger.error(f"批量编码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def decode(self, token_ids: List[int], tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """解码token IDs为文本"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            # 解码
            text = tokenizer.decode(token_ids, **kwargs)
            
            # 更新统计
            self._update_stats(tokenizer_key, "decode", len(token_ids))
            
            return {
                "success": True,
                "text": text,
                "token_count": len(token_ids),
                "text_length": len(text),
                "tokenizer_used": tokenizer_key
            }
            
        except Exception as e:
            self.logger.error(f"解码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def batch_decode(self, batch_token_ids: List[List[int]], tokenizer_key: str, **kwargs) -> Dict[str, Any]:
        """批量解码"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if tokenizer_key not in self.loaded_tokenizers:
            return self._error_response(f"分词器未加载: {tokenizer_key}")
        
        try:
            tokenizer_info = self.loaded_tokenizers[tokenizer_key]
            tokenizer = tokenizer_info["tokenizer"]
            
            # 批量解码
            texts = tokenizer.batch_decode(batch_token_ids, **kwargs)
            
            # 更新统计
            total_tokens = sum(len(ids) for ids in batch_token_ids)
            self._update_stats(tokenizer_key, "decode", total_tokens)
            
            results = []
            for i, (token_ids, text) in enumerate(zip(batch_token_ids, texts)):
                results.append({
                    "index": i,
                    "token_ids": token_ids,
                    "text": text,
                    "token_count": len(token_ids),
                    "text_length": len(text)
                })
            
            return {
                "success": True,
                "results": results,
                "total_texts": len(batch_token_ids),
                "total_tokens": total_tokens,
                "tokenizer_used": tokenizer_key
            }
            
        except Exception as e:
            self.logger.error(f"批量解码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def get_tokenizer_info(self, tokenizer_key: str) -> Dict[str, Any]:
        """获取分词器信息"""
        if tokenizer_key not in self.loaded_tokenizers:
            return {"error": f"分词器未加载: {tokenizer_key}"}
        
        tokenizer_info = self.loaded_tokenizers[tokenizer_key]
        tokenizer = tokenizer_info["tokenizer"]
        
        return {
            "tokenizer_key": tokenizer_key,
            "vocab_size": tokenizer.vocab_size,
            "model_max_length": tokenizer.model_max_length,
            "padding_side": tokenizer.padding_side,
            "truncation_side": tokenizer.truncation_side,
            "special_tokens": {
                "pad_token": tokenizer.pad_token,
                "eos_token": tokenizer.eos_token,
                "bos_token": tokenizer.bos_token,
                "unk_token": tokenizer.unk_token
            },
            "is_fast": isinstance(tokenizer, PreTrainedTokenizerFast)
        }
    
    def _update_stats(self, tokenizer_key: str, operation: str, token_count: int):
        """更新统计信息"""
        if operation == "tokenize":
            self.stats["total_tokenizations"] += 1
        elif operation == "encode":
            self.stats["total_tokenizations"] += 1
        elif operation == "decode":
            self.stats["total_detokenizations"] += 1
        
        self.stats["total_tokens"] += token_count
        
        # 更新分词器使用统计
        if tokenizer_key not in self.stats["tokenizer_usage"]:
            self.stats["tokenizer_usage"][tokenizer_key] = {
                "tokenizations": 0,
                "detokenizations": 0,
                "total_tokens": 0
            }
        
        if operation in ["tokenize", "encode"]:
            self.stats["tokenizer_usage"][tokenizer_key]["tokenizations"] += 1
        elif operation == "decode":
            self.stats["tokenizer_usage"][tokenizer_key]["detokenizations"] += 1
        
        self.stats["tokenizer_usage"][tokenizer_key]["total_tokens"] += token_count
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error": error_msg
        }
    
    def get_loaded_tokenizers(self) -> List[str]:
        """获取已加载的分词器列表"""
        return list(self.loaded_tokenizers.keys())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def unload_tokenizer(self, tokenizer_key: str) -> bool:
        """卸载分词器"""
        if tokenizer_key not in self.loaded_tokenizers:
            self.logger.warning(f"分词器未加载: {tokenizer_key}")
            return False
        
        try:
            del self.loaded_tokenizers[tokenizer_key]
            self.logger.info(f"分词器已卸载: {tokenizer_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载分词器失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        for tokenizer_key in list(self.loaded_tokenizers.keys()):
            self.unload_tokenizer(tokenizer_key)
        
        self.logger.info("分词器管理器清理完成")

