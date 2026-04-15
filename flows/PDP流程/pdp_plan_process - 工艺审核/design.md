# pdp_plan_process 工艺审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_process` |
| 计划类型 | 【流程】工艺审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [工艺审核] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传资料 |
| Activity_process | 工艺审核 | `10` 角色 | 工艺角色ID | 工艺角色固定审核 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_process`。

## 设计要点

- 两节点，执行后直接由工艺角色审核，无需计划负责人二次确认
- 工艺审核角色ID需在 BPMN 配置时确认并填入 `candidateParam`
- 无 `PdpPlanChargeUser` 变量
