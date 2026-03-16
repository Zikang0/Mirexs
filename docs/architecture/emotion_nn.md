# 情绪神经网络（Emotion Neural Network）

**版本：v2.0.0**  
**最后更新：2026-03-16**  
**作者：Zikang.Li**  
**状态：契约优先规范，可直接指导模型实现、训练与集成**

## 1. 目标与核心价值（量化指标）

情绪神经网络是 Mirexs v2.0 的“情感核心”，目标是让系统具备真实、持久、个性化的情绪理解与表达能力，实现：

- 单轮文本情绪分类准确率 ≥ 85%（6 类基本情绪 + 中性）
- 融合多模态（文本+语音韵律+面部微表情）后准确率提升至 ≥ 92%
- 个性化微调后，用户专属情绪模型在 200 次交互内 F1-macro 提升 ≥ 12%
- 推理延迟（单次前向）≤ 180 ms（RTX 3060）
- 情绪强度量化（0.0～1.0），支持连续值输出而非硬分类
- 支持情绪历史衰减（指数衰减，半衰期默认 4 轮对话）
- 与 3D 头像、行为系统、回复生成无缝桥接

**非功能约束**：

| 指标                     | 目标值                  | 验收环境                     | 备注                              |
|--------------------------|-------------------------|------------------------------|-----------------------------------|
| 单次推理延迟 (P95)       | ≤ 180 ms                | RTX 3060 12GB                | batch=1, no torch.compile         |
| 模型大小 (推理态)        | ≤ 180 MB                | —                            | 包含 embedding + LSTM + heads    |
| 微调显存峰值             | ≤ 6.5 GB                | 同上                         | 使用 LoRA rank=16                 |
| 情绪状态持久化开销       | ≤ 2 KB / 对话轮         | —                            | 存入知识图谱或向量内存            |

## 2. 情绪类别与定义（严格 6+1 类）

| 类别       | 英文标签     | 中文描述           | 典型触发场景示例                     | 强度范围映射 |
|------------|--------------|--------------------|--------------------------------------|--------------|
| happy      | HAPPY        | 快乐/满足          | 收到礼物、夸奖、目标达成             | 0.0～1.0    |
| sad        | SAD          | 悲伤/失落          | 失败、被拒绝、回忆负面事件           | 0.0～1.0    |
| angry      | ANGRY        | 愤怒/不满          | 被误解、承诺未兑现、侵犯边界         | 0.0～1.0    |
| fear       | FEAR         | 恐惧/焦虑          | 不确定性、威胁、未知风险             | 0.0～1.0    |
| surprise   | SURPRISE     | 惊讶/意外          | 突发事件、出乎意料的回答             | 0.0～1.0    |
| calm       | CALM         | 平静/中性          | 日常闲聊、无明显情感倾斜             | 0.0～0.4    |
| neutral    | NEUTRAL      | 纯中性（兜底）     | 无任何情绪线索                       | 固定 0.0    |

## 3. 模型架构（完整 PyTorch 定义）

```python
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

class EmotionNN(nn.Module):
    """
    多模态情绪神经网络（v2.0.0）
    输入：文本 tokens + 可选语音特征 + 可选面部 AU
    输出：(batch, 7) softmax 概率 + (batch,) 强度 scalar
    """
    def __init__(self,
                 text_embed_dim: int = 384,          # bge-small-zh-v1.5
                 hidden_dim: int = 256,
                 lstm_layers: int = 2,
                 dropout: float = 0.3,
                 num_classes: int = 7):
        super().__init__()
        
        # 文本路径
        self.text_embedder = AutoModel.from_pretrained("BAAI/bge-small-zh-v1.5")
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-zh-v1.5")
        
        # 时序建模
        self.lstm = nn.LSTM(
            input_size=text_embed_dim,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            bidirectional=True,
            dropout=dropout,
            batch_first=True
        )
        
        # 自注意力（增强长依赖）
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim*2,
            num_heads=8,
            dropout=dropout,
            batch_first=True
        )
        
        # 融合头（晚期融合）
        self.fusion_fc = nn.Sequential(
            nn.Linear(hidden_dim*2 + 64 + 32, 512),  # text + prosody(64) + facial(32)
            nn.LayerNorm(512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256)
        )
        
        # 分类头
        self.classifier = nn.Linear(256, num_classes)
        self.intensity_head = nn.Linear(256, 1)     # sigmoid 后 0~1
        
    def forward(self, text_input, prosody_feats=None, facial_feats=None, attention_mask=None):
        # text_input: dict from tokenizer (input_ids, attention_mask)
        embeds = self.text_embedder(**text_input).last_hidden_state  # (B, L, 384)
        
        lstm_out, _ = self.lstm(embeds)                      # (B, L, 512)
        
        # 自注意力池化
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out,
                                     key_padding_mask=~attention_mask.bool())
        pooled = attn_out.mean(dim=1)                        # (B, 512)
        
        # 多模态融合（若无则用零向量）
        fused = pooled
        if prosody_feats is not None:
            fused = torch.cat([fused, prosody_feats], dim=-1)
        if facial_feats is not None:
            fused = torch.cat([fused, facial_feats], dim=-1)
        
        fused = self.fusion_fc(fused)
        logits = self.classifier(fused)
        intensity = torch.sigmoid(self.intensity_head(fused))
        
        probs = torch.softmax(logits, dim=-1)
        return probs, intensity
```

