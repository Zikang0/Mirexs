---
status: implemented
last_reviewed: 2026-03-26
corresponds_to_code: "application/api_gateway/response_formatter.py"
related_issues: ""
---
# API 响应封装规范 (API Envelope Standard)

## 1. 概述

本规范定义了 Mirexs v2.0 所有 RESTful API 的统一响应格式。规范结合了 RFC 9457 (Problem Details for HTTP APIs) 风格的错误处理与统一的成功响应封装 (Success Wrapper)，以确保客户端能够以一致的方式解析所有 API 响应。

## 2. 成功响应格式 (Success Wrapper)

所有成功的 API 请求（HTTP 状态码 2xx）都必须使用以下 JSON 结构进行封装：

```json
{
  "success": true,
  "data": {
    // 实际的业务数据，可以是对象或数组
  },
  "meta": {
    // 可选的元数据，如分页信息、请求 ID、处理时间等
    "request_id": "req-12345",
    "timestamp": "2026-03-26T12:00:00Z"
  }
}
```

## 3. 错误响应格式 (RFC 9457 Style)

所有失败的 API 请求（HTTP 状态码 4xx, 5xx）都必须遵循 RFC 9457 规范，返回以下 JSON 结构：

```json
{
  "success": false,
  "type": "https://api.mirexs.com/errors/validation-error",
  "title": "请求参数验证失败",
  "status": 400,
  "detail": "提供的实体名称不能为空。",
  "instance": "/api/v1/knowledge/entities",
  "errors": [
    // 可选的详细错误列表，适用于多字段验证失败等场景
    {
      "field": "name",
      "message": "实体名称不能为空"
    }
  ]
}
```

### 字段说明：

- `success`: 固定为 `false`。
- `type`: 错误类型的 URI 标识符，客户端可据此进行错误分类处理。
- `title`: 简短的、人类可读的错误摘要。
- `status`: HTTP 状态码，与响应头的状态码保持一致。
- `detail`: 详细的、人类可读的错误解释。
- `instance`: 发生错误的具体请求 URI。
- `errors`: （可选）具体的错误详情列表。

## 4. 实现对齐

当前代码库中，API 响应的统一格式化由 `application/api_gateway/response_formatter.py` 负责实现。所有新增的 API 路由必须使用该格式化器来生成响应。
