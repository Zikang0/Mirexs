"""
资源管道：资源处理流水线
负责3D资源的导入、处理、优化和导出
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class AssetType(Enum):
    """资源类型"""
    MODEL = "model"              # 3D模型
    TEXTURE = "texture"          # 纹理
    MATERIAL = "material"        # 材质
    ANIMATION = "animation"      # 动画
    SOUND = "sound"              # 声音
    SCRIPT = "script"            # 脚本

class AssetFormat(Enum):
    """资源格式"""
    GLTF = "gltf"               # GLTF格式
    GLB = "glb"                 # GLB格式
    OBJ = "obj"                 # OBJ格式
    FBX = "fbx"                 # FBX格式
    PNG = "png"                 # PNG纹理
    JPG = "jpg"                 # JPG纹理
    JSON = "json"               # JSON数据
    WAV = "wav"                 # WAV音频
    MP3 = "mp3"                 # MP3音频

@dataclass
class AssetImportConfig:
    """资源导入配置"""
    source_format: AssetFormat
    target_format: AssetFormat
    scale_factor: float = 1.0
    generate_tangents: bool = True
    generate_normals: bool = True
    optimize_mesh: bool = True
    compress_textures: bool = True
    max_texture_size: int = 2048

@dataclass
class AssetProcessingStep:
    """资源处理步骤"""
    step_id: str
    processor: str
    parameters: Dict[str, Any]
    enabled: bool = True

@dataclass
class AssetPipelineResult:
    """资源管道处理结果"""
    success: bool
    processed_files: List[str]
    output_path: str
    processing_time: float
    error_message: str = ""

class AssetPipeline:
    """资源处理管道"""
    
    def __init__(self, base_asset_path: str = "./assets/"):
        self.base_asset_path = Path(base_asset_path)
        self.import_configs: Dict[AssetType, AssetImportConfig] = {}
        self.processing_pipelines: Dict[AssetType, List[AssetProcessingStep]] = {}
        self.external_tools: Dict[str, str] = {}
        
        # 输出目录结构
        self.output_directories = {
            AssetType.MODEL: "models/",
            AssetType.TEXTURE: "textures/",
            AssetType.MATERIAL: "materials/",
            AssetType.ANIMATION: "animations/",
            AssetType.SOUND: "sounds/",
            AssetType.SCRIPT: "scripts/"
        }
        
        # 性能统计
        self.stats = {
            "assets_processed": 0,
            "processing_time": 0.0,
            "successful_processes": 0,
            "failed_processes": 0,
            "total_file_size": 0
        }
        
        # 创建目录结构
        self._create_directory_structure()
        
        # 加载默认配置
        self._load_default_configs()
        
        # 检测外部工具
        self._detect_external_tools()
        
        logger.info("资源管道初始化完成")
    
    def _create_directory_structure(self):
        """创建目录结构"""
        directories = [
            self.base_asset_path / "source",
            self.base_asset_path / "processed",
            self.base_asset_path / "temp"
        ]
        
        # 创建输出目录
        for asset_type, directory in self.output_directories.items():
            directories.append(self.base_asset_path / "processed" / directory)
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_default_configs(self):
        """加载默认配置"""
        # 模型导入配置
        model_import_config = AssetImportConfig(
            source_format=AssetFormat.FBX,
            target_format=AssetFormat.GLTF,
            scale_factor=1.0,
            generate_tangents=True,
            generate_normals=True,
            optimize_mesh=True,
            compress_textures=True,
            max_texture_size=2048
        )
        self.import_configs[AssetType.MODEL] = model_import_config
        
        # 纹理导入配置
        texture_import_config = AssetImportConfig(
            source_format=AssetFormat.PNG,
            target_format=AssetFormat.PNG,
            compress_textures=True,
            max_texture_size=2048
        )
        self.import_configs[AssetType.TEXTURE] = texture_import_config
        
        # 创建默认处理管道
        self._create_default_pipelines()
    
    def _create_default_pipelines(self):
        """创建默认处理管道"""
        # 模型处理管道
        model_pipeline = [
            AssetProcessingStep(
                step_id="validate_model",
                processor="model_validator",
                parameters={"check_manifold": True, "check_uvs": True}
            ),
            AssetProcessingStep(
                step_id="optimize_mesh",
                processor="mesh_optimizer", 
                parameters={"reduce_lods": True, "target_triangle_count": 10000}
            ),
            AssetProcessingStep(
                step_id="generate_tangents",
                processor="tangent_generator",
                parameters={"smooth_angle": 30.0}
            ),
            AssetProcessingStep(
                step_id="compress_textures",
                processor="texture_compressor",
                parameters={"format": "astc", "quality": "high"}
            )
        ]
        self.processing_pipelines[AssetType.MODEL] = model_pipeline
        
        # 纹理处理管道
        texture_pipeline = [
            AssetProcessingStep(
                step_id="validate_texture",
                processor="texture_validator",
                parameters={"check_dimensions": True, "check_format": True}
            ),
            AssetProcessingStep(
                step_id="resize_texture",
                processor="texture_resizer",
                parameters={"max_size": 2048, "maintain_aspect": True}
            ),
            AssetProcessingStep(
                step_id="generate_mipmaps",
                processor="mipmap_generator",
                parameters={"levels": 6, "filter": "lanczos"}
            ),
            AssetProcessingStep(
                step_id="compress_texture",
                processor="texture_compressor", 
                parameters={"format": "astc", "quality": "medium"}
            )
        ]
        self.processing_pipelines[AssetType.TEXTURE] = texture_pipeline
    
    def _detect_external_tools(self):
        """检测外部工具"""
        tools_to_detect = {
            "blender": "blender",
            "imagemagick": "convert",
            "ffmpeg": "ffmpeg",
            "assimp": "assimp"
        }
        
        for tool_name, command in tools_to_detect.items():
            try:
                result = subprocess.run([command, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.external_tools[tool_name] = command
                    logger.info(f"检测到外部工具: {tool_name}")
                else:
                    logger.warning(f"外部工具不可用: {tool_name}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning(f"外部工具未找到: {tool_name}")
    
    def import_asset(self, source_file: str, asset_type: AssetType, 
                    output_name: str = None) -> AssetPipelineResult:
        """导入资源"""
        import time
        start_time = time.time()
        
        try:
            source_path = Path(source_file)
            if not source_path.exists():
                return AssetPipelineResult(
                    success=False,
                    processed_files=[],
                    output_path="",
                    processing_time=0.0,
                    error_message=f"源文件不存在: {source_file}"
                )
            
            # 确定输出名称
            if not output_name:
                output_name = source_path.stem
            
            # 复制到源目录
            source_dir = self.base_asset_path / "source" / asset_type.value
            source_dir.mkdir(parents=True, exist_ok=True)
            
            source_copy_path = source_dir / source_path.name
            shutil.copy2(source_path, source_copy_path)
            
            # 处理资源
            result = self._process_asset(str(source_copy_path), asset_type, output_name)
            result.processing_time = time.time() - start_time
            
            # 更新统计
            self.stats["assets_processed"] += 1
            if result.success:
                self.stats["successful_processes"] += 1
                self.stats["processing_time"] += result.processing_time
                
                # 计算文件大小
                for file_path in result.processed_files:
                    if os.path.exists(file_path):
                        self.stats["total_file_size"] += os.path.getsize(file_path)
            else:
                self.stats["failed_processes"] += 1
            
            return result
            
        except Exception as e:
            error_msg = f"导入资源失败: {str(e)}"
            logger.error(error_msg)
            
            self.stats["assets_processed"] += 1
            self.stats["failed_processes"] += 1
            
            return AssetPipelineResult(
                success=False,
                processed_files=[],
                output_path="",
                processing_time=time.time() - start_time,
                error_message=error_msg
            )
    
    def _process_asset(self, source_file: str, asset_type: AssetType, output_name: str) -> AssetPipelineResult:
        """处理资源"""
        processed_files = []
        
        try:
            # 获取导入配置和处理管道
            import_config = self.import_configs.get(asset_type)
            pipeline = self.processing_pipelines.get(asset_type, [])
            
            if not import_config:
                return AssetPipelineResult(
                    success=False,
                    processed_files=[],
                    output_path="",
                    processing_time=0.0,
                    error_message=f"未找到资源类型的导入配置: {asset_type}"
                )
            
            # 临时工作目录
            temp_dir = self.base_asset_path / "temp" / output_name
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 输出目录
            output_dir = self.base_asset_path / "processed" / self.output_directories[asset_type]
            output_dir.mkdir(parents=True, exist_ok=True)
            
            current_file = source_file
            
            # 执行处理管道中的每个步骤
            for step in pipeline:
                if not step.enabled:
                    continue
                
                logger.info(f"执行处理步骤: {step.step_id}")
                
                # 调用相应的处理器
                processor_method = getattr(self, f"_process_{step.processor}", None)
                if processor_method:
                    step_result = processor_method(current_file, temp_dir, step.parameters)
                    if step_result.success:
                        current_file = step_result.output_file
                        processed_files.extend(step_result.additional_files)
                    else:
                        return AssetPipelineResult(
                            success=False,
                            processed_files=processed_files,
                            output_path="",
                            processing_time=0.0,
                            error_message=f"处理步骤失败 {step.step_id}: {step_result.error_message}"
                        )
                else:
                    logger.warning(f"未知的处理器: {step.processor}")
            
            # 转换到目标格式
            final_output_path = output_dir / f"{output_name}.{import_config.target_format.value}"
            conversion_result = self._convert_format(current_file, str(final_output_path), 
                                                   import_config.source_format, 
                                                   import_config.target_format)
            
            if conversion_result.success:
                processed_files.append(str(final_output_path))
                
                return AssetPipelineResult(
                    success=True,
                    processed_files=processed_files,
                    output_path=str(final_output_path),
                    processing_time=0.0
                )
            else:
                return AssetPipelineResult(
                    success=False,
                    processed_files=processed_files,
                    output_path="",
                    processing_time=0.0,
                    error_message=f"格式转换失败: {conversion_result.error_message}"
                )
            
        except Exception as e:
            return AssetPipelineResult(
                success=False,
                processed_files=processed_files,
                output_path="",
                processing_time=0.0,
                error_message=f"处理资源失败: {str(e)}"
            )
    
    def _process_model_validator(self, input_file: str, temp_dir: Path, parameters: Dict[str, Any]) -> Any:
        """模型验证处理器"""
        try:
            # 简化的模型验证
            # 实际应该检查网格完整性、UV坐标等
            
            file_extension = Path(input_file).suffix.lower()
            supported_formats = ['.fbx', '.obj', '.gltf', '.glb']
            
            if file_extension not in supported_formats:
                return type('StepResult', (), {
                    'success': False,
                    'output_file': input_file,
                    'additional_files': [],
                    'error_message': f"不支持的模型格式: {file_extension}"
                })()
            
            # 检查文件大小
            file_size = os.path.getsize(input_file)
            if file_size > 100 * 1024 * 1024:  # 100MB限制
                return type('StepResult', (), {
                    'success': False,
                    'output_file': input_file,
                    'additional_files': [],
                    'error_message': "模型文件过大"
                })()
            
            logger.info(f"模型验证通过: {input_file}")
            return type('StepResult', (), {
                'success': True,
                'output_file': input_file,
                'additional_files': [],
                'error_message': ""
            })()
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'output_file': input_file,
                'additional_files': [],
                'error_message': f"模型验证失败: {str(e)}"
            })()
    
    def _process_mesh_optimizer(self, input_file: str, temp_dir: Path, parameters: Dict[str, Any]) -> Any:
        """网格优化处理器"""
        try:
            # 使用Blender进行网格优化（如果可用）
            if "blender" in self.external_tools:
                output_file = temp_dir / "optimized_model.gltf"
                
                # 构建Blender命令
                blender_script = """
