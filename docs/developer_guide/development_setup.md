# 开发环境搭建（Development Setup）

版本：v2.0.1
最后更新：2026-03-23

## 1. 环境准备

- Python 3.11+
- Git LFS
- CUDA/cuDNN（可选 GPU 加速）
- Java 17（Neo4j）

## 2. 克隆仓库

```
git clone https://github.com/your-org/mirexs.git
cd mirexs
```

## 3. 创建虚拟环境

```
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

## 4. 安装依赖

```
pip install -r requirements.txt
```

## 5. 配置环境变量

- `MIREXS_ENV=dev`
- `MIREXS_DATA_DIR=./data`
- `MIREXS_MODEL_DIR=./models`

## 6. 启动开发环境

> 说明（实现对齐，2026-03-23）：当前仓库 `launch/` 目录中**未提供** `start_development.py` 一键启动脚本；API 网关以
> `application/api_gateway/rest_api.py` 的 `RESTAPI` 管理器形式存在，需要由上层启动器调用 `RESTAPI.start()` 运行。

### 6.1 快速自检（不启动网络服务）

```bash
python -c "from application.api_gateway.rest_api import get_rest_api; print(get_rest_api().get_status())"
```

### 6.2 启动 API 网关（开发用示例）

> 该示例仅用于验证 FastAPI/uvicorn 运行链路，不代表“全系统已可用”。当前默认不包含业务端点注册。

```python
import asyncio
from application.api_gateway.rest_api import get_rest_api

async def main():
    api = get_rest_api()
    await api.start()
    await api.server_task  # 阻塞直到服务退出

if __name__ == "__main__":
    asyncio.run(main())
```

将以上脚本保存为 `scripts/run_api_gateway.py` 后执行：

```bash
python scripts/run_api_gateway.py
```

> 端口与路由前缀的“目标配置口径”见 `config/system/service_configs/api_config.yaml`；当前 `RESTAPI` 默认监听 `0.0.0.0:8000`（代码默认值）。

## 7. 验证

- 若已按 6.1 执行自检，应看到包含 `host/port/docs_url/openapi_url` 的状态输出。
- 若已按 6.2 启动 API 网关，可访问 `http://localhost:8000/docs` 验证 Swagger UI 可用（端点为空属正常）。

---

本文件为契约优先文档。
