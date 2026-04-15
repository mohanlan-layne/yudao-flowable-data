# pdp_plan_doc_pqa PQA审核

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_doc_pqa` |
| 计划类型 | 【文档】PQA审核 |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行上传] → [PQA确认] → 结束
```

| 节点ID | 节点名 | 审批人策略 | 参数 | 说明 |
|--------|--------|-----------|------|------|
| Activity_execute | 执行上传 | `60` 流程表达式 | `${executorUserId}` | 执行并上传文档 |
| Activity_pqa | PQA确认 | `10` 角色 | PQA角色ID | PQA角色固定确认 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |

## 后端监听

复用 `AbstractPlanProcessStatusListener` 基类逻辑，监听 key = `pdp_plan_doc_pqa`。

## 设计要点

- 两节点，PQA角色作为终审
- PQA角色ID需在 BPMN 配置时确认并填入 `candidateParam`
- 与 `pdp_doc_pqe` 结构相同，仅角色不同