## 4. 输入预处理 pipeline（完整代码骨架）
```Python
def preprocess_input(text: str,
                     audio_path: str | None = None,
                     face_landmarks: np.ndarray | None = None) -> dict:
    # 文本
    tokens = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    
    # 语音韵律特征（Librosa + opensmile）
    prosody = None
    if audio_path:
        prosody = extract_prosody_features(audio_path)   # 返回 (B, 64)
    
    # 面部动作单元（MediaPipe + InsightFace）
    facial = None
    if face_landmarks is not None:
        facial = extract_au_features(face_landmarks)     # 返回 (B, 32)
    
    return {
        "text_input": tokens,
        "prosody_feats": prosody,
        "facial_feats": facial
    }
```
## 5. 训练与微调流程（详细步骤）

预训练阶段（离线）
数据集：Weibo Emotion + NLPCC Emotion + 自定义标注（至少 50k 样本）
损失：CrossEntropy + MSE(intensity)
优化器：AdamW lr=2e-5, weight_decay=0.01
epoch：5–8，early stop on dev F1

个性化 LoRA 微调（在线/周期性）
触发条件：用户手动纠正情绪标签 ≥ 20 次，或累计 150 轮对话
使用 PEFT LoRA（rank=16, alpha=32, target=["q_proj","v_proj"]）
数据来源：用户历史对话 + 纠正标签（隐私本地存储）
训练：batch=4, accum=4, lr=1e-4, steps=200–400
保存：每用户一个 adapter 目录（<10MB）


## 6. 输出格式（JSON payload 示例）
```JSON{
  "emotion_probs": {
    "happy": 0.78,
    "sad": 0.03,
    "angry": 0.01,
    "fear": 0.02,
    "surprise": 0.11,
    "calm": 0.05,
    "neutral": 0.00
  },
  "primary_emotion": "happy",
  "intensity": 0.82,
  "timestamp": "2026-03-16T16:45:22.123Z",
  "source": "text+voice",
  "user_corrected": false
}
```
## 7. 与下游模块集成点（关键 hook）

` cognitive/emotion_bridge.py → set_current_emotion(emotion_payload) `

` interaction/threed_avatar/behavior_system.py → trigger_animation(emotion, intensity) `

` cognitive/reply_generator.py → inject_emotion_prompt(emotion_probs) `

## 8. 已知风险与缓解

风险：文化偏差（中文语料偏向）→ 引入多语言预训练 + 用户反馈校准

风险：过拟合用户负面情绪 → 加入正则项 + 情绪平衡采样

风险：隐私泄露 → 所有微调数据加密存储，用户可一键删除

## 9. 测试验收清单（必须覆盖）

单元：单模态/多模态前向一致性

离线评估：F1-macro ≥ 0.84 (dev set)

在线 A/B：用户满意度提升 ≥ 18%（情绪相关回复）

边缘case：极短文本、emoji、重度 sarcasm、混合情绪

```
本规范为情绪模块的唯一权威文档，所有实现必须严格遵循。任何改动需同步更新本文件。
```
