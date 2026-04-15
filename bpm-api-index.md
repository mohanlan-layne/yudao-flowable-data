# BPM API 索引

**Base URL:** `http://192.168.1.182:31084`  
**Auth:** 请求头 `Authorization: Bearer <token>`

---

## 流程模型

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/model/create` | 新建模型 |
| PUT | `/admin-api/bpm/model/update` | 修改模型 |
| PUT | `/admin-api/bpm/model/update-bpmn` | 修改模型的 BPMN XML |
| PUT | `/admin-api/bpm/model/update-state` | 修改模型状态（激活/挂起） |
| PUT | `/admin-api/bpm/model/update-sort-batch` | 批量修改排序 |
| POST | `/admin-api/bpm/model/deploy` | 部署模型 `?id=` |
| GET | `/admin-api/bpm/model/list` | 获得模型分页列表 |
| GET | `/admin-api/bpm/model/get` | 获得模型 `?id=` |
| POST | `/admin-api/bpm/model/simple/update` | 保存仿钉钉设计模型 |
| GET | `/admin-api/bpm/model/simple/get` | 获得仿钉钉设计模型 `?modelId=` |
| DELETE | `/admin-api/bpm/model/delete` | 删除模型 `?id=` |
| DELETE | `/admin-api/bpm/model/clean` | 清理模型 |

**创建/更新模型 Body (`BpmModelSaveReqVO`):**
```json
{
  "key": "string*",         // 流程标识（唯一）
  "name": "string*",        // 流程名称
  "category": "string",     // 流程分类
  "type": 1,                // 流程类型 1=BPMN 2=仿钉钉
  "formType": 1,            // 表单类型 1=动态表单 2=自定义表单
  "formId": 1,              // 动态表单ID（formType=1时）
  "visible": true,          // 是否可见
  "managerUserIds": [],     // 可管理用户ID数组*
  "bpmnXml": "string",     // BPMN XML（type=1时）
  "simpleModel": {}         // 仿钉钉模型（type=2时）
}
```

---

## 流程定义

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/bpm/process-definition/page` | 分页列表 |
| GET | `/admin-api/bpm/process-definition/list` | 全量列表 `?key=` |
| GET | `/admin-api/bpm/process-definition/simple-list` | 精简列表 |
| GET | `/admin-api/bpm/process-definition/get` | 获得定义 `?id=` |

---

## 流程实例

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/process-instance/create` | 发起流程 |
| GET | `/admin-api/bpm/process-instance/my-page` | 我发起的实例列表 |
| GET | `/admin-api/bpm/process-instance/manager-page` | 管理员查看全部 |
| GET | `/admin-api/bpm/process-instance/get` | 获得实例 `?id=` |
| GET | `/admin-api/bpm/process-instance/get-approval-detail` | 审批详情 `?id=` |
| GET | `/admin-api/bpm/process-instance/get-bpmn-model-view` | BPMN视图 `?id=` |
| POST | `/admin-api/bpm/process-instance/get-next-approval-nodes` | 获取下一节点 |
| DELETE | `/admin-api/bpm/process-instance/cancel-by-start-user` | 发起人取消 |
| DELETE | `/admin-api/bpm/process-instance/cancel-by-admin` | 管理员取消 |
| GET | `/admin-api/bpm/process-instance/copy/page` | 抄送列表 |

**发起流程 Body (`BpmProcessInstanceCreateReqVO`):**
```json
{
  "processDefinitionId": "string*",   // 流程定义ID
  "variables": {},                     // 动态表单变量
  "startUserSelectAssignees": {}       // 发起人自选审批人 {nodeId: [userId]}
}
```

**取消流程 Body (`BpmProcessInstanceCancelReqVO`):**
```json
{
  "id": "string*",      // 实例ID
  "reason": "string*"   // 取消原因
}
```

---

## 流程任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin-api/bpm/task/todo-page` | 待办任务 |
| GET | `/admin-api/bpm/task/done-page` | 已办任务 |
| GET | `/admin-api/bpm/task/manager-page` | 全部任务（管理） |
| GET | `/admin-api/bpm/task/list-by-process-instance-id` | 按实例ID查任务 `?processInstanceId=` |
| GET | `/admin-api/bpm/task/list-by-parent-task-id` | 子任务列表 `?parentTaskId=` |
| GET | `/admin-api/bpm/task/list-by-return` | 可退回节点列表 `?taskId=` |
| PUT | `/admin-api/bpm/task/approve` | 通过任务 |
| PUT | `/admin-api/bpm/task/reject` | 拒绝任务 |
| PUT | `/admin-api/bpm/task/transfer` | 转派任务 |
| PUT | `/admin-api/bpm/task/return` | 退回任务 |
| PUT | `/admin-api/bpm/task/delegate` | 委派任务 |
| PUT | `/admin-api/bpm/task/withdraw` | 撤回任务 |
| PUT | `/admin-api/bpm/task/copy` | 抄送任务 |
| PUT | `/admin-api/bpm/task/create-sign` | 加签 |
| DELETE | `/admin-api/bpm/task/delete-sign` | 减签 |

