"""
NLP模块 - 自然语言处理模型
"""

from .language_models import LanguageModelManager, ModelType, GenerationParameters
from .embedding_models import EmbeddingModelManager, EmbeddingConfig
from .knowledge_models import KnowledgeModelManager, KnowledgeModelConfig
from .llama_integration import LlamaIntegration
from .qwen_integration import QwenIntegration
from .mistral_integration import MistralIntegration
from .sentence_transformers import SentenceTransformerManager, SentenceTransformerConfig
from .tokenizer_manager import TokenizerManager, TokenizerConfig
from .model_quantizer import ModelQuantizer, QuantizationConfig

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"

# 导出公共接口
__all__ = [
    # 主管理器
    "LanguageModelManager",
    "EmbeddingModelManager", 
    "KnowledgeModelManager",
    "SentenceTransformerManager",
    "TokenizerManager",
    "ModelQuantizer",
    
    # 模型集成
    "LlamaIntegration",
    "QwenIntegration", 
    "MistralIntegration",
    
    # 配置类
    "ModelType",
    "GenerationParameters",
    "EmbeddingConfig",
    "KnowledgeModelConfig", 
    "SentenceTransformerConfig",
    "TokenizerConfig",
    "QuantizationConfig",
    
    # 版本信息
    "__version__",
    "__author__"
]

# 模块初始化
def initialize_nlp_module(cache_dir: str = "./models") -> dict:
    """
    初始化NLP模块
    
    Args:
        cache_dir: 模型缓存目录
        
    Returns:
        dict: 包含所有管理器的字典
    """
    managers = {
        "language_models": LanguageModelManager(f"{cache_dir}/language"),
        "embedding_models": EmbeddingModelManager(f"{cache_dir}/embeddings"),
        "knowledge_models": KnowledgeModelManager(f"{cache_dir}/knowledge"),
        "sentence_transformers": SentenceTransformerManager(f"{cache_dir}/sentence_transformers"),
        "tokenizer_manager": TokenizerManager(f"{cache_dir}/tokenizers"),
        "model_quantizer": ModelQuantizer(),
        "llama_integration": LlamaIntegration(f"{cache_dir}/llama"),
        "qwen_integration": QwenIntegration(f"{cache_dir}/qwen"),
        "mistral_integration": MistralIntegration(f"{cache_dir}/mistral")
    }
    
    return managers

# 便捷函数
def get_available_models() -> dict:
    """
    获取所有可用的模型信息
    
    Returns:
        dict: 模型信息字典
    """
    return {
        "language_models": [
            "llama-2-7b", "llama-2-13b", "llama-2-70b",
            "qwen-7b", "qwen-14b", "qwen-72b", 
            "mistral-7b", "mixtral-8x7b", "bloom-7b"
        ],
        "embedding_models": [
            "bge-large-zh", "bge-base-en", "text2vec-base-chinese",
            "all-mpnet-base-v2", "multilingual-e5-large"
        ],
        "sentence_transformers": [
            "all-mpnet-base-v2", "all-MiniLM-L6-v2", "paraphrase-multilingual-mpnet-base-v2",
            "bge-large-zh", "e5-large-v2", "multilingual-e5-large"
        ],
        "knowledge_models": [
            "chinese-roberta-wwm-ext", "bert-base-chinese", "mengzi-bert-base",
            "roberta-base-squad2"
        ]
    }

def check_dependencies() -> dict:
    """
    检查依赖库是否可用
    
    Returns:
        dict: 依赖状态字典
    """
    dependencies = {
        "torch": False,
        "transformers": False,
        "sentence_transformers": False,
        "bitsandbytes": False
    }
    
    try:
        import torch
        dependencies["torch"] = True
    except ImportError:
        pass
    
    try:
        import transformers
        dependencies["transformers"] = True
    except ImportError:
        pass
    
    try:
        import sentence_transformers
        dependencies["sentence_transformers"] = True
    except ImportError:
        pass
    
    try:
        import bitsandbytes
        dependencies["bitsandbytes"] = True
    except ImportError:
        pass
    
    return dependencies

# 模块信息
MODULE_INFO = {
    "name": "Mirexs NLP Module",
    "version": __version__,
    "description": "自然语言处理模块，提供多种语言模型、嵌入模型和知识模型",
    "features": [
        "多模型语言生成",
        "文本嵌入和语义搜索", 
        "知识问答和文本分类",
        "模型量化和优化",
        "统一的分词器管理"
    ]
}

def get_module_info() -> dict:
    """
    获取模块信息
    
    Returns:
        dict: 模块信息
    """
    return MODULE_INFO.copy()