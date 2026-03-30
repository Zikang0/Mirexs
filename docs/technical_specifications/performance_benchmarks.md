---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "tests/performance_tests/,docs/architecture/"
related_issues: ""
references: "docs/technical_specifications/system_requirements.md"
---
# 性能基准规范

## 1. 目标

本文件定义 Mirexs 的关键性能指标、测试环境和验收方法，避免文档中只写“要快”，却没有可执行的测量标准。

## 2. 核心指标

- P50 / P95 延迟
- 吞吐量
- 错误率
- GPU 显存峰值
- CPU 与内存占用
- 冷启动与热启动时间

## 3. 重点场景

- 日常聊天
- 复杂推理
- 知识检索与图谱查询
- 多模型路由决策
- 多模态输入处理

## 4. 建议测试环境

### 4.1 推荐环境

- CPU：8 核以上
- 内存：32GB
- GPU：RTX 3060 12GB
- 存储：NVMe SSD

### 4.2 高性能环境

- CPU：16 核以上
- 内存：64GB
- GPU：RTX 4090 24GB
- 存储：高速 NVMe SSD

## 5. 指标目标建议

- 日常聊天：P95 不高于 1000ms
- 复杂推理：P95 控制在 3 到 5 秒区间
- 路由决策：P95 不高于 50ms
- 图谱查询：常见查询不高于 100ms

## 6. 测试要求

- 必须记录环境信息
- 必须说明模型规格和输入规模
- 必须区分冷启动和热路径
- 必须记录失败率和超时率

## 7. 验收标准

- 关键指标达到目标值或有明确偏差说明
- 失败率低于 1%
- 对比基线时说明变化原因
