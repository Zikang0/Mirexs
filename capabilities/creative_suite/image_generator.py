"""
图像生成器：基于文本描述生成和编辑图像
支持多种风格和分辨率的图像生成
"""

import os
import json
import logging
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from io import BytesIO

import torch
import torchvision.transforms as transforms
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
import numpy as np

# 尝试导入Stable Diffusion相关库
try:
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from diffusers import StableDiffusionImg2ImgPipeline
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    logger.warning("diffusers not available, image generation will be limited")

logger = logging.getLogger(__name__)

class ImageStyle(Enum):
    """图像风格枚举"""
    REALISTIC = "realistic"
    ANIME = "anime" 
    OIL_PAINTING = "oil_painting"
    WATERCOLOR = "watercolor"
    DIGITAL_ART = "digital_art"
    MINIMALIST = "minimalist"
    PHOTOGRAPHIC = "photographic"

class ImageSize(Enum):
    """图像尺寸枚举"""
    SMALL = (256, 256)
    MEDIUM = (512, 512)
    LARGE = (768, 768)
    HD = (1024, 1024)

class ImageGenerationConfig(BaseModel):
    """图像生成配置"""
    prompt: str
    negative_prompt: Optional[str] = ""
    style: ImageStyle = ImageStyle.REALISTIC
    size: ImageSize = ImageSize.MEDIUM
    num_images: int = 1
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    seed: Optional[int] = None

class GeneratedImage(BaseModel):
    """生成的图像"""
    image_data: str  # base64编码
    metadata: Dict[str, Any]
    prompt: str
    style: str
    size: Tuple[int, int]

