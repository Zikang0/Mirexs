
# Mirexs 插件开发指南（Plugin Development）

**适用系统版本**：Mirexs v2.x  
**最后更新**：2026-03-23  
**作者**：Zikang Li  
**状态**：规范 + 现状说明（插件框架存在但仍处于逐步落地阶段）

## 1. 术语与范围（避免“一个词指多个系统”）

本仓库当前同时存在两类“插件/扩展”相关代码与目录结构：

1. **平台插件（主要）**：位于 `plugins/`，用于承载官方/社区能力扩展与插件框架代码（`plugins/core`）。  
2. **API 网关插件（次要/待对齐）**：位于 `application/api_gateway/plugin_system.py`，用于扩展 API 网关的请求/响应钩子与路由生命周期（目录口径仍需与 `plugins/` 的现状对齐）。

本文档以 **平台插件（`plugins/`）** 为主，并在需要时说明 API 网关插件系统的差异与对齐点。

## 2. 仓库内插件目录结构（以实际存在为准）

当前 `plugins/` 目录结构：

```
plugins/
├── core/                 # 插件框架核心：加载、注册、生命周期、依赖、安全校验
├── official/             # 官方插件/能力包（按领域分组）
├── community/            # 社区插件（预留）
└── development_tools/    # 插件 SDK、模板、测试框架
```

关键文件（建议从这些入口读代码/对齐文档）：

- `plugins/core/plugin_loader.py`：动态加载/发现/基础校验（`validate_plugin` 当前要求 `activate/deactivate/get_info`）
- `plugins/core/plugin_manager.py`：插件生命周期管理（安装/激活/停用/卸载；部分流程仍为 TODO）
- `plugins/core/plugin_registry.py`：注册表与分类信息（可落盘为 `plugin_registry.json`）
- `plugins/core/security_validator.py`：插件安全扫描（含 manifest/依赖扫描逻辑）
- `plugins/development_tools/plugin_sdk/development_templates/`：插件模板（基础/AI/集成）

## 3. 插件最小接口（当前代码期望）

`plugins/core/plugin_loader.py` 的校验逻辑（`validate_plugin`）当前按“最小接口”检查插件类是否具备以下方法：

- `activate() -> bool`
- `deactivate() -> bool`
- `get_info() -> dict`

> 注意：仓库内部分官方插件目前尚未补齐 `get_info()`，会导致严格校验下无法通过。建议在后续实现中统一补齐接口，并在本文件中更新“最小接口”定义。

## 4. 插件元数据（推荐结构）

插件元数据在框架中以 `PluginInfo` 形式出现（`plugins/core/plugin_registry.py`、`plugins/core/plugin_manager.py` 均有定义）。  
为便于安全扫描与自动注册，建议每个插件目录包含一个 `manifest.json`（`security_validator.py` 会扫描）：

```json
{
  "name": "example_plugin",
  "version": "0.1.0",
  "description": "示例插件",
  "author": "Your Name",
  "category": "community",
  "entry_point": "example_plugin:ExamplePlugin",
  "dependencies": [],
  "permissions": []
}
```

字段解释：

- `entry_point`：`<module>:<class>`（供加载器定位类；实际解析方式可在落地时统一）
- `permissions`：建议与安全层对齐（文件/网络/系统命令等）

## 5. 新建插件的推荐流程（以模板为起点）

仓库提供插件模板骨架：`plugins/development_tools/plugin_sdk/development_templates/`。建议流程：

1. 选择模板：`basic_plugin` / `ai_plugin` / `integration_plugin`
2. 复制为新目录（建议放入 `plugins/community/<your_plugin>/`）
3. 填写 `manifest.json`（见上一节）
4. 实现最小接口 `activate/deactivate/get_info`
5. 如涉及外部网络/文件/系统能力，先通过安全扫描并在 `permissions` 中声明

## 6. 安全与合规约束（与安全文档联动）

- 插件代码应遵循“最小权限原则”，优先使用内置能力或受控 API，而非直接访问系统资源。
- 插件上线前建议运行安全扫描（相关代码：`plugins/core/security_validator.py`），并对高风险能力（网络请求/文件读写/子进程执行）做显式审批与审计记录。
- 系统级安全策略参见：`docs/architecture/security_architecture.md` 与 `docs/security/*`。

## 7. API 网关插件系统（差异说明）

`application/api_gateway/plugin_system.py` 定义了更细粒度的钩子系统（如 `BEFORE_REQUEST/AFTER_RESPONSE` 等），但其默认插件目录为 `plugins/system/` 与 `plugins/user/`，与当前仓库 `plugins/official` 等目录尚未对齐。  
若要启用网关插件体系，建议先完成目录与 manifest 约定的统一，并补齐文档与加载路径。

## 8. 已知限制（当前仓库真实情况）

- `plugins/core/plugin_manager.py` 的安装/依赖/热更新流程仍包含 TODO，占位逻辑不代表最终行为。
- 模板目录内部分文件为空（需要补齐模板内容才能形成端到端开发体验）。

本文件用于“规范 + 现状约束”，任何插件框架接口/目录约定变更都必须同步更新本文档，避免调用方与贡献者被误导。

## 9. 开发落地要求（2026-03-30 补充）

插件体系继续推进时，必须优先统一：

- 目录结构
- manifest 字段
- 生命周期钩子
- 权限声明与审计口径

这些基础约定未稳定前，不应对外宣称插件开发体验已经完整交付。
