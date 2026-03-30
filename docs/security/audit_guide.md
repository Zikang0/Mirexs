# Mirexs 审计指南（Audit Guide）

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**适用范围**：Mirexs v2.0 系统审计日志（默认目录 `data/security/audit/`）、审计查询、导出、分析、事后审查  
**参考**：`docs/architecture/security_architecture.md`、`docs/security/incident_response_plan.md`、`docs/security/privacy_policy.md`

## 0. 实现对齐摘要（2026-03-23）

- **审计实现入口（可核验）**：`security/security_monitoring/audit_logger.py`（`AuditLogger` / `get_audit_logger()`）
- **默认存储口径（可核验）**：`data/security/audit/`（`audit_chain.json`、`audit_index.json`、`audit_archive_*.json`）
- **关键能力（可核验）**：`log_event()`、`query()`、`verify_chain()`、`export_chain()`
- **注意**：`security/audit/*` 在仓库中为占位骨架；审计“运行实现”以 `security/security_monitoring/` 为准

## 1. 审计系统概述

Mirexs 的审计系统目标是提供**可追溯、可验证完整性、可导出**的本地审计链，用于：

- 安全事件回溯（jailbreak、越权、异常插件行为等）
- 关键决策解释（路由决策、写入长期记忆、权限拒绝原因）
- 合规与用户权利支持（导出、删除、授权记录）

**审计日志默认位置**：`data/security/audit/`  
**完整性机制（防篡改可检测）**：

- append-only 审计链（每条记录包含 `previous_hash` → `entry_hash`）
- 可选签名（默认启用，配置键：`enable_signing`，签名密钥：`audit_signing_key`）

> 机密性（加密）与完整性（防篡改）不同：当前实现重点在“可检测篡改”。如需对审计内容加密存储，应在落盘层引入 `security/privacy_protection/data_encryption.py` 的加密封装并配套密钥管理（需要额外实现与验收）。

## 2. 审计记录格式（AuditEntry - 概念字段）

> 实现中的数据结构请以 `security/security_monitoring/audit_logger.py` 为准；下述为便于理解的字段口径。

```json
{
  "entry_id": "audit_...",
  "timestamp": 1710000000.123,
  "event_type": "system_start",
  "severity": "INFO",
  "user_id": "sha256:...",
  "source_ip": "127.0.0.1",
  "resource": "api_gateway",
  "action": "request_received",
  "status": "success",
  "details": {},
  "previous_hash": "...",
  "entry_hash": "...",
  "signature": "..."
}
```

## 3. 审计记录生成规则（强制触发点）

审计记录应覆盖“安全与数据边界”相关关键动作，建议包含但不限于：

- 身份认证/授权（成功/失败、API key/JWT、权限拒绝）
- 关键数据写入（KG 更新、向量索引更新、用户偏好变更）
- 联网行为（如启用实时知识接入：来源、URL、摘要、写入策略）
- 安全拦截（输入过滤、越权、可疑插件行为、隔离/进入 safe mode）
- 数据导出/删除/重置（范围、时间、操作者、结果）

实现入口：`security/security_monitoring/audit_logger.py` 的 `AuditLogger.log_event(...)`。

## 4. 查询与分析指南

### 4.1 通过 AuditLogger API 查询（仓库可核验）

```python
from security.security_monitoring.audit_logger import get_audit_logger

audit = get_audit_logger()

# 最近记录（query 主要查询 recent_entries 缓存）
recent = audit.query(limit=100)

# 完整性验证（审计链哈希/签名校验）
ok = audit.verify_chain()

# 导出
audit.export_chain("audit_export.json")
```

> 若需要更复杂的查询（跨归档文件、全链检索），建议在产品侧提供 CLI/UI 并将归档索引纳入查询路径。

### 4.2 完整性校验输出解释

- `verify_chain() == True`：链结构与签名校验通过（不等于“内容真实性”，只表示“未检测到篡改”）
- `verify_chain() == False`：链断裂/哈希不一致/签名校验失败，应按事件响应流程处理（隔离、保全证据、导出链文件）

## 5. 导出与备份规范

- **导出格式**：当前实现为 JSON（数组）；如需 JSONL，可在导出后转换
- **脱敏建议**：默认只记录最小必要字段；对 `details` 做 PII/密钥等敏感字段剥离
- **备份建议**：定期复制 `data/security/audit/` 到外部加密介质；同时备份配置快照（`config/`）

## 6. 审计日志保留与清理

实现中提供归档与链长度控制（默认配置键）：

- `archive_threshold`：达到阈值时归档旧记录到 `audit_archive_*.json`
- `max_chain_size`：超过最大链长度时保留最近记录

清理原则：

- 禁止“编辑”审计链文件；如需清理应通过归档/保留策略实现可解释的删除
- 清理动作本身应写入审计（记录清理范围与原因）

## 7. 事后审查模板（用于 incident_reports/）

- 事件时间线：从导出文件按 `timestamp` 排序
- 关键证据：`entry_id` + `entry_hash`（必要时附 `signature`）
- 触发路径：resource/action/details
- 根因分析：结合安全策略与模块日志
- 改进项：规则更新、阈值调整、权限收敛、补齐测试

## 8. 注意事项与限制

- 审计链强调“防篡改可检测”；机密性与访问控制需通过独立机制实现（权限管理 + 可选加密）
- 签名密钥管理与轮换策略需与 `security/access_control/key_management.py` 对齐
- 本指南为契约优先文档：任何审计落盘格式、字段含义或保留策略变更需同步更新本文件

## 9. 开发落地要求（2026-03-30 补充）

后续开发审计能力时，必须同时验证：

- 审计是否覆盖关键操作
- 导出格式是否稳定
- 校验链是否可重放验证
- 删除或裁剪策略是否符合隐私与合规要求

**作者签名**：Zikang Li  
**日期**：2026-03-23
