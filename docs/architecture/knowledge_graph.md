
# 知识图谱（Knowledge Graph）架构规范

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**状态：契约优先规范（默认实现为 NetworkX 内存图；Neo4j 为可选持久化后端）**

## 0. 实现对齐摘要（2026-03-23）

为避免“文档描述的目标态”与“仓库可运行实现”混淆，先给出可验证的实现入口：

- **默认内存图实现**：`data/databases/graph_db/knowledge_graph.py`（`KnowledgeGraph`，底层 `networkx.MultiDiGraph`）
- **Neo4j 可选后端**：`data/databases/graph_db/neo4j_integration.py`（`Neo4jIntegration`，需安装 `neo4j` driver 并连接外部 Neo4j）
- **图分析/遍历能力**：`data/databases/graph_db/graph_analyzer.py`、`data/databases/graph_db/graph_traversal.py`
- **向量数据库实现**：`data/databases/vector_db/`（Chroma/FAISS 集成与索引）

本文其余章节以“契约 + 目标架构”为主，同时在关键节点标注默认实现与差异。

## 1. 目标与定位

知识图谱是 Mirexs v2.0 的“长期关系记忆核心”，目标是让系统不仅仅记住孤立事实，还能理解实体之间的多维关系、时间演化、情感强度与因果链条，从而驱动：

- 个性化推荐（“你上次因为 X 而开心，这次推荐 Y”）
- 多跳推理（“A 喜欢 B，B 讨厌 C → A 可能不喜欢 C”）
- 主动行为触发（检测关系冲突后自动询问用户）
- 与向量记忆（Chroma/FAISS）协同，形成 Hybrid Memory
- 遗忘与巩固机制（重要关系自动加强，旧关系指数衰减）

**量化核心目标**：

| 指标                     | 目标值                  | 验收环境                     | 备注                              |
|--------------------------|-------------------------|------------------------------|-----------------------------------|
| 节点上限                 | ≥ 1,000,000             | Neo4j Community 5.20+        | 单机可达，集群无上限             |
| 2 跳推理延迟 (P95)       | ≤ 280 ms                | RTX 3060 + 32GB RAM          | 包含向量重排序                   |
| 实体抽取准确率           | ≥ 91% (F1)              | 自定义 10k 测试集            | 中文对话场景                     |
| 关系强度更新频率         | 每 5 轮对话一次         | —                            | 可配置                           |
| 查询吞吐量               | ≥ 120 QPS               | 同上                         | 混合 Cypher + vector             |
| 最低支持硬件             | 16GB RAM + SSD          | —                            | 纯 CPU 模式可用                  |

## 2. 数据模型（边界层 Schema，Pydantic 示例）

### 2.1 实体（Entity）

```python
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Entity(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="全局唯一 UUID")
    name: str
    type: Literal["PERSON", "OBJECT", "LOCATION", "CONCEPT", "EVENT", "EMOTION_TRIGGER", "USER_PREFERENCE"]
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)  # e.g. {"birth_year": 1998, "favorite_color": "blue"}
    embedding: Optional[list[float]] = None                   # 例如 384 维 bge-small-zh-* embedding
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    importance_score: float = Field(ge=0.0, le=1.0, default=0.5)  # 动态计算
```

### 2.2 关系（Relation）

```python
class Relation(BaseModel):
    relation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relation_type: Literal[
        "LIKES",
        "DISLIKES",
        "BELONGS_TO",
        "HAPPENED_IN",
        "CAUSES",
        "REMEMBERS",
        "EMOTION_TRIGGERED_BY",
        "PREFERENCE_FOR",
        "KNOWS_ABOUT",
        "OWNS",
    ]
    properties: dict[str, Any] = Field(default_factory=dict)  # {"strength": 0.92, "frequency": 7, "last_time": "..."}
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    evidence_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.3 证据链（Evidence，可选高级特性）

```python
class Evidence(BaseModel):
    evidence_id: str
    relation_id: str
    source_type: Literal["dialogue", "file", "web", "user_correction"]
    snippet: str
    weight: float
    timestamp: datetime
