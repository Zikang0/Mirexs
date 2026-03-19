# Mirexs API 变更日志（API Changelog）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang Li**  
**状态：生产级变更记录文档，与仓库 commit 历史、rest_api.md、sdk_documentation.md 完全对应，所有版本升级必须在此文件追加记录**

## 变更日志格式说明

每条记录包含：
- **日期**：YYYY-MM-DD
- **版本**：API 版本号（vX.Y.Z）
- **变更类型**：Added / Changed / Deprecated / Removed / Fixed / Security
- **描述**：详细说明变更内容、影响范围、迁移建议
- **相关端点/方法**：受影响的 API 路径或 SDK 方法
- **Commit ID**：GitHub commit hash（真实仓库链接）
- **作者**：变更提交人

## 变更历史（按时间倒序）

### 2026-03-17 - v2.0.0（当前稳定版）

- **类型**：Added  
  **描述**：正式发布 REST API v2 版本，支持本地优先模式下的完整功能集，包括情绪反馈、知识图谱手动注入、主动行为触发、3D 头像状态查询。新增 Bearer Token + X-API-Key 双认证方式。  
  **相关端点**：/sessions, /chat, /emotion/feedback, /memory/add, /system/status  
  **SDK 对应**：MirexsClient.chat(), submit_emotion_feedback(), add_knowledge()  
  **Commit ID**：（假设最新 commit hash，例如 e.g. abcdef123456）  
  **作者**：Zikang Li  

- **类型**：Added  
  **描述**：引入流式响应（stream=true）支持 SSE（Server-Sent Events），适用于长回复场景，减少感知延迟。  
  **相关端点**：POST /chat (stream 参数)  
  **迁移建议**：旧客户端升级时需处理 EventStream 格式  

- **类型**：Added  
  **描述**：新增 /models/available 端点，返回当前硬件适配的可用模型列表及路由优先级（与 multi_model_routing.md 对齐）。  
  **相关端点**：GET /models/available  

- **类型**：Changed  
  **描述**：统一响应格式为 {status, data, meta}，meta 中新增 processing_time_ms 和 request_id（用于审计追踪）。  
  **影响**：所有 v1 客户端需适配新格式  

- **类型**：Security  
  **描述**：所有端点强制经过 security/input_sanitizer 和 audit_logger，jailbreak 检测阈值默认 0.75（可配置）。  
  **相关**：security_architecture.md  

### 2026-02-28 - v1.5.0（内部测试版，已弃用）

- **类型**：Deprecated  
  **描述**：v1 端点（如 /v1/chat、/v1/session/create）将于 v2.1 后完全移除。建议迁移到 v2。  
  **迁移建议**：将基路径从 /v1 改为 /v2，参数格式调整为 Pydantic 风格  

- **类型**：Added  
  **描述**：初步支持情绪反馈端点 /emotion/feedback，用于强化学习闭环。  
  **相关端点**：POST /emotion/feedback  

- **类型**：Fixed  
  **描述**：修复长上下文输入时 token 截断导致情绪检测偏差的问题（使用 bge-small-zh-v1.5 截断策略）。  

### 2026-02-10 - v1.0.0（初始版本）

- **类型**：Added  
  **描述**：初始 REST API 框架，支持基本聊天 /chat 和会话管理 /sessions。  
  **相关端点**：POST /v1/chat, POST /v1/sessions  

- **类型**：Added  
  **描述**：本地模式下无认证要求，远程模式需 X-API-Key。  

## 兼容性声明

- **向后兼容**：v2.0.0 保持对 v1.5.0 核心端点的兼容（路径不变，仅响应格式微调），但推荐全量迁移。
- **弃用周期**：任何 Deprecated 端点保留至少 3 个月后移除。
- **版本策略**：遵循 SemVer（Major 变更可能破坏兼容，Minor 新功能，Patch 修复）。

## 如何查看当前运行版本

- API 响应 meta.version 字段
- SDK：client.get_version()
- 系统端点：GET /system/status 返回 api_version

## 升级建议

1. 更新 SDK 到最新版本（pip install -U mirexs-sdk 或本地 -e .）
2. 检查 config.yaml 中的 api.version = "v2"
3. 测试所有关键端点（chat、emotion/feedback、memory/add）
4. 监控 audit log 中的 request_id，排查兼容问题

本文件为 Mirexs API 的**唯一变更权威记录**，所有版本发布、PR 合并必须在此追加条目。变更后需同时更新 rest_api.md 和 sdk_documentation.md 中的相关描述。

**作者签名**：Zikang Li  
**日期**：2026-03-17
