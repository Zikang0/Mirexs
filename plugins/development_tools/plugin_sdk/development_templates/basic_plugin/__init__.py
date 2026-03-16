"""
基础插件模板

提供创建基础插件的标准模板，包括：
- 插件结构
- 清单模板
- 示例代码

Author: AI Assistant
Date: 2025-11-05
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class BasicPluginStructure:
    """基础插件结构"""
    plugin_id: str
    plugin_name: str
    version: str
    description: str
    author: str


class BasicPluginTemplate(ABC):
    """基础插件模板抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化插件"""
        self.config = config
        self.logger = None
        
    @abstractmethod
    def activate(self) -> bool:
        """激活插件"""
        pass
    
    @abstractmethod
    def deactivate(self) -> bool:
        """停用插件"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        pass


# 清单模板
MANIFEST_TEMPLATE = """{
    "id": "{plugin_id}",
    "name": "{plugin_name}",
    "version": "{version}",
    "description": "{description}",
    "author": "{author}",
    "main": "main.py",
    "permissions": [],
    "dependencies": [],
    "config": {{
        "enabled": true,
        "auto_start": false
    }}
}"""

# 示例代码模板
EXAMPLE_CODE_TEMPLATE = '''"""
{plugin_name} 插件示例代码

这是一个基础插件的实现示例。
"""

from .basic_plugin_template import BasicPluginTemplate


class {class_name}(BasicPluginTemplate):
    """{plugin_description}"""
    
    def __init__(self, config):
        super().__init__(config)
        self.logger.info("插件初始化完成")
    
    def activate(self):
        """激活插件"""
        try:
            self.logger.info("正在激活插件...")
            # 插件激活逻辑
            return True
        except Exception as e:
            self.logger.error(f"插件激活失败: {{e}}")
            return False
    
    def deactivate(self):
        """停用插件"""
        try:
            self.logger.info("正在停用插件...")
            # 插件停用逻辑
            return True
        except Exception as e:
            self.logger.error(f"插件停用失败: {{e}}")
            return False
    
    def get_info(self):
        """获取插件信息"""
        return {{
            "id": "{plugin_id}",
            "name": "{plugin_name}",
            "version": "{version}",
            "description": "{description}",
            "author": "{author}",
            "status": "active"
        }}


# 插件工厂函数
def create_plugin(config):
    """创建插件实例"""
    return {class_name}(config)


if __name__ == "__main__":
    # 测试代码
    config = {{"enabled": True}}
    plugin = create_plugin(config)
    
    if plugin.activate():
        print("插件激活成功")
        print(plugin.get_info())
        plugin.deactivate()
        print("插件停用成功")
'''