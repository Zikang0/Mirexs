---
status: implemented
last_reviewed: 2026-03-30
corresponds_to_code: "requirements.txt,config/system/main_config.yaml"
related_issues: ""
references: "README.md"
---
# 系统需求规范

## 1. 目标

本文件定义 Mirexs 的运行基线、推荐配置和容量规划，用于开发、部署和硬件采购评估。

## 2. 环境分级

| 级别 | 适用场景 | CPU | 内存 | GPU | 存储 |
|---|---|---|---|---|---|
| 轻量 | 文本聊天、基础验证 | 4 核 | 16GB | 可选 | 100GB SSD |
| 推荐 | 日常开发、多模块验证 | 8 核 | 32GB | RTX 3060 12GB | 500GB SSD |
| 高性能 | 多模型、本地大推理 | 16 核 | 64GB | RTX 4090 24GB | 1TB NVMe |

## 3. 软件环境

- Windows 10/11
- Ubuntu 20.04/22.04
- macOS 12/14
- Python 3.11 优先

## 4. 关键系统依赖

- Git 与 Git LFS
- CUDA / cuDNN（如使用 NVIDIA GPU）
- Java 17（如启用 Neo4j）
- FFmpeg（音视频处理）
- 系统编译工具链（某些依赖需要）

## 5. 外部服务建议

| 服务 | 作用 | 默认端口 |
|---|---|---|
| REST API | 对外接口 | 8000 |
| WebSocket | 实时通信 | 8001 |
| Neo4j | 知识图谱 | 7474 / 7687 |
| Redis | 缓存 | 6379 |
| InfluxDB | 指标存储 | 8086 |

## 6. 存储规划

- 小模型环境：建议至少预留 100GB
- 多模型环境：建议至少预留 500GB
- 图数据库、向量库和日志应单独规划空间，避免与模型目录混用

## 7. 权限要求

- 麦克风、摄像头和输入监听权限按需启用
- 日志、配置和数据目录需要可读写权限
- 涉及自动化和系统控制时，需考虑额外系统授权

## 8. 验收基线

环境准备完成至少应满足：

- 核心依赖可安装
- 主配置可加载
- 关键目录可读写
- 至少一个核心入口可以导入或启动
