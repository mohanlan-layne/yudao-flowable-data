# 公共背景与铁律（所有任务必读）

本仓库正在做「流程工程化改造」。完整设计见 `docs/2026-06-05-流程工程化改造-设计共识.md`，BPM 接口见 `bpm-api-index.md`。**动手前先读这两份。**

## 目标结构（最终形态）

```
<env>/                                  # env ∈ {dev,test,uat,prod}
└── <key> - <流程名>/                    # 一个流程一个目录，平铺（不按分类建目录）
    ├── now/                            # 当前可编辑态（可被 import 回推）
    │   ├── <key>.bpmn
    │   ├── model.json
    │   └── form.json                   # 仅动态表单(formType=10)才有
    ├── v1/  v2/ ... vN/                # 已部署历史版本，冻结只读，结构同 now/
```

## 铁律（违反即错）

1. **formType：10=动态表单，20=自定义表单**（不是文档里写的 1/2）。表单**只管动态表单(10)**；自定义表单(20)不生成 `form.json`，其路由路径留在 model.json。
2. **分类不建目录层**，只作为 model.json 里的 `category` 字段；流程目录在 env 下平铺。
3. **`now/` 可写可回推；`vN/` 只读冻结**。
4. 环境配置（URL/账号）已在 `scripts/bpm_common.py` 的 `CONFIGS`，沿用，不要改。
5. 用 Python 标准库（`urllib`），不引第三方依赖。Python 3.6+ 兼容。
6. 全程 GET/login 是安全的；**任何写操作（model/update、model/create）只允许 import 任务做，且本批验证一律走 `--dry-run`，绝不真改任何环境**。

## model.json 字段规则

从接口返回的对象里，**剥掉**这些键（服务端派生/运行时/已拆成独立文件的）：
```
id, modelId, categoryName, formName, deploymentTime, suspensionState,
createTime, processDefinition, startUsers, startDepts,
bpmnXml, simpleModel, formConf, formFields
```
**保留其余所有非 null 字段**（含 `key,name,category,description,icon,type,modelType,formType,formId,formCustomCreatePath,formCustomViewPath,visible,h5Visible,sort,managerUserIds,managerRoleIds,startUserIds,startDeptIds,allowCancelRunningProcess,allowWithdrawTask,autoApprovalType,processIdRule,titleSetting,summarySetting,printTemplateSetting,以及各 *TriggerSetting`）。

- `bpmnXml` → 写成 `<key>.bpmn` 文件。
- `simpleModel`（仿钉钉，若非空）→ 写成 `simple-model.json`。
- 表单 → `form.json`（见下）。

## form.json 规则（仅 formType==10）

- **now/**：调 `GET /admin-api/bpm/form/get?id={formId}`，取返回的 `{conf, fields, name, remark, status}` 写入（剥掉 `id,createTime`）。
- **vN/**：用该版本流程定义里**冻结的** `formConf`/`formFields`，写成 `{"conf": formConf, "fields": formFields, "name": formName}`。

## 提交要求

- 每个任务完成后 **编译/语法自检通过** 再提交：`python3 -m py_compile scripts/*.py`。
- 跑 export 验证时会在工作目录生成 `dev/`(等) 实测数据——**验证完务必删掉这些 env 数据目录**，本批任务**只提交代码**（`scripts/`、`README.md`），不要把流程数据混进 commit。
- `git add` 只加代码与文档，**不要 `git add -A`**；提交信息用中文、简洁。
