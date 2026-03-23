# Mirexs 代码规范入口（CODE_STYLE）

**最后更新**：2026-03-23

本文件用于补齐 README 中的入口链接。代码规范的权威来源为：

- `docs/developer_guide/coding_standards.md`

建议同时遵循的工程约束：

- 新增对外接口/跨模块 Payload 时，必须提供稳定 Schema，并在边界层统一错误模型（参见 `docs/technical_specifications/api_specification.md`）。
- 任何新增能力模块必须包含可观测性：必要日志、关键指标或最小调试入口。

