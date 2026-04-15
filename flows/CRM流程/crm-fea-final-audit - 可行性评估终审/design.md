# crm-fea-final-audit 可行性评估终审

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `crm-fea-final-audit` |
| 所属模块 | CRM |
| 表单类型 | 自定义表单 |
| 发起页面 | `/crm/fea/create` |
| 查看页面 | `/crm/fea/get` |
| businessKey | `feaId` |

## 流程节点

```
开始 → [终审审批] → 结束
```

| 节点 | 类型 | 审批人策略 | 说明 |
|------|------|-----------|------|
| 终审审批 | UserTask | `35` 发起人自选 | 发起时选定终审人 |

## 后端监听

### BPM侧（bpm-server）

```java
// CrmFeaEndListener.java
getProcessDefinitionKey() → "crm-fea-final-audit"
onEvent() → POST http://crm-server/rpc-api/crm/fea/end-audit
```

### 业务侧（crm-server）

```java
// CrmFeaServiceImpl.endFeaUpdate()
// 接收事件，更新 fea.auditStatus、fea.feaFinalResult、fea.feaStatus
```

**状态流转：**
- APPROVE → 最终判定通过，feaFinalResult=bpmResult，更新最终状态
- REJECT → 最终判定拒绝

## 设计要点

- 与 `crm-fea-audit` 是两个独立流程，通过业务逻辑串联（初审通过后发起终审）
- 终审结果直接写入 `fea.feaFinalResult`，是整个评估的最终结论
- 节点结构极简，只有一个审批节点
