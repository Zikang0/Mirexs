# 数据库与存储结构规范（Database Schema）

版本：v2.0
最后更新：2026-03-16

## 1. 概述

Mirexs 使用“多存储协同”架构：
- 关系型数据库：用户、配置、权限、会话。
- 图数据库：知识图谱与关系推理。
- 向量数据库：记忆与语义检索。
- 时序数据库：运行指标与监控数据。

## 2. 关系型数据库（核心表）

### 2.1 用户表 `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 用户唯一标识 |
| username | VARCHAR | 昵称 |
| email | VARCHAR | 邮箱 |
| created_at | DATETIME | 创建时间 |
| status | ENUM | active/inactive |

### 2.2 会话表 `sessions`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 会话ID |
| user_id | UUID | 用户ID |
| started_at | DATETIME | 开始时间 |
| ended_at | DATETIME | 结束时间 |
| device | VARCHAR | 设备信息 |

### 2.3 记忆索引表 `memory_index`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 记忆ID |
| user_id | UUID | 用户ID |
| type | ENUM | episodic/semantic/procedural |
| importance | FLOAT | 重要度 |
| created_at | DATETIME | 创建时间 |

### 2.4 插件表 `plugins`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | VARCHAR | 插件ID |
| version | VARCHAR | 插件版本 |
| status | ENUM | enabled/disabled |

### 2.5 审计表 `audit_logs`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 日志ID |
| event_type | VARCHAR | 事件类型 |
| user_id | UUID | 用户ID |
| timestamp | DATETIME | 时间 |

## 3. 图数据库（Neo4j）

- 节点类型：Person, Item, Place, Concept, Event
- 关系类型：LIKE, DISLIKE, LOCATED_IN, HAPPENED_AT

## 4. 向量数据库

- `memory_vectors`：情景记忆
- `knowledge_vectors`：知识向量
- `document_vectors`：文件索引

## 5. 时序数据库

- `system_metrics`
- `performance_metrics`
- `security_events`

---

本规范为契约优先文档，作为实现与验收的统一依据。
