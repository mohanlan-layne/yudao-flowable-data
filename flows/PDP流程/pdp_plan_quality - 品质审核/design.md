# pdp_plan_quality 品质审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_quality` |
| 计划类型 | 【流程】品质审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行] → [上级审核] → [品质确认] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行 | `60` 流程表达式 | `${executorUserId}` | 计划执行人 |
| Activity_superior | 上级审核 | `39` 直属领导 | - | 执行人的直属上级 |
| Activity_quality | 品质确认 | `10` 角色 | 品质角色ID | 品质角色固定确认 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_quality`。

## 设计要点

- 三节点：执行 → 直属上级 → 品质角色，流程以品质确认作为终点
- 品质确认角色ID需在 BPMN 配置时确认并填入 `candidateParam`
- 无 `PdpPlanChargeUser` 变量，由品质角色作为终审
