# 多模型智能路由（Multi‑Model Routing）

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**状态：契约优先设计规范（代码落地进行中；仓库目录存在但部分文件为占位）**

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

## 3. 组件划分与接口契约（设计规范）

### 3.1 当前仓库目录（2026-03-23）

```text
infrastructure/model_hub/
  __init__.py
  hardware_profile.py        # 占位：待实现硬件探测/快照
  model_registry.py          # 占位：待实现模型注册/候选筛选
  model_manager.py           # 占位：待实现加载/卸载/LRU 与资源管理
  model_downloader.py        # 占位：待实现下载/校验/缓存
  model_configs.yaml         # 占位：待补齐模型清单与资源估算
```

> 说明：上表为“现状目录”；本文定义的是“目标契约”。落地实现时必须遵循 `architecture/overview.md` 的边界层约束（Schema、错误模型、审计等）。

### 3.2 目标模块拆分（建议）

```text
infrastructure/model_hub/
  hardware_profiler.py
  task_profiler.py
  model_registry.py
  model_loader.py
  routing_policy.py
  smart_model_router.py      # 核心入口（route）
  routing_decision.py
```

### 3.3 数据模型（边界层 Schema，推荐 Pydantic v2）

```python
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class HardwareProfile(BaseModel):
    gpu_name: str
    vram_total_gb: float
    vram_free_gb: float
    cuda_version: Optional[str] = None
    cpu_cores_logical: int
    ram_total_gb: float
    os: str
    is_apple_silicon: bool = False


class TaskProfile(BaseModel):
    task_id: str
    task_type: Literal[
        "casual_chat",
        "emotional",
        "analytical",
        "coding",
        "creative",
        "multi_step",
        "vision",
        "realtime",
    ]
    complexity: float = Field(ge=0.0, le=1.0, default=0.5)
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 512
    modalities: list[Literal["text", "vision", "voice"]] = ["text"]
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
    capability_tags: list[str] = []
    backend: Literal["llama_cpp", "vllm", "transformers"]


class RoutingDecision(BaseModel):
    primary: ModelProfile
    secondary: Optional[ModelProfile] = None
    fallback: ModelProfile
    estimated_latency_ms: float
    estimated_vram_peak_gb: float
    decision_reasons: list[str] = []
    policy_version: str = "v2.0.1"
```

## 4. 路由流程（完整状态机 + 伪代码）
详细流程（8 步，每步异常处理）：

1. 输入解析
   解析 prompt + 历史 + 模态 → 构建 TaskProfile

   异常：输入过长 → 截断 + 警告

2. 任务画像构建（TaskProfiler）

   任务类型判定可选实现：
   - 规则/关键词启发式（MVP 方案，成本低、易控）
   - 轻量分类器（例如 DistilBERT/miniLM 微调，用于提升泛化能力）

   复杂度（示例公式，可替换）：`0.4×token_length + 0.3×关键词权重 + 0.3×历史失败率`

3. 硬件画像读取（HardwareProfiler，每 30s 缓存一次）

   建议按平台选择实现：
   - NVIDIA：`nvidia-smi` + `torch.cuda`
   - CPU/RAM：`psutil`
   - 其他平台（如 macOS）：提供降级路径（跳过 GPU 探测或用系统 API）

4. 模型候选筛选（ModelRegistry）

   过滤：vram_free < vram_est × 1.15 或不支持模态

5. 评分与约束（RoutingPolicy）

   评分必须先做 **归一化**，保证“数值越大越好”，避免单位混用（ms/GB/QPS）导致逻辑错误。示例：

   ```latex
   latency\_score = 1 - \mathrm{clip}\left(\frac{latency\_{ms}}{budget\_{ms}}, 0, 1\right)
   vram\_safety = \mathrm{clip}\left(\frac{vram\_{free} - vram\_{est}}{vram\_{free}}, 0, 1\right)
   score = 0.40 \times latency\_score + 0.35 \times quality\_score + 0.15 \times vram\_safety + 0.10 \times freshness\_score
   ```

   硬约束：`security_level == "restricted"` → 禁用云端模型（只允许本地后端）

6. 组合决策 → 生成 RoutingDecision

7. 模型生命周期管理（ModelLoader）

   状态机：Registered → Downloaded → Loaded → Warm → InUse → Evicted

   LRU + 权重保护（emotion 相关模型优先常驻）

8. 推理与反馈

   记录指标 → 更新模型画像 TPS 曲线


完整核心方法骨架（smart_model_router.py）：
```python
async def route(self, task: TaskProfile) -> RoutingDecision:
    hw = await self.hardware_profiler.get_snapshot()
    candidates = self.registry.get_candidates(task, hw)
    scored = [(self.policy.score(m, task, hw), m) for m in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)
    primary = scored[0][1]
    fallback = scored[1][1] if len(scored) > 1 else primary
    decision = RoutingDecision(...)
    await self.loader.ensure_loaded(decision)
    return decision
```

## 5. 评分机制（完整公式 + 可配置权重）
```latex
score = w_1 \cdot capability + w_2 \cdot hardware_fit + w_3 \cdot latency + w_4 \cdot context_fit + w_5 \cdot reliability - w_6 \cdot cost
```

默认权重（policy.yaml）：
```yaml
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
```json
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
```yaml
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

`routing_decision_latency_ms`

`model_load_time_ms`

`fallback_rate`（目标 < 2%）

## 12. 测试验收标准（必须 100% 通过）

单元测试：10 个边缘 case（低 VRAM、超长 ctx、安全受限）

集成测试：1000 次随机任务，决策一致性 ≥ 99.5%

压力测试：RTX 3060 连续 8 小时无 OOM


本规范为契约优先文档，作为实现、代码审查、验收的统一依据。任何改动必须同步更新本文件。
