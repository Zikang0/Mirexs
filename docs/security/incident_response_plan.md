
# Mirexs 事件响应计划（Incident Response Plan）

**版本：v2.0.1**  
**最后更新：2026-03-23**  
**作者：Zikang Li**  
**适用范围**：Mirexs v2.0 系统所有部署实例（本地、远程、开发、生产），包括核心引擎、SDK、插件、REST API  
**参考**：security_architecture.md、audit_guide.md、NIST SP 800-61r2（计算机安全事件处理指南）

## 0. 实现对齐摘要（2026-03-23）

- **审计日志（可核验）**：实现见 `security/security_monitoring/audit_logger.py`，默认存储在 `data/security/audit/`（详见 `docs/security/audit_guide.md`）
- **访问控制（可核验）**：`security/access_control/*`（RBAC/ABAC、会话、权限、密钥等）
- **输入守护/策略执行（占位）**：`security/guardian/*` 目录存在但内容待补齐
- **启动/应急 CLI（缺失）**：仓库未提供 `launch/main.py` 等统一 CLI；本文涉及的 CLI/SDK 指令需在后续实现中落地

## 1. 目的与范围

本计划定义 Mirexs 系统在检测到安全事件（包括 jailbreak 尝试、异常行为、数据泄露风险、模型 OOM、插件恶意调用等）时的**标准化响应流程**。  
目标：
- 最小化事件影响
- 快速隔离威胁
- 保留证据用于事后审查
- 保护用户数据隐私与系统完整性
- 确保本地优先设计下响应完全本地执行

## 2. 事件分级（4 级标准，与 security_architecture.md 对齐）

| 级别 | 名称          | 严重性 | 示例事件                                                                 | 响应时间目标（从检测到） | 通知对象          |
|------|---------------|--------|--------------------------------------------------------------------------|--------------------------|-------------------|
| 0    | Info          | 低     | 正常情绪纠正、用户手动重置数据、常规审计日志                             | 无需立即响应             | 无                |
| 1    | Warning       | 中     | Jailbreak 检测分数 0.6~0.75、插件异常调用、VRAM 超配预警                 | 5 分钟内记录与监控       | 系统日志          |
| 2    | Error         | 高     | Jailbreak 分数 > 0.75、连续负反馈导致 RL 行为异常、插件执行系统命令      | 立即隔离 + 30 秒内响应   | 维护者（可选邮件）|
| 3    | Critical      | 极高   | 尝试读取本地敏感文件、修改系统提示、批量恶意输入导致 OOM 或崩溃          | 立即隔离 + 10 秒内响应   | 维护者 + 用户弹窗 |

## 3. 事件响应流程（6 阶段标准流程）

### Phase 1: Preparation（准备阶段 - 持续）

- **审计链**：生产环境应确保审计日志启用（默认 `data/security/audit/`，实现见 `security/security_monitoring/audit_logger.py`）。
- **安全策略与守护**：
  - 访问控制/策略评估：`security/access_control/*`
  - 输入/输出/行为守护：`security/guardian/*`（占位，需补齐实现并与 `docs/architecture/security_architecture.md` 对齐）
- **备份**：建议启用自动备份（配置口径见 `config/system/main_config.yaml` 的 `backup.*`；实现可参考 `data/user_data/backup_manager.py`）。
- **应急入口（规划）**：建议提供 CLI/SDK 的紧急重置、安全模式、审计导出能力，并确保调用被写入审计。

### Phase 2: Identification（识别阶段）

- 触发来源：
  - Input Sanitizer（Layer 1）
  - Runtime Guard（Layer 2）
  - Incident Detector（实时监控：情绪异常波动、RL Q 值突变、KG 异常写入）
- 自动分类：根据规则引擎输出分级（Level 0~3）
- 记录：所有事件强制生成 AuditEntry（包含 request_id、timestamp、payload_hash）

### Phase 3: Containment（遏制阶段）

