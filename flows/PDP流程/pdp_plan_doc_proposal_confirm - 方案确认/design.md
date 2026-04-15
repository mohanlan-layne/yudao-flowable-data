# pdp_plan_doc_proposal_confirm 方案确认

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_doc_proposal_confirm` |
| 计划类型 | 【文档】方案确认 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [TPM] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传方案文档 |
| Activity_tpm | TPM | `10` 角色 | TPM角色ID | TPM角色确认方案 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_doc_proposal_confirm`。

## 设计要点

- 两节点，TPM角色作为终审
- TPM角色ID需在 BPMN 配置时确认并填入 `candidateParam`
- 与 `pdp_doc_spare_parts` 中的 TPM审核节点使用同一角色