import bpy
import os

# 清除场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入模型
bpy.ops.import_scene.fbx(filepath="INPUT_FILE")

# 优化网格
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add(type='DECIMATE')
        obj.modifiers["Decimate"].ratio = 0.5

# 导出优化后的模型
bpy.ops.export_scene.gltf(filepath="OUTPUT_FILE", export_format='GLTF_EMBEDDED')
                """
                
                # 替换路径
                blender_script = blender_script.replace("INPUT_FILE", input_file.replace("\\", "\\\\"))
                blender_script = blender_script.replace("OUTPUT_FILE", str(output_file).replace("\\", "\\\\"))
                
                # 保存脚本
                script_file = temp_dir / "optimize_script.py"
                with open(script_file, 'w') as f:
                    f.write(blender_script)
                
                # 执行Blender
                cmd = [
                    self.external_tools["blender"],
                    "--background",
                    "--python", str(script_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and output_file.exists():
                    logger.info(f"网格优化完成: {input_file}")
                    return type('StepResult', (), {
                        'success': True,
                        'output_file': str(output_file),
                        'additional_files': [],
                        'error_message': ""
                    })()
            
            # 如果Blender不可用，直接返回原文件
            logger.warning("Blender不可用，跳过网格优化")
            return type('StepResult', (), {
                'success': True,
                'output_file': input_file,
                'additional_files': [],
                'error_message': ""
            })
            
        except Exception as e:
            logger.error(f"网格优化失败: {str(e)}")
            return type('StepResult', (), {
                'success': False,
                'output_file': input_file,
                'additional_files': [],
                'error_message': f"网格优化失败: {str(e)}"
            })()
    
    def _process_texture_validator(self, input_file: str, temp_dir: Path, parameters: Dict[str, Any]) -> Any:
        """纹理验证处理器"""
        try:
            from PIL import Image
            
            # 打开并验证纹理
            with Image.open(input_file) as img:
                # 检查尺寸
                width, height = img.size
                max_size = parameters.get("max_texture_size", 4096)
                
                if width > max_size or height > max_size:
                    return type('StepResult', (), {
                        'success': False,
                        'output_file': input_file,
                        'additional_files': [],
                        'error_message': f"纹理尺寸过大: {width}x{height}"
                    })()
                
                # 检查格式
                valid_formats = ['PNG', 'JPEG', 'BMP', 'TGA']
                if img.format not in valid_formats:
                    return type('StepResult', (), {
                        'success': False,
                        'output_file': input_file,
                        'additional_files': [],
                        'error_message': f"不支持的纹理格式: {img.format}"
                    })()
            
            logger.info(f"纹理验证通过: {input_file}")
            return type('StepResult', (), {
                'success': True,
                'output_file': input_file,
                'additional_files': [],
                'error_message': ""
            })
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'output_file': input_file,
                'additional_files': [],
                'error_message': f"纹理验证失败: {str(e)}"
            })()
    
    def _process_texture_resizer(self, input_file: str, temp_dir: Path, parameters: Dict[str, Any]) -> Any:
        """纹理缩放处理器"""
        try:
            from PIL import Image
            
            max_size = parameters.get("max_size", 2048)
            maintain_aspect = parameters.get("maintain_aspect", True)
            
            with Image.open(input_file) as img:
                width, height = img.size
                
                # 计算新尺寸
                if width <= max_size and height <= max_size:
                    # 不需要缩放
                    return type('StepResult', (), {
                        'success': True,
                        'output_file': input_file,
                        'additional_files': [],
                        'error_message': ""
                    })
                
                if maintain_aspect:
                    if width > height:
                        new_width = max_size
                        new_height = int(height * max_size / width)
                    else:
                        new_height = max_size
                        new_width = int(width * max_size / height)
                else:
                    new_width = max_size
                    new_height = max_size
                
                # 缩放图像
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # 保存缩放后的图像
                output_file = temp_dir / "resized_texture.png"
                resized_img.save(output_file, "PNG")
                
                logger.info(f"纹理缩放完成: {width}x{height} -> {new_width}x{new_height}")
                return type('StepResult', (), {
                    'success': True,
                    'output_file': str(output_file),
                    'additional_files': [],
                    'error_message': ""
                })
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'output_file': input_file,
                'additional_files': [],
                'error_message': f"纹理缩放失败: {str(e)}"
            })()
    
    def _convert_format(self, input_file: str, output_file: str, 
                       source_format: AssetFormat, target_format: AssetFormat) -> Any:
        """转换资源格式"""
        try:
            if source_format == target_format:
                # 格式相同，直接复制
                shutil.copy2(input_file, output_file)
                return type('StepResult', (), {
                    'success': True,
                    'error_message': ""
                })()
            
            # 模型格式转换
            if source_format in [AssetFormat.FBX, AssetFormat.OBJ] and target_format in [AssetFormat.GLTF, AssetFormat.GLB]:
                return self._convert_model_format(input_file, output_file, source_format, target_format)
            
            # 纹理格式转换
            if source_format in [AssetFormat.JPG, AssetFormat.PNG] and target_format in [AssetFormat.PNG, AssetFormat.JPG]:
                return self._convert_texture_format(input_file, output_file, source_format, target_format)
            
            # 不支持的类型转换
            return type('StepResult', (), {
                'success': False,
                'error_message': f"不支持的类型转换: {source_format.value} -> {target_format.value}"
            })
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'error_message': f"格式转换失败: {str(e)}"
            })()
    
    def _convert_model_format(self, input_file: str, output_file: str,
                            source_format: AssetFormat, target_format: AssetFormat) -> Any:
        """转换模型格式"""
        try:
            # 使用Blender进行格式转换
            if "blender" in self.external_tools:
                # 构建Blender命令
                blender_script = f"""
