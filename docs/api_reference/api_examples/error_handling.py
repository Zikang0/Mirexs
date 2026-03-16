"""Mirexs API 错误处理示例"""

import requests

BASE_URL = "https://api.mirexs.local/api/v1"
API_KEY = "YOUR_API_KEY"


def _headers():
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }


def safe_request(method: str, url: str, **kwargs):
    try:
        resp = requests.request(method, url, timeout=10, **kwargs)
        data = resp.json()
        if not data.get("success", False):
            print("API error:", data.get("error"))
        return data
    except requests.exceptions.Timeout:
        return {"success": False, "error": {"code": "TIMEOUT", "message": "请求超时"}}
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": {"code": "NETWORK_ERROR", "message": str(exc)}}


def main():
    # 错误示例：会话不存在
    data = safe_request("GET", f"{BASE_URL}/conversations/not_found", headers=_headers())
    print(data)

    # 错误示例：触发限流
    for _ in range(3):
        safe_request("GET", f"{BASE_URL}/system/metrics", headers=_headers())


if __name__ == "__main__":
    main()
