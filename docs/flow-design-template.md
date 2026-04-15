# 流程设计模板

> 基于现有流程归纳，设计新流程时参考此模板。

---

## 一、审批人策略速查

| 策略码 | 名称 | 参数 | 使用场景 |
|--------|------|------|---------|
| `10` | 角色 | 角色ID | 固定角色审批（如评审专家组） |
| `20` | 部门成员 | 部门ID | 指定部门所有人 |
| `21` | 部门负责人 | 部门ID | 指定部门负责人 |
| `30` | 用户 | 用户ID | 指定固定用户 |
| `35` | 发起人自选 | 无 | 发起时由申请人选择审批人 |
| `36` | 发起人自己 | 无 | 回到申请人本人（确认/知会场景） |
| `39` | 直属领导 | 无 | 自动取发起人的直属领导 |
| `60` | 流程表达式 | EL表达式 | 审批人由业务逻辑动态传入（推荐） |

---

## 二、常见节点模式

### 模式1：简单单人审批
```
开始 → [审批] (35=发起人自选) → 结束
```
参考：`crm-fea-audit`、`crm-fea-final-audit`

### 模式2：执行-确认两阶段
```
开始 → [执行] (60=${executorUserId}) → [负责人确认] (60=${chargeUserId}) → 结束
```
参考：`pdp_plan_common`

### 模式3：多级串行审批
```
开始 → [主管审批] (35) → [部门审批] (21) → [总经理审批] (30) → 结束
```

### 模式4：并行多实例（任一通过）
```xml
<multiInstanceLoopCharacteristics isSequential="false" flowable:collection="${coll_userList}">
  <completionCondition>${ nrOfCompletedInstances > 0 }</completionCondition>
</multiInstanceLoopCharacteristics>
```
参考：`pdp-review_udit2` 召集评审、评审判断节点

### 模式5：主流程 + 子流程（ReceiveTask 等待）
```
主流程：→ [ServiceTask 触发子流程] → [ReceiveTask 等待] → 结束
子流程：由 JavaDelegate 批量发起，完成后调用 trigger-receive-task 推进主流程
```
参考：`pdp-review_udit2` + `pdp-review-issue-rectify`

---

## 三、节点监听器配置

### taskListener（节点完成时回调业务系统）
```xml
<flowable:taskListener event="complete" delegateExpression="${bpmUserTaskListener}">
  <flowable:field name="listenerConfig">
    <flowable:expression>
      <![CDATA[{"enable":true,"path":"http://xxx-server/rpc-api/xxx/on-node-completed","header":[],"body":[]}]]>
    </flowable:expression>
  </flowable:field>
</flowable:taskListener>
```
- `event`：`create`（创建时）/ `complete`（完成时）/ `assignment`（分配时）
- `path`：业务服务的 RPC 接口，接收 `processInstanceId` 和 `taskDefinitionKey`

---

## 四、后端监听器模板

### BPM侧（bpm-server，HTTP转发）

```java
// 整流程状态监听 → 转发给业务服务
public class XxxStatusListener extends BpmProcessInstanceStatusEventListener {
    @Override
    public String getProcessDefinitionKey() { return "xxx-process-key"; }

    @Override
    public void onEvent(BpmProcessInstanceStatusEvent event) {
        BpmHttpRequestUtils.executeBpmHttpRequest(event,
            "http://xxx-server/rpc-api/xxx/update-audit-status",
            loadBalancedRestTemplate);
    }
}
```

### 业务侧（xxx-server，状态处理）

```java
// 整流程状态回调
POST /rpc-api/xxx/update-audit-status:
  RUNNING → 更新 auditStatus=RUNNING
  APPROVE → 更新业务状态为"完成"
  REJECT  → 更新业务状态为"拒绝/退回"
  CANCEL  → 仅更新 auditStatus

// 节点完成回调（可选）
POST /rpc-api/xxx/on-node-completed?processInstanceId=&taskDefinitionKey=:
  switch(taskDefinitionKey) {
    case "Activity_xxx": → 推进到状态A
    case "Activity_yyy": → 推进到状态B
  }
```

---

## 五、发起流程模板

```java
// 业务服务发起流程
BpmProcessInstanceCreateReqDTO reqDTO = new BpmProcessInstanceCreateReqDTO()
    .setProcessDefinitionKey("xxx-process-key")   // 流程Key
    .setBusinessKey(String.valueOf(bizId))          // 业务ID
    .setVariables(Map.of(                           // 流程变量
        "executorUserId", executorId,
        "chargeUserId", chargeId
    ))
    .setStartUserSelectAssignees(Map.of(            // 发起人自选审批人（35策略时使用）
        "Activity_nodeId", List.of(userId)
    ));
String processInstanceId = bpmProcessInstanceApi.createProcessInstance(loginUserId, reqDTO).getCheckedData();
```

---

## 六、设计文档结构

每个流程的 `design.md` 应包含：

```markdown
# {key} {流程名称}

## 基本信息（Key、模块、表单类型、businessKey）
## 流程节点（ASCII图 + 节点表格）
## 节点监听器（taskListener配置和回调接口）
## 后端监听（BPM侧 + 业务侧）
## 流程变量（变量名、类型、用途）
## 子流程关联（如有）
## 业务状态流转（status 变化时序）
## 设计要点（非标准设计、坑、注意事项）
```

---

## 七、注意事项总结

1. **afterCommit 问题**：子流程完成后通知主流程 trigger-receive-task，必须在 BPM 事务提交后执行，否则 ReceiveTask 尚未激活
2. **tenant-id 传递**：异步场景（afterCommit、MQ消费、HTTP回调）中 TenantContext 会丢失，需提前捕获或从请求头读取，详见 [tenant-context-in-async.md](./tenant-context-in-async.md)
3. **businessKey 设计**：每个业务实体对应一个流程实例，businessKey = 业务主键ID（String类型）
4. **并行多实例**：任一完成用 `nrOfCompletedInstances > 0`，全部完成用 `nrOfCompletedInstances >= nrOfInstances`
5. **ReceiveTask**：需要业务系统主动调用 `/rpc-api/bpm/process-instance/trigger-receive-task` 才能推进，不会自动完成
6. **RPC 跨服务调用**：在 `executeIgnore` 包裹的代码中调用 bpm-server 会因租户为空导致流程定义查不到，必须改用 `TenantUtils.execute(tenantId, ...)`
