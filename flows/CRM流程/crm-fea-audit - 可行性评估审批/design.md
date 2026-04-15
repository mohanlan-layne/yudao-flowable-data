# crm-fea-audit 可行性评估审批

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `crm-fea-audit` |
| 所属模块 | CRM |
| 表单类型 | 自定义表单 |
| 发起页面 | `/crm/fea/create` |
| 查看页面 | `/crm/fea/get` |
| businessKey | `feaId`（可行性评估ID） |

## 流程节点

```
开始 → [审批人] → 结束
```

| 节点 | 类型 | 审批人策略 | 说明 |
|------|------|-----------|------|
| 审批人 | UserTask | `35` 发起人自选 | 发起时由申请人手动选择审批人 |

## 后端监听

### BPM侧（bpm-server）

```java
// CrmFeaStatusListener.java
getProcessDefinitionKey() → "crm-fea-audit"
onEvent() → POST http://crm-server/rpc-api/crm/fea/update-audit-status
```

### 业务侧（crm-server）

```java
// CrmFeaServiceImpl.updateFeaAuditStatus()
// 接收 BpmProcessInstanceStatusEvent，更新 fea 的 auditStatus 和各评估项状态
```

**状态流转：**
- RUNNING → 审批中
- APPROVE → 审批通过，更新评估项状态
- REJECT → 审批拒绝

## 发起方式

```java
// CrmFeaServiceImpl.java
BpmProcessInstanceCreateReqDTO reqDTO = new BpmProcessInstanceCreateReqDTO()
    .setProcessDefinitionKey("crm-fea-audit")
    .setBusinessKey(String.valueOf(feaId))
    .setVariables(variables)
    .setStartUserSelectAssignees(startUserSelectAssignees); // key=节点ID, value=[审批人userId]
```

## 前端页面

- 列表：`/views/crm/feasibility/index.vue`
- 详情：`/views/crm/feasibility/detail/index.vue`
- 表单：`/views/crm/feasibility/modules/form.vue`

## 设计要点

- 审批人在发起时选择，适合评估人不固定的场景
- 每个评估人对应一个流程实例（按评估人分组批量发起）
- 节点完成无额外 taskListener，流程结束事件统一处理状态
