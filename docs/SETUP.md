---
status: implemented
last_reviewed: 2026-03-30
corresponds_to_code: "requirements.txt,config/system/"
related_issues: ""
references: "docs/developer_guide/development_setup.md,docs/developer_guide/deployment_guide.md"
---
# Mirexs 环境准备入口

## 1. 目标

本文件说明在正式进入开发或部署前，必须先确认的环境准备项。详细的开发与部署操作分别见子文档，本文件只负责给出统一入口和准备顺序。

## 2. 开发环境入口

- [开发环境搭建](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/development_setup.md)
- [部署指南](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/developer_guide/deployment_guide.md)

## 3. 必读前置文档

- [系统需求规范](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/system_requirements.md)
- [兼容性矩阵](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/compatibility_matrix.md)
- [REST API 契约规范](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/api_specification.md)
- [API 响应封装规范](/C:/Users/Lee/Desktop/GitHub/Mirexs/docs/technical_specifications/api_envelope_standard.md)

## 4. 环境准备顺序

1. 确认操作系统、Python 版本、GPU/驱动与存储空间是否满足要求。
2. 确认 `requirements.txt` 中的依赖是否能在当前平台安装。
3. 确认外部依赖服务是否需要启用，例如 Neo4j、Redis、InfluxDB。
4. 确认模型目录、数据目录和日志目录的路径规划。
5. 再进入具体的开发或部署步骤。

## 5. 当前仓库口径

截至当前仓库状态：

- `requirements.txt` 提供的是“完整技术栈依赖清单”，并非最小开发依赖集
- 仓库中存在部分架构先行、实现补齐中的模块，因此启动流程需按文档和代码实际入口执行
- 配置主要位于 `config/system/`，默认数据与模型路径位于 `data/`

## 6. 使用原则

- 不要只依赖 README 中的宣传性描述启动项目
- 不要假设所有脚本和一键入口已经完全交付
- 任何环境问题都要先回到 `requirements.txt`、配置文件和对应子文档核对