import bpy
import os

# 清除场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入模型
bpy.ops.import_scene.{source_format.value}(filepath="{input_file.replace('\\', '\\\\')}")

# 导出为目标格式
export_format = 'GLTF_EMBEDDED' if "{target_format.value}" == "glb" else 'GLTF_SEPARATE'
bpy.ops.export_scene.gltf(filepath="{output_file.replace('\\', '\\\\')}", export_format=export_format)
                """
                
                # 保存脚本
                script_file = self.base_asset_path / "temp" / "convert_script.py"
                script_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(script_file, 'w') as f:
                    f.write(blender_script)
                
                # 执行Blender
                cmd = [
                    self.external_tools["blender"],
                    "--background",
                    "--python", str(script_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0 and os.path.exists(output_file):
                    logger.info(f"模型格式转换完成: {source_format.value} -> {target_format.value}")
                    return type('StepResult', (), {
                        'success': True,
                        'error_message': ""
                    })()
            
            return type('StepResult', (), {
                'success': False,
                'error_message': "模型格式转换失败"
            })
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'error_message': f"模型格式转换失败: {str(e)}"
            })()
    
    def _convert_texture_format(self, input_file: str, output_file: str,
                              source_format: AssetFormat, target_format: AssetFormat) -> Any:
        """转换纹理格式"""
        try:
            from PIL import Image
            
            with Image.open(input_file) as img:
                if target_format == AssetFormat.PNG:
                    img.save(output_file, "PNG")
                elif target_format == AssetFormat.JPG:
                    # 转换为RGB模式（JPG不支持透明度）
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    img.save(output_file, "JPEG", quality=85)
            
            logger.info(f"纹理格式转换完成: {source_format.value} -> {target_format.value}")
            return type('StepResult', (), {
                'success': True,
                'error_message': ""
            })
            
        except Exception as e:
            return type('StepResult', (), {
                'success': False,
                'error_message': f"纹理格式转换失败: {str(e)}"
            })()
    
    def add_processing_step(self, asset_type: AssetType, step: AssetProcessingStep):
        """添加处理步骤"""
        if asset_type not in self.processing_pipelines:
            self.processing_pipelines[asset_type] = []
        
        self.processing_pipelines[asset_type].append(step)
        logger.info(f"添加处理步骤: {asset_type.value} -> {step.step_id}")
    
    def remove_processing_step(self, asset_type: AssetType, step_id: str) -> bool:
        """移除处理步骤"""
        if asset_type not in self.processing_pipelines:
            return False
        
        for i, step in enumerate(self.processing_pipelines[asset_type]):
            if step.step_id == step_id:
                del self.processing_pipelines[asset_type][i]
                logger.info(f"移除处理步骤: {asset_type.value} -> {step_id}")
                return True
        
        return False
    
    def set_import_config(self, asset_type: AssetType, config: AssetImportConfig):
        """设置导入配置"""
        self.import_configs[asset_type] = config
        logger.info(f"设置导入配置: {asset_type.value}")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        stats = self.stats.copy()
        stats["import_configs"] = len(self.import_configs)
        stats["processing_pipelines"] = len(self.processing_pipelines)
        stats["external_tools"] = len(self.external_tools)
        
        # 计算成功率
        if stats["assets_processed"] > 0:
            stats["success_rate"] = stats["successful_processes"] / stats["assets_processed"]
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def batch_process_assets(self, asset_directory: str, asset_type: AssetType) -> List[AssetPipelineResult]:
        """批量处理资源"""
        results = []
        asset_dir = Path(asset_directory)
        
        if not asset_dir.exists():
            logger.error(f"资源目录不存在: {asset_directory}")
            return results
        
        # 获取支持的文件扩展名
        supported_extensions = self._get_supported_extensions(asset_type)
        
        # 处理目录中的所有文件
        for file_path in asset_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                logger.info(f"批量处理资源: {file_path.name}")
                result = self.import_asset(str(file_path), asset_type)
                results.append(result)
        
        logger.info(f"批量处理完成: 处理了 {len(results)} 个资源")
        return results
    
    def _get_supported_extensions(self, asset_type: AssetType) -> List[str]:
        """获取支持的文件扩展名"""
        extension_map = {
            AssetType.MODEL: ['.fbx', '.obj', '.gltf', '.glb', '.dae', '.3ds'],
            AssetType.TEXTURE: ['.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tiff'],
            AssetType.ANIMATION: ['.json', '.anim', '.fbx'],
            AssetType.SOUND: ['.wav', '.mp3', '.ogg', '.flac'],
            AssetType.SCRIPT: ['.py', '.lua', '.js']
        }
        
        return extension_map.get(asset_type, [])
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        temp_dir = self.base_asset_path / "temp"
        
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("清理临时文件完成")
    
    def get_asset_info(self, asset_path: str) -> Dict[str, Any]:
        """获取资源信息"""
        try:
            asset_info = {
                "path": asset_path,
                "exists": False,
                "file_size": 0,
                "file_type": "unknown",
                "metadata": {}
            }
            
            if not os.path.exists(asset_path):
                return asset_info
            
            asset_info["exists"] = True
            asset_info["file_size"] = os.path.getsize(asset_path)
            asset_info["file_type"] = Path(asset_path).suffix.lower()
            
            # 根据文件类型提取元数据
            if asset_info["file_type"] in ['.png', '.jpg', '.jpeg']:
                from PIL import Image
                with Image.open(asset_path) as img:
                    asset_info["metadata"] = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode
                    }
            
            elif asset_info["file_type"] in ['.gltf', '.json']:
                with open(asset_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if "meshes" in data:
                            asset_info["metadata"]["mesh_count"] = len(data["meshes"])
                        if "materials" in data:
                            asset_info["metadata"]["material_count"] = len(data["materials"])
                    except:
                        pass
            
            return asset_info
            
        except Exception as e:
            logger.error(f"获取资源信息失败: {str(e)}")
            return {"path": asset_path, "exists": False, "error": str(e)}
    
    def cleanup(self):
        """清理资源管道"""
        self.cleanup_temp_files()
        self.import_configs.clear()
        self.processing_pipelines.clear()
        
        logger.info("资源管道清理完成")

# 全局资源管道实例
asset_pipeline = AssetPipeline()

