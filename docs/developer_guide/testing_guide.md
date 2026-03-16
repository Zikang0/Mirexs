# 测试指南（Testing Guide）

版本：v2.0
最后更新：2026-03-16

## 1. 测试范围

- 单元测试
- 集成测试
- 性能测试
- 安全测试

## 2. 运行方式

```
pytest tests/
```

## 3. 目录说明

- `tests/unit_tests/` 单元测试
- `tests/integration_tests/` 集成测试
- `tests/performance_tests/` 性能测试

## 4. 规范要求

- 新功能必须有测试
- 关键模块覆盖率 >= 80%

## 5. 性能测试

- 验证路由延迟与响应时间
- 压测核心 API

---

本文件为契约优先文档。
