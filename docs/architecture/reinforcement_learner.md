
# 强化学习模块（Reinforcement Learner）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**状态：契约优先规范，可直接指导 Q-learning 实现、奖励函数设计、状态/动作空间定义、训练闭环与集成**

## 1. 目标与核心价值（量化指标）

强化学习模块是 Mirexs v2.0 中实现“行为自主进化”的核心引擎，让数字生命体能够：

- 从用户显式/隐式反馈中学习“什么行为更受欢迎”
- 逐步优化主动发起对话、情绪表达方式、话题选择、3D 头像动作等
- 在不依赖海量标注数据的情况下，实现个性化长期进步
- 避免灾难性遗忘（catastrophic forgetting），保持早期学到的基本礼貌与安全边界

**关键量化目标**：

| 指标                           | 目标值                        | 验收环境                       | 备注                                   |
|--------------------------------|-------------------------------|--------------------------------|----------------------------------------|
| 累计奖励提升（1000 轮后）      | ≥ +25%（相对于随机策略）      | 模拟用户 + 真实交互            | 使用 offline replay buffer 评估       |
| 探索-利用平衡（ε-greedy）      | ε 从 0.5 衰减到 0.05（10k 步）| —                              | 可配置衰减策略                         |
| 单次决策延迟                   | ≤ 120 ms                      | RTX 3060                       | Q-table 或 Q-network 前向              |
| 模型大小（Q-table / 小网络）   | ≤ 50 MB                       | —                              | 支持 SQLite 持久化                     |
| 灾难性遗忘防护（F1 下降）      | ≤ 5%（在旧任务上）            | 回放测试集                     | 使用经验回放 + 重要性采样              |

## 2. 强化学习范式选择与理由

- **算法**：表格型 Q-learning（初期） + 小型 DQN（后续可选升级）
  - 理由：状态/动作空间可控（初期 < 10k 状态），计算资源友好，本地运行无压力
- **类型**：Off-policy + Experience Replay
- **更新方式**：在线增量更新（每轮对话后 batch 更新） + 周期性批量重放
- **探索策略**：ε-greedy（线性衰减） + Boltzmann 探索（可选）

## 3. 状态空间（State Space）定义

状态是当前上下文的高度抽象表示（Pydantic 实现）：

```python
class RLState(BaseModel):
    session_id: str
    turn_count: int                        # 当前对话轮次
    dominant_emotion: str                  # 来自 emotion_nn 的 primary_emotion
    emotion_intensity: float               # 0.0~1.0
    recent_user_sentiment: float           # -1.0（负面）~ +1.0（正面）
    topic_cluster: str                     # 当前话题类别（从 kg 或 embedding 聚类）
    relationship_strength: float           # 与当前用户的关系亲密度（从 kg）
    time_of_day: int                       # 0~23 小时
    user_activity_level: float             # 近期回复频率（0~1）
    last_action_success: float             # 上一次行为的奖励（-1~+1）
    embedding: Optional[List[float]] = None  # 384维上下文 embedding（可选加速）
```

**状态离散化策略**（表格 Q-learning 时使用）：
- emotion × intensity（6 类 × 3 档 = 18）
- sentiment（3 档：负/中/正）
- turn_count（分桶：1-3 / 4-10 / 10+）
- relationship（低/中/高）
- → 理论状态总数 ≈ 18 × 3 × 3 × 3 = ~486（实际远小于此，因组合约束）

## 4. 动作空间（Action Space）

动作是系统可以主动/被动选择的“行为模板”：

```python
class RLAction(BaseModel):
    action_id: str                         # e.g. "ask_about_hobby", "share_funny_story"
    category: Literal[
        "question", "statement", "emotion_expression", "proactive_topic_switch",
        "avatar_gesture", "humor_insert", "empathy_response", "memory_recall"
    ]
    template_prompt: str                   # 用于注入到 reply_generator 的提示片段
    avatar_behavior_tag: Optional[str]     # e.g. "happy_wave", "curious_tilt_head"
    risk_level: Literal["low", "medium", "high"]  # high 动作需更高安全检查
```

**初始动作库规模**：30~50 个（v2.0 MVP），后续可通过用户反馈动态扩展。

## 5. 奖励函数设计（多维度加权，核心公式）

