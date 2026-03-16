# Mirexs REST API 参考文档

版本：v2.0
最后更新：2026-03-16

## 1. 概述

本文档提供 Mirexs REST API 的实用参考，包括端点、请求/响应格式与示例。该文档与 `docs/technical_specifications/api_specification.md` 保持一致。

## 2. 基础信息

- Base URL: `https://{host}/api/v1`
- Content‑Type: `application/json`
- 超时：建议 10‑30 秒

## 3. 认证

支持两种方式：

- Bearer JWT
- API Key

示例：

```
Authorization: Bearer <token>
X-API-Key: <api_key>
```

## 4. 端点详解

### 4.1 系统与健康

**GET /system/status**

- 描述：返回系统运行信息（版本、模块状态）。
- 响应字段：`version`, `uptime`, `modules`。

**GET /system/health**

- 描述：健康检查（CPU/GPU/依赖服务）。
- 响应字段：`cpu`, `gpu`, `db`, `cache`。

### 4.2 会话与消息

**POST /conversations**

请求：

```json
{
  "user_id": "user_001",
  "title": "旅行规划"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "conv_001",
    "title": "旅行规划",
    "created_at": "2026-03-16T10:00:00+08:00"
  }
}
```

**POST /conversations/{id}/messages**

请求：

```json
{
  "role": "user",
  "content": "帮我规划大阪行程"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "message_id": "msg_001",
    "role": "assistant",
    "content": "已生成 3 个方案..."
  }
}
```

### 4.3 知识图谱

**POST /knowledge/entities**

请求：

```json
{
  "name": "周杰伦",
  "type": "person",
  "properties": {"role": "artist"}
}
```

**POST /knowledge/relations**

请求：

```json
{
  "source": "ent_user",
  "target": "ent_001",
  "type": "like"
}
```

### 4.4 模型与路由

**POST /routing/decide**

请求：

```json
{
  "task": "code_generation",
  "complexity": 0.82,
  "context_tokens": 6000
}
```

响应：

```json
{
  "success": true,
  "data": {
    "primary": "deepseek-v3-q4",
    "fallback": "llama3.1-8b-q4"
  }
}
```

### 4.5 插件与工具

**GET /plugins**

返回已安装插件列表。

**POST /tools/execute**

请求：

```json
{
  "tool_id": "web_search",
  "parameters": {"q": "北京今日新闻"}
}
```

## 5. 错误处理

常见错误码：

- `400` 参数错误
- `401` 未认证
- `403` 无权限
- `404` 资源不存在
- `429` 请求过多
- `500` 服务异常

---

本文件为契约优先文档的使用指南版本。