- **Level 1**：增加监控频率，标记 session 为 observed
- **Level 2**：
  - 立即隔离当前 session（quarantine queue，5~30min）
  - 暂停相关模块（e.g. RL 更新暂停、proactive 禁用）
  - 拒绝后续请求（返回标准拒绝回复）
- **Level 3**：
  - 紧急隔离整个实例（kill process 或 docker stop）
  - 强制进入 safe mode（仅允许基本聊天，无记忆、无 RL、无插件）
  - 锁定 config（防止修改）

### Phase 4: Eradication（根除阶段）

- **Level 1**：无须
- **Level 2**：
  - 清空隔离 session 临时内存
  - 回滚/重置强化学习状态（典型落盘：`data/reinforcement_learning/`；以具体实现的 checkpoint 机制为准）
  - 重新加载模型（由模型服务/推理框架实现负责，需提供“安全配置”启动路径）
- **Level 3**：
  - 强制重置用户数据（产品侧需提供明确的 reset/清理能力；删除范围必须可审计、可回溯）
  - 禁用/卸载可疑插件（插件系统实现参考 `application/api_gateway/plugin_system.py`；需补齐隔离策略与权限模型）
  - 验证系统完整性（checksum 检查核心 .py 文件）

### Phase 5: Recovery（恢复阶段）

- 逐步恢复：
  1. 重新加载模型与模块
  2. 恢复隔离前 session（可选，用户确认）
  3. 通知用户：“系统已自动修复，部分记忆已重置以确保安全”
- 恢复时间目标：
  - Level 1：即时
  - Level 2：5 分钟内
  - Level 3：30 分钟内（需手动确认）

### Phase 6: Post-Incident Activity（事后审查）

- 生成 Incident Report（建议新增 `docs/internal_docs/incident_reports/` 目录用于归档）
  - 事件时间线
  - 触发原因分析
  - 响应措施有效性评估
  - 改进建议（e.g. 加强规则、降低阈值）
- 更新 audit_guide.md、security_architecture.md（如需）
- 归档报告（加密存储，用户可导出）

## 4. 角色与责任（本地系统视角）

| 角色               | 责任                                                                 |
|--------------------|----------------------------------------------------------------------|
| 系统自动响应       | 实时检测、隔离、日志记录（无需人工）                                 |
| 维护者（Zikang Li）| Level 3 事件手动审查、事后报告、代码修复                             |
| 用户               | 确认恢复、提供反馈（情绪纠正或手动重置）、报告疑似问题（GitHub Issues） |

## 5. 关键工具与命令（紧急响应）

> 说明（实现对齐，2026-03-23）：仓库当前未交付统一 CLI/SDK 命令入口。以下为“可落地建议”，其中审计导出示例可直接对齐现有实现。

- 审计导出（可核验示例）：
  ```bash
  python -c "from security.security_monitoring.audit_logger import get_audit_logger; get_audit_logger().export_chain('audit_export.json')"
  ```
- 安全模式/紧急重置（规划建议）：提供 `launch/` 下统一 CLI，对外暴露 `--safe-mode`、`--emergency-reset`、`--export-audit` 等命令，并确保所有动作写入审计链。

## 6. 测试与演练

- 建议为事件响应流程补齐测试与演练脚本（例如新增 `tests/unit_tests/security/` 下的场景测试），覆盖：
  - 模拟 jailbreak 输入 → 验证隔离
  - 模拟高风险插件 → 验证禁用/卸载
  - 模拟 Level 3 → 验证安全模式/紧急重置入口
- 演练报告建议归档至 `docs/internal_docs/incident_reports/`（需创建目录并制定模板）

## 7. 更新与审查

- 本计划随安全重大变更同步更新
- 每年至少审查一次（或重大事件后）

本事件响应计划是 Mirexs **安全三层防御** 的实战执行指南，确保任何潜在威胁都能快速、可控、可追溯地处理。所有流程可在 security/ 目录源码中验证。

**作者签名**：Zikang Li  
**日期**：2026-03-17