奖励 = 加权和（范围 -1.0 ~ +1.0）

```latex
r = 0.40 \times r_{explicit} 
  + 0.25 \times r_{implicit}
  + 0.15 \times r_{emotion_consistency}
  + 0.10 \times r_{engagement}
  - 0.10 \times r_{safety_penalty}
```

- **r_explicit**：用户显式反馈（👍 / 👎 / “很好” / “不喜欢”）→ +0.8 / -0.6 等
- **r_implicit**：回复长度、继续对话意愿（下一轮是否快速回复）、表情符号使用
- **r_emotion_consistency**：系统表达情绪与检测情绪匹配度（cosine sim > 0.7 → +0.3）
- **r_engagement**：对话轮次增长率、话题深度
- **r_safety_penalty**：触发安全过滤、jailbreak 尝试、敏感内容 → -0.8 ~ -1.0

## 6. Q-learning 更新规则（标准 + 改进）

```python
Q(s, a) ← Q(s, a) + α [ r + γ max_{a'} Q(s', a') - Q(s, a) ]
```

- α（学习率）：0.1 → 随步数衰减至 0.01
- γ（折扣因子）：0.95（重视长期奖励）
- 改进：Double Q-learning + Prioritized Experience Replay（优先回放高 TD-error 样本）

## 7. 经验回放与训练闭环（代码骨架）

```python
# cognitive/reinforcement_learner.py
class ReinforcementLearner:
    def __init__(self):
        self.q_table = {}                   # 或 torch.nn for DQN
        self.replay_buffer = deque(maxlen=10000)
        self.epsilon = 0.5
        self.alpha = 0.1
        self.gamma = 0.95
    
    def select_action(self, state: RLState) -> RLAction:
        if random.random() < self.epsilon:
            return random.choice(action_space)
        else:
            return argmax_a Q(state, a)
    
    def store_transition(self, state, action, reward, next_state, done):
        self.replay_buffer.append((state, action, reward, next_state, done))
    
    def update(self, batch_size=32):
        if len(self.replay_buffer) < batch_size:
            return
        batch = random.sample(self.replay_buffer, batch_size)
        for s, a, r, s_next, done in batch:
            target = r if done else r + self.gamma * max(self.q_table.get(s_next, {}).values())
            current = self.q_table.setdefault(s, {}).setdefault(a.action_id, 0.0)
            self.q_table[s][a.action_id] += self.alpha * (target - current)
```

## 8. 持久化与防灾难性遗忘

- **存储**：SQLite（`data/rl_qtable.db`）或 pickle + 增量保存
- **防遗忘**：
  - 定期回放旧样本（importance sampling）
  - EWC（Elastic Weight Consolidation）如果升级到神经网络
  - 重要行为锁定（reward > 0.7 的动作降低探索概率）

## 9. 与其他模块集成点（关键 hook）

- `cognitive/emotion_nn.py` → 提供 dominant_emotion → RLState
- `interaction/threed_avatar/` → 执行 avatar_behavior_tag
- `cognitive/reply_generator.py` → 注入 action.template_prompt
- `security_architecture.md` → 高风险动作需二次安全校验
- `knowledge_graph.md` → 关系强度变化作为奖励信号

## 10. 测试验收清单

- 单元：Q 值更新正确性、ε 衰减曲线
- 模拟环境：1000 轮固定用户模型，累计奖励曲线向上
- 真实交互：A/B 测试（RL 版 vs 随机版），用户满意度提升 ≥ 15%
- 边缘：负反馈密集场景不崩溃、不学坏行为
- 安全：所有动作经过 security layer，无绕过

## 11. 已知风险与缓解

- 风险：学到不良行为 → 安全奖励下界 -1.0 + 人工 veto 列表
- 风险：探索过度 → ε 衰减 + 上限动作频率
- 风险：奖励稀疏 → 奖励整形（shaping）+ 内在奖励（好奇心模块可选）
- 风险：状态爆炸 → 定期状态聚类/降维

本规范为强化学习模块的**唯一权威文档**，所有实现必须严格遵循。任何奖励函数或动作空间变更需更新本文件并全量回归测试。

**作者签名**：Zikang.Li  
**日期**：2026-03-17