**通过任务 Body (`BpmTaskApproveReqVO`):**
```json
{
  "id": "string*",          // 任务ID
  "variables": {}/**/,      // 动态表单变量*（可为空对象）
  "reason": "string",       // 审批意见
  "nextAssignees": {}       // 下一节点审批人
}
```

**拒绝任务 Body (`BpmTaskRejectReqVO`):**
```json
{
  "id": "string*",      // 任务ID
  "reason": "string*"   // 拒绝原因
}
```

**转派 Body (`BpmTaskTransferReqVO`):**
```json
{
  "id": "string*",
  "assigneeUserId": 1,   // 新审批人用户ID
  "reason": "string*"
}
```

**退回 Body (`BpmTaskReturnReqVO`):**
```json
{
  "id": "string*",
  "targetTaskDefinitionKey": "string*",  // 退回目标节点Key
  "reason": "string*"
}
```

**委派 Body (`BpmTaskDelegateReqVO`):**
```json
{
  "id": "string*",
  "delegateUserId": 1,   // 被委派人ID
  "reason": "string*"
}
```

---

## 动态表单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/form/create` | 创建表单 |
| PUT | `/admin-api/bpm/form/update` | 更新表单 |
| GET | `/admin-api/bpm/form/page` | 分页列表 |
| GET | `/admin-api/bpm/form/get` | 获得表单 `?id=` |
| GET | `/admin-api/bpm/form/simple-list` | 精简列表 |
| DELETE | `/admin-api/bpm/form/delete` | 删除表单 `?id=` |

---

## 流程分类

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/category/create` | 创建分类 |
| PUT | `/admin-api/bpm/category/update` | 更新分类 |
| PUT | `/admin-api/bpm/category/update-sort-batch` | 批量更新排序 |
| GET | `/admin-api/bpm/category/page` | 分页列表 |
| GET | `/admin-api/bpm/category/get` | 获得分类 `?id=` |
| GET | `/admin-api/bpm/category/simple-list` | 精简列表 |
| DELETE | `/admin-api/bpm/category/delete` | 删除分类 `?id=` |

---

## 用户组

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/user-group/create` | 创建用户组 |
| PUT | `/admin-api/bpm/user-group/update` | 更新用户组 |
| GET | `/admin-api/bpm/user-group/page` | 分页列表 |
| GET | `/admin-api/bpm/user-group/get` | 获得用户组 `?id=` |
| GET | `/admin-api/bpm/user-group/simple-list` | 精简列表 |
| DELETE | `/admin-api/bpm/user-group/delete` | 删除 `?id=` |

---

## 流程监听器 / 表达式

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin-api/bpm/process-listener/create` | 创建监听器 |
| PUT | `/admin-api/bpm/process-listener/update` | 更新监听器 |
| GET | `/admin-api/bpm/process-listener/page` | 分页列表 |
| GET | `/admin-api/bpm/process-listener/get` | 获得 `?id=` |
| DELETE | `/admin-api/bpm/process-listener/delete` | 删除 `?id=` |
| POST | `/admin-api/bpm/process-expression/create` | 创建表达式 |
| PUT | `/admin-api/bpm/process-expression/update` | 更新表达式 |
| GET | `/admin-api/bpm/process-expression/page` | 分页列表 |
| GET | `/admin-api/bpm/process-expression/get` | 获得 `?id=` |
| DELETE | `/admin-api/bpm/process-expression/delete` | 删除 `?id=` |

---

## RPC 内部接口（仅内部调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/rpc-api/bpm/process-instance/create` | 创建实例 |
| POST | `/rpc-api/bpm/process-instance/set-variables` | 设置变量 |
| POST | `/rpc-api/bpm/process-instance/trigger-receive-task` | 触发ReceiveTask推进流程 |
| GET | `/rpc-api/bpm/process-instance/get-variables` | 获取变量 |
| DELETE | `/rpc-api/bpm/process-instance/cancel-by-start-user` | 取消实例 |

---

## 典型操作流程

```
1. 获取流程定义列表
   GET /admin-api/bpm/process-definition/list?key=xxx

2. 发起流程
   POST /admin-api/bpm/process-instance/create
   { processDefinitionId, variables }

3. 查询待办
   GET /admin-api/bpm/task/todo-page

4. 审批通过
   PUT /admin-api/bpm/task/approve
   { id, variables: {}, reason }

5. 审批拒绝
   PUT /admin-api/bpm/task/reject
   { id, reason }
```
