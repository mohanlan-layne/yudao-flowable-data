---
name: bpm-flow
description: "BPM 流程工程技能：在 yudao-flowable-data 仓库中创建/更新/部署流程，并自动化测试（发起→审批→回调验证）。适用于 yudao（Ruoyi-Vue-Plus）平台。"
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [bpm, flowable, yudao, workflow, testing, pdp, automation]
    related_skills: [kanban-worker]
---

# BPM 流程工程技能

本技能覆盖 yudao（Ruoyi-Vue-Plus 分支）BPM 流程的完整生命周期：

| 阶段 | 工具 | 说明 |
|------|------|------|
| 创建/更新 | `scripts/import.py` | 把本地 BPMN + model.json 推到目标环境 |
| 部署 | `scripts/bpm_ops.py deploy` | 激活流程定义，让用户可发起 |
| 测试 | `scripts/bpm_ops.py start/tasks/approve/reject/status` | 完整走审批链 |
| 验证回调 | `scripts/bpm_ops.py poll` | 等待业务状态被 BPM 回调更新 |

---

## 环境信息

| env | URL |
|-----|-----|
| dev  | http://192.168.1.182:30080 |
| test | http://192.168.1.182:30082 |
| uat  | http://192.168.1.182:30084 |
| prod | http://192.168.1.182:30086 |

登录账号：`admin / admin123`（各环境统一）

---

## 仓库获取

```bash
# 内网 Gitea（主推送通道）
REPO=http://192.168.30.14:9001/eastwinbip/codebase/yudao-flowable-data.git

cd ~/code/company
# 首次：
git clone $REPO
# 已有：
cd yudao-flowable-data && git pull
```

---

## 一、创建/更新流程模型

### 1.1 目录结构

```
{env}/
  {key} - {name}/         # key 含 / 用 - 替换，e.g. pdp_quotation_request - 报价需求单审批
    now/
      model.json
      {key}.bpmn
```

### 1.2 model.json 模板（自定义表单）

```json
{
  "description": "...",
  "type": 10,
  "formType": 20,
  "formCustomCreatePath": "/pdp/your-page/detail",
  "formCustomViewPath": "/pdp/your-page/detail",
  "visible": true,
  "h5Visible": false,
  "startUserIds": [],
  "startDeptIds": [],
  "managerUserIds": [1],
  "managerRoleIds": [1],
  "sort": 1000,
  "allowCancelRunningProcess": true,
  "allowWithdrawTask": false,
  "processIdRule": {"enable": false, "prefix": "", "infix": "", "postfix": "", "length": 5},
  "autoApprovalType": 0,
  "titleSetting": {"enable": false, "title": ""},
  "summarySetting": {"enable": false, "summary": []},
  "key": "your_flow_key",
  "name": "流程名称",
  "category": "PDP流程"
}
```

**铁律：**
- `formType: 10` = 动态表单（有 formId）；`formType: 20` = 自定义表单（有 formCustomCreatePath/ViewPath）
- 禁止在 model.json 写：`id, modelId, categoryName, formName, deploymentTime, suspensionState, createTime, processDefinition, startUsers, startDepts, bpmnXml, simpleModel, formConf, formFields`
- 改完必须先 **dry-run** 再正式推

### 1.3 BPMN 模板（两节点：开始 → 审批 → 结束）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:flowable="http://flowable.org/bpmn"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://flowable.org/bpmn"
             id="diagram_{KEY}">
  <process id="{KEY}" name="{NAME}" isExecutable="true">
    <startEvent id="Event_start"/>
    <userTask id="Activity_approve" name="审批">
      <extensionElements>
        <flowable:candidateStrategy><![CDATA[39]]></flowable:candidateStrategy>
        <flowable:candidateParam></flowable:candidateParam>
        <flowable:assignStartUserHandlerType>1</flowable:assignStartUserHandlerType>
        <flowable:rejectHandlerType>1</flowable:rejectHandlerType>
        <flowable:rejectReturnTaskId></flowable:rejectReturnTaskId>
        <flowable:assignEmptyHandlerType>1</flowable:assignEmptyHandlerType>
        <flowable:assignEmptyUserIds></flowable:assignEmptyUserIds>
      </extensionElements>
    </userTask>
    <sequenceFlow id="Flow_start_approve" sourceRef="Event_start" targetRef="Activity_approve"/>
    <endEvent id="Event_end"/>
    <sequenceFlow id="Flow_approve_end" sourceRef="Activity_approve" targetRef="Event_end"/>
  </process>
  <!-- BPMNDiagram 省略，import.py 推送时不需要渲染坐标 -->
