# 情绪模型训练指南（Emotion NN Training）

版本：v2.0
最后更新：2026-03-16

## 1. 训练目标

- 识别 6 种基础情绪
- 支持个性化微调

## 2. 数据要求

- 文本情绪标注数据
- 语音/表情数据（可选）
- 数据需匿名化与授权

## 3. 训练流程

1. 数据准备
2. 特征抽取（Sentence‑Transformers 384 维）
3. LSTM 训练
4. 评估与校准

## 4. 输出

- `models/emotion/emotion_model.pth`

---

本文件为契约优先文档。
