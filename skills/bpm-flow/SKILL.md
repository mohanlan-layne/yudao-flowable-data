---
name: bpm-flow
description: "BPM 流程工程技能：在 yudao-flowable-data 仓库里创建/更新/对比/跨环境同步/部署/测试 BPM 流程。本仓库只存流程定义数据(BPMN+model.json)，业务前后端代码在 yudao-cloud / yudao-ui-vben 等项目。适用于 yudao(Ruoyi-Vue-Plus) 平台。"
version: 2.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [bpm, flowable, yudao, workflow, sync, testing, pdp, automation]
---

# BPM 流程工程技能

本仓库（yudao-flowable-data）**只存放各环境的 BPM 流程定义数据**：每个流程一个
`{env}/{key} - {name}/now/` 目录，含 `{key}.bpmn`（流程图：节点/连线/审批配置）+
`model.json`（流程配置项：名称/分类/表单路由/可管理人/标题/可见性等）+ 动态表单的
`form.json`。**不含任何业务后端(yudao-cloud)/前端表单(yudao-ui-vben)代码**——流程是
配置数据、与业务代码解耦，`formCustomCreatePath/ViewPath` 只是指向业务前端的路由字符串。

## 工具总览（统一入口 `scripts/bpm.py`，或直接调各脚本）

| 命令 | 脚本 | 用途 |
|------|------|------|
| `bpm compare <keys>` | compare.py | **多环境对比**：语义+字节+字段差异 |
| `bpm check-refs <keys>` | check_refs.py | **ID 引用核对**：角色/用户/岗位ID跨环境是否一致存在 |
| `bpm sync --from A --to B <keys>` | sync.py | **任意方向同步**：覆盖+import+deploy |
| `bpm export --env X <keys>` | export.py | 环境→本地 |
| `bpm import --env X [--deploy] <keys>` | import.py | 本地→环境（可顺带部署）|
| `bpm deploy --env X <key>` | bpm_ops.py | 单独部署 |
| `bpm start/tasks/approve/reject/status/poll` | bpm_ops.py | 测试审批链 + 回调验证 |

---

## 环境信息

| env | URL |
|-----|-----|
| dev  | http://192.168.1.182:30080 |
| test | http://192.168.1.182:30082 |
| uat  | http://192.168.1.182:30084 |
| prod | http://192.168.1.182:30086 |

登录 `admin / admin123`（各环境统一）。配置集中在 `scripts/bpm_common.py`。

仓库：`http://192.168.30.14:9001/eastwinbip/codebase/yudao-flowable-data.git`（当前工作分支 **dev**，不是 master）。

---

## ★ 核心工作流

### A. 开发/修改一个流程（在单个环境，通常 dev）
在 dev 的 BPM 后台设计器里拖拽改流程，或直接改本地 `now/` 的 bpmn/model.json，然后：
```bash
bpm import --env dev --deploy pdp_quotation_request   # 推送并部署
bpm start  --env dev pdp_quotation_request            # 走一遍审批链自测
```

### B. 跨环境同步/晋级（最高频、最易错，必须按序）

**晋级常见路径**：dev 开发调试 → 定版后同步 test/uat → uat 验证通过、配好人员角色 → 推 prod。

**⚠ 方向不固定，以用户每次口头指定为准。** 用户可能临时直接改 uat 或 prod 再反向同步；
每次会说明"从哪个环境往哪个环境"。**绝不自己假设方向**（所以 `sync --from/--to` 任意）。

**标准操作序列（务必按此顺序，别跳步）：**
```bash
# 1) 看清差异，判断"以哪个环境为准"（不总是 dev！见下）
bpm compare pdp_plan_common

# 2) 核对 ID 引用：角色/用户/岗位 ID 在源和目标环境是否同名存在
bpm check-refs pdp_plan_common

# 3) 按用户指定的方向同步（自动 import+deploy）
bpm sync --from uat --to dev,test,prod pdp_plan_common
#    只同步流程逻辑、保留目标环境的人员/排序：
bpm sync --from uat --to prod --keep managerUserIds,managerRoleIds,sort xxx

# 4) 复核四环境一致
bpm compare pdp_plan_common
```

### 「以哪个环境为准」不总是 dev —— 逐流程判断
本仓库的经验：dc 系列常是 dev 领先；pdp 系列反而 uat/prod 更新、dev/test 落后；
个别字段（如某流程 titleSetting）prod 最完整。**先 compare 看清，再决定基准，必要时问用户。**

