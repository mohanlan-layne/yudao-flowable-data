# pdp_plan_wire 线材审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_wire` |
| 计划类型 | 【流程】线材审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行] → [上级主管审核] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行 | `60` 流程表达式 | `${executorUserId}` | 计划执行人 |
| Activity_dept_leader | 上级主管审核 | `21` 部门负责人 | - | 执行人所属部门的负责人 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_wire`。

## 设计要点

- 两节点，以部门负责人审核作为终点，无计划负责人节点
- 上级主管审核用策略 `21`（部门负责人），不同于上级审核的 `39`（直属领导）
- 无 `PdpPlanChargeUser` 变量
