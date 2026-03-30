---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "infrastructure/model_hub/,data/models/"
related_issues: ""
references: "docs/architecture/multi_model_routing.md"
---
# 模型集成指南

## 1. 目标

本文件说明如何把新的语言模型、多模态模型或云端增强模型接入 Mirexs 的模型注册、下载、管理和路由体系。

## 2. 当前相关代码入口

- `infrastructure/model_hub/model_configs.yaml`
- `infrastructure/model_hub/model_registry.py`
- `infrastructure/model_hub/model_downloader.py`
- `infrastructure/model_hub/model_manager.py`
- `infrastructure/model_hub/smart_model_router.py`

## 3. 集成前要确认的信息

- 模型用途：聊天、推理、编程、视觉或混合
- 模型格式：GGUF、Transformers、vLLM 或云端 API
- 资源要求：显存、内存、存储、上下文长度
- 部署方式：本地还是云端
- 风险级别：是否允许在受限场景下使用

## 4. 集成步骤

1. 准备模型权重或远程地址。
2. 规划模型存储路径，默认放在 `data/models/`。
3. 在 `model_configs.yaml` 中注册模型画像。
4. 校验字段完整性和路径可解析性。
5. 如有必要，补充下载地址和校验值。
6. 验证模型是否能进入路由候选集。
7. 补充对应测试和文档。

## 5. 注册字段建议

建议至少提供：

- `id`
- `family`
- `quant`
- `backend`
- `vram_est_gb`
- `ctx_len`
- `capability_tags`
- `modalities`
- `deployment`
- `path` 或 `url`

## 6. 示例

```yaml
- id: my-model-q4_k_m.gguf
  family: custom
  quant: q4_k_m
  backend: llama_cpp
  vram_est_gb: 8
  ctx_len: 32768
  capability_tags: ["chat", "reasoning"]
  modalities: ["text"]
  deployment: local
  path: data/models/nlp/gguf/my-model-q4_k_m.gguf
```

## 7. 路由影响

新增模型后，需要确认：

- 是否会被当前任务画像正确命中
- 是否会在低显存场景被错误选中
- 是否会影响 restricted 场景的本地优先约束
- 是否需要新增 secondary 或 fallback 策略

## 8. 验收标准

模型接入完成至少应满足：

- 注册文件能正确解析
- 模型路径可解析
- 能被路由器正确识别
- 对应资源要求和能力标签合理
- 文档和测试已同步更新
