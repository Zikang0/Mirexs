---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "cognitive/,capabilities/,tests/"
related_issues: ""
references: "docs/architecture/fact_checker.md,docs/api_reference/fact_checker_api.md"
---
# 事实核查器开发指南

## 1. 目标

事实核查器用于降低模型输出错误信息的风险。它不是单一模型，而是一条包含事实抽取、信源检索、多源对比、冲突仲裁和结果输出的处理链路。

## 2. 建议模块划分

- Source Manager：维护信源清单、优先级和可用性
- Claim Extractor：从输入中抽取可验证陈述
- Evidence Retriever：检索候选证据
- Validator：比较陈述与证据的一致性
- Conflict Resolver：处理相互矛盾的证据
- Reporter：输出最终结论、置信度和证据摘要

## 3. 研发时应优先保证的能力

- 能区分“事实陈述”和“观点表达”
- 能输出明确的核查状态
- 能返回证据来源而不是只给结论
- 在无法确认时返回“不确定”，而不是编造确定答案

## 4. 开发流程

### 4.1 增加新信源

1. 定义信源类型、可信等级和获取方式
2. 实现数据抓取或 API 适配
3. 标准化输出字段
4. 为该信源补充测试样例

### 4.2 优化核查逻辑

1. 明确要解决的是召回不足、冲突误判还是延迟过高
2. 修改验证或仲裁逻辑
3. 增加对应回归样本
4. 说明对误判率和延迟的影响

## 5. 结果状态建议

- `verified`：多源一致支持
- `false`：权威证据明确否定
- `uncertain`：证据冲突或不足
- `pending`：异步深度核查中

## 6. 安全与隐私要求

- 不把用户敏感数据直接发送到不可信第三方
- 对外部抓取失败要有回退逻辑
- 证据引用需要可追踪

## 7. 测试要求

- 单元测试覆盖事实抽取、证据标准化、冲突仲裁
- 集成测试覆盖多源核查链路
- 性能测试至少关注延迟和失败率
