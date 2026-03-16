# Mirexs SDK 文档

版本：v2.0
最后更新：2026-03-16

## 1. 概述

Mirexs SDK 提供对 REST API 的一致封装，简化鉴权、重试、分页与错误处理。

## 2. 安装

```
pip install mirexs-sdk
```

## 3. SDK 结构

- `Client`：统一入口
- `Conversations`：会话管理
- `Knowledge`：知识图谱
- `Memory`：长期记忆
- `Models`：模型与路由
- `Plugins`：插件系统

## 4. Python 示例

```python
from mirexs_sdk import MirexsClient

client = MirexsClient(
    base_url="https://api.mirexs.local/api/v1",
    api_key="YOUR_API_KEY",
    timeout=20,
    retries=2
)

conv = client.conversations.create(title="周会", user_id="user_001")
msg = client.conversations.send_message(conv.id, "帮我整理周会要点")
print(msg.content)
```

## 5. JavaScript 示例

```javascript
import { MirexsClient } from "mirexs-sdk";

const client = new MirexsClient({
  baseUrl: "https://api.mirexs.local/api/v1",
  apiKey: "YOUR_API_KEY"
});

const conv = await client.conversations.create({
  userId: "user_001",
  title: "旅行规划"
});

const reply = await client.conversations.sendMessage(conv.id, "帮我规划大阪行程");
console.log(reply.content);
```

## 6. 错误处理

SDK 会抛出结构化异常：

```json
{
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "请求频率超限"
}
```

## 7. 配置项

- `base_url`
- `api_key`
- `timeout`
- `retries`
- `proxy`（可选）

---

本文件为契约优先文档的 SDK 使用说明。
