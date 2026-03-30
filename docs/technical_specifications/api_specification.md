---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "config/system/service_configs/api_config.yaml,application/api_gateway/response_formatter.py"
related_issues: ""
references: docs/technical_specifications/api_envelope_standard.md
---
# Mirexs REST API 契约规范（Contract‑First Specification）

**API 版本**：v2  
**适用系统版本**：Mirexs v2.x  
**最后更新**：2026-03-30  
**作者**：Zikang Li  
**状态**：契约优先（实现进行中，以配置与代码为准）

## 1. 文档定位与权威来源

本文档定义 Mirexs 的对外 REST API 契约，用于约束 **路径、认证、通用响应、错误模型、版本策略**。  
在本仓库中，与本文档直接关联的“权威来源”如下（用于消歧与对齐）：

- **配置（最终生效口径）**：`config/system/service_configs/api_config.yaml`  
  - 网关 host/port：`gateway.service`  
  - 路由前缀：`gateway.routing.prefix`（默认 `/api/v2`）  
  - 认证/限流/健康检查等策略：对应各章节配置段落
- **响应封装（统一 Envelope）**：`application/api_gateway/response_formatter.py`（`ResponseWrapper`）
- **鉴权字段命名**：`application/api_gateway/api_authenticator.py`（`X-API-Key` 默认 header 名等）
- **参数校验错误结构**：`application/api_gateway/request_validator.py`（`ValidationError`）

如本文档与上述文件出现冲突，以 **配置 + 代码实现** 为准；文档应在同一 PR 内完成同步更新。

## 2. 基础信息

### 2.1 Base URL（部署相关）

Base URL 由 `api_config.yaml` 中的 `gateway.service.host/port` 与 `gateway.routing.prefix` 拼接得到。

- **本地默认**（单机开发/测试）：`http://localhost:8000/api/v2`
- **私有化/生产**：`https://{host}:{port}/api/v2`（是否启用 TLS 取决于部署配置；未启用 TLS 时使用 `http`）

### 2.2 通用请求头

- `Content-Type: application/json; charset=utf-8`
- `Accept: application/json`

### 2.3 时间与时区约定

- **请求参数**：如包含时间字段，推荐使用 ISO‑8601（含时区偏移）字符串。
- **响应字段**：通用 Envelope 中的 `timestamp` 使用 **Unix epoch seconds（float）**（与实现对齐）。

## 3. 认证与授权

认证是否启用由部署/配置决定；本规范只定义支持的认证方式与字段名。

### 3.1 API Key

```
X-API-Key: <api_key>
```

### 3.2 Bearer Token（JWT/Token）

```
Authorization: Bearer <token>
```

### 3.3 权限控制（策略约束）

- 推荐按 **RBAC/ABAC** 做权限判定（策略在网关或上游服务实现）。
- 高风险操作（例如“数据导出/删除、配置变更、插件安装/启用”等）建议要求更高权限，必要时引入 **二次确认或 MFA**。

## 4. 通用响应 Envelope（统一格式）

所有 JSON 响应统一使用如下 Envelope（与 `ResponseWrapper` 对齐）。

### 4.1 字段定义

| 字段 | 类型 | 必填 | 说明 |
|---|---:|:---:|---|
| `status` | string | 是 | `success` / `error` / `fail` / `warning` |
| `code` | int | 是 | 建议与 HTTP 状态码一致（200/4xx/5xx） |
| `message` | string | 是 | 面向调用方的简短信息 |
| `timestamp` | number | 是 | Unix epoch seconds（float） |
| `data` | any | 否 | 成功/警告场景的业务数据 |
| `meta` | object | 否 | 可选元数据（分页、耗时、追踪信息等） |
| `errors` | array | 否 | 参数校验/业务错误的结构化详情 |

### 4.2 成功示例

```json
{
  "status": "success",
  "code": 200,
  "message": "Success",
  "timestamp": 1711161600.123,
  "data": {},
  "meta": {}
}
```

### 4.3 参数校验失败示例（`fail`）

```json
{
  "status": "fail",
  "code": 422,
  "message": "Validation failed",
  "timestamp": 1711161600.123,
  "errors": [
    {
      "field": "user_id",
      "message": "Field is required",
      "code": "required",
      "value": null
    }
  ]
}
```

### 4.4 服务器错误示例（`error`）

```json
{
  "status": "error",
  "code": 500,
  "message": "Internal error",
  "timestamp": 1711161600.123
}
```

## 5. 错误模型与错误码约定

### 5.1 `errors[]` 结构

`errors` 数组元素遵循如下结构（与 `ValidationError` 对齐）：

| 字段 | 类型 | 必填 | 说明 |
|---|---:|:---:|---|
| `field` | string | 是 | 出错字段名；非字段错误可使用 `_schema` / `_request` |
| `message` | string | 是 | 可读错误信息 |
| `code` | string | 是 | 稳定错误码（例如 `required`、`type`、`range`、`pattern` 等） |
| `value` | any | 否 | 触发错误的值（如可安全返回） |

### 5.2 业务错误

业务错误推荐：
- `status = "error"` 或 `status = "fail"`（视是否为客户端可修正错误而定）
- `errors[]` 中放入业务子码（例如 `code="rate_limit_exceeded"`），并在 `message` 中给出短说明

## 6. 速率限制（Rate Limiting）

速率限制为配置项，默认口径参考 `api_config.yaml`：

- 全局默认：1000 req/min（`rate_limiting.global.requests_per_minute`）
- 用户默认：100 req/min（`rate_limiting.user.requests_per_minute`）
- IP 默认：200 req/min（`rate_limiting.ip.requests_per_minute`）

如启用限流，建议返回：
- HTTP 429
- Envelope：`status="error"`、`code=429`
- 可选响应头：`Retry-After`

## 7. 端点契约（按域划分）

> 说明：以下为 **契约清单**。端点是否已实现，应在 `docs/api_reference/rest_api.md` 中标注“实现状态”，并在 `docs/api_reference/api_changelog.md` 中记录变更。

### 7.1 系统与健康

- `GET /system/health`：健康检查（CPU/GPU/内存/依赖服务状态）
- `GET /system/status`：系统运行状态（版本、运行时间、核心模块状态）
- `GET /system/metrics`：性能指标（QPS、延迟、错误率等）

### 7.2 会话与对话

- `POST /sessions`：创建会话
- `GET /sessions/{session_id}`：获取会话状态与历史
- `DELETE /sessions/{session_id}`：结束会话
- `POST /chat`：发送消息并获取回复（可选流式）

### 7.3 情绪反馈

- `POST /emotion/feedback`：用户纠正情绪，用于学习/策略优化闭环

### 7.4 记忆与知识

- `POST /memory/add`：写入记忆/偏好
- `POST /memory/search`：语义检索
- `POST /knowledge/entities`：创建/更新实体
- `POST /knowledge/relations`：创建/更新关系

### 7.5 模型与路由

- `GET /models/available`：可用模型列表（含路由状态）
- `POST /routing/decide`：给定任务画像返回路由决策

### 7.6 插件与工具

- `GET /plugins`：获取插件列表
- `POST /plugins/install`：安装插件
- `POST /tools/execute`：执行工具（受安全策略约束）

---

本规范为契约优先文档，作为实现、测试与对接的统一依据。任何端点或响应结构变更，必须同步更新本文档与对应参考文档。
