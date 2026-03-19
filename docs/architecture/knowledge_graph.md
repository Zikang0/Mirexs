
# 知识图谱（Knowledge Graph）架构规范

**版本：v2.0.0**  
**最后更新：2026-03-16**  
**作者：Zikang Li**  
**状态：契约优先规范，可直接指导 Neo4j 建模、实体抽取 pipeline、查询 API 与推理引擎实现**

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

## 2. 数据模型（精确定义 + Pydantic 实现）

### 2.1 实体（Entity）

```python
class Entity(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="全局唯一 UUID")
    name: str
    type: Literal["PERSON", "OBJECT", "LOCATION", "CONCEPT", "EVENT", "EMOTION_TRIGGER", "USER_PREFERENCE"]
    aliases: List[str] = []
    properties: Dict[str, Any] = Field(default_factory=dict)  # e.g. {"birth_year": 1998, "favorite_color": "blue"}
    embedding: Optional[List[float]] = None                   # 384维 bge-small-zh-v1.5
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
        "LIKES", "DISLIKES", "BELONGS_TO", "HAPPENED_IN", "CAUSES", "REMEMBERS",
        "EMOTION_TRIGGERED_BY", "PREFERENCE_FOR", "KNOWS_ABOUT", "OWNS"
    ]
    properties: Dict[str, Any] = Field(default_factory=dict)  # {"strength": 0.92, "frequency": 7, "last_time": "2026-03-10"}
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime
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

## 3. 存储策略（三层架构 + 同步机制）

- **持久层**：Neo4j 5.20+（Community Edition）
  - 索引：`CREATE INDEX ON :Entity(name)` + `CREATE VECTOR INDEX ON :Entity(embedding)`
  - APOC 扩展用于批量导入
- **内存层**：NetworkX（快速本地遍历，用于实时推理）
- **向量层**：Chroma（实体 embedding 语义检索）+ FAISS（备用）
- **同步机制**：每 30 秒或 50 次更新后，Neo4j → Chroma 增量同步（仅更新 embedding）

## 4. 建图流程（完整 pipeline + 代码骨架）

```python
# cognitive/kg_builder.py
async def build_from_dialogue(dialogue: str, emotion_payload: dict):
    # Step 1: 实体抽取（LLM + 小模型混合）
    entities = await llm_extract_entities(dialogue)  # 使用 Qwen2.5-7B prompt
    
    # Step 2: 关系抽取（规则 + LLM）
    relations = await extract_relations(entities, dialogue)
    
    # Step 3: 消歧 & 合并（Neo4j MERGE）
    for entity in entities:
        await neo4j_merge_entity(entity)
    
    # Step 4: 写入关系 + 更新强度
    for rel in relations:
        await neo4j_create_relation(rel, emotion_payload)
    
    # Step 5: 更新 importance_score
    await recalculate_importance()
```

**实体抽取 Prompt（精确模板）**：
```text
你是一个中文实体抽取专家。从以下对话中提取所有实体（人、物、地点、概念、事件），输出严格 JSON 数组。
对话：{dialogue}
输出格式：[{"name": "...", "type": "PERSON", "aliases": [...], "properties": {...}}]
```

## 5. 查询与推理（Cypher 模板库 + 混合查询）

### 5.1 基础查询

```cypher
-- 精确实体检索
MATCH (e:Entity {name: $name})
RETURN e, e.importance_score AS score

-- 带向量相似度
CALL db.index.vector.queryNodes('entity_embedding_index', 10, $query_embedding)
YIELD node, score
RETURN node.name, score
```

### 5.2 多跳推理（最多 4 跳，带权重）

```cypher
MATCH path = (start:Entity {name: $start_name})-[:LIKES|DISLIKES*1..3]->(end:Entity)
WHERE all(r IN relationships(path) WHERE r.strength > 0.6)
RETURN path, 
       reduce(total = 0, r IN relationships(path) | total + r.strength) AS path_strength
ORDER BY path_strength DESC
LIMIT 5
```

### 5.3 情绪触发推理

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
- **向量记忆桥接**：Chroma 查询结果 → Neo4j 二次验证路径

## 8. API 契约（完整异步接口 + Pydantic）

```python
class KnowledgeGraphAPI:
    async def add_entity(self, entity: Entity) -> str:
        """返回 entity_id"""
    
    async def add_relation(self, relation: Relation, emotion_intensity: float = 0.5):
        """自动更新强度 = 旧强度 * 0.7 + 新强度 * 0.3"""
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """混合向量 + 图查询"""
    
    async def infer_path(self, start_name: str, relation_types: List[str], max_hops: int = 3) -> List[Path]:
        """返回推理路径列表"""
    
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
- 风险：Neo4j 崩溃 → 每日全量备份 + WAL 日志

本规范为知识图谱模块的**唯一权威文档**，所有实现、代码审查、性能验收必须严格遵循。任何改动需同步更新本文件并提交 PR。

**作者签名**：Zikang Li  
**日期**：2026-03-16
```
