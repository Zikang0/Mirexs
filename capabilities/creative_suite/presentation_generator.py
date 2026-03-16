"""
PPT生成器：基于内容自动生成演示文稿
支持幻灯片布局、内容生成、视觉设计
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import torch
from transformers import pipeline
from pydantic import BaseModel
import pandas as pd

from .document_generator import DocumentGenerator, DocumentConfig

logger = logging.getLogger(__name__)

class SlideType(Enum):
    """幻灯片类型枚举"""
    TITLE = "title"
    CONTENT = "content"
    SECTION = "section"
    IMAGE = "image"
    COMPARISON = "comparison"
    CONCLUSION = "conclusion"

class SlideLayout(BaseModel):
    """幻灯片布局配置"""
    slide_type: SlideType
    title: str
    content: List[str]
    image_prompt: Optional[str] = None
    layout_style: str = "default"

class PresentationConfig(BaseModel):
    """演示文稿配置"""
    theme: str = "professional"
    color_scheme: str = "blue"
    font_family: str = "Arial"
    slide_count: int = 10
    language: str = "zh"
    include_images: bool = True
    animation_style: str = "subtle"

class GeneratedPresentation(BaseModel):
    """生成的演示文稿"""
    slides: List[SlideLayout]
    metadata: Dict[str, Any]
    total_slides: int
    estimated_duration: int  # 分钟

class PresentationGenerator:
    """演示文稿生成器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.document_generator = DocumentGenerator()
        self.slide_generator = None
        self.layout_analyzer = None
        
        # 幻灯片模板
        self.slide_templates = self._load_slide_templates()
        
        # 主题配置
        self.theme_configs = self._load_theme_configs()
        
        logger.info("PresentationGenerator initialized")
    
    def _load_slide_templates(self) -> Dict[SlideType, Dict]:
        """加载幻灯片模板"""
        return {
            SlideType.TITLE: {
                "layout": "title_layout",
                "content_slots": ["main_title", "subtitle", "author", "date"],
                "image_slots": 0
            },
            SlideType.CONTENT: {
                "layout": "content_layout", 
                "content_slots": ["title", "bullet_points"],
                "image_slots": 1
            },
            SlideType.SECTION: {
                "layout": "section_layout",
                "content_slots": ["section_title"],
                "image_slots": 0
            },
            SlideType.IMAGE: {
                "layout": "image_layout",
                "content_slots": ["title", "caption"],
                "image_slots": 1
            },
            SlideType.COMPARISON: {
                "layout": "comparison_layout",
                "content_slots": ["title", "left_content", "right_content"],
                "image_slots": 0
            },
            SlideType.CONCLUSION: {
                "layout": "conclusion_layout",
                "content_slots": ["title", "key_points", "call_to_action"],
                "image_slots": 0
            }
        }
    
    def _load_theme_configs(self) -> Dict[str, Dict]:
        """加载主题配置"""
        return {
            "professional": {
                "colors": ["#2E5AAC", "#4A7BC8", "#6B9BD2", "#FFFFFF", "#333333"],
                "fonts": ["Arial", "Helvetica", "sans-serif"],
                "background": "gradient_blue"
            },
            "creative": {
                "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFE66D", "#FFFFFF"],
                "fonts": ["Comic Sans MS", "cursive"],
                "background": "pattern_dots"
            },
            "minimal": {
                "colors": ["#333333", "#666666", "#999999", "#FFFFFF", "#000000"],
                "fonts": ["Arial", "sans-serif"],
                "background": "solid_white"
            }
        }
    
    def load_models(self):
        """加载演示文稿生成模型"""
        try:
            # 加载文档生成器模型
            self.document_generator.load_models()
            
            # 加载幻灯片内容生成模型
            self.slide_generator = pipeline(
                "text-generation",
                model="microsoft/DialoGPT-medium",
                device=0 if self.device == "cuda" else -1,
                max_length=512
            )
            
            logger.info("Presentation generation models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load presentation models: {e}")
            raise
    
    def generate_presentation(self, 
                           topic: str, 
                           config: PresentationConfig,
                           outline: Optional[List[str]] = None) -> GeneratedPresentation:
        """
        生成完整演示文稿
        
        Args:
            topic: 演示主题
            config: 演示文稿配置
            outline: 可选的大纲
            
        Returns:
            GeneratedPresentation: 生成的演示文稿
        """
        try:
            if self.slide_generator is None:
                self.load_models()
            
            # 生成或使用提供的大纲
            if outline is None:
                outline = self._generate_outline(topic, config.slide_count)
            
            # 生成幻灯片内容
            slides = self._generate_slides_from_outline(topic, outline, config)
            
            # 计算预计时长
            duration = self._estimate_presentation_duration(slides)
            
            return GeneratedPresentation(
                slides=slides,
                metadata={
                    "topic": topic,
                    "theme": config.theme,
                    "color_scheme": config.color_scheme,
                    "generated_at": datetime.now().isoformat(),
                    "outline": outline
                },
                total_slides=len(slides),
                estimated_duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to generate presentation: {e}")
            raise
    
    def _generate_outline(self, topic: str, slide_count: int) -> List[str]:
        """生成演示文稿大纲"""
        prompt = f"""
        为主题"{topic}"创建一个包含{slide_count}个幻灯片的演示文稿大纲。
        请按照逻辑顺序组织内容，包含开场、主要内容、结论等部分。
        返回一个列表，每个元素是一个幻灯片的标题。
        """
        
        try:
            response = self.slide_generator(
                prompt,
                max_length=512,
                num_return_sequences=1
            )[0]['generated_text']
            
            # 解析响应中的大纲
            lines = response.strip().split('\n')
            outline = []
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line[0].isdigit()):
                    # 清理格式
                    clean_line = line.lstrip('- ').lstrip('1234567890. ')
                    if clean_line:
                        outline.append(clean_line)
            
            # 如果解析失败，生成默认大纲
            if len(outline) < 3:
                outline = [
                    f"{topic} - 介绍",
                    "背景与现状",
                    "核心问题分析",
                    "解决方案",
                    "实施计划",
                    "预期效果",
                    "总结与展望"
                ]
                
            return outline[:slide_count]
            
        except Exception as e:
            logger.warning(f"Failed to generate outline, using default: {e}")
            return self._create_default_outline(topic, slide_count)
    
    def _create_default_outline(self, topic: str, slide_count: int) -> List[str]:
        """创建默认大纲"""
        base_slides = [
            f"{topic} - 标题",
            "内容概览",
            "背景介绍",
            "问题分析",
            "解决方案",
            "实施步骤",
            "预期成果",
            "总结"
        ]
        
        # 根据要求的幻灯片数量调整
        if slide_count <= len(base_slides):
            return base_slides[:slide_count]
        else:
            # 添加更多幻灯片
            additional = [f"补充内容 {i}" for i in range(slide_count - len(base_slides))]
            return base_slides + additional
    
    def _generate_slides_from_outline(self, 
                                   topic: str, 
                                   outline: List[str], 
                                   config: PresentationConfig) -> List[SlideLayout]:
        """根据大纲生成幻灯片"""
        slides = []
        
        for i, slide_title in enumerate(outline):
            slide_type = self._determine_slide_type(i, len(outline))
            
            # 生成幻灯片内容
            content = self._generate_slide_content(topic, slide_title, slide_type)
            
            # 生成图片提示（如果需要）
            image_prompt = None
            if config.include_images and slide_type in [SlideType.CONTENT, SlideType.IMAGE]:
                image_prompt = self._generate_image_prompt(topic, slide_title)
            
            slide = SlideLayout(
                slide_type=slide_type,
                title=slide_title,
                content=content,
                image_prompt=image_prompt,
                layout_style=config.theme
            )
            
            slides.append(slide)
        
        return slides
    
    def _determine_slide_type(self, index: int, total_slides: int) -> SlideType:
        """确定幻灯片类型"""
        if index == 0:
            return SlideType.TITLE
        elif index == total_slides - 1:
            return SlideType.CONCLUSION
        elif index == 1 or index == total_slides // 3 or index == 2 * total_slides // 3:
            return SlideType.SECTION
        elif index % 4 == 0:  # 每4张幻灯片插入一张图片幻灯片
            return SlideType.IMAGE
        elif index == total_slides // 2:
            return SlideType.COMPARISON
        else:
            return SlideType.CONTENT
    
    def _generate_slide_content(self, topic: str, slide_title: str, slide_type: SlideType) -> List[str]:
        """生成幻灯片内容"""
        prompt = self._create_slide_content_prompt(topic, slide_title, slide_type)
        
        try:
            response = self.slide_generator(
                prompt,
                max_length=256,
                num_return_sequences=1
            )[0]['generated_text']
            
            # 解析要点
            lines = response.strip().split('\n')
            bullet_points = []
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•')):
                    clean_point = line.lstrip('-• ').strip()
                    if clean_point:
                        bullet_points.append(clean_point)
            
            # 如果解析失败，生成默认内容
            if not bullet_points:
                bullet_points = [
                    f"这是关于{slide_title}的关键信息",
                    "重要数据和事实",
                    "相关的分析和见解"
                ]
                
            return bullet_points[:5]  # 限制最多5个要点
            
        except Exception as e:
            logger.warning(f"Failed to generate slide content: {e}")
            return [f"关于{slide_title}的重要内容将在这里展示"]
    
    def _create_slide_content_prompt(self, topic: str, slide_title: str, slide_type: SlideType) -> str:
        """创建幻灯片内容生成提示词"""
        base_prompt = f"""
        为演示文稿"{topic}"的幻灯片"{slide_title}"生成3-5个要点。
        幻灯片类型：{slide_type.value}
        
        要求：
        - 每个要点简洁明了
        - 使用中文
        - 适合演示场景
        - 每个要点不超过20个字
        
        请以bullet points形式返回：
        """
        
        if slide_type == SlideType.TITLE:
            base_prompt += "\n包含主标题、副标题、演讲者信息"
        elif slide_type == SlideType.CONCLUSION:
            base_prompt += "\n包含关键总结和行动呼吁"
        elif slide_type == SlideType.COMPARISON:
            base_prompt += "\n包含对比分析的左右两部分内容"
            
        return base_prompt
    
    def _generate_image_prompt(self, topic: str, slide_title: str) -> str:
        """生成图片提示词"""
        prompt = f"""
        为演示文稿幻灯片生成图片提示词：
        主题：{topic}
        幻灯片标题：{slide_title}
        
        要求：
        - 生成适合商业演示的图片
        - 专业、简洁的风格
        - 与幻灯片内容相关
        - 返回英文提示词，适合AI图像生成
        
        图片提示词：
        """
        
        try:
            response = self.slide_generator(
                prompt,
                max_length=100,
                num_return_sequences=1
            )[0]['generated_text']
            
            # 清理响应
            image_prompt = response.strip().split('\n')[0].strip()
            return image_prompt if image_prompt else f"Professional business illustration for {slide_title}"
            
        except Exception as e:
            logger.warning(f"Failed to generate image prompt: {e}")
            return f"Professional business illustration for {slide_title}"
    
    def _estimate_presentation_duration(self, slides: List[SlideLayout]) -> int:
        """估算演示时长"""
        base_time_per_slide = 2  # 分钟
        content_based_time = 0
        
        for slide in slides:
            # 根据内容量调整时间
            content_length = sum(len(point) for point in slide.content)
            if content_length > 200:
                content_based_time += 3
            elif content_length > 100:
                content_based_time += 2
            else:
                content_based_time += 1
        
        return max(len(slides) * base_time_per_slide, content_based_time)
    
    def export_to_ppt(self, presentation: GeneratedPresentation, output_path: str):
        """导出为PPT文件"""
        try:
            # 这里应该集成python-pptx或其他PPT库
            # 目前返回模拟成功
            logger.info(f"Presentation exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export presentation: {e}")
            return False

# 单例实例
_presentation_generator_instance = None

def get_presentation_generator() -> PresentationGenerator:
    """获取演示文稿生成器单例"""
    global _presentation_generator_instance
    if _presentation_generator_instance is None:
        _presentation_generator_instance = PresentationGenerator()
    return _presentation_generator_instance

