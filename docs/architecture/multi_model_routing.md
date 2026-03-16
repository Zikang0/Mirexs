# 多模型智能路由（Multi‑Model Routing）

**版本：v2.0.0**  
**最后更新：2026-03-16**  
**作者：Zikang.Li**  
**状态：可直接指导代码实现**

## 1. 目标与范围（量化版）

多模型智能路由是 Mirexs v2.0 的核心能力之一，目标是在**不同硬件、不同任务强度、不同上下文条件下**自动选择最合适的模型组合，保证：

- 日常对话“快且自然”（P95 延迟 ≤ 800ms）
- 复杂推理“准且可靠”（准确率提升 ≥ 25%）
- 低配设备（RTX 3060 12GB）可用，高配设备（RTX 4090 24GB+）充分发挥
- 模型切换对用户**完全无感知**（热切换延迟 ≤ 120ms）
- 系统可自动降级与回退，兼容**纯本地**与**可选云端增强**模型

**非功能需求（必须达标）**：

| 指标                     | 目标值 (P95)       | 验收环境                     | 备注                          |
|--------------------------|--------------------|------------------------------|-------------------------------|
| 路由决策耗时             | ≤ 45ms             | i7-12700H + RTX 3060 12GB   | 包含硬件探测 + 任务画像      |
| 模型冷启动延迟 (首次)    | ≤ 18s (Q5_K_M)     | 同上                         | GGUF 已预下载                |
| 热切换延迟               | ≤ 120ms            | 同上                         | vLLM ↔ llama.cpp             |
| VRAM 超配容忍度          | +15%               | —                            | 超过则强制 fallback          |
| 最低支持硬件             | 16GB RAM + 8GB VRAM| —                            | 强制降级至 8B 模型           |
| 回退成功率               | ≥ 99.8%            | 1000 次压力测试              | —                            |

## 2. 关键概念（精确定义）

- **任务画像（TaskProfile）**：对单次请求的结构化描述（类型、复杂度、模态、时效、安全）。
- **硬件画像（HardwareProfile）**：实时设备资源快照（VRAM、CPU、RAM、OS）。
- **模型画像（ModelProfile）**：每个模型的元数据、能力标签、资源消耗曲线。
- **路由决策（RoutingDecision）**：主模型 + 辅助模型 + 回退模型的三元组。
- **策略引擎（PolicyEngine）**：可配置的加权评分 + 硬约束规则。

## 3. 组件划分与接口契约（生产级）

```python
# infrastructure/model_hub/
├── hardware_profiler.py
├── task_profiler.py
├── model_registry.py
├── model_loader.py
├── routing_policy.py
├── smart_model_router.py   ← 核心入口
└── routing_decision.py
每个组件精确接口（Pydantic v2 + async）：
Pythonclass HardwareProfile(BaseModel):
    gpu_name: str
    vram_total_gb: float
    vram_free_gb: float
    cuda_version: str
    cpu_cores_logical: int
    ram_total_gb: float
    os: str
    is_apple_silicon: bool = False

class TaskProfile(BaseModel):
    task_id: str
    task_type: Literal["casual_chat", "emotional", "analytical", "coding", "creative", "multi_step", "vision", "realtime"]
    complexity: float = Field(ge=0.0, le=1.0)
    estimated_input_tokens: int
    estimated_output_tokens: int = 512
    modalities: List[Literal["text", "vision", "voice"]]
    requires_realtime: bool = False
    security_level: Literal["normal", "restricted"] = "normal"

class ModelProfile(BaseModel):
    model_id: str
    family: str
    quant: str
    vram_est_gb: float
    ctx_len: int
    tps_chat: float
    tps_reason: float
    capability_tags: List[str]
    backend: Literal["llama_cpp", "vllm", "transformers"]

class RoutingDecision(BaseModel):
    primary: ModelProfile
    secondary: Optional[ModelProfile] = None
    fallback: ModelProfile
    estimated_latency_ms: float
    estimated_vram_peak_gb: float
    decision_reasons: List[str]
    policy_version: str = "v2.0.1"
```

## 4. 路由流程（完整状态机 + 伪代码）
详细流程（8 步，每步异常处理）：

