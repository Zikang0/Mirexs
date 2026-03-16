"""Mirexs API 高级特性示例"""

import requests

BASE_URL = "https://api.mirexs.local/api/v1"
API_KEY = "YOUR_API_KEY"


def _headers():
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }


def create_entity(name: str, entity_type: str):
    payload = {"name": name, "type": entity_type}
    return requests.post(f"{BASE_URL}/knowledge/entities", json=payload, headers=_headers()).json()


def create_relation(source_id: str, target_id: str, relation_type: str):
    payload = {"source": source_id, "target": target_id, "type": relation_type}
    return requests.post(f"{BASE_URL}/knowledge/relations", json=payload, headers=_headers()).json()


def search_memory(query: str):
    payload = {"query": query, "top_k": 5}
    return requests.post(f"{BASE_URL}/memory/search", json=payload, headers=_headers()).json()


def routing_decision(task: str, complexity: float):
    payload = {"task": task, "complexity": complexity}
    return requests.post(f"{BASE_URL}/routing/decide", json=payload, headers=_headers()).json()


def execute_tool(tool_id: str, params: dict):
    payload = {"tool_id": tool_id, "parameters": params}
    return requests.post(f"{BASE_URL}/tools/execute", json=payload, headers=_headers()).json()


def main():
    # 1) 知识图谱
    e1 = create_entity("周杰伦", "person")
    e2 = create_entity("夜曲", "song")
    create_relation(e1["data"]["id"], e2["data"]["id"], "created")

    # 2) 记忆检索
    print(search_memory("上次说的旅行计划"))

    # 3) 模型路由
    print(routing_decision("code_generation", 0.85))

    # 4) 工具执行
    print(execute_tool("web_search", {"q": "北京今日新闻"}))


if __name__ == "__main__":
    main()
