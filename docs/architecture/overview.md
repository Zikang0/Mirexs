---
status: partial
last_reviewed: 2026-03-26
corresponds_to_code: "暂无"
related_issues: ""
---
# Mirexs v2.0 整体架构概述（Architecture Overview）

## 0. 实现对齐摘要（2026-03-26）

本文档为 Mirexs v2.0 的整体架构概述，当前状态为 **partial**。文档中描述的多个核心模块（如多模型路由、情绪网络、主动行为引擎等）在代码仓库中仍处于占位或部分实现状态。实际代码实现主要集中在 API 网关、访问控制以及基于 NetworkX 的知识图谱内存实现。后续将持续推进代码落地，以完全对齐本架构设计。

**版本：v2.0.1**  
**最后更新：2026-03-26**  
**作者：Zikang Li**  
**状态：契约优先总览文档（已校准文档/代码口径）；所有子架构文档必须引用并遵守本概述中的分层、原则与约束**

## 1. 设计哲学与核心原则

Mirexs v2.0 不是传统聊天机器人，而是一个**本地优先、情感驱动、具备长期自主能力的数字生命体**。架构设计遵循以下铁律（不可违反）：

1. **本地优先 & 隐私至上**：所有核心计算（模型推理、情绪网络、知识图谱、强化学习）默认 100% 本地运行；云端仅作为可选增强（需用户明确授权）。
2. **分层解耦 & 模块热插拔**：采用严格的层级 + 接口契约，任何模块可独立替换/升级（e.g. 换情绪模型不影响路由层）。
3. **硬件自适应**：从 8GB VRAM 笔记本到多卡工作站无缝降级/升级。
4. **情感闭环**：情绪理解 → 行为决策 → 回复生成 → 用户反馈 → 情绪/知识/策略更新，形成完整 OODA 循环。
5. **可观测 & 可审计**：所有决策、状态变更必须记录不可篡改日志（security/audit layer）。
6. **渐进式演化**：v2.0 核心模块必须 MVP 可运行，v3.0 再扩展多模态/IoT/联邦学习。

## 2. 整体分层架构（自顶向下）

```
Mirexs v2.0 系统分层（由外到内）

┌─────────────────────────────────────────────────────────────┐
│  Presentation & Interaction Layer                           │
│  - 3D Avatar (Panda3D)                                      │
│  - Multimodal I/O (Voice / Vision / Text)                   │
│  - UI/CLI/WebSocket 接口                                    │
└─────────────────────────────────────────────────────────────┘
            ↓↑ (事件总线 + Emotion Payload)
┌─────────────────────────────────────────────────────────────┐
│  Cognitive & Decision Core (情感 + 智能中枢)                 │
│  - Emotion Neural Network                                   │
│  - Knowledge Graph + Hybrid Memory                          │
│  - Multi-Model Intelligent Routing                          │
│  - Reinforcement Learner (RL + User Feedback)               │
│  - Proactive Behavior Engine                                │
└─────────────────────────────────────────────────────────────┘
            ↓↑ (标准接口 + Pydantic Payloads)
┌─────────────────────────────────────────────────────────────┐
│  Infrastructure & Runtime Layer                             │
│  - Model Hub & Loader (vLLM / llama.cpp / transformers)     │
│  - Vector DB (Chroma / FAISS)                               │
│  - Graph DB (NetworkX / Neo4j)                              │
│  - Hardware Profiler & Resource Manager                     │
│  - Real-time Knowledge Updater (RSS / Optional Web)         │
└─────────────────────────────────────────────────────────────┘
            ↓↑ (加密通道 + Audit Log)
┌─────────────────────────────────────────────────────────────┐
│  Security & Trust Layer (三层防护)                           │
│  - Input Sanitization & Jailbreak Defense                   │
│  - Immutable Audit Trail (append-only)                      │
│  - Incident Response & Auto-quarantine                      │
│  - Privacy Controls (Data Export / Delete / Local-only)     │
└─────────────────────────────────────────────────────────────┘
```

## 3. 关键模块间依赖与数据流（简化图 + 关键路径）

### 主要数据流路径示例

1. **用户输入 → 回复生成（最常见路径）**  
   User Input → Input Sanitization → Task Profiler → Emotion NN → Multi-Model Router → Primary Model Inference → Reply Post-process (注入情绪提示) → 3D Avatar Sync → Output

2. **长期记忆更新路径**  
   Dialogue → Entity/Relation Extraction → Knowledge Graph Update → Importance Recalc → Vector Embed Sync → Emotion Payload Archive

3. **主动行为触发路径**  
   Emotion Trend Analyzer → Knowledge Graph Query (关系冲突/未决事件) → Proactive Engine → Behavior Proposal → Router (低优先级任务) → Output Queue

## 4. 统一接口规范（所有模块必须遵守）