---

## ★ 跨环境同步前核对清单（血泪教训，逐条过）

1. **ID 引用跨环境一致**：跑 `bpm check-refs`。BPMN 的 `candidateParam`/`copyParam`、
   model 的 `managerUserIds/managerRoleIds/startUserIds/startDeptIds` 引用的是**实体 ID**，
   ID 跟环境走。**核对时必须按 candidateStrategy 判断实体类型再查对应实体**——
   踩过的坑：把 `candidateStrategy=30`(用户) 误当岗位去查、角色 817 名字其实是"条码查询"。
2. **路由前端已部署**：`formCustomCreatePath/ViewPath` 指向 yudao-ui-vben 的路由，
   同步前确认目标环境前端有该组件。踩过：误配成 `/pdp/plantemplate`、pdp_plan_common
   该用 `other` 而非 `doc`（前端按 doc/other/process 三分类）。
3. **后端支持新流程变量/候选策略**：若流程用了新 `${var}` 或策略，目标环境后端要已部署。
4. **方向别搞反**：以哪个环境为准逐流程判断，拿不准就 compare 后问用户。

---

## ★ 项目约定

- **BPMN 序列化风格统一以 prod 为规范**（`bpmn2:` 前缀 + 值直写 + 空元素自闭合），
  比"默认命名空间 + CDATA"更干净、git diff 噪音小。同一语义两种风格都合法、可互转；
  服务端存什么样、读什么样（推一次即永久统一）。**判断是否一致用语义(compare)，不要文本 diff。**
- **小程序路径前缀用 `pages-`（复数）**，如 `/pages-dcprocess/...`、`/pages-erp/...`。
- **model.json 禁止手写这些派生字段**（export 已剥离、见 `bpm_common.DERIVED_FIELDS`）：
  `id, modelId, categoryName, formName, deploymentTime, suspensionState, createTime,
  processDefinition, startUsers, startDepts, bpmnXml, simpleModel, formConf, formFields`。
- `formType: 10` = 动态表单（有 formId + form.json）；`formType: 20` = 自定义表单（有 formCustomXxxPath）。

---

## candidateStrategy / copyStrategy 对照表（**任何审批人判断前必读**）

来源：yudao-cloud `BpmTaskCandidateStrategyEnum`。`bpm_common.CANDIDATE_STRATEGY` 有机器可读版，
`check_refs.py` 据此自动判断该查哪类实体。**核对 param 时务必按下表的实体类型去查（查错实体=误判）：**

| 值 | 含义 | candidateParam | 核对实体 |
|----|------|---------------|---------|
| 1 | 审批人为空 | - | 无 |
| 10 | 角色 | 角色 ID(逗号分隔) | 角色 |
| 20 | 部门成员(含负责人) | 部门 ID | 部门 |
| 21 | 部门负责人 | 部门 ID | 部门 |
| 22 | **岗位** | 岗位 ID | 岗位 |
| 23 | 连续多级部门负责人 | 部门 ID | 部门 |
| 30 | **用户** | 用户 ID(逗号分隔) | 用户 |
| 34 | 审批人自身 | 空 | 无 |
| 35 | 发起人自选 | 空 | 无 |
| 36 | 发起人自己 | 空 | 无 |
| 37 | 发起人部门负责人 | 空 | 无 |
| 38 | 发起人连续多级部门负责人 | 空 | 无 |
| 39 | 直属领导 | 空 | 无 |
| 40 | 用户组 | 用户组 ID | 用户组 |
| 50 | 表单内用户字段 | 表单字段名(如 `driverUserId`) | 无(非ID) |
| 51 | 表单内部门负责人 | 表单字段名 | 无(非ID) |
| 60 | 流程表达式 | `${variableName}` | 无(非ID) |
| 70 | 团队成员 | 角色字典编号；按流程变量 `bizType`+`bizId` 查团队成员，发起时必须已写入这两个变量 | 角色 |
| 71 | 虚拟组织 | 虚拟组织 ID | 无 |

> 教训：`22` 才是岗位，`30` 是用户。曾把 30 当岗位、去查不存在的"岗位1240"，
> 误判成坏配置——其实 1240 是有效用户。**先查表、再按类型核对。**

---

## 创建/更新流程模型

### 目录结构
```
{env}/{key} - {name}/now/
    model.json
    {key}.bpmn
```

