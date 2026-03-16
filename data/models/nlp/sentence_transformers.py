"""
Sentence Transformers - 句子嵌入模型
"""

import os
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

@dataclass
class SentenceTransformerConfig:
    """Sentence Transformer配置"""
    model_name: str
    device: str = "auto"
    batch_size: int = 32
    normalize_embeddings: bool = True
    show_progress_bar: bool = False

class SentenceTransformerManager:
    """Sentence Transformer管理器"""
    
    def __init__(self, model_cache_dir: str = "./models/sentence_transformers"):
        self.model_cache_dir = model_cache_dir
        self.loaded_models: Dict[str, Any] = {}
        
        # 支持的Sentence Transformer模型
        self.supported_models = {
            "all-mpnet-base-v2": {
                "model_name": "sentence-transformers/all-mpnet-base-v2",
                "description": "MPNet基础模型，适用于通用文本嵌入",
                "dimension": 768,
                "max_seq_length": 384,
                "language": "en"
            },
            "all-MiniLM-L6-v2": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "description": "MiniLM小型模型，速度快",
                "dimension": 384,
                "max_seq_length": 256,
                "language": "en"
            },
            "all-MiniLM-L12-v2": {
                "model_name": "sentence-transformers/all-MiniLM-L12-v2",
                "description": "MiniLM中型模型，平衡性能",
                "dimension": 384,
                "max_seq_length": 256,
                "language": "en"
            },
            "paraphrase-multilingual-mpnet-base-v2": {
                "model_name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                "description": "多语言MPNet模型，支持50+语言",
                "dimension": 768,
                "max_seq_length": 128,
                "language": "multilingual"
            },
            "paraphrase-multilingual-MiniLM-L12-v2": {
                "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "description": "多语言MiniLM模型，支持50+语言",
                "dimension": 384,
                "max_seq_length": 128,
                "language": "multilingual"
            },
            "distiluse-base-multilingual-cased-v1": {
                "model_name": "sentence-transformers/distiluse-base-multilingual-cased-v1",
                "description": "多语言DistilUSE模型，支持50+语言",
                "dimension": 512,
                "max_seq_length": 128,
                "language": "multilingual"
            },
            "bge-large-zh": {
                "model_name": "BAAI/bge-large-zh",
                "description": "BGE中文大模型，中文任务表现优秀",
                "dimension": 1024,
                "max_seq_length": 512,
                "language": "zh"
            },
            "bge-base-zh": {
                "model_name": "BAAI/bge-base-zh",
                "description": "BGE中文基础模型",
                "dimension": 768,
                "max_seq_length": 512,
                "language": "zh"
            },
            "bge-small-zh": {
                "model_name": "BAAI/bge-small-zh",
                "description": "BGE中文小型模型，速度快",
                "dimension": 512,
                "max_seq_length": 512,
                "language": "zh"
            },
            "e5-large-v2": {
                "model_name": "intfloat/e5-large-v2",
                "description": "E5大模型，通用文本嵌入",
                "dimension": 1024,
                "max_seq_length": 512,
                "language": "en"
            },
            "e5-base-v2": {
                "model_name": "intfloat/e5-base-v2",
                "description": "E5基础模型",
                "dimension": 768,
                "max_seq_length": 512,
                "language": "en"
            },
            "multilingual-e5-large": {
                "model_name": "intfloat/multilingual-e5-large",
                "description": "多语言E5大模型",
                "dimension": 1024,
                "max_seq_length": 512,
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
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("SentenceTransformerManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_model(self, model_key: str, config: Optional[SentenceTransformerConfig] = None) -> bool:
        """加载Sentence Transformer模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.error("sentence_transformers库不可用")
            return False
        
        if model_key not in self.supported_models:
            self.logger.error(f"不支持的模型: {model_key}")
            return False
        
        if model_key in self.loaded_models:
            self.logger.info(f"模型已加载: {model_key}")
            return True
        
        try:
            model_info = self.supported_models[model_key]
            model_name = model_info["model_name"]
            
            self.logger.info(f"开始加载Sentence Transformer模型: {model_key}")
            
            # 设置设备
            device = config.device if config else "auto"
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 加载模型
            model = SentenceTransformer(
                model_name,
                cache_folder=self.model_cache_dir,
                device=device
            )
            
            # 保存模型信息
            self.loaded_models[model_key] = {
                "model": model,
                "config": model_info,
                "device": device,
                "loaded_time": torch.cuda.Event(enable_timing=True) if device == "cuda" else None
            }
            
            self.logger.info(f"Sentence Transformer模型加载成功: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载Sentence Transformer模型失败: {e}")
            self.stats["error_count"] += 1
            return False
    
    def encode_sentences(self, 
                        sentences: List[str], 
                        model_key: str,
                        batch_size: int = 32,
                        normalize_embeddings: bool = True,
                        show_progress_bar: bool = False,
                        convert_to_numpy: bool = True,
                        convert_to_tensor: bool = False) -> Dict[str, Any]:
        """编码句子为嵌入向量"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return self._error_response("sentence_transformers库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        if not sentences:
            return self._error_response("输入句子列表为空")
        
        try:
            import time
            start_time = time.time()
            
            model_info = self.loaded_models[model_key]
            model = model_info["model"]
            
            # 编码句子
            embeddings = model.encode(
                sentences,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                normalize_embeddings=normalize_embeddings,
                convert_to_numpy=convert_to_numpy,
                convert_to_tensor=convert_to_tensor
            )
            
            processing_time = time.time() - start_time
            
            # 转换为列表（如果是numpy数组）
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            elif torch.is_tensor(embeddings):
                embeddings = embeddings.cpu().numpy().tolist()
            
            # 更新统计
            self._update_stats(model_key, processing_time, len(sentences), len(embeddings))
            
            return {
                "success": True,
                "embeddings": embeddings,
                "sentence_count": len(sentences),
                "embedding_dim": len(embeddings[0]) if embeddings else 0,
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"句子编码失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def encode_single_sentence(self, sentence: str, model_key: str, **kwargs) -> Dict[str, Any]:
        """编码单个句子"""
        result = self.encode_sentences([sentence], model_key, **kwargs)
        
        if result["success"]:
            result["embedding"] = result["embeddings"][0] if result["embeddings"] else []
            # 移除列表形式的embeddings
            if "embeddings" in result:
                del result["embeddings"]
        
        return result
    
    def semantic_similarity(self, 
                          sentence1: str, 
                          sentence2: str, 
                          model_key: str) -> Dict[str, Any]:
        """计算句子语义相似度"""
        result = self.encode_sentences([sentence1, sentence2], model_key)
        
        if not result["success"]:
            return result
        
        embeddings = result["embeddings"]
        if len(embeddings) != 2:
            return self._error_response("编码结果不完整")
        
        # 计算余弦相似度
        vec1 = np.array(embeddings[0])
        vec2 = np.array(embeddings[1])
        
        similarity = self._cosine_similarity(vec1, vec2)
        
        result["similarity"] = float(similarity)
        return result
    
    def semantic_search(self,
                       query: str,
                       documents: List[str],
                       model_key: str,
                       top_k: int = 5,
                       score_threshold: float = 0.0) -> Dict[str, Any]:
        """语义搜索"""
        # 编码查询和文档
        all_texts = [query] + documents
        result = self.encode_sentences(all_texts, model_key)
        
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
            if similarity >= score_threshold:
                results.append({
                    "rank": i + 1,
                    "document_index": doc_idx,
                    "score": float(similarity),
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
    
    def batch_semantic_similarity(self,
                                sentence_pairs: List[tuple],
                                model_key: str) -> Dict[str, Any]:
        """批量计算句子相似度"""
        if not sentence_pairs:
            return self._error_response("句子对列表为空")
        
        # 提取所有唯一句子
        all_sentences = set()
        for sent1, sent2 in sentence_pairs:
            all_sentences.add(sent1)
            all_sentences.add(sent2)
        
        # 编码所有句子
        result = self.encode_sentences(list(all_sentences), model_key)
        if not result["success"]:
            return result
        
        embeddings = result["embeddings"]
        sentence_to_embedding = {sent: emb for sent, emb in zip(all_sentences, embeddings)}
        
        # 计算每对的相似度
        similarities = []
        for sent1, sent2 in sentence_pairs:
            if sent1 in sentence_to_embedding and sent2 in sentence_to_embedding:
                vec1 = np.array(sentence_to_embedding[sent1])
                vec2 = np.array(sentence_to_embedding[sent2])
                similarity = self._cosine_similarity(vec1, vec2)
                similarities.append({
                    "sentence1": sent1,
                    "sentence2": sent2,
                    "similarity": float(similarity)
                })
            else:
                similarities.append({
                    "sentence1": sent1,
                    "sentence2": sent2,
                    "similarity": 0.0,
                    "error": "句子编码失败"
                })
        
        return {
            "success": True,
            "similarities": similarities,
            "total_pairs": len(sentence_pairs),
            "model_used": model_key
        }
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
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
            
            self.logger.info(f"Sentence Transformer模型已卸载: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载Sentence Transformer模型失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        for model_key in list(self.loaded_models.keys()):
            self.unload_model(model_key)
        
        self.logger.info("Sentence Transformer管理器清理完成")

