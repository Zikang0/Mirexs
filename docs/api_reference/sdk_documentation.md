
# Mirexs SDK / 客户端文档（Draft）

**适用 API 版本**：v1  
**适用系统版本**：Mirexs v2.x  
**最后更新**：2026-03-23  
**作者**：Zikang Li  
**状态**：草案（仓库当前未提供可直接发布的 SDK；本文档用于明确“现状、约束与落地路径”）

## 1. 当前现状（必须先澄清）

为避免“文档口径与代码/配置不一致”导致集成失败，现对 SDK 相关现状做如下明确约束：

1. **仓库当前不具备可发布的 Python 包形态**：`pyproject.toml` 与 `setup.py` 目前为空文件，无法直接 `pip install` 形成可 import 的 `mirexs` SDK 包。
2. **存在 SDK 生成器的代码骨架**：`application/api_gateway/sdk_development.py` 提供从 OpenAPI 加载并生成多语言 SDK 的 scaffolding；但其默认依赖的模板目录 `templates/sdk/` **当前缺失**，因此“自动生成 SDK”尚不可用。
3. **推荐的集成方式（当前可行）**：调用方按 `docs/api_reference/rest_api.md` 与 `docs/technical_specifications/api_specification.md` 直接封装轻量 HTTP 客户端。

## 2. 推荐的最小客户端封装（Python 示例）

> 说明：以下示例为“调用方项目中的封装方式”，不依赖本仓库打包结果；仅用于展示 Envelope 解析与认证头规范。

```python
import json
import requests

API_BASE = "http://localhost:8000/api/v1"

def _headers(api_key: str | None = None) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers

def create_session(user_id: str, initial_prompt: str | None = None, api_key: str | None = None) -> dict:
    payload = {"user_id": user_id, "initial_prompt": initial_prompt}
    resp = requests.post(f"{API_BASE}/sessions", headers=_headers(api_key), data=json.dumps(payload))
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"API failed: {data}")
    return data["data"]
```

## 3. 错误处理建议（与 Envelope 对齐）

调用方应统一按以下规则处理响应：

- `status == "success"`：正常处理 `data`
- `status == "warning"`：业务可继续，但建议记录 `message/meta`
- `status == "fail"`：可修正错误（通常是 400/422），读取 `errors[]` 指示用户修正输入
- `status == "error"`：不可修正或需要重试/升级权限（401/403/429/5xx）

## 4. 配置口径（避免“找不到 config.yaml”）

调用方如需了解网关地址、路由前缀、认证方式等，优先参考：

- `config/system/service_configs/api_config.yaml`（网关 host/port、`/api/v1` 前缀、认证/限流）

如需了解用户偏好（语言/隐私/交互等），优先参考：

- `config/user/preferences/*.yaml`

## 5. SDK 生成器落地步骤（后续工作清单）

若要在仓库内形成“可发布 SDK”，建议按以下路径推进（以可验证为准）：

1. **补齐 OpenAPI 输出**：在 API 网关层生成并落盘 `openapi.json`（相关代码：`application/api_gateway/documentation.py`）。
2. **补齐模板目录**：新增 `templates/sdk/`，与 `application/api_gateway/sdk_development.py` 的 Jinja2 Loader 路径一致。
3. **定义包结构与打包配置**：完善 `pyproject.toml` 或 `setup.py`，形成可 `pip install` 的包。
4. **CI 校验**：为 SDK 生成结果加 lint/test（至少确保 import 与基本请求拼装正确）。

## 6. 变更记录

SDK 相关变更（尤其是“可用性变化”）必须同步记录在：

- `docs/api_reference/api_changelog.md`

## 7. 开发落地要求（2026-03-30 补充）

本文件当前描述的是“如何在仓库里补齐 SDK 能力”，不是“现成可发布 SDK 的最终用户说明”。

后续要真正落地，至少需要补齐：

- OpenAPI 产物输出
- SDK 模板目录
- 打包配置
- 最小导入和请求测试

