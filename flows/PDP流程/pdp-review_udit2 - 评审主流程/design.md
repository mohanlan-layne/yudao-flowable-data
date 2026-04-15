# pdp-review_udit2 评审主流程

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp-review_udit2` |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `reviewId` |

## 流程节点

```
开始
  → [主管审批]（发起人自选，单人）
  → [召集评审]（角色组ID=1，并行多实例，任一完成即推进）
  → [评审判断]（流程变量${reviewJudgeAssignees}，并行多实例，任一完成）
  → [问题整改触发] ServiceTask
  → [问题整改完成] ReceiveTask（等待所有子流程回调）
  → 结束
```

| 节点ID | 节点名 | 类型 | 审批人策略 | 说明 |
|--------|--------|------|-----------|------|
| Activity_1rjbckl | 主管审批 | UserTask | `35` 发起人自选 | 完成时触发 taskListener |
| Activity_0ebfrvl | 召集评审 | UserTask | `10` 角色(ID=1) | 并行多实例，任一完成推进 |
| Activity_1336e53 | 评审判断 | UserTask | `60` 表达式`${reviewJudgeAssignees}` | 并行多实例，任一完成推进 |
| Activity_0kdeurx | 问题整改(触发) | ServiceTask | - | 调用`CreateSubProcessListener` |
| Activity_0uxzs0b | 问题整改(完成) | ReceiveTask | - | 等子流程全部完成后被主动触发 |

## 节点监听器

### 主管审批节点完成（taskListener on complete）

```
BPMN 配置：
  delegateExpression: ${bpmUserTaskListener}
  field listenerConfig: {"enable":true,"path":"http://pdp-server/rpc-api/pdp/review/on-node-completed","header":[],"body":[]}

回调接口：POST /rpc-api/pdp/review/on-node-completed
  ?processInstanceId=xxx&taskDefinitionKey=Activity_1rjbckl
```

触发时机：主管审批节点完成时，同步通知 pdp-server 推进业务状态。

## 后端监听

### BPM侧（bpm-server）

```java
// PdpReviewAuditStatusListener.java
getProcessDefinitionKey() → "pdp-review_udit2"
onEvent() → POST http://pdp-server/rpc-api/pdp/review/update-audit-status
```

### 业务侧（pdp-server）

```java
// ReviewAuditStatusListener.java（同时也是 RPC Controller）
// 整流程状态回调
POST /rpc-api/pdp/review/update-audit-status:
  APPROVE → review.status = 50（评估完成）
  REJECT  → review.status = 10（待主管审核）
  CANCEL  → 仅更新 auditStatus

// 节点完成回调
POST /rpc-api/pdp/review/on-node-completed?processInstanceId=&taskDefinitionKey=:
  Activity_1rjbckl（主管审批）→ review.status = 20（待召集）
  Activity_0ebfrvl（召集评审）→ review.status = 30（评审中）
  其他节点                   → 不改 status
```

### ServiceTask: CreateSubProcessListener

```java
// CreateSubProcessListener.java（bpm-server JavaDelegate）
// 在"问题整改触发"节点执行，通过 businessKey(=reviewId) 通知 pdp-server 批量发起问题整改子流程

POST http://pdp-server/rpc-api/pdp/review-issue/start-rectify-sub-processes
  ?reviewId={businessKey}
  &mainProcessInstanceId={processInstanceId}
  &receiveTaskActivityId=Activity_0uxzs0b
```

## 流程变量

| 变量名 | 类型 | 来源 | 用途 |
|--------|------|------|------|
| `reviewJudgeAssignees` | List\<Long\> | 发起时传入 | 评审判断节点的审批人列表 |
| `coll_userList` | List | 系统生成 | 多实例集合变量 |

## 子流程关联

与 `pdp-review-issue-rectify` 联动：
- ServiceTask 触发后，pdp-server 为每个问题单发起一个子流程实例
- 所有子流程完成后，通过 RPC `/bpm/process-instance/trigger-receive-task` 推进主流程 ReceiveTask

## review.status 状态流转

```
10（待主管审核）
  → [发起流程]
  → 主管审批完成 → 20（待召集）
  → 召集评审完成 → 30（评审中）
  → 评审判断完成 → 触发问题整改子流程
  → 所有子流程完成 → 流程结束 APPROVE → 50（评估完成）
  → 任意节点 REJECT → 10（回到待主管审核）
```

## 设计要点

- 召集评审和评审判断都是**并行多实例、任一完成**（一人代表多人决策场景）
- ReceiveTask 是 Flowable 的等待模式，必须外部主动调用 `trigger-receive-task` 才能推进
- taskListener 用于节点级的状态推进（比整流程监听粒度更细）
- 节点完成回调必须是同步的，整流程监听用异步 afterCommit 避免事务问题