- **Payload 标准（边界层强制）**：对外 API、跨模块事件、持久化日志必须有稳定 Schema（优先 Pydantic v2 BaseModel；允许 dataclass 但必须配套显式序列化/反序列化）；禁止“无 Schema 的 dict”跨边界流转
- **Payload 标准（内部层建议）**：内部模块可使用 dataclass/dict，但必须保留类型注解与字段约束，并在对外边界处转换为稳定 Schema
- **异步优先（I/O 场景）**：网络/磁盘/数据库等 I/O 路径建议 `async def`；纯 CPU 逻辑可保持同步实现
- **错误处理（边界层强制）**：对外接口必须转换为统一错误模型（参见 `docs/technical_specifications/api_specification.md` 的 Envelope + `errors[]` 结构）；内部异常可保留模块自定义，但需在边界层收敛
- **日志级别**：
  - DEBUG：详细数据流
  - INFO：决策点、状态变更
  - WARNING：降级、fallback
  - ERROR：模块失败（触发 incident response）
- **版本控制**：每个模块文档头部必须声明版本与最后更新日期；若与代码不一致，必须在文档中明确“现状差异”

## 5. 子架构文档清单（architecture/ 目录）

| 文件名                    | 主要职责 | 依赖本概述章节 | 优先级 | 文档状态 | 对应实现/配置入口（示例） |
|---------------------------|----------|----------------|--------|----------|--------------------------|
| overview.md               | 架构总览 + 分层 + 约束 | — | 最高 | 已存在 | `docs/architecture/overview.md` |
| multi_model_routing.md    | 多模型路由、硬件自适应、决策引擎 | 2, 3, 4 | 高 | planned | `infrastructure/model_hub/`（占位）、`config/system/model_configs/router_config.yaml`（占位） |
| emotion_nn.md             | 情绪网络、多模态融合、个性化微调 | 2, 3 | 高 | planned | `cognitive/learning/emotion_nn.py`（占位）、`docs/internal_docs/research_papers/emotion_recognition.md`（研究稿） |
| knowledge_graph.md        | 知识图谱建模、抽取、查询、遗忘机制 | 2, 3 | 高 | partial | `data/databases/graph_db/knowledge_graph.py`（内存图实现）、`data/databases/vector_db/`（向量库实现） |
| security_architecture.md  | 安全三层设计、审计、隐私、事件响应 | 2, 5 | 高 | partial | `security/`、`docs/security/*`、`config/system/service_configs/api_config.yaml`（认证/限流） |
| reinforcement_learner.md  | 强化学习策略与接口约束 | 2 | 中 | planned | `cognitive/learning/reinforcement_learner.py` |
| proactive_behavior.md     | 主动能力引擎、触发条件、行为提案 | 2, 3 | 中 | planned | （待补齐实现入口） |
| hybrid_memory.md          | 向量 + 图谱 + 情景 + 程序记忆协同 | 2, 3 | 中 | planned | `docs/architecture/hybrid_memory.md`、`cognitive/memory/`、`data/databases/vector_db/` |
| realtime_knowledge.md     | 实时知识接入、RSS/Web 增量更新 | 2 | 低 | planned | `docs/architecture/realtime_knowledge.md`、`capabilities/knowledge/*`（占位） |

后续子文档必须在头部声明依赖关系（示例）：

> 本文档依赖并遵守 `architecture/overview.md` v2.0.1 中的分层与约束。

## 6. 非功能性全局约束（所有模块必须满足）

- **最低硬件**：16GB RAM + 8GB VRAM（强制降级 8B 模型）
- **响应延迟目标**：
  - 日常聊天：P95 ≤ 800ms
  - 复杂推理：P95 ≤ 4.5s
- **内存峰值**：单次对话 ≤ 14GB（RTX 3060 可接受）
- **启动时间**：首次冷启动 ≤ 45s（后续热启动 ≤ 5s）
- **开源许可**：Apache 2.0，所有模块代码必须兼容

## 7. 演进路线图（architecture 视角）

- **v2.0 MVP**：实现 overview 中 核心 4 模块（multi-model, emotion, kg, security）
- **v2.1**：加入 reinforcement + proactive
- **v2.5**：完善 hybrid memory + realtime
- **v3.0**：多模态扩展 + IoT + 联邦微调

本文件为 Mirexs v2.0 **架构层唯一入口文档**，所有其他 architecture/*.md 必须以此为顶层约束。任何重大设计变更需更新本文件并全量 review。

## 8. 文档一致性与对齐规则（2026-03-26 起执行）

为保证文档“严谨、可执行、可验证”，所有架构文档必须满足：

1. **声明现状**：文档头部必须包含 `状态`（规划/部分落地/已落地），且不得用“生产级/100% 对齐”替代可验证描述。
2. **映射实现**：至少给出 1 个“对应实现/配置入口”（文件路径），并说明关键差异与待办。
3. **避免虚构**：不写不存在的脚本/路径/配置名；如为目标态，必须标注“规划”并给出落地前置条件。
4. **变更联动**：接口/Envelope/路径变更需同步更新 `docs/technical_specifications/*` 与 `docs/api_reference/*`，并在 `docs/api_reference/api_changelog.md` 记录。

**作者签名**：Zikang Li  
**日期**：2026-03-26
