"""
文档生成器：基于LLM生成各种类型的文档
支持报告、文章、邮件、代码等文档类型
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    pipeline,
    GenerationConfig
)
import pandas as pd
from pydantic import BaseModel

from config.system.main_config import load_system_config
from cognitive.reasoning.task_decomposer import TaskDecomposer

logger = logging.getLogger(__name__)

class DocumentConfig(BaseModel):
    """文档生成配置"""
    document_type: str  # report, article, email, code, etc.
    style: str = "professional"
    tone: str = "neutral"
    length: str = "medium"  # short, medium, long
    language: str = "zh"  # zh, en, etc.
    template: Optional[str] = None

class GeneratedDocument(BaseModel):
    """生成的文档结果"""
    content: str
    metadata: Dict[str, Any]
    quality_score: float
    revision_suggestions: List[str]

class DocumentGenerator:
    """文档生成器核心类"""
    
    def __init__(self, model_name: str = "Qwen/Qwen-7B-Chat"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self.generation_pipeline = None
        self.task_decomposer = TaskDecomposer()
        
        # 文档模板系统
        self.templates = self._load_document_templates()
        
        # 质量评估模型
        self.quality_model = None
        
        logger.info(f"DocumentGenerator initialized with device: {self.device}")
    
    def _load_document_templates(self) -> Dict[str, Dict]:
        """加载文档模板"""
        templates = {
            "report": {
                "structure": "引言|背景|方法|结果|讨论|结论|建议",
                "sections": ["title", "introduction", "background", "methodology", 
                           "results", "discussion", "conclusion", "recommendations"]
            },
            "article": {
                "structure": "标题|导语|正文|总结",
                "sections": ["title", "lead", "body", "conclusion"]
            },
            "email": {
                "structure": "主题|称呼|正文|结束语|签名",
                "sections": ["subject", "greeting", "body", "closing", "signature"]
            },
            "code": {
                "structure": "文件头|导入|类定义|函数定义|主程序",
                "sections": ["header", "imports", "classes", "functions", "main"]
            }
        }
        return templates
    
    def load_models(self):
        """加载文档生成模型"""
        try:
            logger.info(f"Loading document generation model: {self.model_name}")
            
            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            # 创建文本生成pipeline
            self.generation_pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                max_new_tokens=2048,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                return_full_text=False
            )
            
            logger.info("Document generation models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load document generation models: {e}")
            raise
    
    def generate_document(self, 
                         topic: str, 
                         config: DocumentConfig,
                         context: Optional[str] = None) -> GeneratedDocument:
        """
        生成完整文档
        
        Args:
            topic: 文档主题
            config: 文档配置
            context: 上下文信息
            
        Returns:
            GeneratedDocument: 生成的文档
        """
        try:
            if self.generation_pipeline is None:
                self.load_models()
            
            # 任务分解
            decomposition = self.task_decomposer.decompose_document_generation(
                topic, config.document_type, config.style
            )
            
            # 生成文档结构
            structure = self._generate_document_structure(topic, config)
            
            # 分步生成文档内容
            document_parts = {}
            for section in structure["sections"]:
                section_prompt = self._create_section_prompt(
                    topic, section, config, context
                )
                section_content = self._generate_section_content(section_prompt)
                document_parts[section] = section_content
            
            # 组合完整文档
            full_document = self._assemble_document(document_parts, config)
            
            # 质量评估
            quality_score, suggestions = self._evaluate_document_quality(
                full_document, topic, config
            )
            
            return GeneratedDocument(
                content=full_document,
                metadata={
                    "topic": topic,
                    "document_type": config.document_type,
                    "style": config.style,
                    "tone": config.tone,
                    "length": config.length,
                    "language": config.language,
                    "generated_at": datetime.now().isoformat(),
                    "structure": structure,
                    "sections": list(document_parts.keys())
                },
                quality_score=quality_score,
                revision_suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Failed to generate document: {e}")
            raise
    
    def _generate_document_structure(self, topic: str, config: DocumentConfig) -> Dict:
        """生成文档结构"""
        template = self.templates.get(config.document_type, self.templates["report"])
        
        prompt = f"""
        为以下主题生成一个{config.document_type}的详细结构：
        主题：{topic}
        风格：{config.style}
        语气：{config.tone}
        长度：{config.length}
        
        请基于{template['structure']}的基本结构，提供详细的章节划分。
        返回JSON格式，包含sections字段，每个section包含name和description。
        """
        
        try:
            if self.generation_pipeline is None:
                self.load_models()
                
            response = self.generation_pipeline(
                prompt,
                max_new_tokens=512,
                temperature=0.3
            )[0]['generated_text']
            
            # 解析响应中的JSON结构
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                structure = json.loads(json_match.group())
                return structure
            else:
                # 如果无法解析JSON，使用模板结构
                return {
                    "sections": [{"name": section, "description": f"{section}部分"} 
                               for section in template["sections"]]
                }
                
        except Exception as e:
            logger.warning(f"Failed to generate custom structure, using template: {e}")
            return {
                "sections": [{"name": section, "description": f"{section}部分"} 
                           for section in template["sections"]]
            }
    
    def _create_section_prompt(self, 
                             topic: str, 
                             section: Dict, 
                             config: DocumentConfig,
                             context: Optional[str] = None) -> str:
        """创建章节生成提示词"""
        section_name = section["name"]
        section_desc = section.get("description", "")
        
        prompt = f"""
        请为以下文档的{section_name}部分生成内容：
        
        文档主题：{topic}
        文档类型：{config.document_type}
        风格：{config.style}
        语气：{config.tone}
        语言：{config.language}
        部分描述：{section_desc}
        """
        
        if context:
            prompt += f"\n上下文信息：{context}"
            
        if config.document_type == "code":
            prompt += f"\n请生成高质量的{config.language}代码，包含适当的注释和文档字符串。"
        elif config.document_type == "email":
            prompt += f"\n请生成专业、得体的邮件内容。"
        elif config.document_type == "report":
            prompt += f"\n请生成结构严谨、数据驱动的报告内容。"
            
        prompt += f"\n\n请只生成{section_name}部分的内容："
        
        return prompt
    
    def _generate_section_content(self, prompt: str) -> str:
        """生成章节内容"""
        try:
            response = self.generation_pipeline(
                prompt,
                max_new_tokens=1024,
                temperature=0.7,
                top_p=0.9
            )[0]['generated_text']
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate section content: {e}")
            return f"内容生成失败: {str(e)}"
    
    def _assemble_document(self, document_parts: Dict, config: DocumentConfig) -> str:
        """组合文档各部分"""
        if config.document_type == "code":
            return self._assemble_code_document(document_parts)
        elif config.document_type == "email":
            return self._assemble_email_document(document_parts)
        else:
            return self._assemble_general_document(document_parts, config)
    
    def _assemble_general_document(self, document_parts: Dict, config: DocumentConfig) -> str:
        """组合通用文档"""
        assembled_doc = ""
        
        for section_name, content in document_parts.items():
            if section_name == "title":
                assembled_doc += f"# {content}\n\n"
            else:
                assembled_doc += f"## {section_name}\n\n{content}\n\n"
                
        return assembled_doc
    
    def _assemble_code_document(self, document_parts: Dict) -> str:
        """组合代码文档"""
        code_doc = ""
        
        # 文件头
        if "header" in document_parts:
            code_doc += f'"""{document_parts["header"]}"""\n\n'
        
        # 导入部分
        if "imports" in document_parts:
            code_doc += document_parts["imports"] + "\n\n"
        
        # 类定义
        if "classes" in document_parts:
            code_doc += document_parts["classes"] + "\n\n"
        
        # 函数定义
        if "functions" in document_parts:
            code_doc += document_parts["functions"] + "\n\n"
        
        # 主程序
        if "main" in document_parts:
            code_doc += f"if __name__ == '__main__':\n"
            main_code = document_parts["main"]
            # 缩进主程序代码
            for line in main_code.split('\n'):
                code_doc += f"    {line}\n"
                
        return code_doc
    
    def _assemble_email_document(self, document_parts: Dict) -> str:
        """组合邮件文档"""
        email = ""
        
        if "subject" in document_parts:
            email += f"主题: {document_parts['subject']}\n\n"
        
        if "greeting" in document_parts:
            email += f"{document_parts['greeting']}\n\n"
        
        if "body" in document_parts:
            email += f"{document_parts['body']}\n\n"
        
        if "closing" in document_parts:
            email += f"{document_parts['closing']}\n\n"
        
        if "signature" in document_parts:
            email += f"{document_parts['signature']}\n"
            
        return email
    
    def _evaluate_document_quality(self, 
                                 document: str, 
                                 topic: str, 
                                 config: DocumentConfig) -> tuple:
        """评估文档质量"""
        # 简单的基于规则的质量评估
        quality_score = 0.8  # 基础分数
        
        # 长度评估
        doc_length = len(document)
        if config.length == "short" and doc_length > 500:
            quality_score -= 0.1
        elif config.length == "medium" and (doc_length < 300 or doc_length > 2000):
            quality_score -= 0.1
        elif config.length == "long" and doc_length < 1000:
            quality_score -= 0.1
            
        # 结构评估
        if config.document_type == "report":
            sections = ["引言", "方法", "结果", "结论"]
            found_sections = sum(1 for section in sections if section in document)
            quality_score += found_sections * 0.05
            
        # 生成改进建议
        suggestions = []
        if len(document) < 100:
            suggestions.append("文档内容较短，建议补充更多细节")
        if "。" not in document and "." not in document:
            suggestions.append("文档可能缺乏完整的句子结构")
            
        return min(1.0, max(0.0, quality_score)), suggestions
    
    def batch_generate_documents(self, 
                               topics: List[str], 
                               configs: List[DocumentConfig]) -> List[GeneratedDocument]:
        """批量生成文档"""
        results = []
        for topic, config in zip(topics, configs):
            try:
                document = self.generate_document(topic, config)
                results.append(document)
            except Exception as e:
                logger.error(f"Failed to generate document for topic '{topic}': {e}")
                # 创建失败的占位符
                results.append(GeneratedDocument(
                    content=f"文档生成失败: {str(e)}",
                    metadata={"error": str(e), "topic": topic},
                    quality_score=0.0,
                    revision_suggestions=["生成过程出现错误"]
                ))
        return results

# 单例实例
_document_generator_instance = None

def get_document_generator() -> DocumentGenerator:
    """获取文档生成器单例"""
    global _document_generator_instance
    if _document_generator_instance is None:
        _document_generator_instance = DocumentGenerator()
    return _document_generator_instance

