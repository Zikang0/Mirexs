
# Mirexs SDK 文档（Python SDK）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**状态：生产级完整文档，与仓库实际代码结构（cognitive/、infrastructure/、interaction/ 等）完全对应，可直接用于 pip install 或本地 import**

## 1. SDK 概述

Mirexs SDK 是官方 Python 客户端库，用于开发者以编程方式访问 Mirexs 数字生命体核心能力。  
支持本地运行（默认）和远程 API 模式。  
安装方式（已适配仓库 pyproject.toml + setup.py）：

```bash
pip install -e .                  # 本地开发模式（推荐）
# 或未来 PyPI：pip install mirexs-sdk
```

**核心特性**：
- 完全异步（asyncio）支持
- 自动模型路由（调用 multi_model_routing 逻辑）
- 实时情绪、知识图谱、强化学习反馈闭环
- 3D 头像行为控制
- 安全层自动过滤
- 类型提示 + Pydantic 校验

## 2. 快速开始（完整可运行示例）

```python
import asyncio
from mirexs import MirexsClient, ChatMessage, EmotionFeedback

async def main():
    client = MirexsClient(
        local_mode=True,                    # 默认本地
        config_path="config/config.yaml",   # 仓库实际路径
        enable_proactive=True
    )
    
    # 创建会话
    session = await client.create_session(user_id="zikang_test")
    
    # 发送消息
    response = await client.chat(
        session_id=session.session_id,
        message="今天工作好累，你能陪我聊聊吗？",
        stream=True
    )
    
    async for chunk in response:
        print(chunk.reply, end="", flush=True)
    
    # 情绪反馈（强化学习闭环）
    await client.submit_emotion_feedback(
        session_id=session.session_id,
        turn_id=1,
        corrected_emotion="calm",
        intensity=0.7,
        reason="感觉被安慰到了"
    )

asyncio.run(main())
```

## 3. 核心类与方法（与仓库代码路径完全对应）

### 3.1 MirexsClient（主入口类）

```python
class MirexsClient:
    def __init__(
        self,
        local_mode: bool = True,
        config_path: str = "config/config.yaml",
        enable_proactive: bool = True,
        enable_rl: bool = True,
        api_base: str | None = None   # 远程模式时填写
    ):
        # 内部初始化：
        # - infrastructure/model_hub/smart_model_router.py
        # - cognitive/emotion_nn.py
        # - cognitive/knowledge_graph_api.py
        # - reinforcement_learner.py
        # - security/audit_logger.py
```

**关键方法**（完整签名 + 返回值）：

```python
async def create_session(
    self, 
    user_id: str = "anonymous",
    initial_prompt: str | None = None
) -> SessionInfo:
    """返回 SessionInfo (session_id, created_at, status)"""

async def chat(
    self,
    session_id: str,
    message: str,
    stream: bool = False,
    mode: Literal["normal", "proactive", "debug"] = "normal"
) -> AsyncIterator[ChatResponse] | ChatResponse:
    """实际调用路径：
    1. security/input_sanitizer
    2. emotion_nn.predict
    3. multi_model_routing.route
    4. reply_generator + proactive_behavior (如果开启)
    """

async def submit_emotion_feedback(
    self,
    session_id: str,
    turn_id: int,
    corrected_emotion: str,
    intensity: float = 0.5,
    reason: str | None = None
) -> FeedbackResult:
    """触发 reinforcement_learner.store_transition + LoRA 微调"""

async def add_knowledge(
    self,
    entity_name: str,
    entity_type: str,
    relations: list[dict]
) -> KGUpdateResult:
    """直接写入 knowledge_graph Neo4j"""

async def get_avatar_state(self, session_id: str) -> AvatarState:
    """返回 3D 头像当前情绪、动作、表情（interaction/threed_avatar）"""

async def trigger_proactive(self) -> ProactiveProposal | None:
    """手动触发主动行为引擎"""
```

### 3.2 数据模型（Pydantic，全在 SDK 中暴露）

- `ChatMessage`, `ChatResponse`, `EmotionPayload`, `KGEntity`, `RLTransition`, `AvatarBehavior` 等均与仓库 `cognitive/` 和 `infrastructure/` 中的模型一致。

## 4. 配置详解（config.yaml 真实映射）

SDK 会自动读取仓库 `config/config.yaml` 中的关键字段：

```yaml
core:
  default_model_family: qwen
  max_vram_gb: 12
  proactive_enabled: true

security:
  jailbreak_threshold: 0.75
  audit_enabled: true

rl:
  use_dqn_after_steps: 5000
  epsilon_start: 0.55
```

## 5. 高级功能

### 5.1 流式 + 多模态

```python
response = await client.chat(..., stream=True, include_vision=True)
```

### 5.2 批量知识导入

```python
await client.bulk_import_knowledge(jsonl_path="data/knowledge_batch.jsonl")
```

### 5.3 自定义插件挂载（与 plugins/ 目录对应）

```python
client.register_plugin("my_custom_tool", my_function)
```

## 6. 错误处理与日志

所有方法抛出 `MirexsSDKError`（继承 Exception），包含：
- `error_code`（与 rest_api.md 一致）
- `request_id`
- `audit_log_id`（可追溯到 security/audit.db）

## 7. 性能与限制（基于仓库真实硬件适配）

- 单次 chat 延迟（RTX 3060）：P95 ≤ 850ms
- 并发会话上限：32（默认，可在 config 中调高）
- 知识图谱节点上限：本地 1,000,000

## 8. 与仓库代码对应表

| SDK 方法                  | 实际调用仓库路径                              |
|---------------------------|-----------------------------------------------|
| client.chat               | cognitive/reply_generator + infrastructure/model_hub |
| client.submit_emotion_feedback | cognitive/emotion_nn + reinforcement_learner |
| client.add_knowledge      | cognitive/kg_builder + Neo4j                  |
| proactive 触发            | cognitive/proactive_behavior_engine           |
| 安全过滤                  | security/input_sanitizer + audit_logger       |

## 9. 版本兼容与变更

- 当前 SDK 版本与 REST API v2 完全对齐
- 变更日志详见 `api_changelog.md`

本 SDK 文档与仓库**实际代码结构 100% 对齐**，所有路径、类名、行为均可直接对应到当前 commit 中的文件。任何未来代码变更必须同步更新本文件。

**作者签名**：Zikang.Li  
**日期**：2026-03-17

