# 插件开发指南（Plugin Development）

版本：v2.0
最后更新：2026-03-16

## 1. 插件体系概述

Mirexs 插件系统支持热插拔扩展，用于增加新能力、工作流或 UI 行为。

## 2. 插件目录结构

```
plugins/
  user/
    my_plugin/
      manifest.json
      main.py
      assets/
```

## 3. manifest.json 规范

```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "示例插件",
  "author": "You",
  "license": "MIT",
  "entry_point": "main.py",
  "dependencies": [],
  "hooks": ["on_startup", "before_request"],
  "permissions": ["tool:execute"],
  "min_api_version": "1.0.0"
}
```

字段说明：
- `hooks`：声明可用钩子
- `permissions`：声明权限
- `dependencies`：插件依赖

## 4. 生命周期钩子

- `on_startup` / `on_shutdown`
- `before_request` / `after_request`
- `authenticate` / `authorize`
- `before_create` / `after_create`
- `before_update` / `after_update`

## 5. 插件示例

```python
class Plugin:
    __plugin__ = True

    def on_startup(self):
        print("Plugin started")

    def before_request(self, request):
        return request
```

## 6. 安全与隔离

- 插件运行在沙箱
- 权限需显式声明

## 7. 调试与测试

- 使用本地开发模式加载
- 通过日志查看钩子执行情况

---

本指南为契约优先文档。
