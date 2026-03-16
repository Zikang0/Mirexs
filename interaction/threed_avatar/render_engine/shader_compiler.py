"""
着色器编译器
负责GLSL着色器的编译、链接和优化
"""

import logging
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ShaderType(Enum):
    """着色器类型"""
    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"

@dataclass
class ShaderSource:
    """着色器源代码"""
    source_code: str
    shader_type: ShaderType
    file_path: str
    compile_status: bool = False
    compile_log: str = ""

@dataclass
class ShaderProgram:
    """着色器程序"""
    name: str
    vertex_shader: ShaderSource
    fragment_shader: ShaderSource
    geometry_shader: Optional[ShaderSource] = None
    program_id: Optional[int] = None
    link_status: bool = False
    link_log: str = ""
    uniforms: Dict[str, Any] = None
    attributes: Dict[str, Any] = None

class ShaderCompiler:
    """着色器编译器"""
    
    def __init__(self, shader_directory: str = "shaders"):
        self.shader_directory = shader_directory
        self.shader_programs: Dict[str, ShaderProgram] = {}
        self.shader_cache: Dict[str, ShaderSource] = {}
        self.include_paths: List[str] = [shader_directory, "shaders/include"]
        
        # 预定义着色器模板
        self.shader_templates = self._load_shader_templates()
        
        logger.info("Shader compiler initialized")
    
    def _load_shader_templates(self) -> Dict[str, str]:
        """加载着色器模板"""
        templates = {
            "pbr_vertex": """
#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;
layout(location = 3) in vec3 aTangent;
layout(location = 4) in vec3 aBitangent;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vTexCoord;
out mat3 vTBN;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    vec4 worldPos = uModel * vec4(aPosition, 1.0);
    vWorldPos = worldPos.xyz;
    
    mat3 normalMatrix = transpose(inverse(mat3(uModel)));
    vNormal = normalize(normalMatrix * aNormal);
    
    vTexCoord = aTexCoord;
    
    // 计算TBN矩阵
    vec3 T = normalize(normalMatrix * aTangent);
    vec3 B = normalize(normalMatrix * aBitangent);
    vec3 N = normalize(normalMatrix * aNormal);
    vTBN = mat3(T, B, N);
    
    gl_Position = uProjection * uView * worldPos;
}
""",
            "pbr_fragment": """
#version 330 core
in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vTexCoord;
in mat3 vTBN;

out vec4 FragColor;

// 材质属性
struct Material {
    sampler2D albedoMap;
    sampler2D normalMap;
    sampler2D metallicMap;
    sampler2D roughnessMap;
    sampler2D aoMap;
    
    vec3 albedo;
    float metallic;
    float roughness;
    float ao;
};

// 光照计算
vec3 calculatePBRLighting(Material material, vec3 worldPos, vec3 normal, vec3 viewDir);

uniform Material uMaterial;
uniform vec3 uCameraPos;

// 光源
uniform vec3 uLightPositions[4];
uniform vec3 uLightColors[4];

void main() {
    // 视图方向
    vec3 viewDir = normalize(uCameraPos - vWorldPos);
    
    // 从法线贴图获取法线
    vec3 normal = texture(uMaterial.normalMap, vTexCoord).rgb;
    normal = normalize(normal * 2.0 - 1.0);
    normal = normalize(vTBN * normal);
    
    // 计算PBR光照
    vec3 color = calculatePBRLighting(uMaterial, vWorldPos, normal, viewDir);
    
    // HDR色调映射
    color = color / (color + vec3(1.0));
    // Gamma校正
    color = pow(color, vec3(1.0/2.2));
    
    FragColor = vec4(color, 1.0);
}
""",
            "simple_vertex": """
#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

out vec3 vNormal;
out vec2 vTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    gl_Position = uProjection * uView * uModel * vec4(aPosition, 1.0);
    vNormal = mat3(transpose(inverse(uModel))) * aNormal;
    vTexCoord = aTexCoord;
}
""",
            "simple_fragment": """
#version 330 core
in vec3 vNormal;
in vec2 vTexCoord;

out vec4 FragColor;

uniform sampler2D uTexture;
uniform vec3 uLightDir;
uniform vec3 uLightColor;

void main() {
    vec3 normal = normalize(vNormal);
    float diff = max(dot(normal, uLightDir), 0.0);
    vec3 diffuse = diff * uLightColor;
    
    vec4 texColor = texture(uTexture, vTexCoord);
    FragColor = vec4(texColor.rgb * (diffuse + vec3(0.1)), texColor.a);
}
"""
        }
        return templates
    
    def load_shader_file(self, file_path: str, shader_type: ShaderType) -> Optional[ShaderSource]:
        """加载着色器文件"""
        try:
            # 在包含路径中查找文件
            full_path = None
            for include_path in self.include_paths:
                test_path = os.path.join(include_path, file_path)
                if os.path.exists(test_path):
                    full_path = test_path
                    break
            
            if full_path is None:
                logger.error(f"Shader file not found: {file_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 处理包含指令
            source_code = self._process_includes(source_code, os.path.dirname(full_path))
            
            shader_source = ShaderSource(
                source_code=source_code,
                shader_type=shader_type,
                file_path=full_path
            )
            
            self.shader_cache[file_path] = shader_source
            logger.info(f"Loaded shader: {file_path} ({shader_type.value})")
            return shader_source
            
        except Exception as e:
            logger.error(f"Failed to load shader file {file_path}: {e}")
            return None
    
    def _process_includes(self, source_code: str, base_dir: str) -> str:
        """处理#include指令"""
        include_pattern = r'#include\s+["<]([^">]+)[">]'
        
        def replace_include(match):
            include_file = match.group(1)
            
            # 在基础目录中查找包含文件
            include_path = os.path.join(base_dir, include_file)
            if not os.path.exists(include_path):
                # 在包含路径中查找
                for include_dir in self.include_paths:
                    test_path = os.path.join(include_dir, include_file)
                    if os.path.exists(test_path):
                        include_path = test_path
                        break
            
            try:
                with open(include_path, 'r', encoding='utf-8') as f:
                    include_content = f.read()
                # 递归处理嵌套包含
                return self._process_includes(include_content, os.path.dirname(include_path))
            except Exception as e:
                logger.warning(f"Failed to include shader file {include_file}: {e}")
                return f"// ERROR: Failed to include {include_file}\n"
        
        return re.sub(include_pattern, replace_include, source_code)
    
    def create_shader_program(self, name: str, 
                            vertex_shader: ShaderSource,
                            fragment_shader: ShaderSource,
                            geometry_shader: Optional[ShaderSource] = None) -> ShaderProgram:
        """创建着色器程序"""
        shader_program = ShaderProgram(
            name=name,
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
            geometry_shader=geometry_shader,
            uniforms={},
            attributes={}
        )
        
        self.shader_programs[name] = shader_program
        logger.info(f"Created shader program: {name}")
        return shader_program
    
    def compile_shader_program(self, name: str) -> bool:
        """编译着色器程序"""
        try:
            if name not in self.shader_programs:
                logger.error(f"Shader program not found: {name}")
                return False
            
            program = self.shader_programs[name]
            
            # 编译顶点着色器
            if not self._compile_shader(program.vertex_shader):
                logger.error(f"Failed to compile vertex shader for {name}")
                return False
            
            # 编译片段着色器
            if not self._compile_shader(program.fragment_shader):
                logger.error(f"Failed to compile fragment shader for {name}")
                return False
            
            # 编译几何着色器（如果存在）
            if program.geometry_shader and not self._compile_shader(program.geometry_shader):
                logger.error(f"Failed to compile geometry shader for {name}")
                return False
            
            # 链接程序
            if not self._link_program(program):
                logger.error(f"Failed to link shader program {name}")
                return False
            
            # 提取uniform和attribute信息
            self._extract_program_info(program)
            
            program.link_status = True
            logger.info(f"Compiled and linked shader program: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compile shader program {name}: {e}")
            return False
    
    def _compile_shader(self, shader_source: ShaderSource) -> bool:
        """编译单个着色器"""
        try:
            # 这里实现实际的着色器编译
            # 模拟编译过程
            shader_source.compile_status = True
            shader_source.compile_log = "Compilation successful"
            
            # 检查语法错误
            if not self._validate_shader_syntax(shader_source):
                shader_source.compile_status = False
                shader_source.compile_log = "Syntax validation failed"
                return False
            
            return True
            
        except Exception as e:
            shader_source.compile_status = False
            shader_source.compile_log = f"Compilation error: {e}"
            return False
    
    def _link_program(self, program: ShaderProgram) -> bool:
        """链接着色器程序"""
        try:
            # 这里实现实际的程序链接
            # 模拟链接过程
            program.program_id = self._generate_program_id()
            program.link_status = True
            program.link_log = "Linking successful"
            
            return True
            
        except Exception as e:
            program.link_status = False
            program.link_log = f"Linking error: {e}"
            return False
    
    def _validate_shader_syntax(self, shader_source: ShaderSource) -> bool:
        """验证着色器语法"""
        try:
            source = shader_source.source_code
            
            # 检查版本声明
            if "#version" not in source:
                logger.warning(f"Shader missing version directive: {shader_source.file_path}")
            
            # 检查基本的语法结构
            if shader_source.shader_type == ShaderType.VERTEX:
                if "main()" not in source:
                    logger.error("Vertex shader missing main function")
                    return False
            
            elif shader_source.shader_type == ShaderType.FRAGMENT:
                if "main()" not in source:
                    logger.error("Fragment shader missing main function")
                    return False
                if "FragColor" not in source and "gl_FragColor" not in source:
                    logger.warning("Fragment shader may not output color")
            
            return True
            
        except Exception as e:
            logger.error(f"Shader syntax validation failed: {e}")
            return False
    
    def _extract_program_info(self, program: ShaderProgram):
        """提取程序信息（uniforms、attributes等）"""
        try:
            # 从着色器源代码中提取uniform声明
            program.uniforms = self._extract_uniforms(program)
            program.attributes = self._extract_attributes(program)
            
        except Exception as e:
            logger.error(f"Failed to extract program info: {e}")
    
    def _extract_uniforms(self, program: ShaderProgram) -> Dict[str, Any]:
        """从着色器代码中提取uniform声明"""
        uniforms = {}
        shader_sources = [program.vertex_shader.source_code, program.fragment_shader.source_code]
        
        if program.geometry_shader:
            shader_sources.append(program.geometry_shader.source_code)
        
        uniform_pattern = r'uniform\s+(\w+)\s+(\w+)\s*;'
        
        for source in shader_sources:
            matches = re.finditer(uniform_pattern, source)
            for match in matches:
                uniform_type = match.group(1)
                uniform_name = match.group(2)
                uniforms[uniform_name] = {
                    'type': uniform_type,
                    'location': None,  # 在实际实现中会查询位置
                    'value': None
                }
        
        return uniforms
    
    def _extract_attributes(self, program: ShaderProgram) -> Dict[str, Any]:
        """从着色器代码中提取attribute声明"""
        attributes = {}
        vertex_source = program.vertex_shader.source_code
        
        attribute_pattern = r'layout\s*\(\s*location\s*=\s*(\d+)\s*\)\s*in\s+(\w+)\s+(\w+)\s*;'
        
        matches = re.finditer(attribute_pattern, vertex_source)
        for match in matches:
            location = int(match.group(1))
            attr_type = match.group(2)
            attr_name = match.group(3)
            attributes[attr_name] = {
                'type': attr_type,
                'location': location
            }
        
        return attributes
    
    def _generate_program_id(self) -> int:
        """生成程序ID（模拟实现）"""
        import random
        return random.randint(1000, 9999)
    
    def get_shader_template(self, template_name: str) -> Optional[str]:
        """获取着色器模板"""
        return self.shader_templates.get(template_name)
    
    def create_shader_from_template(self, template_name: str, replacements: Dict[str, str]) -> Optional[str]:
        """从模板创建着色器"""
        template = self.get_shader_template(template_name)
        if template is None:
            return None
        
        # 应用替换
        result = template
        for key, value in replacements.items():
            result = result.replace(f"{{{key}}}", value)
        
        return result
    
    def optimize_shader(self, shader_source: ShaderSource) -> ShaderSource:
        """优化着色器代码"""
        try:
            optimized_code = shader_source.source_code
            
            # 移除注释
            optimized_code = re.sub(r'//.*$', '', optimized_code, flags=re.MULTILINE)
            optimized_code = re.sub(r'/\*.*?\*/', '', optimized_code, flags= re.DOTALL)
            
            # 移除多余的空格和空行
            optimized_code = re.sub(r'\n\s*\n', '\n', optimized_code)
            optimized_code = re.sub(r'^\s+', '', optimized_code, flags=re.MULTILINE)
            
            # 创建优化后的着色器
            optimized_shader = ShaderSource(
                source_code=optimized_code,
                shader_type=shader_source.shader_type,
                file_path=shader_source.file_path + ".optimized"
            )
            
            logger.info(f"Optimized shader: {shader_source.file_path}")
            return optimized_shader
            
        except Exception as e:
            logger.error(f"Failed to optimize shader: {e}")
            return shader_source
    
    def validate_shader_program(self, name: str) -> Dict[str, Any]:
        """验证着色器程序"""
        if name not in self.shader_programs:
            return {"valid": False, "error": "Program not found"}
        
        program = self.shader_programs[name]
        validation_result = {
            "valid": program.link_status,
            "program_name": name,
            "vertex_shader": {
                "compiled": program.vertex_shader.compile_status,
                "log": program.vertex_shader.compile_log
            },
            "fragment_shader": {
                "compiled": program.fragment_shader.compile_status,
                "log": program.fragment_shader.compile_log
            },
            "link_status": program.link_status,
            "link_log": program.link_log,
            "uniform_count": len(program.uniforms) if program.uniforms else 0,
            "attribute_count": len(program.attributes) if program.attributes else 0
        }
        
        if program.geometry_shader:
            validation_result["geometry_shader"] = {
                "compiled": program.geometry_shader.compile_status,
                "log": program.geometry_shader.compile_log
            }
        
        return validation_result
    
    def get_program_info(self, name: str) -> Dict[str, Any]:
        """获取程序信息"""
        if name not in self.shader_programs:
            return {}
        
        program = self.shader_programs[name]
        return {
            "name": program.name,
            "program_id": program.program_id,
            "link_status": program.link_status,
            "uniforms": program.uniforms,
            "attributes": program.attributes
        }

