# 模型集成指南（Model Integration）

版本：v2.0
最后更新：2026-03-16

## 1. 目标

指导开发者将新模型接入 Mirexs 的模型管理与路由体系。

## 2. 集成步骤

1. 下载模型权重并保存至 `data/models/` 或 `models/gguf/`
2. 在 `infrastructure/model_hub/model_configs.yaml` 中注册
3. 配置量化格式与上下文窗口
4. 更新路由策略权重
5. 运行模型兼容性测试

## 3. 注册示例

```yaml
- id: my-model-q4
  tags: [chat, reasoning]
  vram_requirement_gb: 8
  context_window: 32000
```

---

本文件为契约优先文档。
