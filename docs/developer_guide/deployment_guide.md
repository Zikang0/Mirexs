# 部署指南（Deployment Guide）

版本：v2.0.1
最后更新：2026-03-23

## 1. 部署模式

- 单机本地部署（个人版）
- 单节点私有化部署
- 多节点集群部署（企业版）

## 2. 单机部署

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 启动服务（实现对齐说明）

截至 2026-03-23，本仓库未提供 `launch/start_development.py` 作为可直接运行的“一键启动入口”。部署时需按组件分别启动，或编写上层启动器统一拉起：

- API 网关（FastAPI/uvicorn）：`application/api_gateway/rest_api.py` 的 `RESTAPI.start()`
- 认知/能力/数据等其他服务：当前以目录结构与接口骨架为主，需补齐可运行进程与注册机制后再纳入部署编排

> 若仅需验证 API 网关运行链路，可参考 `development_setup.md` 的“启动 API 网关（开发用示例）”。

3. 验证
如果已启动 API 网关进程（示例），可访问 `http://<host>:8000/docs` 验证服务可达。

## 3. 生产部署要点

- **产物口径**：当前仓库 `deployment/` 下主要为部署能力/生成器代码骨架，并未提供可直接用于生产的 Dockerfile/Helm Chart/系统服务脚本“最终产物”。如需生产部署，建议先固化并版本化交付物。
- **容器化与编排**：建议使用 Docker/K8s；如采用生成器能力，可从 `deployment/containerization/` 中抽取/扩展。
- **安全**：启用 TLS（证书路径可参考 `config/system/service_configs/api_config.yaml` 中的 `gateway.service.ssl.*` 口径）。
- **外部依赖**：按需配置 Redis/Neo4j/InfluxDB 等（见 `config/system/service_configs/*_config.yaml`）。
- **可观测性**：日志与监控接入 Prometheus/Grafana（见 `deployment/monitoring_ops/` 与 `config/system/service_configs/api_config.yaml` 的 `monitoring.*` 口径）。

## 4. 回滚策略

- 保留上一版本镜像
- 数据库使用迁移版本控制
- 支持蓝绿发布

---

本文件为契约优先文档。
