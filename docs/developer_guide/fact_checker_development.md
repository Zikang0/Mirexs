# 事实核查器开发指南 (Fact Checker Development)

## 1. 目标 (Goal)

本指南旨在指导开发者如何参与 Mirexs 事实核查器（Fact Checker）的开发、优化和信源扩展。

## 2. 核心组件 (Core Components)

*   **Source Manager**: 管理信源列表和权重。
*   **Extraction Engine**: 从非结构化文本中提取事实陈述。
*   **Validation Engine**: 执行多源交叉验证逻辑。
*   **Conflict Resolver**: 处理不同信源之间的冲突。

## 3. 开发流程 (Development Workflow)

### 3.1 增加新信源 (Adding a New Source)

1.  在 `infrastructure/fact_checker/sources/` 目录下创建一个新的信源配置文件（如 `reuters.yaml`）。
2.  定义信源的元数据：名称、URL、类别、默认权重。
3.  实现信源解析器（Parser），用于从该信源的 API 或网页中提取结构化事实。

### 3.2 优化验证逻辑 (Optimizing Validation Logic)

1.  修改 `cognitive/fact_checker/validation_engine.py` 中的 `cross_validate` 函数。
2.  引入新的语义相似度算法或置信度计算模型。
3.  在 `tests/fact_checker/` 中添加测试用例，确保新逻辑的准确性。

### 3.3 冲突解决策略 (Conflict Resolution)

1.  在 `cognitive/fact_checker/conflict_resolver.py` 中定义新的仲裁规则。
2.  支持基于时效性、信源权重或多数原则的冲突解决。

## 4. 测试与评估 (Testing & Evaluation)

*   **单元测试**: 针对每个解析器和验证逻辑编写单元测试。
*   **准确率评估**: 使用 FEVER 等公开数据集或自建数据集进行端到端准确率评估。
*   **性能监控**: 监控核查请求的延迟和信源响应时间。

## 5. 最佳实践 (Best Practices)

*   **优先考虑权威信源**：官方机构、学术期刊、主流新闻媒体。
*   **处理不确定性**：当无法得出确定结论时，应返回“待核查”状态并提供相关证据。
*   **保护隐私**：在核查过程中，避免将用户的敏感隐私信息发送给不可信的第三方信源。

---
**作者**: Zikang Li
**日期**: 2026-03-18
**版本**: v2.0.0
