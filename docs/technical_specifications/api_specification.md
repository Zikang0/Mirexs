# API 规范（Contract‑First Specification）

版本：v2.0
最后更新：2026-03-16

## 1. 概述

本文档定义 Mirexs 的对外 API 契约，作为设计、实现、测试与对接的唯一规范来源。

## 2. 基础信息

- Base URL：`https://{host}/api/v1`
- Content‑Type：`application/json`
- 编码：UTF‑8
- 时区：默认使用 ISO‑8601，带时区偏移

## 3. 认证与授权

### 3.1 Bearer JWT

```
Authorization: Bearer <token>
```

### 3.2 API Key

```
X-API-Key: <api_key>
```

### 3.3 权限控制

- 所有接口按 RBAC/ABAC 进行权限判定。
- 高风险操作需 MFA。

## 4. 通用响应格式

### 成功

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "req_001",
    "timestamp": "2026-03-16T10:00:00+08:00",
    "version": "v1"
  }
}
```

### 错误

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数错误",
    "details": []
  }
}
```

## 5. 速率限制

- 默认：1000 req/min
- 认证用户：5000 req/min
- 企业用户：10000 req/min

## 6. 端点规范

### 6.1 系统与健康

**GET /system/status**

- 描述：系统运行状态
- 响应：版本、运行时间、核心模块状态

**GET /system/health**

- 描述：健康检查
- 响应：CPU/GPU/内存/依赖服务状态

**GET /system/metrics**

- 描述：性能指标
- 响应：QPS、延迟、错误率

### 6.2 会话与消息

**POST /conversations**

- 请求
```json
{
  "user_id": "user_001",
  "title": "周会"
}
```

**POST /conversations/{id}/messages**

- 请求
```json
{
  "role": "user",
  "content": "帮我整理周会要点"
}
```

### 6.3 记忆与知识

**POST /memory/items**

- 用途：写入记忆

**POST /memory/search**

- 用途：语义检索

**POST /knowledge/entities**

- 用途：创建实体

**POST /knowledge/relations**

- 用途：创建关系

**POST /knowledge/infer**

- 用途：图谱推理

### 6.4 模型与路由

**GET /models**

- 返回可用模型列表

**POST /routing/decide**

- 请求
```json
{
  "task": "code_generation",
  "complexity": 0.82,
  "context_tokens": 6000
}
```

### 6.5 插件与工具

**GET /plugins**

- 获取插件列表

**POST /plugins/install**

- 安装插件

**POST /tools/execute**

- 执行工具

---

本规范为契约优先文档，作为实现与验收的统一依据。
