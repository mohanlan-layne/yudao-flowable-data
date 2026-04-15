# pdp_plan_doc_spare_parts 备品申请

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_doc_spare_parts` |
| 计划类型 | 【文档】备品申请 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [TPM审核] → [报价审核] → [业务跟单] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传备品申请资料 |
| Activity_tpm | TPM审核 | `10` 角色 | TPM角色ID | TPM角色审核 |
| Activity_quote | 报价审核 | `10` 角色 | 报价角色ID | 报价角色审核 |
| Activity_business | 业务跟单 | `10` 角色 | 业务跟单角色ID | 业务跟单角色确认 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_doc_spare_parts`。

## 设计要点

- 节点最多的流程，四个节点串行推进
- TPM审核、报价审核、业务跟单三个角色ID均需在 BPMN 配置时确认
- 无计划负责人节点，以业务跟单作为最终闭环节点
