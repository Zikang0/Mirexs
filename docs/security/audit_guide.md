# 审计日志指南（Audit Guide）

版本：v2.0
最后更新：2026-03-16

## 1. 目标

审计日志用于安全合规、事件追溯与责任界定。Mirexs 采用“不可篡改审计链”机制，保证日志可信度。

## 2. 日志结构

```json
{
  "id": "audit_001",
  "timestamp": "2026-03-16T10:00:00+08:00",
  "user_id": "user_001",
  "event_type": "MODEL_SWITCH",
  "severity": "INFO",
  "details": {
    "from": "qwen3.5-32b",
    "to": "deepseek-v3"
  },
  "prev_hash": "...",
  "hash": "..."
}
```

## 3. 审计链机制

- 每条日志包含 `prev_hash` 与 `hash`。
- `hash = SHA256(prev_hash + payload)`。
- 任何篡改都会导致链断裂。

## 4. 日志保留策略

- 高风险事件：永久保留
- 普通事件：默认 365 天
- 可配置为企业合规要求

## 5. 访问控制

- 仅管理员可查看完整日志
- 用户可查看自身相关记录

## 6. 审计事件类型（示例）

- SYSTEM_START
- USER_LOGIN
- MODEL_SWITCH
- DATA_EXPORT
- INCIDENT_RESPONSE

---

本指南为契约优先文档，作为安全实现与验收依据。