```

## 3. 存储策略（默认实现 + 可选后端）

### 3.1 默认实现（本仓库现状）

- **内存图（NetworkX）**：`KnowledgeGraph` 使用 `networkx.MultiDiGraph` 存储节点与关系（`data/databases/graph_db/knowledge_graph.py`）
  - 优点：本地部署成本低、依赖少、适合 MVP 与单机推理
  - 限制：跨进程共享与大规模持久化需要额外落盘/索引策略
- **向量层**：Chroma + FAISS（`data/databases/vector_db/`）

### 3.2 可选持久化后端（部分实现）

- **Neo4j**：用于更强的持久化与查询能力（`data/databases/graph_db/neo4j_integration.py`）
  - 说明：需要外部 Neo4j 服务与 Python driver；是否启用由部署决定

### 3.3 同步机制（目标约束）

当知识图谱更新影响检索/推理结果时，应同步更新向量索引（增量优先）：

- 图谱写入成功 → 触发 embedding 生成/更新 → 写入向量库
- 向量检索命中结果 → 图谱二次验证（NetworkX 或 Neo4j）→ 返回可解释路径/证据

## 4. 建图流程（pipeline 约束 + 伪代码）

> 说明：实体/关系抽取的具体实现属于“能力层/认知层”的 NLP pipeline。仓库当前提供图存储与遍历能力，抽取模块仍在逐步落地（可先用规则/LLM 占位）。

关键流程约束（必须满足）：

1. **抽取**：从对话/文本中抽取实体与关系（NER/RE）
2. **标准化**：统一类型、别名、时间字段；对不确定信息赋置信度
3. **消歧与合并**：同名实体消歧；重复实体/关系合并（保留证据与版本）
4. **写入图谱**：
   - 默认：调用 `KnowledgeGraph.add_entity/add_relation`
   - Neo4j 模式：调用 `Neo4jIntegration.create_node/create_relationship`
5. **同步向量**：对新增/更新的实体生成 embedding，更新到向量库

伪代码（默认 NetworkX 实现）：

```python
from data.databases.graph_db.knowledge_graph import KnowledgeGraph


def upsert_from_dialogue(graph: KnowledgeGraph, dialogue: str) -> None:
    entities = extract_entities(dialogue)   # 规则/LLM/小模型，按实际实现替换
    relations = extract_relations(dialogue, entities)

    entity_ids: dict[str, str] = {}
    for e in entities:
        entity_ids[e["name"]] = graph.add_entity(e["name"], e["type"], e.get("properties", {}), confidence=e.get("confidence", 0.85))

    for r in relations:
        graph.add_relation(
            source_entity=entity_ids[r["source"]],
            target_entity=entity_ids[r["target"]],
            relation_type=r["relation_type"],
            properties=r.get("properties", {}),
            confidence=r.get("confidence", 0.85),
        )
```

**实体抽取 Prompt（精确模板）**：
```text
你是一个中文实体抽取专家。从以下对话中提取所有实体（人、物、地点、概念、事件），输出严格 JSON 数组。
对话：{dialogue}
输出格式：[{"name": "...", "type": "PERSON", "aliases": [...], "properties": {...}}]
```

## 5. 查询与推理（默认实现 + Neo4j 模板）

### 5.1 Neo4j 查询模板（Cypher，适用于 Neo4j 后端）

```cypher
-- 精确实体检索
MATCH (e:Entity {name: $name})
RETURN e, e.importance_score AS score

-- 带向量相似度
CALL db.index.vector.queryNodes('entity_embedding_index', 10, $query_embedding)
YIELD node, score
RETURN node.name, score
```

### 5.2 Neo4j 多跳推理（最多 4 跳，带权重）

```cypher
MATCH path = (start:Entity {name: $start_name})-[:LIKES|DISLIKES*1..3]->(end:Entity)
WHERE all(r IN relationships(path) WHERE r.strength > 0.6)
RETURN path, 
       reduce(total = 0, r IN relationships(path) | total + r.strength) AS path_strength