### model.json 模板（自定义表单）
```json
{
  "description": "...",
  "type": 10,
  "formType": 20,
  "formCustomCreatePath": "/pdp/your-page/detail",
  "formCustomViewPath": "/pdp/your-page/detail",
  "visible": true,
  "h5Visible": false,
  "startUserIds": [], "startDeptIds": [],
  "managerUserIds": [1], "managerRoleIds": [1],
  "sort": 1000,
  "allowCancelRunningProcess": true, "allowWithdrawTask": false,
  "processIdRule": {"enable": false, "prefix": "", "infix": "", "postfix": "", "length": 5},
  "autoApprovalType": 0,
  "titleSetting": {"enable": false, "title": ""},
  "summarySetting": {"enable": false, "summary": []},
  "key": "your_flow_key", "name": "流程名称", "category": "PDP流程"
}
```

### BPMN 模板（开始 → 审批 → 结束）
新流程建议直接在 BPM 设计器里画后 `export`（能拿到规范的 prod 风格 XML + 图形坐标）。
手写时最小骨架如下（推送后服务端会补全、并按 prod 风格规范化）：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"
                   xmlns:flowable="http://flowable.org/bpmn"
                   targetNamespace="http://flowable.org/bpmn" id="diagram_{KEY}">
  <bpmn2:process id="{KEY}" name="{NAME}" isExecutable="true">
    <bpmn2:startEvent id="Event_start"/>
    <bpmn2:userTask id="Activity_approve" name="审批">
      <bpmn2:extensionElements>
        <flowable:candidateStrategy>39</flowable:candidateStrategy>
        <flowable:candidateParam />
      </bpmn2:extensionElements>
    </bpmn2:userTask>
    <bpmn2:sequenceFlow id="Flow_1" sourceRef="Event_start" targetRef="Activity_approve"/>
    <bpmn2:endEvent id="Event_end"/>
    <bpmn2:sequenceFlow id="Flow_2" sourceRef="Activity_approve" targetRef="Event_end"/>
  </bpmn2:process>
</bpmn2:definitions>
```

### 推送
```bash
bpm import --env dev --dry-run pdp_quotation_request   # 先预览
bpm import --env dev --deploy  pdp_quotation_request   # 推送并部署
```
> `import` 只更新模型草稿，**必须 deploy 才生效**。加 `--deploy` 一步到位，或后面单独 `bpm deploy`。

---

## 测试（完整审批链）
```bash
ENV=dev; KEY=pdp_quotation_request
bpm start   --env $ENV $KEY --vars '{}'        # → processInstanceId
bpm tasks   --env $ENV <processInstanceId>     # → taskId, 审批人
bpm approve --env $ENV <taskId> --reason 同意   # 或 reject
bpm status  --env $ENV <processInstanceId>     # 期望 status=2(完成)/3(驳回)
```

## 验证 BPM 回调
审批完成后会回调业务服务更新单据状态，用 poll 断言：
```bash
bpm poll --url 'http://192.168.1.182:30080/admin-api/pdp/quotation-request/get?id=123' \
  --token <Bearer> --key data.status --expect 3 --timeout 30
```
超时 → 回调没生效，查 yudao-cloud 的 `@BpmProcessListenerComponent` processKey 是否与流程 key 一致。

---

## 提交规范
```bash
git add -A
git commit -m "fix(bpm): <说明>"
git push origin dev     # 当前工作分支是 dev
```
建议**一个流程一个 commit**，信息写清"以哪个环境为准、改了什么、纠正了什么"，便于回退。

---

## 常见问题

**Q: compare 显示 BPMN「字节不一致」但「语义一致」** —— 只是序列化风格不同，语义相同即业务无差异；
若要 git diff 干净，用 `sync` 以 prod 风格环境为源统一一次即可。

**Q: dry-run 通过但正式 import 报 BPMN 被 XSS 过滤损坏** —— 检查目标环境 `yudao.xss.exclude-urls`
是否含 `/admin-api/bpm/model/create` 和 `/update`。

**Q: deploy 报"流程定义名字期望是X当前是Y"** —— model.json 的 `name` 和 BPMN 里 `<process name=>`
不一致，两处都要改一致。

**Q: check-refs 报某 ID 缺失/名称不一致** —— 该环境没有这个角色/用户/岗位，或是不同实体；
同步前先在目标环境补/改，或调整流程里的引用，别硬推。

**Q: export/import 频繁超时** —— `bpm_common.api_request` 已内置超时+重试；仍失败就单个重试。
