# 多模型智能路由（Multi‑Model Routing）

版本：v2.0
最后更新：2026-03-16

## 1. 目标与范围

多模型智能路由是 Mirexs v2.0 的核心能力之一，目标是在不同硬件、不同任务强度、不同上下文条件下自动选择最合适的模型组合，保证：

- 日常对话“快且自然”，复杂推理“准且可靠”。
- 低配设备可用，高配设备充分发挥。
- 模型切换对用户无感知，系统可自动降级与回退。
- 兼容本地模型与可选云端增强模型。

本规范定义路由系统的契约、策略、数据结构、配置与观测指标，作为实现与验收的共同依据。

## 2. 关键概念

- 任务画像（Task Profile）：对请求的结构化描述，包含任务类型、复杂度、长度、模态、时效性与安全等级。
- 硬件画像（Hardware Profile）：对设备资源的描述，包含 GPU 显存、CPU 核数、内存、磁盘与系统环境。
- 模型画像（Model Profile）：对模型能力、上下文长度、量化格式、资源需求与可靠性的描述。
- 路由决策（Routing Decision）：主模型 + 辅助模型 + 回退模型的组合输出。
- 策略引擎（Policy Engine）：根据规则与评分函数输出决策。

## 3. 组件划分

- `HardwareProfiler`：硬件检测与能力分级
- `TaskProfiler`：任务识别与复杂度评估
- `ModelRegistry`：模型元数据与能力标签
- `ModelLoader`：下载、加载、卸载与缓存
- `RoutingPolicy`：评分与约束规则
- `RoutingDecision`：最终决策结构
- `RoutingMetrics`：路由与切换指标

## 4. 路由流程（详细）

1. 输入解析
- 解析输入内容、模态类型、上下文长度。

2. 任务画像构建
- 任务类型：聊天、编程、分析、检索、创作、多模态。
- 复杂度：基于结构化输入长度、关键词、历史失败率。
- 时效性：是否需要实时检索。
- 安全等级：敏感/受限/普通。

3. 硬件画像读取
- GPU 显存、CPU 线程、内存、磁盘吞吐。

4. 模型候选筛选
- 过滤不满足硬件约束的模型。
- 过滤不支持模态的模型。

5. 评分与约束
- 对候选模型计算综合评分。
- 强约束：安全等级与云端使用策略。

6. 组合与决策
- 输出主模型、辅助模型、回退模型。

7. 模型生命周期管理
- 若模型未加载则触发下载/加载。
- 使用缓存策略避免频繁切换。

8. 推理与反馈
- 推理完成后记录延迟、失败、质量指标。

## 5. 评分机制

### 5.1 评分维度

- 能力匹配度（capability）
- 硬件可运行性（hardware_fit）
- 速度与延迟（latency）
- 上下文容量（context_fit）
- 可靠性（reliability）
- 成本预算（cost）

### 5.2 参考公式

```
score = w1*capability + w2*hardware_fit + w3*latency + w4*context_fit + w5*reliability - w6*cost
```

权重由策略配置提供，默认按“能力优先”。

## 6. 模型生命周期

- Registered：已注册
- Downloaded：已下载
- Loaded：已加载
- Warm：已热启动
- Evicted：被逐出（内存不足或优先级低）

默认缓存策略：
- LRU + 权重加成（高优先级模型不易被淘汰）。

## 7. 回退策略

- 加载失败：切换同类型低资源模型
- 推理超时：降低复杂度或切换低延迟模型
- 内存不足：强制降级并关闭非核心插件
- 质量下降：触发二次验证模型

## 8. 数据结构（契约）

### TaskProfile

```json
{
  "task_id": "task_20260316_001",
  "type": "analysis",
  "complexity": 0.72,
  "modalities": ["text"],
  "estimated_context_tokens": 4800,
  "requires_realtime": true,
  "security_level": "restricted"
}
```

### HardwareProfile

```json
{
  "gpu": {"name": "RTX 3060", "vram_gb": 12},
  "cpu": {"cores": 12, "threads": 20},
  "ram_gb": 32,
  "os": "Windows 11"
}
```

### RoutingDecision

```json
{
  "primary": "deepseek-v3-q4",
  "secondary": "qwen3-coder-32b-q5",
  "fallback": "llama3.1-8b-q4",
  "reason": ["complexity_high", "coding_task"],
  "policy_version": "v2.0.3"
}
```

## 9. 典型场景示例

- 日常聊天：Qwen 3.5 32B → Llama 3.1 8B（降级）
- 编程任务：DeepSeek V3 → Qwen3‑Coder（回退）
- 长文本分析：Llama 4 Maverick → Qwen3‑Next
- 多模态：Qwen3‑Omni → Llama 4 Scout

## 10. 配置文件示例

```yaml
models:
  - id: qwen3.5-32b-q5
    tags: [chat, reasoning]
    vram_requirement_gb: 20
    context_window: 128000
    latency_grade: A
    reliability: 0.98
policy:
  weights:
    capability: 0.35
    hardware_fit: 0.25
    latency: 0.15
    context_fit: 0.15
    reliability: 0.10
  thresholds:
    fallback_latency_ms: 3500
```

## 11. 指标与观测

- 路由延迟（routing_decision_latency_ms）
- 模型加载时间（model_load_time_ms）
- 回退率（fallback_rate）
- 失败率（model_failure_rate）
- GPU 压力（gpu_memory_pressure）

## 12. 测试验收标准

- 决策延迟 < 50ms
- 回退后 1s 内恢复可用
- 低配机器支持 8B 模型
- 高配机器可运行 70B 模型

---

本规范为契约优先文档，作为实现与验收的统一依据。