ORDER BY path_strength DESC
LIMIT 5
```

### 5.3 Neo4j 情绪触发推理

```cypher
MATCH (user:Entity {type: 'USER'})-[:EMOTION_TRIGGERED_BY]->(trigger:Entity)
WHERE trigger.name CONTAINS $keyword
RETURN trigger, avg(trigger.properties.strength) AS avg_intensity
```

## 6. 一致性与冲突处理（完整规则）

1. **多源冲突**：新事实置信度 > 旧事实 0.15 时覆盖，否则保留双版本（用 `version` 属性）
2. **用户纠错优先级**：`confidence = 1.0`，强制覆盖
3. **时间衰减公式**（KaTeX）：
   ```latex
   importance_{t} = importance_{0} \times e^{-\lambda \cdot (t - t_0)}
   ```
   其中 \(\lambda = 0.0008\)（每天衰减约 0.08%）

## 7. 与记忆系统的协同（精确集成点）

- **情景记忆** → 每条对话生成一个 EVENT 实体 + 关系链
- **语义记忆** → 抽象为长期关系（每周运行聚合 Job）
- **程序记忆** → 将用户偏好流程映射为 CONCEPT 节点
- **向量记忆桥接**：Chroma/FAISS 查询结果 → 图谱二次验证路径（NetworkX 或 Neo4j）

## 8. API 契约（接口草案 + 对齐说明）

```python
class KnowledgeGraphAPI:
    async def add_entity(self, entity: Entity) -> str:
        """返回 entity_id"""
    
    async def add_relation(self, relation: Relation, emotion_intensity: float = 0.5):
        """自动更新强度 = 旧强度 * 0.7 + 新强度 * 0.3"""
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """混合向量 + 图查询"""
    
    async def infer_path(self, start_name: str, relation_types: List[str], max_hops: int = 3) -> List[dict]:
        """返回推理路径列表（结构由调用方约定）"""
    
    async def forget_low_importance(self, threshold: float = 0.05):
        """每周 cron 任务"""
```

## 9. 性能指标与观测（精确公式）

- 节点查询延迟：`P95 < 80ms`
- 关系更新吞吐：`≥ 180 次/秒`
- 向量索引构建：`每 10k 实体 < 45s`
- 监控指标（Prometheus）：
  - `kg_node_count`
  - `kg_relation_update_latency_ms`
  - `kg_inference_hops_avg`

## 10. 测试验收清单（必须 100% 通过）

- 单元测试：实体合并、关系强度更新、冲突解决（50 cases）
- 集成测试：端到端对话 → 图谱更新 → 推理结果正确（200 轮）
- 压力测试：1M 节点下多跳查询 ≤ 300ms
- 准确率测试：实体抽取 F1 ≥ 0.91，关系类型准确率 ≥ 0.88
- 边缘 case：同名实体消歧、重叠关系、用户手动删除节点

## 11. 已知风险与缓解措施

- 风险：图爆炸（节点过多）→ 每周运行 `prune_low_importance` + 实体合并 Job
- 风险：抽取幻觉 → 双重验证（小模型 + LLM）+ 用户反馈闭环
- 风险：隐私 → 所有图数据加密（Neo4j 企业特性或自加密），用户可导出/删除个人子图
- 风险：持久化后端崩溃（如 Neo4j）→ 每日备份 + 恢复演练（具体策略取决于部署形态）

本规范为知识图谱模块的**唯一权威文档**，所有实现、代码审查、性能验收必须严格遵循。任何改动需同步更新本文件并提交 PR。

**作者签名**：Zikang Li  
**日期**：2026-03-23
### 5.4 默认实现：NetworkX 推理入口（本仓库现状）

默认内存图实现已提供基础推理与检索能力（示例方法）：

- `KnowledgeGraph.infer_relations(entity_id, max_depth=2)`：DFS 推理路径
- `KnowledgeGraph.search_entities(query, entity_types=None)`：实体搜索
- `KnowledgeGraph.get_subgraph(center_entity, radius=2)`：子图提取

> 以上方法定义与实现见：`data/databases/graph_db/knowledge_graph.py`。
