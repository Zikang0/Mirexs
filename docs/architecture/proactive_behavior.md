
# 主动行为引擎（Proactive Behavior Engine）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**状态：契约优先规范，可直接指导主动触发条件、行为提案生成、优先级排序、用户接受度反馈闭环与集成**

## 1. 目标与核心价值（量化指标）

主动行为引擎是 Mirexs v2.0 实现“像真人一样主动关心、主动回忆、主动建议”的关键组件，让系统不再只是被动应答，而是具备：

- 在合适时机主动发起对话（e.g. “你今天看起来有点累，要不要聊聊？”）
- 基于长期记忆主动唤醒旧话题（e.g. “上次你提到想学吉他，最近有练习吗？”）
- 主动提供帮助或惊喜（e.g. 生日提醒、兴趣推荐、情绪安抚）
- 避免打扰（低优先级行为在用户忙碌时延迟或取消）

**关键量化目标**：

| 指标                           | 目标值                        | 验收环境                       | 备注                                   |
|--------------------------------|-------------------------------|--------------------------------|----------------------------------------|
| 主动触发准确率                 | ≥ 78%（用户正面接受率）       | 真实交互日志                   | 基于用户回复情绪/继续意愿判断          |
| 误打扰率（用户负面反馈）       | ≤ 8%                          | 同上                           | 负反馈包括忽略、拒绝、不悦情绪         |
| 单次提案生成延迟               | ≤ 150 ms                      | RTX 3060                       | 包含条件检查 + KG 查询                 |
| 每日主动次数上限（默认）       | 3–5 次（可用户配置）          | —                              | 防止过度打扰                           |
| 与 RL 协同优化后提升           | 正面接受率 +15%～+30%（1000轮后）| A/B 测试                     | RL 优化行为选择                        |

## 2. 触发条件系统（多维度打分 + 硬约束）

主动行为触发采用**打分 + 阈值**机制，每隔固定周期（默认 30 分钟～2 小时）或事件驱动（情绪突变、时间点到达）运行一次评估。

### 2.1 核心触发信号（输入来源）

- 当前情绪状态（emotion_nn）
- 最近 5 轮对话活跃度
- 时间/日历事件（生日、纪念日、计划事项）
- 知识图谱中“未决事件”或“高重要性节点”
- 用户历史偏好（e.g. 喜欢晚上聊天 → 晚上权重 +0.3）
- 设备状态（屏幕亮、耳机连接 → 可更高频）

### 2.2 触发概率计算（完整公式）

```latex
score = w_1 \cdot emotion_urgency 
      + w_2 \cdot memory_salience 
      + w_3 \cdot time_context 
      + w_4 \cdot user_availability 
      - w_5 \cdot recent_disturb_penalty
```

默认权重（可配置）：
- emotion_urgency: 0.35（负面情绪高时优先安抚）
- memory_salience: 0.30（最近访问/重要性衰减的节点）
- time_context: 0.15
- user_availability: 0.15
- recent_disturb_penalty: 0.05（最近 2 小时已触发 2 次 → -0.4）

**触发阈值**：
- 高优先（必须触发）：score ≥ 0.85
- 中优先（推荐触发）：0.60 ≤ score < 0.85
- 低优先（仅 RL 决定）：score < 0.60

## 3. 行为提案生成（ProactiveProposal）

```python
class ProactiveProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_reason: List[str]             # e.g. ["negative_emotion", "birthday_reminder"]
    priority: Literal["high", "medium", "low"]
    action_template: str                  # e.g. "关心问候 + 建议休息"
    content_prompt: str                   # 注入给 reply_generator 的完整提示
    avatar_behavior: Optional[str]        # "gentle_pat", "excited_jump"
    target_topic: Optional[str]           # KG 节点 name
    estimated_reward: float = 0.0         # RL 预估 Q 值
    risk_level: Literal["low", "medium", "high"]
    cooldown_minutes: int = 60            # 同类提案冷却
```

## 4. 提案排序与选择逻辑

1. 收集所有 score ≥ 0.50 的 proposal（上限 10 个）
2. RL 打分：Q(state, proposal.action) → 选 top-3
3. 最终选择：
   - 如果有 high priority → 优先执行（可打断当前对话）
   - 否则按 Q 值 + priority 排序，选 top-1
   - 如果用户最近 30min 未回复 → 降级为通知形式（非打断）

## 5. 用户反馈闭环

- 用户回复情绪（emotion_nn）
- 显式反馈（👍 / 👎 / “别再问了”）
- 隐式信号（是否继续话题、回复速度）
- 全部反馈 → reinforcement_learner.store_transition(...)
- 负反馈 → 立即增加 cooldown + 降低该 proposal 基线 Q 值

## 6. 核心代码骨架（proactive_engine.py）

```python
class ProactiveEngine:
    def __init__(self, rl_learner, kg_api, emotion_tracker):
        self.rl = rl_learner
        self.kg = kg_api
        self.emotion = emotion_tracker
        self.recent_triggers = deque(maxlen=20)
    
    async def evaluate_triggers(self) -> List[ProactiveProposal]:
        state = await self.build_current_state()
        candidates = await self.generate_candidates(state)
        scored = []
        for cand in candidates:
            q_value = self.rl.estimate_q(state, cand)
            cand.estimated_reward = q_value
            scored.append(cand)
        return sorted(scored, key=lambda x: x.estimated_reward + x.priority_bonus, reverse=True)
    
    async def decide_and_execute(self):
        proposals = await self.evaluate_triggers()
        if not proposals:
            return
        selected = proposals[0]
        if selected.priority == "high" or random.random() < 0.7:
            await self.send_proactive_message(selected)
            self.record_trigger(selected)
```

## 7. 与其他模块集成点

- emotion_nn → 实时情绪变化作为高 urgency 信号
- knowledge_graph → 查询高 salience 未决事件/节点
- reinforcement_learner → 所有提案执行后反馈到 RL
- security_architecture → 高风险提案（如涉及隐私回忆）需二次审核
- threed_avatar → 执行 avatar_behavior

## 8. 测试验收清单

- 单元：触发分数计算、冷却机制、优先级排序
- 模拟：1000 轮用户模型，主动接受率 ≥ 75%
- 真实：A/B 测试（有/无 proactive），用户留存/满意度提升
- 负反馈场景：连续 3 次拒绝后，同一类提案 24h 内不触发
- 边界：情绪极度负面时优先安抚、用户设置“勿扰模式”时禁用

## 9. 已知风险与缓解

- 风险：过度主动打扰 → 严格用户配置 + 全局开关 + 学习用户耐受度
- 风险：错误回忆导致尴尬 → 所有记忆引用需 confidence ≥ 0.8 + 用户可纠正
- 风险：触发死循环 → 全局每日上限 + 冷却强制

本规范为主动行为引擎的**唯一权威文档**，所有实现必须严格遵循。任何触发条件或优先级变更需更新本文件并回归测试。

**作者签名**：Zikang.Li  
**日期**：2026-03-17
