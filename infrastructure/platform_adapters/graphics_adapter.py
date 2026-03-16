"""
图形适配器 - 跨平台图形渲染
"""

import os
import sys
import platform
from typing import Dict, Any, List, Optional, Tuple

try:
    import OpenGL.GL as gl
    import OpenGL.GLUT as glut
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class GraphicsAdapter:
    """跨平台图形渲染适配器"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.graphics_backend = self._select_graphics_backend()
        self.initialized = False
        self.window = None
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化图形适配器"""
        self.hardware_info = hardware_info
        self.graphics_info = self._get_graphics_info()
        self.initialized = True
        
    def _select_graphics_backend(self) -> str:
        """选择图形后端"""
        if OPENGL_AVAILABLE:
            return "opengl"
        elif PYGAME_AVAILABLE:
            return "pygame"
        else:
            return "none"
    
    def _get_graphics_info(self) -> Dict[str, Any]:
        """获取图形设备信息"""
        info = {
            'backend': self.graphics_backend,
            'gpu_vendor': 'Unknown',
            'gpu_renderer': 'Unknown',
            'opengl_version': 'Unknown',
            'max_texture_size': 0,
            'extensions': []
        }
        
        try:
            if self.graphics_backend == "opengl":
                # 需要先创建OpenGL上下文
                if self._init_opengl_context():
                    info.update({
                        'gpu_vendor': gl.glGetString(gl.GL_VENDOR),
                        'gpu_renderer': gl.glGetString(gl.GL_RENDERER),
                        'opengl_version': gl.glGetString(gl.GL_VERSION),
                        'max_texture_size': gl.glGetIntegerv(gl.GL_MAX_TEXTURE_SIZE),
                        'extensions': gl.glGetString(gl.GL_EXTENSIONS).split()
                    })
                    
        except Exception as e:
            print(f"⚠️ 获取图形信息失败: {e}")
            
        return info
    
    def _init_opengl_context(self) -> bool:
        """初始化OpenGL上下文"""
        try:
            if self.platform == "windows":
                import ctypes
                # Windows下需要创建临时窗口来获取上下文
                pass
            elif self.platform == "linux":
                # Linux下使用GLX
                pass
            elif self.platform == "darwin":
                # macOS下使用CGL
                pass
                
            return True
        except:
            return False
    
    def create_window(self, title: str, width: int, height: int, 
                     fullscreen: bool = False) -> bool:
        """创建图形窗口"""
        if self.graphics_backend == "none":
            print("❌ 没有可用的图形后端")
            return False
            
        try:
            if self.graphics_backend == "opengl":
                return self._create_opengl_window(title, width, height, fullscreen)
            elif self.graphics_backend == "pygame":
                return self._create_pygame_window(title, width, height, fullscreen)
        except Exception as e:
            print(f"❌ 创建窗口失败: {e}")
            return False
    
    def _create_opengl_window(self, title: str, width: int, height: int, 
                             fullscreen: bool) -> bool:
        """使用OpenGL创建窗口"""
        try:
            glut.glutInit()
            glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGBA)
            glut.glutInitWindowSize(width, height)
            glut.glutCreateWindow(title.encode())
            
            if fullscreen:
                glut.glutFullScreen()
                
            self.window = {
                'type': 'opengl',
                'width': width,
                'height': height,
                'fullscreen': fullscreen
            }
            return True
        except Exception as e:
            print(f"❌ 创建OpenGL窗口失败: {e}")
            return False
    
    def _create_pygame_window(self, title: str, width: int, height: int,
                             fullscreen: bool) -> bool:
        """使用Pygame创建窗口"""
        try:
            flags = pygame.DOUBLEBUF | pygame.OPENGL
            if fullscreen:
                flags |= pygame.FULLSCREEN
                
            self.window = pygame.display.set_mode((width, height), flags)
            pygame.display.set_caption(title)
            
            self.window_info = {
                'type': 'pygame',
                'width': width,
                'height': height,
                'fullscreen': fullscreen
            }
            return True
        except Exception as e:
            print(f"❌ 创建Pygame窗口失败: {e}")
            return False
    
    def clear_screen(self, color: Tuple[float, float, float, float] = (0, 0, 0, 1)) -> None:
        """清屏"""
        if self.graphics_backend == "opengl":
            gl.glClearColor(*color)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        elif self.graphics_backend == "pygame":
            self.window.fill((int(color[0]*255), int(color[1]*255), 
                            int(color[2]*255), int(color[3]*255)))
    
    def swap_buffers(self) -> None:
        """交换缓冲区"""
        if self.graphics_backend == "opengl":
            glut.glutSwapBuffers()
        elif self.graphics_backend == "pygame":
            pygame.display.flip()
    
    def draw_texture(self, texture_id: int, x: float, y: float, 
                    width: float, height: float) -> None:
        """绘制纹理"""
        if self.graphics_backend == "opengl":
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(0, 0); gl.glVertex2f(x, y)
            gl.glTexCoord2f(1, 0); gl.glVertex2f(x + width, y)
            gl.glTexCoord2f(1, 1); gl.glVertex2f(x + width, y + height)
            gl.glTexCoord2f(0, 1); gl.glVertex2f(x, y + height)
            gl.glEnd()
    
    def load_texture(self, image_path: str) -> Optional[int]:
        """加载纹理"""
        if self.graphics_backend == "opengl":
            return self._load_texture_opengl(image_path)
        return None
    
    def _load_texture_opengl(self, image_path: str) -> Optional[int]:
        """使用OpenGL加载纹理"""
        try:
            from PIL import Image
            import numpy as np
            
            image = Image.open(image_path)
            image_data = np.array(image.convert("RGBA"), dtype=np.uint8)
            
            texture_id = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image.width, image.height,
                          0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
            
            return texture_id
        except Exception as e:
            print(f"❌ 加载纹理失败: {e}")
            return None
    
    def get_graphics_capabilities(self) -> Dict[str, Any]:
        """获取图形能力"""
        capabilities = {
            'opengl_available': OPENGL_AVAILABLE,
            'vulkan_available': self._check_vulkan_available(),
            'directx_available': self.platform == "windows",
            'metal_available': self.platform == "darwin",
            'shader_support': self._check_shader_support(),
            'compute_shaders': self._check_compute_shaders(),
            'texture_compression': self._check_texture_compression()
        }
        return capabilities
    
    def _check_vulkan_available(self) -> bool:
        """检查Vulkan是否可用"""
        try:
            if self.platform == "windows":
                # 检查Windows下的Vulkan支持
                vulkan_lib = "vulkan-1.dll"
            elif self.platform == "linux":
                vulkan_lib = "libvulkan.so.1"
            else:
                return False
                
            # 简单的库存在检查
            import ctypes
            try:
                ctypes.CDLL(vulkan_lib)
                return True
            except:
                return False
        except:
            return False
    
    def _check_shader_support(self) -> bool:
        """检查着色器支持"""
        if self.graphics_backend == "opengl":
            try:
                version_str = gl.glGetString(gl.GL_VERSION)
                version = float(version_str.split()[0])
                return version >= 2.0
            except:
                pass
        return False
    
    def _check_compute_shaders(self) -> bool:
        """检查计算着色器支持"""
        if self.graphics_backend == "opengl":
            try:
                # 检查OpenGL 4.3+ 或 ARB_compute_shader扩展
                version_str = gl.glGetString(gl.GL_VERSION)
                version = float(version_str.split()[0])
                if version >= 4.3:
                    return True
                    
                extensions = gl.glGetString(gl.GL_EXTENSIONS)
                if extensions and "ARB_compute_shader" in extensions:
                    return True
            except:
                pass
        return False
    
    def _check_texture_compression(self) -> bool:
        """检查纹理压缩支持"""
        if self.graphics_backend == "opengl":
            try:
                extensions = gl.glGetString(gl.GL_EXTENSIONS)
                if extensions:
                    compressed_formats = [
                        "GL_EXT_texture_compression_s3tc",
                        "GL_ARB_texture_compression",
                        "GL_EXT_texture_compression_dxt1"
                    ]
                    return any(fmt in extensions for fmt in compressed_formats)
            except:
                pass
        return False
    
    def set_vsync(self, enabled: bool) -> bool:
        """设置垂直同步"""
        if self.graphics_backend == "opengl":
            try:
                import ctypes
                if self.platform == "windows":
                    wgl = ctypes.windll.opengl32
                    wgl.wglSwapInterval(1 if enabled else 0)
                    return True
                elif self.platform == "linux":
                    glx = ctypes.CDLL("libGL.so.1")
                    glx.glXSwapIntervalSGI(1 if enabled else 0)
                    return True
            except:
                pass
        return False