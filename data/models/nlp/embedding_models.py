"""
嵌入模型 - 文本嵌入向量模型
"""

import os
import json
import time
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    import torch
    import transformers
    from transformers import AutoModel, AutoTokenizer
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
    EMBEDDING_LIBS_AVAILABLE = True
except ImportError:
    EMBEDDING_LIBS_AVAILABLE = False

@dataclass
class EmbeddingConfig:
    """嵌入模型配置"""
    model_name: str
    max_length: int = 512
    batch_size: int = 32
    normalize_embeddings: bool = True
    device: str = "auto"

class EmbeddingModelManager:
    """嵌入模型管理器"""
    
    def __init__(self, model_cache_dir: str = "./models/embeddings"):
        self.model_cache_dir = model_cache_dir
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, Dict] = {}
        
        # 支持的嵌入模型
        self.supported_models = {
            "bge-large-zh": {
                "type": "sentence_transformers",
                "model_name": "BAAI/bge-large-zh",
                "description": "BGE 中文大模型",
                "dimension": 1024,
                "language": "zh"
            },
            "bge-base-en": {
                "type": "sentence_transformers", 
                "model_name": "BAAI/bge-base-en",
                "description": "BGE 英文基础模型",
                "dimension": 768,
                "language": "en"
            },
            "text2vec-base-chinese": {
                "type": "transformers",
                "model_name": "shibing624/text2vec-base-chinese",
                "description": "文本向量化中文基础模型",
                "dimension": 768,
                "language": "zh"
            },
            "all-mpnet-base-v2": {
                "type": "sentence_transformers",
                "model_name": "sentence-transformers/all-mpnet-base-v2",
                "description": "MPNet基础模型",
                "dimension": 768,
                "language": "en"
            },
            "multilingual-e5-large": {
                "type": "transformers",
                "model_name": "intfloat/multilingual-e5-large",
                "description": "多语言E5大模型",
                "dimension": 1024,
                "language": "multilingual"
            }
        }
        
        # 性能统计
        self.stats = {
            "total_embeddings": 0,
            "total_texts": 0,
            "average_embedding_time": 0.0,
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
        logger = logging.getLogger("EmbeddingModelManager")
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
        config_path = os.path.join(self.model_cache_dir, "embedding_configs.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.model_configs = json.load(f)
                self.logger.info("嵌入模型配置加载成功")
            except Exception as e:
                self.logger.warning(f"加载嵌入模型配置失败: {e}")
    
    def _save_model_configs(self):
        """保存模型配置"""
        config_path = os.path.join(self.model_cache_dir, "embedding_configs.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.model_configs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存嵌入模型配置失败: {e}")
    
    def load_model(self, model_key: str, config: Optional[EmbeddingConfig] = None) -> bool:
        """加载嵌入模型"""
        if not EMBEDDING_LIBS_AVAILABLE:
            self.logger.error("嵌入模型库不可用")
            return False
        
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的嵌入模型: {model_key}")
            return False
        
        if model_key in self.loaded_models:
            self.logger.info(f"模型已加载: {model_key}")
            return True
        
        try:
            model_info = self.supported_models[model_key]
            model_name = model_info["model_name"]
            
            self.logger.info(f"开始加载嵌入模型: {model_key} ({model_name})")
            start_time = time.time()
            
            # 设置设备
            device = config.device if config else "auto"
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 加载模型
            if model_info["type"] == "sentence_transformers":
                model = SentenceTransformer(
                    model_name,
                    cache_folder=self.model_cache_dir,
                    device=device
                )
            else:  # transformers
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    trust_remote_code=True
                )
                model = AutoModel.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32
                )
                model = model.to(device)
                model.eval()
                
                # 包装模型以便统一接口
                model = TransformersEmbeddingModel(model, tokenizer)
            
            # 保存模型信息
            self.loaded_models[model_key] = {
                "model": model,
                "config": model_info,
                "device": device,
                "loaded_time": time.time()
            }
            
            load_time = time.time() - start_time
            self.logger.info(f"嵌入模型加载完成，耗时: {load_time:.2f}秒")
            
            # 更新配置
            if model_key not in self.model_configs:
                self.model_configs[model_key] = {}
            self.model_configs[model_key]["last_loaded"] = time.time()
            self.model_configs[model_key]["load_time"] = load_time
            self._save_model_configs()
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载嵌入模型失败: {e}")
            self.stats["error_count"] += 1
            return False
    
    def encode_texts(self, 
                    texts: List[str], 
                    model_key: str,
                    batch_size: int = 32,
                    normalize: bool = True,
                    show_progress: bool = False) -> Dict[str, Any]:
        """编码文本为嵌入向量"""
        if not EMBEDDING_LIBS_AVAILABLE:
            return self._error_response("嵌入模型库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        if not texts:
            return self._error_response("输入文本列表为空")
        
        try:
            start_time = time.time()
            model_info = self.loaded_models[model_key]
            model = model_info["model"]
            
            # 编码文本
            if isinstance(model, SentenceTransformer):
                embeddings = model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True
                )
            else:  # TransformersEmbeddingModel
                embeddings = model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize=normalize
                )
            
            # 转换为列表
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            
            processing_time = time.time() - start_time
            
            # 更新统计
            self._update_stats(model_key, processing_time, len(texts), len(embeddings))
            
            return {
                "success": True,
                "embeddings": embeddings,
                "text_count": len(texts),
                "embedding_dim": len(embeddings[0]) if embeddings else 0,
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"文本编码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def encode_single_text(self, text: str, model_key: str, normalize: bool = True) -> Dict[str, Any]:
        """编码单个文本"""
        result = self.encode_texts([text], model_key, normalize=normalize)
        
        if result["success"]:
            result["embedding"] = result["embeddings"][0] if result["embeddings"] else []
            # 移除列表形式的embeddings
            if "embeddings" in result:
                del result["embeddings"]
        
        return result
    
    def compute_similarity(self, 
                          text1: str, 
                          text2: str, 
                          model_key: str,
                          similarity_metric: str = "cosine") -> Dict[str, Any]:
        """计算文本相似度"""
        # 编码两个文本
        result = self.encode_texts([text1, text2], model_key)
        
        if not result["success"]:
            return result
        
        embeddings = result["embeddings"]
        if len(embeddings) != 2:
            return self._error_response("编码结果不完整")
        
        # 计算相似度
        vec1 = np.array(embeddings[0])
        vec2 = np.array(embeddings[1])
        
        if similarity_metric == "cosine":
            similarity = self._cosine_similarity(vec1, vec2)
        elif similarity_metric == "dot":
            similarity = np.dot(vec1, vec2)
        elif similarity_metric == "euclidean":
            distance = np.linalg.norm(vec1 - vec2)
            similarity = 1 / (1 + distance)  # 转换为相似度
        else:
            return self._error_response(f"不支持的相似度度量: {similarity_metric}")
        
        result["similarity"] = float(similarity)
        result["similarity_metric"] = similarity_metric
        return result
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def semantic_search(self,
                       query: str,
                       documents: List[str],
                       model_key: str,
                       top_k: int = 5,
                       similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """语义搜索"""
        # 编码查询和文档
        all_texts = [query] + documents
        result = self.encode_texts(all_texts, model_key)
        
        if not result["success"]:
            return result
        
        embeddings = result["embeddings"]
        if len(embeddings) != len(all_texts):
            return self._error_response("编码结果不完整")
        
        query_embedding = np.array(embeddings[0])
        doc_embeddings = np.array(embeddings[1:])
        
        # 计算相似度
        similarities = []
        for i, doc_embedding in enumerate(doc_embeddings):
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append((i, similarity, documents[i]))
        
        # 排序和过滤
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []
        
        for i, (doc_idx, similarity, document) in enumerate(similarities[:top_k]):
            if similarity >= similarity_threshold:
                results.append({
                    "rank": i + 1,
                    "document_index": doc_idx,
                    "similarity": float(similarity),
                    "document": document
                })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_documents": len(documents),
            "returned_results": len(results),
            "model_used": model_key
        }
    
    def _update_stats(self, model_key: str, processing_time: float, text_count: int, embedding_count: int):
        """更新统计信息"""
        self.stats["total_embeddings"] += embedding_count
        self.stats["total_texts"] += text_count
        
        # 更新平均处理时间
        alpha = 0.1
        self.stats["average_embedding_time"] = (
            alpha * processing_time + (1 - alpha) * self.stats["average_embedding_time"]
        )
        
        # 更新模型使用统计
        if model_key not in self.stats["model_usage"]:
            self.stats["model_usage"][model_key] = {
                "texts_processed": 0,
                "embeddings_generated": 0,
                "total_time": 0.0
            }
        
        self.stats["model_usage"][model_key]["texts_processed"] += text_count
        self.stats["model_usage"][model_key]["embeddings_generated"] += embedding_count
        self.stats["model_usage"][model_key]["total_time"] += processing_time
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error": error_msg,
            "embeddings": [],
            "processing_time": 0.0
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
        
        # 计算每个模型的平均处理时间
        for model_key, usage in stats["model_usage"].items():
            if usage["embeddings_generated"] > 0:
                usage["average_time_per_embedding"] = usage["total_time"] / usage["embeddings_generated"]
            else:
                usage["average_time_per_embedding"] = 0.0
        
        return stats
    
    def unload_model(self, model_key: str) -> bool:
        """卸载模型"""
        if model_key not in self.loaded_models:
            self.logger.warning(f"模型未加载: {model_key}")
            return False
        
        try:
            # 清理模型资源
            del self.loaded_models[model_key]
            
            # 强制垃圾回收
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info(f"嵌入模型已卸载: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载嵌入模型失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        for model_key in list(self.loaded_models.keys()):
            self.unload_model(model_key)
        
        self.logger.info("嵌入模型管理器清理完成")

class TransformersEmbeddingModel:
    """Transformers嵌入模型包装器"""
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device
    
    def encode(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> np.ndarray:
        """编码文本"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # 编码批处理
            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                # 使用平均池化获取句子嵌入
                embeddings = self._mean_pooling(outputs, inputs['attention_mask'])
                
                if normalize:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                
                all_embeddings.append(embeddings.cpu().numpy())
        
        # 合并所有批处理结果
        return np.vstack(all_embeddings)
    
    def _mean_pooling(self, model_output, attention_mask):
        """平均池化"""
        token_embeddings = model_output[0]  # 第一个元素包含token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

        