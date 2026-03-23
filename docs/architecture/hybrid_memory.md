# 混合记忆系统（Hybrid Memory）架构规范

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**状态：契约优先规范（核心模块已存在；跨模块桥接仍需补齐）**

> 本文档依赖并遵守 `architecture/overview.md` v2.0.1 中的分层与约束。

## 0. 实现对齐摘要（2026-03-23）

本仓库中与“混合记忆”直接相关的可验证入口：

- **记忆系统（认知层）**：`cognitive/memory/`（工作/情景/语义/程序记忆与巩固/遗忘/检索）
  - 典型模块：`working_memory.py`、`episodic_memory.py`、`semantic_memory.py`、`procedural_memory.py`
  - 管理与策略：`memory_consolidation.py`、`memory_forgetting.py`、`memory_retrieval.py`、`memory_metrics.py`
  - 桥接占位：`memory_graph_bridge.py`、`smart_memory.py`（当前为占位，需补齐）
- **向量数据库（数据层）**：`data/databases/vector_db/`（Chroma/FAISS、索引、相似度检索）
- **知识图谱（数据层）**：`data/databases/graph_db/knowledge_graph.py`（NetworkX 内存图实现）

本文其余章节以“契约 + 目标行为”为主，并在关键节点标注当前实现与差异。

## 1. 目标与范围

混合记忆系统的目标是把**不同形态的长期/短期信息**以最合适的结构存储与检索，使 Mirexs 具备：

- 长期一致的个性化（偏好、关系、背景）
- 可解释的推理依据（“我为什么这么回答/这么做”）
- 高效检索与渐进式压缩（不让上下文无限膨胀）
- 可控的隐私与用户主权（导出/删除/暂停记忆）

本模块关注“记忆的表示、存储、检索、巩固与遗忘”，不直接规定：

- 大模型推理后端（见 `multi_model_routing.md` / `big_data_models.md`）
- 对外 API 细节（见 `technical_specifications/api_specification.md` 与 `api_reference/*`）

## 2. 记忆类型与职责边界（统一术语）

为避免文档与实现语义漂移，统一记忆类型定义如下：

1. **工作记忆（Working Memory）**：强时效、强上下文依赖；用于当前任务/对话窗口内的临时状态。
2. **情景记忆（Episodic Memory）**：以事件/片段为单位的可回放记录（对话片段、关键决策点、用户反馈）。
3. **语义记忆（Semantic Memory）**：抽象知识与长期事实（概念、实体属性、稳定偏好）。
4. **程序记忆（Procedural Memory）**：可执行的流程/习惯/技能（“用户喜欢的做事方式”）。

混合记忆（Hybrid Memory）指：**向量检索 + 图谱推理 + 分层记忆策略** 的组合，而不是某一种单一存储。

## 3. 存储层与数据形态（默认实现口径）

### 3.1 默认实现（本地优先）

- **工作记忆**：进程内结构（可序列化快照），随会话生命周期变化
- **情景记忆**：向量库（Chroma/FAISS）+ 元数据（重要度、时间、来源）
- **语义记忆**：知识图谱（NetworkX 内存图；可选 Neo4j 持久化）
- **程序记忆**：结构化配置/规则/技能索引（实现形态由上层能力系统决定）

### 3.2 标识与一致性

- 所有记忆项必须具备稳定 ID（UUID 或等价方案）
- 同一事实/偏好在不同存储层出现时，必须定义“权威源”与“冲突解决规则”（见 `knowledge_graph.md` 的冲突处理思路）

## 4. 统一数据模型（边界层 Schema，示例）

> 说明：内部模块可用 dataclass/自定义结构；但跨模块传递与持久化建议使用稳定 Schema（Pydantic 示例如下）。

```python
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    memory_type: Literal["working", "episodic", "semantic", "procedural"]
    content: str
    summary: Optional[str] = None
    embedding: Optional[list[float]] = None
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    source: Literal["dialogue", "user_input", "file", "web", "system"] = "dialogue"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## 5. 摄取与写入（Ingestion）

### 5.1 写入触发条件（建议）

- 用户显式声明：“记住这个/别忘了/我喜欢/我讨厌……”
- 系统推断且置信度高（需可回滚/可纠错）
- 用户反馈信号（情绪纠正、满意度评分、任务成功/失败）

### 5.2 写入流程（约束）

1. 规范化（清洗文本、去敏、结构化字段）
2. 分类（episodic/semantic/procedural）
3. 重要度评估（importance）与置信度评估（confidence）
4. 写入目标存储（向量库/图谱/程序索引）
5. 记录审计（如启用审计；参见 `security_architecture.md`）

## 6. 检索（Retrieval）：混合检索的标准流程

混合检索的核心是：**向量召回负责“相关性”，图谱负责“约束/一致性/可解释性”**。

推荐标准流程：

1. **查询理解**：识别用户意图、时间范围、实体与约束（可复用 reasoning 模块）
2. **向量召回（Top‑K）**：从 episodic/semantic 向量索引召回候选片段
3. **图谱二次验证**：对候选实体/关系做一致性检查（避免冲突与幻觉放大）
4. **重排序**：融合相关性、重要度、时间衰减、可信度、用户纠错优先级
5. **上下文拼装**：输出“可控长度”的上下文片段给推理/回复模块（带来源标注）

## 7. 巩固与遗忘（Consolidation & Forgetting）

混合记忆必须具备“越用越稳”和“可控遗忘”的机制：

- **巩固**：高频/高重要度 episodic → 抽象为 semantic（例如偏好、稳定事实）
- **遗忘**：低重要度、长期未访问、被用户否定/纠错的记忆应衰减或删除

实现入口（当前仓库可检索模块）：

- `cognitive/memory/memory_consolidation.py`
- `cognitive/memory/memory_forgetting.py`

> 注：是否已与向量库/图谱打通，需要在桥接模块中明确（`memory_graph_bridge.py` 当前为占位）。

## 8. 与其他模块的集成点

- **知识图谱**：semantic 的结构化部分进入图谱；图谱反过来为检索提供约束与解释（见 `knowledge_graph.md`）
- **深度思考引擎**：检索结果作为证据输入；反思环可触发记忆纠错与巩固（见 `deep_thinking_engine.md`）
- **事实核查**：外部信息写入前应通过核查；冲突时触发降级或用户确认（见 `fact_checker.md`）
- **安全与隐私**：记忆写入必须可追溯/可删除；对外导出需脱敏（见 `security_architecture.md` 与 `docs/security/*`）

## 9. 已知差异与待办

1. **桥接模块缺失**：`cognitive/memory/memory_graph_bridge.py`、`cognitive/memory/smart_memory.py` 仍为占位，需要补齐“向量库/图谱/记忆层”的端到端打通。
2. **统一 API 未固化**：跨模块统一的 Memory API（异步/Schema/错误模型）需要在实现层落地并在文档中固定。
3. **验收基准待定义**：应补充最小验收用例（写入→检索→巩固→遗忘）与可观测指标（命中率、延迟、冲突率）。

本文件为混合记忆系统的顶层约束文档；任何跨层行为（写入/检索/遗忘）规则变更必须同步更新本文档并说明原因。

**作者签名**：Zikang Li  
**日期**：2026-03-23

