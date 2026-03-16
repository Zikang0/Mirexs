# 部署指南（Deployment Guide）

版本：v2.0
最后更新：2026-03-16

## 1. 部署模式

- 单机本地部署（个人版）
- 单节点私有化部署
- 多节点集群部署（企业版）

## 2. 单机部署

1. 安装依赖
```
pip install -r requirements.txt
```

2. 启动服务
```
python launch/start_development.py
```

3. 验证
```
GET /api/v1/system/health
```

## 3. 生产部署要点

- 使用 Docker/K8s
- 启用 TLS
- 配置 Redis/Neo4j/InfluxDB
- 日志与监控接入 Prometheus/Grafana

## 4. 回滚策略

- 保留上一版本镜像
- 数据库使用迁移版本控制
- 支持蓝绿发布

---

本文件为契约优先文档。
