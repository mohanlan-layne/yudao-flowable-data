# pdp_plan_pmc PMC审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_pmc` |
| 计划类型 | 【流程】PMC审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行] → [计划负责人] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行 | `60` 流程表达式 | `${executorUserId}` | 计划执行人 |
| Activity_charge | 计划负责人 | `60` 流程表达式 | `${PdpPlanChargeUser}` | 来源计划的负责人 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |
| `PdpPlanChargeUser` | Long | 计划负责人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_pmc`。

## 设计要点

- 最简两节点结构，与 `pdp_plan_common` 结构完全相同
- PMC 无需上级审核，直接由计划负责人确认即可
- BPMN 可直接复制 `pdp_plan_common` 修改 key 和 name