class ImageEditor:
    """图像编辑器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.editing_models = {}
        
    def resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """调整图像尺寸"""
        return image.resize(size, Image.Resampling.LANCZOS)
    
    def adjust_brightness(self, image: Image.Image, factor: float) -> Image.Image:
        """调整亮度"""
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    
    def adjust_contrast(self, image: Image.Image, factor: float) -> Image.Image:
        """调整对比度"""
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    def apply_filter(self, image: Image.Image, filter_type: str) -> Image.Image:
        """应用滤镜"""
        if filter_type == "grayscale":
            return image.convert("L").convert("RGB")
        elif filter_type == "sepia":
            # 简单的棕褐色滤镜
            data = np.array(image)
            r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
            tr = 0.393 * r + 0.769 * g + 0.189 * b
            tg = 0.349 * r + 0.686 * g + 0.168 * b
            tb = 0.272 * r + 0.534 * g + 0.131 * b
            data[:,:,0] = np.minimum(tr, 255)
            data[:,:,1] = np.minimum(tg, 255)
            data[:,:,2] = np.minimum(tb, 255)
            return Image.fromarray(data.astype('uint8'))
        else:
            return image

class ImageGenerator:
    """图像生成器"""
    
    def __init__(self, model_name: str = "runwayml/stable-diffusion-v1-5"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.generation_pipeline = None
        self.editing_pipeline = None
        self.image_editor = ImageEditor()
        
        # 风格提示词映射
        self.style_prompts = self._load_style_prompts()
        
        # 模型配置
        self.model_config = {
            "safety_checker": None,  # 禁用安全检查器以节省内存
            "requires_safety_checker": False
        }
        
        logger.info(f"ImageGenerator initialized with device: {self.device}")
    
    def _load_style_prompts(self) -> Dict[ImageStyle, str]:
        """加载风格提示词"""
        return {
            ImageStyle.REALISTIC: "photorealistic, highly detailed, realistic",
            ImageStyle.ANIME: "anime style, vibrant colors, Japanese animation",
            ImageStyle.OIL_PAINTING: "oil painting, brush strokes, artistic",
            ImageStyle.WATERCOLOR: "watercolor painting, soft colors, transparent",
            ImageStyle.DIGITAL_ART: "digital art, concept art, illustration",
            ImageStyle.MINIMALIST: "minimalist, simple, clean lines",
            ImageStyle.PHOTOGRAPHIC: "professional photography, sharp focus"
        }
    
    def load_models(self):
        """加载图像生成模型"""
        try:
            if not DIFFUSERS_AVAILABLE:
                logger.warning("diffusers not available, using placeholder image generation")
                return
            
            logger.info(f"Loading image generation model: {self.model_name}")
            
            # 加载文本到图像生成管道
            self.generation_pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                **self.model_config
            )
            
            # 使用更快的调度器
            self.generation_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.generation_pipeline.scheduler.config
            )
            
            if self.device == "cuda":
                self.generation_pipeline = self.generation_pipeline.to("cuda")
                # 启用内存优化
                self.generation_pipeline.enable_attention_slicing()
                self.generation_pipeline.enable_memory_efficient_attention()
            
            # 加载图像到图像编辑管道
            self.editing_pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                **self.model_config
            )
            
            if self.device == "cuda":
                self.editing_pipeline = self.editing_pipeline.to("cuda")
                self.editing_pipeline.enable_attention_slicing()
            
            logger.info("Image generation models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load image generation models: {e}")
            # 不抛出异常，允许使用占位符模式
    
    def _enhance_prompt(self, prompt: str, style: ImageStyle, negative_prompt: str) -> Tuple[str, str]:
        """增强提示词"""
        style_prompt = self.style_prompts.get(style, "")
        enhanced_prompt = f"{prompt}, {style_prompt}, high quality, masterpiece"
        
        # 增强负面提示词
        enhanced_negative = f"{negative_prompt}, low quality, blurry, distorted, ugly"
        
        return enhanced_prompt, enhanced_negative
    
    def generate_image(self, config: ImageGenerationConfig) -> GeneratedImage:
        """
        生成图像
        
        Args:
            config: 图像生成配置
            
        Returns:
            GeneratedImage: 生成的图像
        """
        try:
            # 如果模型不可用，生成占位符图像
            if self.generation_pipeline is None and not DIFFUSERS_AVAILABLE:
                return self._generate_placeholder_image(config)
            
            if self.generation_pipeline is None:
                self.load_models()
            
            # 设置随机种子
            if config.seed is not None:
                torch.manual_seed(config.seed)
            
            # 增强提示词
            enhanced_prompt, enhanced_negative = self._enhance_prompt(
                config.prompt, config.style, config.negative_prompt
            )
            
            # 生成图像
            with torch.autocast("cuda" if self.device == "cuda" else "cpu"):
                result = self.generation_pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=enhanced_negative,
                    height=config.size.value[1],
                    width=config.size.value[0],
                    num_inference_steps=config.num_inference_steps,
                    guidance_scale=config.guidance_scale,
                    num_images_per_prompt=config.num_images
                )
            
            # 获取第一张图像
            generated_image = result.images[0]
            
            # 转换为base64
            buffered = BytesIO()
            generated_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return GeneratedImage(
                image_data=img_str,
                metadata={
                    "model": self.model_name,
                    "style": config.style.value,
                    "size": config.size.value,
                    "guidance_scale": config.guidance_scale,
                    "inference_steps": config.num_inference_steps,
                    "seed": config.seed,
                    "generated_at": datetime.now().isoformat()
                },
                prompt=config.prompt,
                style=config.style.value,
                size=config.size.value
            )
            
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            # 返回占位符图像
            return self._generate_placeholder_image(config)
    
    def _generate_placeholder_image(self, config: ImageGenerationConfig) -> GeneratedImage:
        """生成占位符图像（当模型不可用时）"""
        width, height = config.size.value
        
        # 创建简单的占位图像
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)
        
        # 添加文本
        try:
            font = ImageFont.load_default()
            text = f"Placeholder for: {config.prompt}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            draw.text((x, y), text, fill='black', font=font)
        except:
            # 如果字体加载失败，使用简单绘制
            draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill='white')
        
        # 转换为base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return GeneratedImage(
            image_data=img_str,
            metadata={
                "model": "placeholder",
                "style": config.style.value,
                "size": config.size.value,
                "note": "Real model not available, using placeholder",
                "generated_at": datetime.now().isoformat()
            },
            prompt=config.prompt,
            style=config.style.value,
            size=config.size.value
        )
    
    def edit_image(self, 
                  base_image: Image.Image, 
                  edit_prompt: str,
                  strength: float = 0.75) -> GeneratedImage:
        """
        编辑现有图像
        
        Args:
            base_image: 基础图像
            edit_prompt: 编辑提示词
            strength: 编辑强度
            
        Returns:
            GeneratedImage: 编辑后的图像
        """
        try:
            if self.editing_pipeline is None:
                self.load_models()
            
            if self.editing_pipeline is None:
                raise RuntimeError("Image editing pipeline not available")
            
            # 调整图像尺寸以适应模型
            base_image = base_image.resize((512, 512))
            
            # 执行图像编辑
            with torch.autocast("cuda" if self.device == "cuda" else "cpu"):
                result = self.editing_pipeline(
                    prompt=edit_prompt,
                    image=base_image,
                    strength=strength,
                    guidance_scale=7.5,
                    num_inference_steps=50
                )
            
            edited_image = result.images[0]
            
            # 转换为base64
            buffered = BytesIO()
            edited_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return GeneratedImage(
                image_data=img_str,
                metadata={
                    "model": self.model_name,
                    "edit_type": "img2img",
                    "strength": strength,
                    "edit_prompt": edit_prompt,
                    "edited_at": datetime.now().isoformat()
                },
                prompt=edit_prompt,
                style="edited",
                size=edited_image.size
            )
            
        except Exception as e:
            logger.error(f"Failed to edit image: {e}")
            raise
    
    def batch_generate_images(self, configs: List[ImageGenerationConfig]) -> List[GeneratedImage]:
        """批量生成图像"""
        results = []
        for config in configs:
            try:
                image = self.generate_image(config)
                results.append(image)
            except Exception as e:
                logger.error(f"Failed to generate image for prompt '{config.prompt}': {e}")
                # 创建失败的占位符
                results.append(self._generate_placeholder_image(config))
        return results
    
    def apply_style_transfer(self, 
                           content_image: Image.Image, 
                           style_image: Image.Image,
                           strength: float = 0.5) -> GeneratedImage:
        """
        应用风格迁移
        
        Args:
            content_image: 内容图像
            style_image: 风格图像
            strength: 风格强度
            
        Returns:
            GeneratedImage: 风格迁移后的图像
        """
        try:
            # 这里应该实现神经风格迁移
            # 目前使用简单的图像混合作为占位
            content_resized = content_image.resize((512, 512))
            style_resized = style_image.resize((512, 512))
            
            # 简单的alpha混合
            blended = Image.blend(content_resized, style_resized, strength)
            
            # 转换为base64
            buffered = BytesIO()
            blended.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return GeneratedImage(
                image_data=img_str,
                metadata={
                    "method": "alpha_blending",
                    "strength": strength,
                    "processed_at": datetime.now().isoformat()
                },
                prompt="Style transfer result",
                style="transferred",
                size=blended.size
            )
            
        except Exception as e:
            logger.error(f"Failed to apply style transfer: {e}")
            raise

# 单例实例
_image_generator_instance = None

def get_image_generator() -> ImageGenerator:
    """获取图像生成器单例"""
    global _image_generator_instance
    if _image_generator_instance is None:
        _image_generator_instance = ImageGenerator()
    return _image_generator_instance