</definitions>
```

### 1.4 candidateStrategy 完整对照表

来源：`yudao-cloud` 后端 `BpmTaskCandidateStrategyEnum`（源码为准，下表之前版本有误，30 曾被误标为"指定角色"，实际是"用户"）。

| 值 | 含义 | candidateParam |
|----|------|---------------|
| 1 | 审批人为空 | - |
| 10 | 角色 | 角色 ID，多个用逗号 |
| 20 | 部门的成员（含负责人） | 部门 ID |
| 21 | 部门的负责人 | 部门 ID |
| 22 | 岗位 | 岗位 ID |
| 23 | 连续多级部门的负责人 | 部门 ID |
| 30 | 用户 | 用户 ID，多个用逗号 |
| 34 | 审批人自身 | 空（当前审批人可在审批时选择下一节点审批人） |
| 35 | 发起人自选 | 空（申请人提交时自选此节点审批人） |
| 36 | 发起人自己 | 空 |
| 37 | 发起人部门负责人 | 空 |
| 38 | 发起人连续多级部门的负责人 | 空 |
| 39 | 直属领导 | 空 |
| 40 | 用户组 | 用户组 ID |
| 50 | 表单内用户字段 | 表单字段名（如 `driverUserId`） |
| 51 | 表单内部门负责人 | 表单字段名 |
| 60 | 流程表达式 | `${variableName}` |
| 70 | 团队成员 | 角色字典编号（多个用逗号），按流程变量 `bizType`+`bizId` 从 `DataPermissionApi.getDataPermissionListByBizAndRole` 查团队成员；发起流程时必须已把这两个变量写进流程实例，否则查不到人、静默无候选人 |
| 71 | 虚拟组织 | 虚拟组织相关 ID |

`copyStrategy`（抄送）复用同一套编码，字段名从 `candidate*` 换成 `copy*`（如 `copyStrategy`/`copyParam`）。

### 1.5 推送命令

```bash
cd ~/code/company/yudao-flowable-data

# dry-run（必须先跑）
python3 scripts/import.py --env dev --dry-run pdp_quotation_request

# 正式推送
python3 scripts/import.py --env dev pdp_quotation_request
```

---

## 二、部署流程

> import（创建/更新模型） ≠ deploy（发布为可发起的流程定义）。每次更新 BPMN 后都要重新 deploy。

```bash
python3 scripts/bpm_ops.py deploy --env dev pdp_quotation_request
# 输出: [deploy] 成功: key=pdp_quotation_request  modelId=<uuid>
```

---

## 三、自动化测试（完整审批链）

```bash
ENV=dev
KEY=pdp_quotation_request

# 1. 发起流程
python3 scripts/bpm_ops.py start --env $ENV $KEY --vars '{}'
# → processInstanceId=<uuid>  记录备用
PROC_ID=<粘贴>

# 2. 查待办任务
python3 scripts/bpm_ops.py tasks --env $ENV $PROC_ID
# → taskId=<uuid>  name=上级审批
TASK_ID=<粘贴>

# 3a. 审批通过
python3 scripts/bpm_ops.py approve --env $ENV $TASK_ID --reason '同意'

# 3b. 或拒绝
# python3 scripts/bpm_ops.py reject --env $ENV $TASK_ID --reason '材料不全'

# 4. 查流程状态
python3 scripts/bpm_ops.py status --env $ENV $PROC_ID
# 期望: status=2（已完成）或 3（已驳回）
```

---

## 四、验证 BPM 回调

BPM 审批通过/拒绝后，会调用业务服务的回调接口（`BpmProcessListener`），回调应更新业务单据状态。用 `poll` 等待并断言：

```bash
# 等待报价需求单 id=123 的 status 变为 3（已通过）
python3 scripts/bpm_ops.py poll \
  --url 'http://192.168.1.182:30080/admin-api/pdp/quotation-request/get?id=123' \
  --token <Bearer Token，从 bpm_common.login() 或登录接口获取> \
  --key data.status \
  --expect 3 \
  --timeout 30
```

超时未满足 → 回调接口出问题，查 yudao-cloud 服务日志：
```bash
grep -i "BpmProcessListener\|bpm.*callback\|quotation.*request.*bpm" <log_path>
```

---

## 五、提交规范

```bash
git add -A
git commit -m "feat(bpm/dev): add pdp_quotation_request flow"
git push origin master   # 或对应分支
```

---

## 常见问题

**Q: dry-run 通过但正式 import 报 XSS 过滤损坏 BPMN**  
A: 检查目标环境 `yudao.xss.exclude-urls` 是否包含 `/admin-api/bpm/model/create` 和 `/admin-api/bpm/model/update`

**Q: deploy 成功但 start 报找不到流程定义**  
A: deploy 后等 1-2s 再试；或检查 process-definition/list?key= 是否有返回

**Q: tasks 返回空列表但流程实例存在**  
A: `list-by-process-instance-id` 返回所有任务（含已完成），pending 筛选 `endTime==null`；如果连实例都查不到说明 candidateStrategy=39 找不到上级用户，检查用户的上级配置

**Q: poll 超时**  
A: 回调接口未注册或 processKey 不匹配；在 yudao-cloud 中确认 `@BpmProcessListenerComponent` 的 `processKey` 与流程 key 完全一致
