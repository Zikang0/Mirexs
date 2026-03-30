---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "requirements.txt,config/system/,application/api_gateway/rest_api.py"
related_issues: ""
references: "README.md,docs/technical_specifications/system_requirements.md"
---
# 开发环境搭建

## 1. 文档目标

本文件说明开发者如何在本地准备 Mirexs 开发环境。由于当前仓库仍处于“架构已成形、部分模块持续补齐”的状态，本文件同时说明哪些入口已经存在、哪些仍需要开发者自行编排。

## 2. 环境基线

- Python 3.11 优先，3.9 为最低兼容
- Git 与 Git LFS
- 充足磁盘空间，推荐至少 100GB 可用空间
- 如需本地推理，建议具备 NVIDIA GPU 与 CUDA 环境
- 如果要启用 Neo4j，需安装 Java 17

## 3. 获取代码

```bash
git clone https://github.com/your-org/mirexs.git
cd mirexs
```

## 4. 创建隔离环境

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

## 5. 安装依赖

```bash
pip install -r requirements.txt
```

注意：

- `requirements.txt` 当前更接近“完整技术栈清单”，不是最小开发依赖集
- 某些依赖依赖系统库、GPU 驱动或额外编译环境
- 如果只是开发单一模块，可根据实际情况按需安装

## 6. 推荐环境变量

- `MIREXS_ENV=development`
- `MIREXS_DATA_DIR=./data`
- `MIREXS_MODELS_DIR=./data/models`
- `MIREXS_CONFIG_DIR=./config`

## 7. 配置入口

开发时需要优先了解以下配置目录：

- `config/system/main_config.yaml`
- `config/system/model_configs/`
- `config/system/service_configs/`
- `config/system/platform_configs/`

## 8. 当前可验证的启动入口

当前仓库没有完整交付“一键启动全部系统”的稳定脚本。开发者应按模块分别验证。

### 8.1 API 网关链路验证

核心入口位于 `application/api_gateway/rest_api.py`。

如果你只想验证 API 管理器是否可初始化，可先做导入和状态检查。

### 8.2 模块级开发验证

开发某一模块时，建议使用以下顺序：

1. 先验证配置是否能加载
2. 再验证模块能否导入
3. 最后验证核心方法是否能独立执行

## 9. 常见问题

- 依赖安装失败：优先检查 Python 版本、系统编译工具、CUDA 和系统库
- 模型相关报错：优先检查模型路径、GPU 驱动和对应推理后端
- 数据库相关报错：优先检查 Neo4j、Redis、InfluxDB 等外部服务是否启用

## 10. 完成定义

本地开发环境准备完成，至少需要满足：

- 能创建并激活虚拟环境
- 能安装核心依赖
- 能加载主配置
- 能独立验证至少一个开发入口
