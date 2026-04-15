# pdp_plan_superior 上级审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_superior` |
| 计划类型 | 【流程】上级审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [上级审核] → [计划负责人] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传资料 |
| Activity_superior | 上级审核 | `39` 直属领导 | - | 执行人的直属上级 |
| Activity_charge | 计划负责人 | `60` 流程表达式 | `${PdpPlanChargeUser}` | 来源计划的负责人 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |
| `PdpPlanChargeUser` | Long | 计划负责人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_superior`。

## 设计要点

- 与 `pdp_plan_3d_refine` / `pdp_plan_outsource` 结构完全相同
- "执行上传"强调需要在执行节点上传附件/文档
- BPMN 可复制 `pdp_plan_3d_refine` 修改 key 和 name
