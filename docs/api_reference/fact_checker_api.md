# 事实核查器 API 参考 (Fact Checker API)

## 1. 概述 (Overview)

事实核查器 API 允许开发者利用 Mirexs 的核心核查引擎来验证文本内容的事实准确性。该 API 结合了多源信源管理、交叉验证和置信度评估。

## 2. 基础信息 (Base Info)

*   **Base URL**: `https://api.mirexs.com/v1/fact-checker`
*   **Content-Type**: `application/json`
*   **Authentication**: `Bearer <token>`

## 3. 端点参考 (Endpoints)

### 3.1 验证事实 (Verify Fact)

**POST /verify**

*   **描述**: 提交一段文本或一个具体的事实陈述进行核查。
*   **请求体**:
    ```json
    {
      "claim": "2024年巴黎奥运会的开幕式在塞纳河上举行。",
      "context": "体育新闻",
      "options": {
        "deep_check": true,
        "include_sources": true
      }
    }
    ```
*   **响应**:
    ```json
    {
      "status": "verified",
      "confidence_score": 0.98,
      "summary": "该陈述与多个权威新闻源一致。",
      "sources": [
        {
          "name": "Olympics Official",
          "url": "https://olympics.com/...",
          "weight": 1.0
        }
      ]
    }
    ```

### 3.2 获取信源列表 (Get Sources)

**GET /sources**

*   **描述**: 获取当前事实核查器使用的可信信源列表。
*   **响应**:
    ```json
    {
      "sources": [
        { "id": "src_001", "name": "Wikipedia", "category": "General" },
        { "id": "src_002", "name": "Reuters", "category": "News" }
      ]
    }
    ```

## 4. 错误码 (Error Codes)

| 错误码 | 描述 |
| :--- | :--- |
| `INVALID_CLAIM` | 提交的陈述格式不正确或为空。 |
| `INSUFFICIENT_SOURCES` | 无法找到足够的信源进行验证。 |
| `RATE_LIMIT_EXCEEDED` | 超过 API 调用频率限制。 |

---
**作者**: Zikang Li
**日期**: 2026-03-18
**版本**: v1.0.0
