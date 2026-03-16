"""
知识模型 - 知识相关模型
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    import torch
    import transformers
    from transformers import (
        AutoModelForQuestionAnswering,
        AutoModelForSequenceClassification,
        AutoTokenizer,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

@dataclass
class KnowledgeModelConfig:
    """知识模型配置"""
    model_name: str
    task_type: str  # qa, classification, ner, etc.
    max_length: int = 512
    device: str = "auto"

class KnowledgeModelManager:
    """知识模型管理器"""
    
    def __init__(self, model_cache_dir: str = "./models/knowledge"):
        self.model_cache_dir = model_cache_dir
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, Dict] = {}
        
        # 支持的知识模型
        self.supported_models = {
            "chinese-roberta-wwm-ext": {
                "type": "qa",
                "model_name": "hfl/chinese-roberta-wwm-ext",
                "description": "中文RoBERTa模型，适用于问答任务",
                "language": "zh"
            },
            "bert-base-chinese": {
                "type": "classification",
                "model_name": "bert-base-chinese", 
                "description": "中文BERT基础模型",
                "language": "zh"
            },
            "mengzi-bert-base": {
                "type": "qa",
                "model_name": "Langboat/mengzi-bert-base",
                "description": "孟子中文BERT模型",
                "language": "zh"
            },
            "albert-base-chinese": {
                "type": "classification",
                "model_name": "voidful/albert-chinese-base",
                "description": "中文ALBERT模型",
                "language": "zh"
            },
            "roberta-base-squad2": {
                "type": "qa", 
                "model_name": "deepset/roberta-base-squad2",
                "description": "英文问答模型",
                "language": "en"
            }
        }
        
        # 性能统计
        self.stats = {
            "total_queries": 0,
            "total_classifications": 0,
            "average_processing_time": 0.0,
            "model_usage": {},
            "error_count": 0
        }
        
        # 创建缓存目录
        os.makedirs(model_cache_dir, exist_ok=True)
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("KnowledgeModelManager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_model(self, model_key: str, config: Optional[KnowledgeModelConfig] = None) -> bool:
        """加载知识模型"""
        if not TRANSFORMERS_AVAILABLE:
            self.logger.error("transformers库不可用")
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
            task_type = model_info["type"]
            
            self.logger.info(f"开始加载知识模型: {model_key} ({model_name})")
            start_time = time.time()
            
            # 设置设备
            device = config.device if config else "auto"
            if device == "auto":
                device = 0 if torch.cuda.is_available() else -1
            
            # 根据任务类型加载模型
            if task_type == "qa":
                # 问答模型
                model = AutoModelForQuestionAnswering.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir
                )
                pipeline_task = "question-answering"
                
            elif task_type == "classification":
                # 文本分类模型
                model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir
                )
                pipeline_task = "text-classification"
            
            else:
                self.logger.error(f"不支持的任务类型: {task_type}")
                return False
            
            # 创建pipeline
            knowledge_pipeline = pipeline(
                pipeline_task,
                model=model,
                tokenizer=tokenizer,
                device=device,
                framework="pt"
            )
            
            # 保存模型信息
            self.loaded_models[model_key] = {
                "pipeline": knowledge_pipeline,
                "model": model,
                "tokenizer": tokenizer,
                "config": model_info,
                "device": device,
                "task_type": task_type,
                "loaded_time": time.time()
            }
            
            load_time = time.time() - start_time
            self.logger.info(f"知识模型加载完成，耗时: {load_time:.2f}秒")
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载知识模型失败: {e}")
            self.stats["error_count"] += 1
            return False
    
    def question_answering(self, 
                          question: str, 
                          context: str, 
                          model_key: str,
                          **kwargs) -> Dict[str, Any]:
        """问答任务"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        model_info = self.loaded_models[model_key]
        if model_info["task_type"] != "qa":
            return self._error_response(f"模型不支持问答任务: {model_key}")
        
        try:
            start_time = time.time()
            
            # 执行问答
            result = model_info["pipeline"](
                question=question,
                context=context,
                **kwargs
            )
            
            processing_time = time.time() - start_time
            
            # 更新统计
            self._update_stats(model_key, processing_time, "qa")
            
            return {
                "success": True,
                "answer": result["answer"],
                "score": result["score"],
                "start": result.get("start", 0),
                "end": result.get("end", 0),
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"问答任务失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def text_classification(self, 
                           text: str, 
                           model_key: str,
                           **kwargs) -> Dict[str, Any]:
        """文本分类"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        model_info = self.loaded_models[model_key]
        if model_info["task_type"] != "classification":
            return self._error_response(f"模型不支持分类任务: {model_key}")
        
        try:
            start_time = time.time()
            
            # 执行分类
            results = model_info["pipeline"](text, **kwargs)
            
            # 处理单条和多条结果
            if isinstance(results, dict):
                results = [results]
            
            processing_time = time.time() - start_time
            
            # 更新统计
            self._update_stats(model_key, processing_time, "classification")
            
            return {
                "success": True,
                "predictions": results,
                "top_prediction": results[0] if results else {},
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"文本分类失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def batch_classification(self, 
                            texts: List[str], 
                            model_key: str,
                            batch_size: int = 32,
                            **kwargs) -> Dict[str, Any]:
        """批量文本分类"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        model_info = self.loaded_models[model_key]
        if model_info["task_type"] != "classification":
            return self._error_response(f"模型不支持分类任务: {model_key}")
        
        try:
            start_time = time.time()
            
            # 批量执行分类
            all_results = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_results = model_info["pipeline"](batch_texts, **kwargs)
                all_results.extend(batch_results)
            
            processing_time = time.time() - start_time
            
            # 更新统计
            self._update_stats(model_key, processing_time, "classification", len(texts))
            
            return {
                "success": True,
                "predictions": all_results,
                "text_count": len(texts),
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"批量文本分类失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def knowledge_extraction(self, 
                           text: str, 
                           questions: List[str],
                           model_key: str,
                           **kwargs) -> Dict[str, Any]:
        """知识提取 - 从文本中提取多个问题的答案"""
        if not TRANSFORMERS_AVAILABLE:
            return self._error_response("transformers库不可用")
        
        if model_key not in self.loaded_models:
            return self._error_response(f"模型未加载: {model_key}")
        
        model_info = self.loaded_models[model_key]
        if model_info["task_type"] != "qa":
            return self._error_response(f"模型不支持问答任务: {model_key}")
        
        try:
            start_time = time.time()
            
            results = []
            for question in questions:
                qa_result = self.question_answering(question, text, model_key, **kwargs)
                if qa_result["success"]:
                    results.append({
                        "question": question,
                        "answer": qa_result["answer"],
                        "score": qa_result["score"]
                    })
                else:
                    results.append({
                        "question": question,
                        "answer": "",
                        "score": 0.0,
                        "error": qa_result.get("error", "未知错误")
                    })
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "extracted_knowledge": results,
                "question_count": len(questions),
                "successful_answers": len([r for r in results if r.get("score", 0) > 0]),
                "processing_time": processing_time,
                "model_used": model_key
            }
            
        except Exception as e:
            self.logger.error(f"知识提取失败: {e}")
            self.stats["error_count"] += 1
            return self._error_response(str(e))
    
    def _update_stats(self, model_key: str, processing_time: float, task_type: str, count: int = 1):
        """更新统计信息"""
        if task_type == "qa":
            self.stats["total_queries"] += count
        elif task_type == "classification":
            self.stats["total_classifications"] += count
        
        # 更新平均处理时间
        alpha = 0.1
        self.stats["average_processing_time"] = (
            alpha * processing_time + (1 - alpha) * self.stats["average_processing_time"]
        )
        
        # 更新模型使用统计
        if model_key not in self.stats["model_usage"]:
            self.stats["model_usage"][model_key] = {
                "qa_queries": 0,
                "classifications": 0,
                "total_time": 0.0
            }
        
        if task_type == "qa":
            self.stats["model_usage"][model_key]["qa_queries"] += count
        elif task_type == "classification":
            self.stats["model_usage"][model_key]["classifications"] += count
        
        self.stats["model_usage"][model_key]["total_time"] += processing_time
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error": error_msg,
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
            info["task_type"] = model_info["task_type"]
        
        return info
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()
        
        # 计算每个模型的平均处理时间
        for model_key, usage in stats["model_usage"].items():
            total_operations = usage["qa_queries"] + usage["classifications"]
            if total_operations > 0:
                usage["average_time"] = usage["total_time"] / total_operations
            else:
                usage["average_time"] = 0.0
        
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
            
            self.logger.info(f"知识模型已卸载: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载知识模型失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        for model_key in list(self.loaded_models.keys()):
            self.unload_model(model_key)
        
        self.logger.info("知识模型管理器清理完成")

