
# REST API 参考文档

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang Li**  
**状态：契约优先规范，所有 REST API 实现、客户端调用、文档生成必须严格遵守本文件**

## 1. API 概述

Mirexs v2.0 提供一套 RESTful API，用于：

- 本地/远程客户端与核心引擎交互
- 第三方插件/应用集成
- Web UI、移动端、CLI 等前端调用
- 调试、监控、批量操作

**基地址**（默认本地）：
```
http://localhost:8765/api/v2
```

**所有端点均支持**：
- JSON 请求/响应
- Bearer Token 认证（可选，本地模式可禁用）
- CORS（跨域支持，默认开启）

## 2. 认证方式

| 类型          | 方式                  | 适用场景                     | 备注                              |
|---------------|-----------------------|------------------------------|-----------------------------------|
| 无认证        | 无                    | 本地开发、纯本地运行         | 默认推荐                          |
| API Key       | Header: X-API-Key     | 远程访问、插件               | 在 config.yaml 中配置             |
| Bearer Token  | Header: Authorization | 生产级、多用户场景           | JWT 或简单 token，未来扩展 OAuth |

## 3. 通用响应格式

成功响应：
```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-03-17T14:27:00Z",
    "processing_time_ms": 320
  }
}
```

错误响应：
```json
{
  "status": "error",
  "code": "INVALID_INPUT",
  "message": "Prompt too long, max 32000 tokens",
  "details": { ... },
  "request_id": "req_def456"
}
```

## 4. 核心端点清单

### 4.1 会话管理

**POST /sessions**  
创建新会话  
请求体：
```json
{
  "user_id": "anonymous_hash_abc123",
  "initial_prompt": "你好，我是 Zikang"
}
```
响应：`{ "session_id": "sess_001", "created_at": "..." }`

**GET /sessions/{session_id}**  
获取会话状态与历史

**DELETE /sessions/{session_id}**  
结束会话（清理临时内存）

### 4.2 对话交互（核心）

**POST /chat**  
发送消息并获取回复  
请求体：
```json
{
  "session_id": "sess_001",
  "message": "今天心情怎么样？",
  "mode": "normal",               // normal / proactive / debug
  "stream": true                  // 是否 SSE 流式返回
}
```
响应（非流式）：
```json
{
  "reply": "我感觉你今天有点疲惫，要不要聊聊最近的事？",
  "emotion": { "primary": "calm", "intensity": 0.45 },
  "proactive_triggered": false,
  "used_model": "qwen2.5-32b-q5_k_m"
}
```

**GET /chat/history/{session_id}**  
获取完整对话历史（分页支持）

### 4.3 情绪与记忆操作

**POST /emotion/feedback**  
用户手动纠正情绪  
请求体：
```json
{
  "session_id": "sess_001",
  "turn_id": 5,
  "corrected_emotion": "happy",
  "intensity": 0.85,
  "reason": "因为收到了礼物"
}
```

**POST /memory/add**  
手动添加知识到图谱  
请求体：
```json
{
  "entity_name": "吉他",
  "type": "OBJECT",
  "relation": {
    "target": "Zikang",
    "type": "LIKES",
    "strength": 0.92
  }
}
```

### 4.4 系统状态与配置

**GET /system/status**  
获取运行状态（模型加载、VRAM 使用、会话数等）

**POST /config/update**  
动态更新配置（需管理员权限）

**GET /models/available**  
列出当前可用模型及路由状态

## 5. 错误码表

| 代码               | HTTP 状态码 | 描述                              |
|--------------------|-------------|-----------------------------------|
| SUCCESS            | 200         | 成功                              |
| INVALID_INPUT      | 400         | 输入无效                          |
| AUTH_REQUIRED      | 401         | 需要认证                          |
| FORBIDDEN          | 403         | 无权限                            |
| NOT_FOUND          | 404         | 资源不存在                        |
| RATE_LIMIT         | 429         | 频率限制                          |
| INTERNAL_ERROR     | 500         | 服务器内部错误                    |
| MODEL_UNAVAILABLE  | 503         | 模型未加载或 OOM                  |

## 6. 版本控制与变更

- 当前版本：v2
- 向后兼容：v1 端点保留 6 个月后弃用
- 变更日志见：api_changelog.md

## 7. 安全约束

- 所有输入经过 security layer 过滤（参考 security_architecture.md）
- 敏感操作需二次确认（e.g. /memory/delete）
- 日志记录所有 API 调用（audit log）

本文件为 Mirexs REST API 的**唯一权威参考**，所有前端、插件、测试必须以此为准。任何端点变更需同步更新本文件并发布 changelog。

**作者签名**：Zikang Li  
**日期**：2026-03-17
