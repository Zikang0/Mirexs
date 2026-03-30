---
status: implemented
last_reviewed: 2026-03-30
corresponds_to_code: "全仓库"
related_issues: ""
references: "docs/developer_guide/contribution_guide.md,docs/developer_guide/code_review_process.md,docs/developer_guide/testing_guide.md"
---
# Mirexs 贡献总指南

## 1. 文档定位

本文件说明贡献者进入仓库后的最小工作流程，包括提 Issue、提 PR、修改代码、补文档和完成验证。详细规则见子文档，但本文件定义的是“所有贡献都必须满足”的底线。

## 2. 可接受的贡献类型

- Bug 修复与回归修复
- 架构实现补齐与空壳模块落地
- 性能优化、稳定性增强、可观测性补齐
- 文档修订与代码口径对齐
- 测试用例补齐和测试基础设施完善
- 插件、适配器、模型接入和工具链增强

## 3. 不建议提交的改动

- 同一个 PR 同时混入多个无关主题
- 只改文档描述，不验证代码是否真实存在
- 以“TODO/占位”替代明确的实现或文档约束
- 没有说明影响范围的大规模重构

## 4. 推荐工作流程

1. 明确问题或目标。先确认是修复现有问题、补齐缺失实现，还是新增能力。
2. 阅读对应文档。至少阅读相关的架构文档、开发指南和技术规范。
3. 在本地完成最小可运行改动。不要在仓库中留下无法解释的半成品状态。
4. 同步更新文档。凡是修改路径、配置、接口、模型选择或安全策略，必须更新对应文档。
5. 完成验证。优先运行与改动直接相关的最小测试，再补充更大范围验证。
6. 提交变更说明。必须写清楚背景、方案、影响范围、验证方式和已知限制。

## 5. PR 内容要求

每个 PR 至少应说明：

- 解决的问题是什么
- 改了哪些模块
- 是否修改接口、配置、数据结构或默认行为
- 如何验证
- 是否存在已知风险或后续待办

如果涉及破坏性变更，还必须额外说明：

- 旧行为是什么
- 新行为是什么
- 调用方需要如何迁移

## 6. 文档同步要求

出现以下情况时，PR 中必须同步更新文档：

- 新增目录、模块、配置文件或环境变量
- 修改 API 路径、参数、返回结构或错误模型
- 变更默认模型、推理策略、部署方式
- 变更安全、合规或隐私处理策略
- 修改用户可见的功能流程

最低同步范围：

- 技术契约：`docs/technical_specifications/`
- 接口参考：`docs/api_reference/`
- 架构说明：`docs/architecture/`
- 开发指南：`docs/developer_guide/`

## 7. 评审前自检清单

- 引用的代码路径是否真实存在
- 修改后的文档是否与 README、requirements 和配置文件一致
- 是否为新增功能提供了合理的验证方式
- 是否说明了当前限制和未完成部分
- 是否影响其他模块的边界或默认行为

## 8. 提交建议

- 分支命名建议：`feature/...`、`fix/...`、`docs/...`、`refactor/...`
- Commit 建议使用 Conventional Commits
- 一次提交只表达一个明确意图，避免把格式化、重构和功能变更混在一起

## 9. 相关文档

- [贡献指南](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/contribution_guide.md)
- [代码评审流程](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/code_review_process.md)
- [编码规范](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/coding_standards.md)
- [测试指南](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/testing_guide.md)
