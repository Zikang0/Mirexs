# 强化学习模块（Reinforcement Learner）架构规范

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**状态：契约优先规范（实现已存在；需由上层提供环境与奖励信号）**

> 本文档依赖并遵守 `architecture/overview.md` v2.0.1 中的分层与约束。

## 1. 实现对齐摘要（2026-03-23）

本仓库的强化学习实现入口为：

- `cognitive/learning/reinforcement_learner.py`：`ReinforcementLearner`（支持 `dqn` / `policy_gradient` / `actor_critic`）

文档以该实现为基线进行说明；如后续算法/参数发生变化，必须同步更新本文件。

## 2. 目标与定位

强化学习模块用于在“用户反馈/长期交互”场景下优化策略选择，例如：

- 回复风格/行为策略的偏好适配
- 主动行为触发阈值与动作选择
- 多方案决策的探索‑利用平衡

模块是 **环境无关** 的：上层必须提供状态表示（state）、动作空间（action）、奖励函数（reward）与交互环境（env）。

## 3. 核心数据流（闭环）

典型闭环如下：

1. 上层构造 `state: np.ndarray`（长度 = `state_dim`）
2. RL 选择动作：`action = select_action(state)`
3. 上层执行动作并得到反馈：`next_state, reward, done = env.step(action)`
4. 存储经验：`store_experience(state, action, reward, next_state, done)`
5. 训练更新：`loss = update_model()`（按 batch 抽样更新）
6. 持久化与观测：`save_models()` / `get_training_status()` / `get_learning_curves()`

## 4. 算法支持与选择

`initialize_environment(state_dim, action_dim, algorithm="dqn")` 支持三类算法：

- `dqn`：默认推荐；实现为 **Dueling DQN**（`DQNNetwork` + target network + replay buffer）
- `policy_gradient`：策略梯度（`PolicyNetwork` 输出动作分布）
- `actor_critic`：Actor‑Critic（`PolicyNetwork` 同时输出 policy 与 value）

选择建议：

- 动作空间离散且可枚举：优先 `dqn`
- 需要显式策略分布（或更平滑探索）：考虑 `policy_gradient/actor_critic`

## 5. 状态、动作与奖励（契约约束）

### 5.1 状态（State）

- 类型：`np.ndarray`
- 维度：`state_dim`（由上层定义并在 `initialize_environment` 中传入）
- 约束：必须是可数值化、可归一化的特征向量

建议的特征来源（示例，不强制）：

- 最近 N 轮情绪强度统计（mean/max/trend）
- 用户活跃度、会话时长、交互频率
- 关系强度（来自知识图谱/记忆）
- 上一次动作成功率/用户反馈

### 5.2 动作（Action）

- 类型：离散动作 `int`，范围 `[0, action_dim)`
- 上层需维护“动作 ID → 真实行为”的映射（例如生成策略选择/主动行为类型等）

### 5.3 奖励（Reward）

- 类型：`float`
- 建议范围：`[-1, 1]` 或经归一化的有界范围，便于训练稳定
- 安全约束：必须引入对高风险/越权动作的负奖励或硬约束（参见 `architecture/security_architecture.md`）

## 6. 训练参数与持久化

实现内置 `learning_config`（可通过 `update_learning_config` 更新），关键项包括：

- `gamma`（折扣因子）、`lr`（学习率）、`batch_size`
- `epsilon_start/epsilon_end/epsilon_decay`（探索策略）
- `target_update`（目标网络更新步频）
- `memory_size`（经验回放容量）、`warmup_steps`

持久化目录（默认）：`data/reinforcement_learning/`

主要文件：

- `learning_config.json`：训练配置
- `learning_history.json`：学习历史
- `rl_models.pth`：模型权重（若已初始化并训练）

日志：

- `logs/reinforcement_learning.log`（由实现写入；部署时需确保 `logs/` 可写）

## 7. 可观测性与调试

实现提供的观测接口：

- `get_training_status()`：训练步数、epsilon、经验池大小、最近奖励均值等
- `get_learning_curves()`：reward/episode 长度与移动平均
- `get_policy_analysis(state)`：给定状态下的动作概率/置信度/熵等（用于解释与调参）

## 8. 已知差异与待补齐项

- 当前仓库缺少与“真实用户反馈/安全策略/业务动作映射”的端到端集成示例；需要在上层模块补齐 env 与 reward 计算。
- 测试用例需补齐（建议覆盖：epsilon 衰减、目标网络更新、replay buffer 行为、不同算法分支等）。

本规范用于约束 RL 模块的接口与行为边界；任何算法变更或持久化格式变更必须同步更新本文档并在 ADR/变更记录中说明。

**作者签名**：Zikang Li  
**日期**：2026-03-23
