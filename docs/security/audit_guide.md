
# Mirexs 审计指南（Audit Guide）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**适用范围**：Mirexs v2.0 系统所有审计日志（data/audit.db）、审计查询、导出、分析、事后审查  
**参考**：security_architecture.md、incident_response_plan.md、privacy_policy.md

## 1. 审计系统概述

Mirexs 的审计系统是**不可篡改、可追溯、安全三层防御**的核心组成部分。  
所有关键操作、决策、输入/输出、异常事件均强制生成审计记录，存储在本地加密数据库中。

**审计日志位置**：`data/audit.db`（SQLite + AES-256-GCM 加密）  
**不可篡改机制**：  
- 记录采用 append-only 模式（SQLite WAL + 文件权限只读）  
- 每条记录包含 SHA-256 hash（entry_id + timestamp + payload + prev_hash）  
- 链式校验：修改任何记录会导致后续所有 hash 失效  

## 2. 审计记录格式（AuditEntry - Pydantic 定义）

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Dict, Optional

class AuditEntry(BaseModel):
    entry_id: str = Field(..., description="UUID v4")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    user_hash: str = Field(..., description="匿名用户 hash")
    action_type: Literal[
        "session_create", "chat_input", "chat_output", "routing_decision",
        "emotion_detected", "emotion_feedback", "kg_update", "rl_transition",
        "proactive_trigger", "plugin_call", "security_alert", "data_export",
        "user_reset", "error", "incident_level_up"
    ]
    level: Literal["INFO", "WARN", "ERROR", "CRIT"] = "INFO"
    payload: Dict[str, Any] = Field(default_factory=dict)  # 脱敏数据
    status: Literal["success", "rejected", "quarantined", "failed"]
    reason: Optional[str] = None
    request_id: Optional[str] = None
    prev_hash: Optional[str] = None  # 链式 hash
    current_hash: str = Field(..., description="SHA256(entry_id + timestamp + payload + prev_hash)")
```

**示例记录（JSON 表示）**：
```json
{
  "entry_id": "uuid-1234-5678",
  "timestamp": "2026-03-17T14:30:00Z",
  "session_id": "sess_001",
  "user_hash": "sha256:abc...def",
  "action_type": "chat_input",
  "level": "INFO",
  "payload": {
    "message_length": 128,
    "detected_keywords": ["累", "聊聊"]
  },
  "status": "success",
  "reason": null,
  "request_id": "req_abc123",
  "current_hash": "sha256:xyz...789"
}
```

## 3. 审计记录生成规则（强制触发点）

| 触发时机                          | action_type 示例              | 记录内容关键字段                          | 级别默认 |
|-----------------------------------|-------------------------------|-------------------------------------------|----------|
| 新会话创建                        | session_create                | session_id, user_hash                     | INFO     |
| 用户输入接收（经过 sanitization） | chat_input                    | message_length, detected_emotion          | INFO     |
| 模型路由决策                      | routing_decision              | primary_model, estimated_latency_ms       | INFO     |
| 情绪检测/反馈                     | emotion_detected / feedback   | primary_emotion, intensity, corrected     | INFO     |
| 知识图谱更新                      | kg_update                     | entity_count, relation_added              | INFO     |
| 强化学习过渡                      | rl_transition                 | reward, td_error, action_id               | INFO     |
| 主动行为触发                      | proactive_trigger             | proposal_id, priority, estimated_reward   | INFO     |
| 插件工具调用                      | plugin_call                   | plugin_name, tool_name, params            | INFO     |
| 安全拒绝/隔离                     | security_alert                | reason, jailbreak_score, quarantined      | WARN/ERROR/CRIT |
| 用户数据导出/重置                 | data_export / user_reset      | export_type, reset_scope                  | INFO     |
| 系统错误/崩溃                     | error                         | error_code, stack_trace (脱敏)            | ERROR    |

**所有记录**均在 security/audit_logger.py 中统一生成。

## 4. 查询与分析指南

### 4.1 CLI 查询工具（推荐）

```bash
# 查看最近 100 条记录
python tools/audit_viewer.py --last 100

# 按 session_id 查询
python tools/audit_viewer.py --session sess_001 --level ERROR

# 导出指定时间范围
python tools/audit_viewer.py --export --start 2026-03-01 --end 2026-03-17 --format jsonl
```

### 4.2 SDK 查询方法

```python
from mirexs import MirexsClient

client = MirexsClient()
audit_logs = await client.query_audit(
    session_id="sess_001",
    level="ERROR",
    limit=50,
    start_time="2026-03-01T00:00:00Z"
)
for log in audit_logs:
    print(log.action_type, log.reason)
```

### 4.3 完整性校验

```bash
# 验证日志链是否完整（脚本示例）
python tools/audit_integrity_check.py
# 输出：All 12345 entries verified. No tampering detected.
```

## 5. 导出与备份规范

- **格式**：JSONL（每行一条 AuditEntry JSON）
- **脱敏规则**：
  - message 内容截断至前 200 字符 + "..."（隐私敏感）
  - user_hash 永不导出真实身份
  - payload 中敏感键（如 api_key）移除
- **导出命令**：`--export --anonymized`（默认匿名化）
- **备份建议**：定期复制 data/audit.db 到外部加密介质

## 6. 审计日志保留与清理

- **默认保留**：365 天（可配置）
- **自动清理**：超过保留期 + Level=INFO 的记录可安全删除（保留 Level WARN+）
- **手动清理**：用户重置时仅删除与个人数据相关的记录（session_id/user_hash 匹配）

## 7. 事后审查模板（用于 incident_reports/）

- 事件 ID：从 audit.db 查询
- 时间线：按 timestamp 排序
- 关键证据：提取相关 entry_id
- 根因分析：结合 reason、level
- 改进建议：更新 rules_engine 或阈值

## 8. 注意事项与限制

- 审计日志**不可手动编辑**（修改会导致 hash 链断裂，系统启动时校验失败）
- 加密密钥丢失将导致日志无法读取（密钥由用户管理）
- 审计系统本身受安全三层保护（Layer 2 运行时守卫）

本审计指南是 Mirexs **可追溯性与信任基础** 的核心文档。所有审计实现可在 security/audit_logger.py 与 data/audit.db schema 中验证。

**作者签名**：Zikang.Li  
**日期**：2026-03-17
