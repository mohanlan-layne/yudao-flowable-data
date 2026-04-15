# pdp_plan_doc_purchase 采购审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_doc_purchase` |
| 计划类型 | 【文档】采购审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [主管审核] → [采购确认] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传采购相关文档 |
| Activity_superior | 主管审核 | `39` 直属领导 | - | 执行人的直属上级 |
| Activity_purchase | 采购确认 | `10` 角色 | 采购角色ID | 采购角色固定确认 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_doc_purchase`。

## 设计要点

- 三节点：执行上传 → 主管审核 → 采购角色确认
- 采购角色ID需在 BPMN 配置时确认并填入 `candidateParam`
- 主管审核用策略 39（直属领导）
