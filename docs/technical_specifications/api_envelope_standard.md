---
status: partial
last_reviewed: 2026-03-30
corresponds_to_code: "application/api_gateway/response_formatter.py"
related_issues: ""
references: "docs/technical_specifications/api_specification.md"
---
# API 响应封装规范

## 1. 目标

本规范定义 Mirexs 所有 HTTP API 的统一响应外壳，确保客户端、SDK、测试脚本和日志系统都能用一致方式解析返回值。

## 2. 设计原则

- 同一类成功响应必须有统一结构
- 错误响应必须包含可定位和可程序处理的信息
- Envelope 与业务数据分离，避免每个接口自己发明格式
- 状态码、错误码和消息必须相互一致

## 3. 成功响应结构

建议所有成功响应遵循以下结构：

```json
{
  "status": "success",
  "code": 200,
  "message": "Success",
  "timestamp": 1711771200.123,
  "data": {},
  "meta": {}
}
```

字段说明：

- `status`：固定为 `success`
- `code`：建议与 HTTP 状态码一致
- `message`：简短可读说明
- `timestamp`：服务端生成时间戳
- `data`：实际业务数据
- `meta`：可选元数据，例如分页、追踪 ID、耗时

## 4. 失败响应结构

建议失败响应遵循以下结构：

```json
{
  "status": "fail",
  "code": 422,
  "message": "Validation failed",
  "timestamp": 1711771200.123,
  "errors": [
    {
      "field": "name",
      "message": "Field is required",
      "code": "required",
      "value": null
    }
  ]
}
```

对于不可恢复的服务端异常，可使用：

```json
{
  "status": "error",
  "code": 500,
  "message": "Internal error",
  "timestamp": 1711771200.123
}
```

## 5. 状态值约定

- `success`：请求成功
- `fail`：客户端可修正问题，例如参数校验失败
- `error`：服务端异常或不可恢复问题
- `warning`：成功但附带降级、部分结果或提示信息

## 6. `errors[]` 结构要求

`errors` 数组元素建议包含：

- `field`：出错字段
- `message`：错误描述
- `code`：稳定错误码
- `value`：触发错误的值，若安全可返回

## 7. 使用要求

- 所有新接口必须复用统一格式化器
- 不允许某个接口返回裸对象，另一个接口返回自定义包裹结构
- 如果业务场景需要分页、追踪或调试信息，应写入 `meta`，而不是污染 `data`

## 8. 与代码对齐说明

当前仓库中统一响应格式由 `application/api_gateway/response_formatter.py` 负责。若代码实现与本文档不同，应以代码真实行为为准，并在同一变更中同步修正文档。
