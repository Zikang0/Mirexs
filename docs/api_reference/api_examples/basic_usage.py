"""Mirexs API 基础使用示例"""

import requests

BASE_URL = "https://api.mirexs.local/api/v2"
API_KEY = "YOUR_API_KEY"


def _headers():
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }


def create_conversation(title: str, user_id: str):
    payload = {"title": title, "user_id": user_id}
    resp = requests.post(f"{BASE_URL}/conversations", json=payload, headers=_headers(), timeout=10)
    return resp.json()


def send_message(conversation_id: str, content: str):
    payload = {"role": "user", "content": content}
    resp = requests.post(f"{BASE_URL}/conversations/{conversation_id}/messages", json=payload, headers=_headers(), timeout=30)
    return resp.json()


def get_system_status():
    resp = requests.get(f"{BASE_URL}/system/status", headers=_headers(), timeout=10)
    return resp.json()


def main():
    print("System status:", get_system_status())

    conv = create_conversation("周会准备", "user_001")
    conv_id = conv.get("data", {}).get("id")
    print("Conversation:", conv)

    reply = send_message(conv_id, "帮我整理周会要点")
    print("Reply:", reply)


if __name__ == "__main__":
    main()
