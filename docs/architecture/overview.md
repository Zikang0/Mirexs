
# Mirexs v2.0 整体架构概述（Architecture Overview）

**版本：v2.0.0**  
**最后更新：2026-03-16**  
**作者：Zikang.Li**  
**状态：契约优先总览文档，所有子架构文档必须引用并遵守本概述中的分层、原则与约束**

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
│  - Reinforcement Learner (Q-learning + User Feedback)       │
│  - Proactive Behavior Engine                                │
└─────────────────────────────────────────────────────────────┘
            ↓↑ (标准接口 + Pydantic Payloads)
┌─────────────────────────────────────────────────────────────┐
│  Infrastructure & Runtime Layer                             │
│  - Model Hub & Loader (vLLM / llama.cpp / transformers)     │
│  - Vector DB (Chroma / FAISS)                               │
│  - Graph DB (Neo4j)                                         │
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

- **Payload 标准**：全部使用 Pydantic v2 BaseModel，禁止 dict/自定义类
- **异步优先**：所有 I/O、重计算操作必须 async def
- **错误处理**：统一使用自定义异常继承自 `MirexsError`，携带 error_code + user_friendly_message
- **日志级别**：
  - DEBUG：详细数据流
  - INFO：决策点、状态变更
  - WARNING：降级、fallback
  - ERROR：模块失败（触发 incident response）
- **版本控制**：每个模块文档头部必须声明版本，与本概述版本同步或更高

## 5. 子架构文档清单（architecture/ 目录下规划文件）

| 文件名                        | 主要职责                                   | 依赖本概述章节 | 优先级 | 状态（GitHub） |
|-------------------------------|--------------------------------------------|----------------|--------|----------------|
| overview.md                   | 本文档，总览 + 分层 + 原则                 | —              | 最高   | 待创建         |
| multi_model_routing.md        | 多模型路由、硬件自适应、决策引擎           | 2, 3, 4        | 高     | 待创建         |
| emotion_nn.md                 | 情绪神经网络、多模态融合、个性化微调       | 2, 3           | 高     | 待创建         |
| knowledge_graph.md            | 知识图谱建模、抽取、查询、遗忘机制         | 2, 3           | 高     | 待创建         |
| security_architecture.md      | 安全三层设计、审计、隐私、事件响应         | 2, 5           | 高     | 待创建         |
| reinforcement_learner.md      | Q-learning 行为优化、奖励设计、探索策略   | 2              | 中     | 待创建         |
| proactive_behavior.md         | 主动能力引擎、触发条件、行为提案           | 2, 3           | 中     | 待创建         |
| hybrid_memory.md              | 向量 + 图谱 + 情景 + 程序记忆协同机制      | 2, 3           | 中     | 待创建         |
| realtime_knowledge.md         | 实时知识接入、RSS/Web 增量更新             | 2              | 低     | 待创建         |

**注意**：以上文件**全部**在 GitHub 当前为空，需要逐个创建并 commit。后续子文档必须在头部声明：

> 本文档依赖并遵守 `architecture/overview.md` v2.0.0 中的分层与原则。

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

**作者签名**：Zikang.Li  
**日期**：2026-03-16

