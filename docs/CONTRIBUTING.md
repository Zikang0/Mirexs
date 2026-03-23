# Mirexs 贡献指南（CONTRIBUTING）

**最后更新**：2026-03-23  
**适用范围**：本仓库所有代码与文档贡献

本文件用于补齐 README 中的入口链接，并给出最小可执行的贡献流程。更细的开发规范请参考：

- `docs/developer_guide/contribution_guide.md`
- `docs/developer_guide/code_review_process.md`
- `docs/developer_guide/coding_standards.md`
- `docs/developer_guide/testing_guide.md`

## 1. 贡献类型

- Bug 修复 / 兼容性修复
- 新能力模块（cognitive / capabilities / interaction / plugins 等）
- 性能优化与可观测性
- 文档修订（尤其是 docs/ 下的“契约与路径对齐”）
- 测试补齐（unit / integration）

## 2. 开发流程（推荐）

1. Fork 仓库并创建分支（建议以 `feature/`、`fix/`、`docs/` 前缀命名）
2. 保持改动聚焦：一个 PR 只做一件事（或一组强相关变更）
3. 修改代码时同步更新相关文档；修改契约/路径/配置名时必须同步更新：
   - `docs/technical_specifications/*`
   - `docs/api_reference/*`
   - `docs/architecture/*`（如涉及架构约束）
4. 运行对应测试（若仓库未具备可运行测试，请在 PR 中说明原因与替代验证方式）
5. 提交 PR：
   - 描述问题、解决方案、影响范围
   - 给出可复现步骤/验证方式
   - 标注是否包含破坏性变更（Breaking Change）

## 3. 文档贡献的强制要求

为保证文档严谨性，所有 docs 相关 PR 必须满足：

- 不引用不存在的文件/脚本/配置名；若为目标态，必须明确标注“规划”
- 同一主题的口径一致（尤其是 API base path、Envelope、配置路径）
- 新增/变更契约必须在 `docs/api_reference/api_changelog.md` 追加记录

