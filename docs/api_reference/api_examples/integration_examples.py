"""Mirexs API 集成示例"""

import json
import hmac
import hashlib
import requests

BASE_URL = "https://api.mirexs.local/api/v1"
API_KEY = "YOUR_API_KEY"
WEBHOOK_SECRET = "your-webhook-secret"


def _headers():
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }


def register_webhook(url: str, events: list):
    payload = {"url": url, "events": events, "secret": WEBHOOK_SECRET}
    return requests.post(f"{BASE_URL}/webhooks/register", json=payload, headers=_headers()).json()


def verify_signature(payload: str, signature: str) -> bool:
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def install_plugin(path: str):
    payload = {"plugin_path": path}
    return requests.post(f"{BASE_URL}/plugins/install", json=payload, headers=_headers()).json()


def main():
    # 1) 注册 Webhook
    print(register_webhook("https://example.com/webhook", ["task.complete", "model.loaded"]))

    # 2) 安装插件
    print(install_plugin("/path/to/plugin.zip"))

    # 3) 模拟 Webhook 接收
    payload = json.dumps({"event": "task.complete", "data": {"task_id": "task_001"}})
    signature = hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    print("Webhook signature valid:", verify_signature(payload, signature))


if __name__ == "__main__":
    main()
