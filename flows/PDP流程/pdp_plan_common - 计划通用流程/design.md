# pdp_plan_common 计划通用流程

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_common` |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| 发起页面 | `/crm/fea/create`（⚠️ 疑似沿用CRM配置，待确认） |
| 查看页面 | `/crm/fea/get`（⚠️ 同上） |
| businessKey | `planId` |

## 流程节点

```
开始 → [执行]（流程变量指定人）→ [计划负责人]（流程变量指定人）→ 结束
```

| 节点 | 类型 | 审批人策略 | 变量名 | 说明 |
|------|------|-----------|--------|------|
| 执行 | UserTask | `60` 流程表达式 | `${executorUserId}` | 计划执行人，发起时传入 |
| 计划负责人 | UserTask | `60` 流程表达式 | `${PdpPlanChargeUser}` | 计划负责人确认，发起时传入 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |
| `PdpPlanChargeUser` | Long | 计划负责人用户ID |

## 后端监听

### 业务侧（pdp-server）

```java
// AbstractPlanProcessStatusListener（抽象基类）
// PlanDefMainProcessStatusListener 等子类监听具体的 pdp_plan_xxx key
// 前缀约定：所有 pdp_plan_ 开头的流程共用同一套状态处理逻辑

APPROVE → plan.status = 5（已完成），设置 completedTime
REJECT  → 仅更新 auditStatus
CANCEL  → 仅更新 auditStatus
```

## 设计要点

- 这是一个**通用模板**，所有 `pdp_plan_` 前缀的流程共用 `AbstractPlanProcessStatusListener`
- 审批人完全由流程变量决定，不在 BPMN 中硬编码，灵活性高
- 两个节点：执行（做事的人）→ 负责人（确认的人），是典型的执行-确认两阶段模式
- 如需特殊逻辑，子类重写 `onProcessCompleted` 方法扩展
