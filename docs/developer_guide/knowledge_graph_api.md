---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "data/databases/graph_db/,docs/architecture/knowledge_graph.md"
related_issues: ""
references: "docs/technical_specifications/api_envelope_standard.md"
---
# 知识图谱内部接口契约

## 1. 文档目标

本文件定义知识图谱模块对内部研发暴露的最小接口契约，便于上层能力在不依赖底层具体存储实现的情况下进行实体写入、关系更新和查询推理。

## 2. 核心对象

- 实体：人、地点、事件、物品、概念等节点
- 关系：喜欢、拥有、位于、参与、相关等边
- 查询结果：实体集合、关系路径、推理结论

## 3. 推荐接口

- `add_entity(name, type, properties)`
- `update_entity(entity_id, properties)`
- `add_relation(source_id, target_id, relation_type, properties=None)`
- `search_entities(query, filters=None)`
- `get_neighbors(entity_id, relation_types=None, max_depth=1)`
- `infer_relations(entity_id, max_depth=2)`

## 4. 输入约束

- `name` 应是可读字符串，不应为空
- `type` 应使用受控类别，而不是任意自由文本
- `properties` 应为可序列化字典
- `relation_type` 应为稳定枚举或受控字符串

## 5. 输出要求

接口返回时至少应包含：

- 唯一标识
- 类型
- 核心属性
- 关系摘要
- 可选置信度或来源信息

## 6. 示例

```python
from data.databases.graph_db.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
user_id = kg.add_entity("周杰伦", "person", {"source": "conversation"})
album_id = kg.add_entity("夜曲", "song", {"genre": "pop"})
kg.add_relation(user_id, album_id, "LIKES")
```

## 7. 设计要求

- 上层不得依赖底层图库专有 API
- 写入接口必须支持去重或冲突处理
- 查询接口应支持后续替换为内存图、Neo4j 或其他后端
- 推理结果应可解释，不能只返回黑盒结论
