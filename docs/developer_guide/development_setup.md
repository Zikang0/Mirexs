# 开发环境搭建（Development Setup）

版本：v2.0
最后更新：2026-03-16

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

```
python launch/start_development.py
```

## 7. 验证

- 访问 `GET /api/v1/system/health`
- 打开 UI 观察日志输出

---

本文件为契约优先文档。
