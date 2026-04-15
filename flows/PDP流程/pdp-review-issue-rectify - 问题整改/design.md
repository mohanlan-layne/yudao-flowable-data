# pdp-review-issue-rectify 问题整改（子流程）

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp-review-issue-rectify` |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| businessKey | `issueId`（问题单ID） |
| 发起方式 | **不由用户手动发起**，由评审主流程 ServiceTask 批量触发 |

## 流程节点

```
开始 → [问题整改]（发起人自选）→ [问题确认]（发起人自己）→ 完成
```

| 节点 | 类型 | 审批人策略 | 说明 |
|------|------|-----------|------|
| 问题整改 | UserTask | `35` 发起人自选 | 整改执行人，发起时选定 |
| 问题确认 | UserTask | `36` 发起人自己 | 由流程发起人（评审负责人）确认整改结果 |

## 后端监听

### BPM侧（bpm-server）

```java
// PdpReviewIssueRectifyStatusListener.java
getProcessDefinitionKey() → "pdp-review-issue-rectify"

// 关键设计：必须在事务提交后再通知 pdp-server（afterCommit）
// 原因：主流程 ReceiveTask 在 BPM 事务提交前尚未激活，trigger 会失败
onEvent() → 事务提交后（afterCommit）POST:
  http://pdp-server/rpc-api/pdp/review-issue/on-sub-process-completed
    ?issueId={businessKey}&bpmStatus={status}
  携带 tenant-id header（从事务前预取，afterCommit 时上下文已清空）
```

### 业务侧（pdp-server）

```java
// on-sub-process-completed 接口
// 1. 更新 reviewIssue.rectifyStatus
// 2. 检查该 review 下所有问题单是否全部完成
// 3. 若全部完成，调用 RPC /bpm/process-instance/trigger-receive-task
//    推进主流程的 ReceiveTask（Activity_0uxzs0b）
```

## 与主流程的协作关系

```
主流程 pdp-review_udit2
  ↓ ServiceTask（CreateSubProcessListener）
  ↓ POST /start-rectify-sub-processes?reviewId=&mainProcessInstanceId=&receiveTaskActivityId=Activity_0uxzs0b
pdp-server 批量发起子流程（每个 issue 一个实例）
  ↓ 每个子流程完成后回调 on-sub-process-completed
pdp-server 检查所有子流程完成
  ↓ 调用 BPM RPC trigger-receive-task
主流程 ReceiveTask 被触发，推进到结束
```

## 设计要点

- 这是一个**纯子流程**，不出现在流程列表供用户发起
- `afterCommit` 是关键设计：避免主流程 ReceiveTask 在 BPM 事务未提交前被触发失败
- tenant-id 需要在事务内预读，因为 afterCommit 时 TenantContext 已被清空 → 详见 [tenant-context-in-async.md](../../../docs/tenant-context-in-async.md)
- businessKey = issueId（不是 reviewId），每个问题单对应独立的流程实例
