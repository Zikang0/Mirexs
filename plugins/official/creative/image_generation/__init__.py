"""
图像生成插件模块

提供AI驱动的图像生成功能，包括：
- 文本到图像生成
- 图像编辑和增强
- 风格转换
- 批量图像处理
"""

from .image_generator import ImageGeneratorPlugin
from .style_transfer import StyleTransferPlugin
from .batch_processor import BatchImageProcessor
from .image_editor import ImageEditorPlugin

__all__ = [
    'ImageGeneratorPlugin',
    'StyleTransferPlugin', 
    'BatchImageProcessor',
    'ImageEditorPlugin'
]

__version__ = '1.0.0'
__author__ = 'AI Plugin Team'