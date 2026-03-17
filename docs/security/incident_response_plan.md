
# Mirexs 事件响应计划（Incident Response Plan）

**版本：v2.0.0**  
**最后更新：2026-03-17**  
**作者：Zikang.Li**  
**适用范围**：Mirexs v2.0 系统所有部署实例（本地、远程、开发、生产），包括核心引擎、SDK、插件、REST API  
**参考**：security_architecture.md、audit_guide.md、NIST SP 800-61r2（计算机安全事件处理指南）

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

- 审计日志始终启用（data/audit.db 加密 append-only）
- 安全规则引擎实时运行（security/rules_engine.py）
- 自动备份：每日 00:00 备份 config/、data/（用户可选关闭）
- 应急工具：client.reset_system()、CLI --emergency-reset

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
  - 回滚 RL Q 值（从最近安全 checkpoint）
  - 重新加载模型（model_loader.reload_safe()）
- **Level 3**：
  - 强制重置用户数据（client.reset_user_data(full=True)）
  - 删除可疑插件（plugin_loader.unload(suspicious_name)）
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

- 生成 Incident Report（docs/internal_docs/incident_reports/ 下新增 .md）
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

- CLI 命令：
  ```bash
  python launch/main.py --emergency-reset          # 强制重置
  python launch/main.py --safe-mode                # 进入安全模式
  python launch/main.py --export-audit             # 导出审计日志
  ```
- SDK 方法：
  ```python
  await client.emergency_reset(full=True)          # 完整重置
  await client.get_incident_status()               # 查询当前事件状态
  ```

## 6. 测试与演练

- 每月模拟演练（tests/security/test_incident_response.py）
  - 模拟 jailbreak 输入 → 验证隔离
  - 模拟高风险插件 → 验证卸载
  - 模拟 Level 3 → 验证自动 safe mode
- 演练报告存入 internal_docs/incident_reports/

## 7. 更新与审查

- 本计划随安全重大变更同步更新
- 每年至少审查一次（或重大事件后）

本事件响应计划是 Mirexs **安全三层防御** 的实战执行指南，确保任何潜在威胁都能快速、可控、可追溯地处理。所有流程可在 security/ 目录源码中验证。

**作者签名**：Zikang.Li  
**日期**：2026-03-17
