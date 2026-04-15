# pdp_plan_3d_refine 3D细化审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_3d_refine` |
| 计划类型 | 【流程】3D细化审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行] → [上级审核] → [计划负责人] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行 | `60` 流程表达式 | `${executorUserId}` | 计划执行人 |
| Activity_superior | 上级审核 | `39` 直属领导 | - | 执行人的直属上级 |
| Activity_charge | 计划负责人 | `60` 流程表达式 | `${PdpPlanChargeUser}` | 来源计划的负责人 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID，系统发起时传入 |
| `PdpPlanChargeUser` | Long | 计划负责人用户ID，系统发起时传入 |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑：
- APPROVE → plan.status = 5（已完成），设置 completedTime
- REJECT → 仅更新 auditStatus
- CANCEL → 仅更新 auditStatus

需在 pdp-server 新增对应子类，监听 key = `pdp_plan_3d_refine`。

## 设计要点

- 三节点标准流程：执行 → 直属上级审核 → 计划负责人确认
- 上级审核用策略 39（直属领导），自动取执行人的直属上级，无需发起时传入
- 工艺审核、品质确认等专项角色本流程不涉及，如需可参考品质审核流程
