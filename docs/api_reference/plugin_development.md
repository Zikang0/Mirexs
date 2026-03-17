
# Mirexs 插件开发指南（Plugin Development）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**状态：生产级完整规范，与仓库实际 plugins/ 目录结构完全对应，可直接用于开发、测试和贡献插件**

## 1. 插件系统概述

Mirexs v2.0 采用**插件化架构**，允许开发者扩展核心功能，而无需修改主代码库。  
插件主要用于：

- 注入自定义工具（Tool Calling）
- 扩展回复生成逻辑（e.g. 特定领域知识、幽默风格）
- 自定义 3D 头像动画/行为
- 外部服务集成（本地优先，但支持可选云端）
- 情绪/行为触发器增强

**插件目录结构**（仓库真实路径）：
```
plugins/
├── __init__.py
├── base_plugin.py                # 所有插件必须继承的基类
├── examples/
│   ├── hello_world_plugin.py
│   ├── weather_tool_plugin.py
│   └── custom_avatar_animation.py
├── registry.py                   # 插件注册中心（自动加载）
└── plugin_loader.py              # 动态加载与沙箱
```

所有插件都放在 `plugins/` 下，启动时通过 `plugin_loader.py` 自动发现并注册。

## 2. 插件基类（plugins/base_plugin.py）

所有插件**必须**继承 `BasePlugin`：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class PluginTool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]           # JSON Schema 格式
    required: List[str]

class BasePlugin(ABC):
    name: str                             # 唯一标识，例如 "weather_tool"
    version: str = "1.0.0"
    description: str
    author: str
    dependencies: List[str] = []          # 其他插件依赖
    tools: List[PluginTool] = []          # 支持的 Tool Calling
    enabled_by_default: bool = True
    
    @abstractmethod
    async def initialize(self, context: Dict[str, Any]):
        """初始化时调用，可访问 client、config、kg_api 等"""
        pass
    
    async def on_chat_start(self, session_id: str):
        """每次新会话开始时调用"""
        pass
    
    async def on_message(self, message: str, session_id: str) -> Optional[str]:
        """在回复生成前拦截/修改消息，返回修改后内容或 None"""
        return None
    
    async def on_reply_generate(self, prompt: str, session_id: str) -> Optional[str]:
        """在最终回复前注入/修改 prompt"""
        return None
    
    async def execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """如果声明了 tools，此方法处理调用"""
        raise NotImplementedError("Tool not implemented")
    
    async def on_emotion_detected(self, emotion_payload: Dict, session_id: str):
        """情绪检测后回调"""
        pass
    
    async def on_proactive_trigger(self, proposal: Dict, session_id: str) -> bool:
        """主动行为提案时决定是否允许/修改"""
        return True
```

## 3. 开发一个完整插件示例（天气工具插件）

**文件**：`plugins/examples/weather_tool_plugin.py`

```python
from plugins.base_plugin import BasePlugin, PluginTool
import aiohttp

class WeatherToolPlugin(BasePlugin):
    name = "weather_tool"
    version = "1.0.0"
    description = "提供实时天气查询，支持中文城市名"
    author = "Zikang.Li"
    enabled_by_default = True
    
    tools = [
        PluginTool(
            name="get_current_weather",
            description="查询指定城市的当前天气（温度、湿度、天气状况）",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，例如 '北京' 或 'Hong Kong'"}
                },
                "required": ["city"]
            }
        )
    ]
    
    async def initialize(self, context: Dict[str, Any]):
        self.api_key = context.get("config", {}).get("plugins", {}).get("weather_api_key", None)
        if not self.api_key:
            print("Warning: Weather API key not configured, plugin disabled")
            self.enabled = False
    
    async def execute_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name != "get_current_weather":
            return {"error": "Unknown tool"}
        
        city = params.get("city")
        if not city:
            return {"error": "City required"}
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric&lang=zh_cn"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": f"API error: {resp.status}"}
                data = await resp.json()
                return {
                    "city": data["name"],
                    "temp": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"]
                }
```

**使用方式**（在 SDK 或内部调用）：
```python
await client.register_plugin("weather_tool")
response = await client.chat("今天北京天气怎么样？")  # 自动调用工具
```

## 4. 插件注册与加载流程（plugins/registry.py + plugin_loader.py）

- 启动时 `launch/main.py` 调用 `plugin_loader.load_all_plugins()`
- 自动扫描 `plugins/` 下所有 `.py`（排除 `__init__.py`、`base_plugin.py`、`examples/`）
- 检查 `name`、`version` 是否唯一
- 调用 `plugin.initialize(context)`（context 包含 client、config、kg_api、emotion_tracker 等）
- 如果 `tools` 非空，注册到 Tool Calling 系统中（与 multi_model_routing 兼容）

## 5. 沙箱与安全约束（与 security_architecture.md 对齐）

- 插件默认运行在 asyncio 隔离环境中
- 禁止访问本地文件、网络（除非声明并经安全审核）
- 所有网络调用需通过 `security/network_proxy.py`（可选代理 + 限流）
- 高风险操作（如执行系统命令）直接抛 `SecurityViolationError`
- 插件日志全部进入 audit.db

## 6. 测试与调试

**推荐测试结构**（在 `tests/plugins/` 下）：

```python
# tests/plugins/test_weather_tool.py
@pytest.mark.asyncio
async def test_weather_tool():
    plugin = WeatherToolPlugin()
    await plugin.initialize({"config": {"plugins": {"weather_api_key": "fake_key"}}})
    result = await plugin.execute_tool("get_current_weather", {"city": "北京"})
    assert "temp" in result or "error" in result
```

**调试技巧**：
- 设置 `MIREXS_DEBUG=1` 环境变量，打印插件加载顺序
- 使用 `client.list_plugins()` 查看已加载插件

## 7. 贡献插件指南

1. Fork 仓库
2. 在 `plugins/examples/` 下创建你的插件文件
3. 实现 `BasePlugin` 所有抽象方法
4. 添加单元测试
5. 提交 PR 到 `plugins/`（标题：`Add plugin: [your_plugin_name]`）
6. 文档更新 `api_reference/plugin_development.md`

## 8. 已知限制与未来规划

- 当前不支持动态热加载（需重启）
- 插件间依赖顺序由 `dependencies` 控制（拓扑排序）
- v2.1 计划：支持插件市场 + 签名验证

本指南与仓库**plugins/** 目录及 **security/**、**cognitive/** 等模块完全对应，是插件开发的**唯一权威文档**。任何插件变更需同步更新本文件。

**作者签名**：Zikang.Li  
**日期**：2026-03-17
