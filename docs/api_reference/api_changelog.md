---
status: partial
last_reviewed: 2026-03-26
corresponds_to_code: "暂无"
related_issues: ""
references: docs/technical_specifications/api_envelope_standard.md
---
# Mirexs API 变更日志（API Changelog）

**API 版本**：v1  
**适用系统版本**：Mirexs v2.x  
**最后更新**：2026-03-23  
**作者**：Zikang Li  
**状态**：变更记录（用于追踪“契约/文档/实现”变化，避免口径漂移）

## 1. 本文件记录范围

本文件用于记录**对外 API 契约**的变更（新增/变更/弃用/移除/修复/安全），以及会影响调用方的关键行为变化。

不建议在此文件中填写“假设 commit hash / 未验证的版本宣称”。如需追溯具体提交，请使用 `git log` 查询并在条目中补充真实信息。

## 2. 当前基线口径（Baseline）

- 路由前缀（默认）：`/api/v1`（见 `config/system/service_configs/api_config.yaml`：`gateway.routing.prefix`）
- 通用响应 Envelope：`{status, code, message, timestamp, data?, meta?, errors?}`（见 `application/api_gateway/response_formatter.py`）
- 契约规范文档：`docs/technical_specifications/api_specification.md`
- 调用参考文档：`docs/api_reference/rest_api.md`

## 3. 维护规则（必须遵守）

每条变更记录应包含：

- **日期**：YYYY-MM-DD
- **版本**：vX.Y.Z（如暂无发布版本，可记录为 `unreleased`）
- **类型**：Added / Changed / Deprecated / Removed / Fixed / Security / Docs
- **影响范围**：端点/字段/认证方式/错误模型/限流策略等
- **迁移建议**：对调用方需要做什么
- **相关文档**：至少包含契约规范与参考文档的链接（文件路径）

## 4. 变更历史（倒序）

### 2026-03-23 - unreleased

- **类型**：Docs  
  **描述**：统一 API 契约与参考文档口径：基地址与版本前缀对齐为 `/api/v1`；通用响应 Envelope 对齐 `ResponseWrapper`；补充端点“实现状态”字段，避免将规划能力描述为已实现。  
  **影响范围**：`docs/technical_specifications/api_specification.md`、`docs/api_reference/rest_api.md`  
  **迁移建议**：无（仅文档口径修订；如你已按旧文档实现客户端，请以 `/api/v1` 与 Envelope 字段为准）

## 5. 记录模板（复制后填写）

### YYYY-MM-DD - vX.Y.Z

- **类型**：Added/Changed/Deprecated/Removed/Fixed/Security/Docs  
  **描述**：  
  **影响范围**：  
  **迁移建议**：  
  **相关端点**：  
  **相关文档**：  
  **作者**：  
