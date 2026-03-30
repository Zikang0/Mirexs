---
status: planned
last_reviewed: 2026-03-30
corresponds_to_code: "data/,config/system/"
related_issues: ""
references: "docs/architecture/knowledge_graph.md,docs/architecture/hybrid_memory.md"
---
# 数据库与存储结构规范

## 1. 目标

Mirexs 采用多存储协同架构。本文件定义关系型数据库、图数据库、向量数据库和时序数据库的职责边界与核心结构，作为未来实现和迁移的依据。

## 2. 存储角色划分

- 关系型数据库：保存用户、会话、配置、权限和业务状态
- 图数据库：保存实体关系和可推理知识网络
- 向量数据库：保存语义向量、记忆检索索引和文档 embedding
- 时序数据库：保存指标、事件和运行性能数据
- 文件系统：保存模型、缓存、导出文件和原始附件

## 3. 关系型数据库建议结构

### 3.1 `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键 |
| `username` | VARCHAR | 用户名 |
| `display_name` | VARCHAR | 展示名称 |
| `email` | VARCHAR | 邮箱，可选 |
| `status` | VARCHAR | 用户状态 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 3.2 `sessions`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键 |
| `user_id` | UUID | 所属用户 |
| `started_at` | DATETIME | 会话开始时间 |
| `ended_at` | DATETIME | 会话结束时间 |
| `device` | VARCHAR | 设备标识 |
| `channel` | VARCHAR | 文本、语音、视觉等 |

### 3.3 `memory_index`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键 |
| `user_id` | UUID | 所属用户 |
| `memory_type` | VARCHAR | 情景、语义、程序记忆 |
| `importance` | FLOAT | 重要度 |
| `source` | VARCHAR | 来源 |
| `created_at` | DATETIME | 创建时间 |

### 3.4 `plugins`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | VARCHAR | 插件 ID |
| `version` | VARCHAR | 版本 |
| `status` | VARCHAR | 启用状态 |
| `installed_at` | DATETIME | 安装时间 |

### 3.5 `audit_logs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键 |
| `event_type` | VARCHAR | 事件类型 |
| `user_id` | UUID | 相关用户 |
| `severity` | VARCHAR | 严重度 |
| `payload` | JSON | 扩展字段 |
| `timestamp` | DATETIME | 发生时间 |

## 4. 图数据库建议结构

常见节点类型：

- `Person`
- `Item`
- `Place`
- `Concept`
- `Event`

常见关系类型：

- `LIKES`
- `DISLIKES`
- `OWNS`
- `LOCATED_IN`
- `PARTICIPATED_IN`
- `RELATED_TO`

## 5. 向量数据库建议集合

- `memory_vectors`
- `knowledge_vectors`
- `document_vectors`
- `conversation_vectors`

每条向量记录建议至少关联：

- 业务主键
- 用户标识
- 文本摘要
- 来源类型
- 时间戳

## 6. 时序数据库建议指标

- `system_metrics`
- `performance_metrics`
- `security_events`
- `model_metrics`

## 7. 设计约束

- 主键必须稳定且可追踪
- 用户相关数据必须支持删除、导出和审计
- 图数据库与向量数据库间必须有可追溯关联
- 任何存储结构变更都必须同步更新文档和迁移说明
