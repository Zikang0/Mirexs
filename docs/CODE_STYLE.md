---
status: implemented
last_reviewed: 2026-03-30
corresponds_to_code: "全仓库"
related_issues: ""
references: "docs/developer_guide/coding_standards.md,docs/technical_specifications/api_specification.md"
---
# Mirexs 代码风格总则

## 1. 定位

本文件是根目录层面的代码风格入口，给出全仓库统一适用的最低要求。更具体的实现细则以 [coding_standards.md](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/coding_standards.md) 为准。

## 2. 全仓库最低要求

- Python 代码必须包含类型注解，尤其是跨模块函数、公共类和配置对象
- 每个模块必须有模块级 docstring，说明职责与边界
- 跨模块输入输出必须有稳定结构，禁止把无约束的 `dict` 作为长期公共契约
- I/O、网络、模型加载、数据库访问必须有清晰错误处理和日志
- 禁止硬编码敏感信息、绝对机器路径和不可说明来源的常量

## 3. 代码组织要求

- 一个文件只承载一组强相关职责，避免“超级模块”
- 公共能力优先放在基础设施层、数据层或能力层，避免 UI 或脚本层反向承载核心逻辑
- 新增目录时必须同步补充 `__init__.py`、文档入口和必要的导出说明

## 4. 契约要求

- 新增对外接口、事件、配置或持久化结构时，必须同步更新文档
- API 返回格式统一遵循 Envelope 规范
- 需要被其他模块复用的结构，应优先使用 `dataclass` 或 Pydantic 模型

## 5. 可维护性要求

- 不写“看起来能跑”的占位实现替代真实逻辑
- 对临时方案必须标注限制、回退路径和后续替换条件
- 注释只解释复杂原因、边界条件和设计取舍，不写显而易见的废话

## 6. 开发前应同步阅读

- [coding_standards.md](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/coding_standards.md)
- [code_review_process.md](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/code_review_process.md)
- [api_specification.md](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/api_specification.md)
- [api_envelope_standard.md](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/api_envelope_standard.md)
