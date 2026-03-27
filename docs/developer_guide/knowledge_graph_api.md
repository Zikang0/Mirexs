---
status: partial
last_reviewed: 2026-03-26
corresponds_to_code: "暂无"
related_issues: ""
references: docs/technical_specifications/api_envelope_standard.md
---
# 知识图谱 API（内部接口契约）

版本：v2.0
最后更新：2026-03-16

## 1. 核心接口

- `add_entity(name, type, properties)`
- `add_relation(source_id, target_id, relation_type)`
- `search_entities(query)`
- `infer_relations(entity_id, max_depth)`

## 2. 示例

```python
from data.databases.graph_db.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
entity_id = kg.add_entity("周杰伦", "person")
```

---

本文件为契约优先文档。
