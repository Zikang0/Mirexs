
---
status: partial
last_reviewed: 2026-03-26
corresponds_to_code: "暂无"
related_issues: ""
references: docs/technical_specifications/api_envelope_standard.md
---
# Mirexs REST API 参考文档（API Reference）

**API 版本**：v1  
**适用系统版本**：Mirexs v2.x  
**最后更新**：2026-03-23  
**作者**：Zikang Li  
**状态**：参考文档（与 `technical_specifications/api_specification.md` 保持一致）

## 1. 文档关系与阅读顺序

- **契约规范（定义口径）**：`docs/technical_specifications/api_specification.md`  
- **本文档（调用方参考）**：提供可读的端点清单、请求/响应示例与注意事项  

当两者出现冲突时，以契约规范与仓库配置/实现为准，并在同一 PR 内同步修订。

## 2. 基地址（Base URL）

基地址由 `config/system/service_configs/api_config.yaml` 决定：

- 默认本地：`http://localhost:8000/api/v1`
- 私有化/生产：`https://{host}:{port}/api/v1`（是否启用 TLS 取决于部署配置）

## 3. 认证方式（Authentication）

认证是否启用由部署决定；字段命名与默认值与实现对齐（`application/api_gateway/api_authenticator.py`）：

| 类型 | Header | 说明 |
|---|---|---|
| API Key | `X-API-Key: <api_key>` | 适用于远程访问、插件/服务间调用 |
| Bearer Token | `Authorization: Bearer <token>` | 适用于多用户/更严格场景（JWT/Token） |
| 无认证 | — | 可用于本地开发（需在网关/部署层放行） |

## 4. 通用响应格式（Envelope）

所有 JSON 响应使用统一 Envelope（与 `application/api_gateway/response_formatter.py` 的 `ResponseWrapper` 对齐）。

成功示例：
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

校验失败示例（`fail` + 422）：
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

> 说明：`timestamp` 为 Unix epoch seconds（float）；`errors[]` 结构与 `request_validator.py` 对齐。

## 5. 端点清单（按域）

> 说明：下表为 **契约端点清单**。若某端点尚未实现，必须在此处标注“规划/未实现”，避免对调用方产生误导。

| 域 | 方法 | 路径（相对 `/api/v1`） | 说明 | 实现状态 |
|---|---|---|---|---|
| system | GET | `/system/health` | 健康检查 | 规划 |
| system | GET | `/system/status` | 系统状态 | 规划 |
| system | GET | `/system/metrics` | 指标输出 | 规划 |
| session | POST | `/sessions` | 创建会话 | 规划 |
| session | GET | `/sessions/{session_id}` | 会话详情/历史 | 规划 |
| session | DELETE | `/sessions/{session_id}` | 结束会话 | 规划 |
| chat | POST | `/chat` | 对话入口（可选流式） | 规划 |
| emotion | POST | `/emotion/feedback` | 用户纠正情绪 | 规划 |
| memory | POST | `/memory/add` | 写入记忆/偏好 | 规划 |
| memory | POST | `/memory/search` | 语义检索 | 规划 |
| knowledge | POST | `/knowledge/entities` | 创建/更新实体 | 规划 |
| knowledge | POST | `/knowledge/relations` | 创建/更新关系 | 规划 |
| routing | GET | `/models/available` | 可用模型列表 | 规划 |
| routing | POST | `/routing/decide` | 路由决策 | 规划 |
| plugin | GET | `/plugins` | 插件列表 | 规划 |
| plugin | POST | `/plugins/install` | 安装插件 | 规划 |
| tools | POST | `/tools/execute` | 工具执行 | 规划 |

## 6. 示例（契约级示例）

### 6.1 创建会话

`POST /sessions`

请求体：
```json
{
  "user_id": "anonymous_hash_abc123",
  "initial_prompt": "你好，我是 Zikang"
}
```

响应（Envelope）：
```json
{
  "status": "success",
  "code": 200,
  "message": "Success",
  "timestamp": 1711161600.123,
  "data": {
    "session_id": "sess_001",
    "created_at": "2026-03-23T10:00:00+08:00"
  }
}
```

### 6.2 对话入口（非流式）

`POST /chat`

请求体：
```json
{
  "session_id": "sess_001",
  "message": "今天心情怎么样？",
  "mode": "normal",
  "stream": false
}
```

响应（示例）：
```json
{
  "status": "success",
  "code": 200,
  "message": "Success",
  "timestamp": 1711161600.123,
  "data": {
    "reply": "我感觉你今天有点疲惫，要不要聊聊最近的事？",
    "emotion": { "primary": "calm", "intensity": 0.45 },
    "proactive_triggered": false,
    "used_model": "qwen2.5-32b-q5_k_m"
  }
}
```

## 7. 错误与状态码建议

- 200：成功（`status=success` / `warning`）
- 400：输入无效（`status=fail`）
- 401：需要认证（`status=error`）
- 403：无权限（`status=error`）
- 404：资源不存在（`status=error`）
- 422：参数校验失败（`status=fail`）
- 429：限流（`status=error`）
- 500：服务器错误（`status=error`）

## 8. 变更与兼容

- 端点/字段变更必须在 `docs/api_reference/api_changelog.md` 追加记录。
- 建议遵循语义化版本（SemVer），并通过 `/api/v{major}` 路径体现破坏性变更。

## 9. 联调与实现要求（2026-03-30 补充）

后续联调时必须同时核对：

- `docs/technical_specifications/api_specification.md`
- `docs/technical_specifications/api_envelope_standard.md`
- `application/api_gateway/rest_api.py`
- `application/api_gateway/response_formatter.py`

如果文档、示例和真实返回不一致，应优先修正文档和实现口径，而不是让调用方长期兼容错误格式。