1. 输入解析
   解析 prompt + 历史 + 模态 → 构建 TaskProfile

   异常：输入过长 → 截断 + 警告

2. 任务画像构建（TaskProfiler）

   使用小型 DistilBERT 分类任务类型

   复杂度 = 0.4×token_length + 0.3×关键词权重 + 0.3×历史失败率

3. 硬件画像读取（HardwareProfiler，每 30s 缓存一次）

   ` nvidia-smi + psutil + torch.cuda `

4. 模型候选筛选（ModelRegistry）

   过滤：vram_free < vram_est × 1.15 或不支持模态

5. 评分与约束（RoutingPolicy）
   ```latex
    score = 0.40 \times latency + 0.35 \times quality + 0.15 \times vram_safety + 0.10 \times freshness
   ```
   硬约束：security_level == "restricted" → 禁用云端模型

6. 组合决策 → 生成 RoutingDecision

7. 模型生命周期管理（ModelLoader）

   状态机：Registered → Downloaded → Loaded → Warm → InUse → Evicted

   LRU + 权重保护（emotion 相关模型优先常驻）

8. 推理与反馈

   记录指标 → 更新模型画像 TPS 曲线


完整核心方法骨架（smart_model_router.py）：
```Python
async def route(self, task: TaskProfile) -> RoutingDecision:
    hw = await self.hardware_profiler.get_snapshot()
    candidates = self.registry.get_candidates(task, hw)
    scored = [(self.policy.score(m, task, hw), m) for m in candidates]
    primary = max(scored)[1]
    fallback = min(scored)[1] if len(scored) > 1 else primary
    decision = RoutingDecision(...)
    await self.loader.ensure_loaded(decision)
    return decision
```

## 5. 评分机制（完整公式 + 可配置权重）
```latex
score = w_1 \cdot capability + w_2 \cdot hardware_fit + w_3 \cdot latency + w_4 \cdot context_fit + w_5 \cdot reliability - w_6 \cdot cost
```

默认权重（policy.yaml）：
```YAML
weights:
  capability: 0.40
  hardware_fit: 0.25
  latency: 0.15
  context_fit: 0.10
  reliability: 0.10
```

## 6. 模型生命周期（状态机图描述 + 代码）

Evicted 条件：VRAM 压力 > 90% 或 30 分钟未使用

Warm 阶段：预跑 5 个 dummy prompt（ctx=512）


## 7. 回退策略（4 级优先级）

同家族低量化模型

8B 通用模型

规则引擎 fallback

最终降级到本地最小模型

## 8. 数据结构示例（JSON Schema）
TaskProfile 示例（已精确到字段）：
```JSON
{
  "task_id": "task_20260316_001",
  "task_type": "analytical",
  "complexity": 0.85,
  "estimated_input_tokens": 12400,
  "modalities": ["text"],
  "requires_realtime": true,
  "security_level": "restricted"
}
```
## 9. 典型场景示例（带决策路径）

日常聊天（复杂性 0.3）：Qwen2.5-32B-Q5 → 无 secondary

编程任务（复杂性 0.9）：DeepSeek-V3-Q4 → secondary: Qwen-Coder-32B

## 10. 配置文件示例（model_registry.yaml 完整版）
``` YAML
models:
  - id: qwen2.5-32b-instruct-q5_k_m.gguf
    family: qwen
    quant: q5_k_m
    vram_est_gb: 21.8
    ctx_len: 131072
    tps_chat: 58
    capability_tags: ["chat", "emotional", "long_ctx"]
    backend: llama_cpp
```
## 11. 指标与观测（Prometheus 格式）

` routing_decision_latency_ms `

` model_load_time_ms `

` fallback_rate（目标 < 2%） `

## 12. 测试验收标准（必须 100% 通过）

单元测试：10 个边缘 case（低 VRAM、超长 ctx、安全受限）

集成测试：1000 次随机任务，决策一致性 ≥ 99.5%

压力测试：RTX 3060 连续 8 小时无 OOM


本规范为契约优先文档，作为实现、代码审查、验收的统一依据。任何改动必须同步更新本文件。
