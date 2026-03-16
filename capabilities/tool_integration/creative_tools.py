"""
创意工具集成模块
提供图像生成、音乐创作、视频编辑等创意工具集成
"""

import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import base64
import json
from datetime import datetime

try:
    import torch
    import torchvision
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from transformers import pipeline
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

logger = logging.getLogger(__name__)

class ImageGenerator:
    """图像生成器"""
    
    def __init__(self):
        self.sd_pipeline = None
        self.image_editor = ImageEditor()
        self.initialize_models()
    
    def initialize_models(self):
        """初始化模型"""
        try:
            if DIFFUSERS_AVAILABLE and torch.cuda.is_available():
                # 初始化Stable Diffusion管道
                self.sd_pipeline = StableDiffusionPipeline.from_pretrained(
                    "runwayml/stable-diffusion-v1-5",
                    torch_dtype=torch.float16,
                    safety_checker=None,
                    requires_safety_checker=False
                )
                self.sd_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.sd_pipeline.scheduler.config
                )
                self.sd_pipeline = self.sd_pipeline.to("cuda")
                logger.info("Stable Diffusion模型初始化成功")
            else:
                logger.warning("Stable Diffusion模型不可用，将使用基础图像生成功能")
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
    
    async def generate_image(self, prompt: str, 
                           negative_prompt: str = "",
                           width: int = 512, 
                           height: int = 512,
                           num_inference_steps: int = 20,
                           guidance_scale: float = 7.5) -> Dict[str, Any]:
        """根据提示生成图像"""
        try:
            if self.sd_pipeline:
                # 使用Stable Diffusion生成图像
                with torch.autocast("cuda"):
                    image = self.sd_pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale
                    ).images[0]
                
                # 保存临时文件
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                image.save(temp_file.name)
                
                return {
                    "success": True,
                    "image_path": temp_file.name,
                    "prompt": prompt,
                    "dimensions": (width, height)
                }
            else:
                # 基础图像生成（占位符实现）
                return await self._generate_basic_image(prompt, width, height)
        except Exception as e:
            logger.error(f"图像生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_basic_image(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """基础图像生成（当AI模型不可用时使用）"""
        try:
            # 创建基础图像
            image = Image.new('RGB', (width, height), color='lightblue')
            draw = ImageDraw.Draw(image)
            
            # 添加文本
            try:
                font = ImageFont.load_default()
                text = f"Prompt: {prompt}"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                draw.text((x, y), text, fill='black', font=font)
            except Exception:
                # 如果字体加载失败，使用简单绘图
                draw.rectangle([50, 50, width-50, height-50], outline='blue', width=5)
            
            # 保存图像
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(temp_file.name)
            
            return {
                "success": True,
                "image_path": temp_file.name,
                "prompt": prompt,
                "dimensions": (width, height),
                "note": "使用基础图像生成（AI模型不可用）"
            }
        except Exception as e:
            logger.error(f"基础图像生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_image_variations(self, image_path: str, 
                                      num_variations: int = 4,
                                      strength: float = 0.7) -> Dict[str, Any]:
        """生成图像变体"""
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": "图像文件不存在"}
            
            # 这里需要img2img模型，简化实现
            variations = []
            base_image = Image.open(image_path)
            
            for i in range(num_variations):
                # 创建变体（这里使用简单的图像处理）
                variation = base_image.copy()
                
                # 应用随机变换
                if PILLOW_AVAILABLE:
                    enhancer = ImageEnhance.Brightness(variation)
                    variation = enhancer.enhance(0.8 + 0.4 * (i / num_variations))
                    
                    enhancer = ImageEnhance.Color(variation)
                    variation = enhancer.enhance(0.7 + 0.6 * (i / num_variations))
                
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                variation.save(temp_file.name)
                variations.append(temp_file.name)
            
            return {
                "success": True,
                "variations": variations,
                "original_image": image_path,
                "num_variations": num_variations
            }
        except Exception as e:
            logger.error(f"图像变体生成失败: {e}")
            return {"success": False, "error": str(e)}

class ImageEditor:
    """图像编辑器"""
    
    def __init__(self):
        pass
    
    async def resize_image(self, image_path: str, 
                          width: int, 
                          height: int,
                          maintain_aspect: bool = True) -> Dict[str, Any]:
        """调整图像尺寸"""
        try:
            if not PILLOW_AVAILABLE:
                return {"success": False, "error": "PIL库不可用"}
            
            if not os.path.exists(image_path):
                return {"success": False, "error": "图像文件不存在"}
            
            image = Image.open(image_path)
            
            if maintain_aspect:
                # 保持宽高比
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
            else:
                # 强制调整尺寸
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(temp_file.name)
            
            return {
                "success": True,
                "output_path": temp_file.name,
                "original_dimensions": image.size,
                "new_dimensions": (width, height)
            }
        except Exception as e:
            logger.error(f"图像尺寸调整失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def apply_filter(self, image_path: str, 
                          filter_type: str,
                          intensity: float = 1.0) -> Dict[str, Any]:
        """应用图像滤镜"""
        try:
            if not PILLOW_AVAILABLE:
                return {"success": False, "error": "PIL库不可用"}
            
            if not os.path.exists(image_path):
                return {"success": False, "error": "图像文件不存在"}
            
            image = Image.open(image_path)
            
            filter_map = {
                "blur": ImageFilter.GaussianBlur(radius=intensity*5),
                "sharpen": ImageFilter.UnsharpMask(radius=intensity, percent=150),
                "edge_enhance": ImageFilter.EDGE_ENHANCE,
                "emboss": ImageFilter.EMBOSS,
                "contour": ImageFilter.CONTOUR,
                "smooth": ImageFilter.SMOOTH
            }
            
            if filter_type in filter_map:
                filtered_image = image.filter(filter_map[filter_type])
            else:
                return {"success": False, "error": f"不支持的滤镜类型: {filter_type}"}
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            filtered_image.save(temp_file.name)
            
            return {
                "success": True,
                "output_path": temp_file.name,
                "filter_type": filter_type,
                "intensity": intensity
            }
        except Exception as e:
            logger.error(f"滤镜应用失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def adjust_colors(self, image_path: str,
                          brightness: float = 1.0,
                          contrast: float = 1.0,
                          saturation: float = 1.0,
                          hue: float = 0.0) -> Dict[str, Any]:
        """调整图像颜色"""
        try:
            if not PILLOW_AVAILABLE:
                return {"success": False, "error": "PIL库不可用"}
            
            if not os.path.exists(image_path):
                return {"success": False, "error": "图像文件不存在"}
            
            image = Image.open(image_path)
            
            # 调整亮度
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(brightness)
            
            # 调整对比度
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(contrast)
            
            # 调整饱和度
            if saturation != 1.0:
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(saturation)
            
            # 调整色调（需要转换为HSV）
            if hue != 0.0:
                image = image.convert('HSV')
                pixels = image.load()
                for i in range(image.width):
                    for j in range(image.height):
                        h, s, v = pixels[i, j]
                        h = (h + int(hue * 255)) % 255
                        pixels[i, j] = (h, s, v)
                image = image.convert('RGB')
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(temp_file.name)
            
            return {
                "success": True,
                "output_path": temp_file.name,
                "adjustments": {
                    "brightness": brightness,
                    "contrast": contrast,
                    "saturation": saturation,
                    "hue": hue
                }
            }
        except Exception as e:
            logger.error(f"颜色调整失败: {e}")
            return {"success": False, "error": str(e)}

class MusicGenerator:
    """音乐生成器"""
    
    def __init__(self):
        self.music_models = {}
        self.initialize_models()
    
    def initialize_models(self):
        """初始化音乐生成模型"""
        try:
            # 这里可以集成MusicGen或其他音乐生成模型
            # 简化实现，实际使用时需要集成具体模型
            logger.info("音乐生成器初始化完成")
        except Exception as e:
            logger.error(f"音乐生成器初始化失败: {e}")
    
    async def generate_music(self, prompt: str,
                           duration: float = 10.0,
                           temperature: float = 1.0) -> Dict[str, Any]:
        """根据提示生成音乐"""
        try:
            # 简化实现，实际使用时需要集成音乐生成模型
            # 这里返回一个占位符结果
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            
            # 创建简单的音频文件（静音）
            import wave
            import struct
            
            sample_rate = 44100
            num_frames = int(duration * sample_rate)
            
            with wave.open(temp_file.name, 'w') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                
                # 生成简单的正弦波（作为示例）
                for i in range(num_frames):
                    frequency = 440  # A4音符
                    value = int(32767.0 * 0.5 * 
                              math.sin(2.0 * math.pi * frequency * i / sample_rate))
                    data = struct.pack('<h', value)
                    wav_file.writeframes(data)
            
            return {
                "success": True,
                "audio_path": temp_file.name,
                "prompt": prompt,
                "duration": duration,
                "note": "使用基础音乐生成（AI模型不可用）"
            }
        except Exception as e:
            logger.error(f"音乐生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def compose_melody(self, style: str = "classical",
                           tempo: int = 120,
                           length: int = 16) -> Dict[str, Any]:
        """创作旋律"""
        try:
            # 简化实现，返回基础旋律数据
            melody_data = {
                "notes": ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"],
                "durations": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0],
                "style": style,
                "tempo": tempo
            }
            
            return {
                "success": True,
                "melody": melody_data,
                "length": length,
                "style": style
            }
        except Exception as e:
            logger.error(f"旋律创作失败: {e}")
            return {"success": False, "error": str(e)}

class VideoEditor:
    """视频编辑器"""
    
    def __init__(self):
        pass
    
    async def create_video_from_images(self, image_paths: List[str],
                                     output_path: str,
                                     fps: int = 24,
                                     duration_per_image: float = 3.0) -> Dict[str, Any]:
        """从图像序列创建视频"""
        try:
            if not OPENCV_AVAILABLE:
                return {"success": False, "error": "OpenCV不可用"}
            
            if not image_paths:
                return {"success": False, "error": "没有提供图像文件"}
            
            # 读取第一张图像获取尺寸
            first_image = cv2.imread(image_paths[0])
            if first_image is None:
                return {"success": False, "error": f"无法读取图像: {image_paths[0]}"}
            
            height, width, layers = first_image.shape
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 为每张图像写入足够的帧数
            frames_per_image = int(fps * duration_per_image)
            
            for image_path in image_paths:
                image = cv2.imread(image_path)
                if image is None:
                    logger.warning(f"跳过无法读取的图像: {image_path}")
                    continue
                
                # 调整图像尺寸以匹配第一张图像
                if image.shape != first_image.shape:
                    image = cv2.resize(image, (width, height))
                
                for _ in range(frames_per_image):
                    video_writer.write(image)
            
            video_writer.release()
            
            return {
                "success": True,
                "output_path": output_path,
                "num_images": len(image_paths),
                "fps": fps,
                "duration_per_image": duration_per_image,
                "total_duration": len(image_paths) * duration_per_image
            }
        except Exception as e:
            logger.error(f"视频创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def extract_frames(self, video_path: str,
                           output_dir: str,
                           frame_interval: int = 10) -> Dict[str, Any]:
        """从视频中提取帧"""
        try:
            if not OPENCV_AVAILABLE:
                return {"success": False, "error": "OpenCV不可用"}
            
            if not os.path.exists(video_path):
                return {"success": False, "error": "视频文件不存在"}
            
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            extracted_frames = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    frame_path = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
                    cv2.imwrite(frame_path, frame)
                    extracted_frames.append(frame_path)
                
                frame_count += 1
            
            cap.release()
            
            return {
                "success": True,
                "extracted_frames": extracted_frames,
                "total_frames": frame_count,
                "output_dir": output_dir
            }
        except Exception as e:
            logger.error(f"帧提取失败: {e}")
            return {"success": False, "error": str(e)}

class CreativeToolsManager:
    """创意工具管理器"""
    
    def __init__(self):
        self.image_generator = ImageGenerator()
        self.image_editor = ImageEditor()
        self.music_generator = MusicGenerator()
        self.video_editor = VideoEditor()
    
    async def create_art_project(self, project_name: str,
                               project_type: str = "digital_art") -> Dict[str, Any]:
        """创建艺术项目"""
        try:
            project_dir = tempfile.mkdtemp(prefix=f"art_project_{project_name}_")
            
            # 创建项目结构
            subdirs = ["images", "audio", "videos", "assets"]
            for subdir in subdirs:
                os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)
            
            # 创建项目配置文件
            project_config = {
                "project_name": project_name,
                "project_type": project_type,
                "created_date": datetime.now().isoformat(),
                "directories": subdirs
            }
            
            config_path = os.path.join(project_dir, "project_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "project_dir": project_dir,
                "project_name": project_name,
                "config_path": config_path
            }
        except Exception as e:
            logger.error(f"艺术项目创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_process_creative_assets(self, 
                                          input_dir: str,
                                          operation: str,
                                          **kwargs) -> Dict[str, Any]:
        """批量处理创意资源"""
        try:
            if not os.path.exists(input_dir):
                return {"success": False, "error": "输入目录不存在"}
            
            results = []
            supported_extensions = {
                'images': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
                'audio': ['.mp3', '.wav', '.flac', '.aac'],
                'videos': ['.mp4', '.avi', '.mov', '.mkv']
            }
            
            for filename in os.listdir(input_dir):
                file_path = os.path.join(input_dir, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                result = {"filename": filename, "success": False}
                
                try:
                    if operation == "resize_images" and file_ext in supported_extensions['images']:
                        # 调整图像尺寸
                        resize_result = await self.image_editor.resize_image(
                            file_path,
                            kwargs.get('width', 800),
                            kwargs.get('height', 600),
                            kwargs.get('maintain_aspect', True)
                        )
                        result.update(resize_result)
                    
                    elif operation == "apply_filter" and file_ext in supported_extensions['images']:
                        # 应用滤镜
                        filter_result = await self.image_editor.apply_filter(
                            file_path,
                            kwargs.get('filter_type', 'blur'),
                            kwargs.get('intensity', 1.0)
                        )
                        result.update(filter_result)
                    
                    else:
                        result["error"] = f"不支持的操作或文件类型: {operation}"
                
                except Exception as e:
                    result["error"] = str(e)
                
                results.append(result)
            
            return {
                "success": True,
                "operation": operation,
                "processed_files": len(results),
                "results": results
            }
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            return {"success": False, "error": str(e)}

