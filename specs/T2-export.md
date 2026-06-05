# T2：重写 scripts/export.py（拉取到四环境新结构）

先读 `specs/00-common.md`。依赖 T1 已重构的 `bpm_common.py`。本任务只改 `scripts/export.py`。

## 行为

交互模式（无参数）：`prompt_env()` 选环境 → 连服务端拉 model 列表 → `prompt_flows(...)` 按分类分组选流程（回车=全量）。
参数模式：`--env dev`（默认 dev）+ 可选 `keys...`（指定 key，不填=全量）。

对每个选中的流程 key，落地到 `<env>/<key> - <name>/`，分两部分：

### A) now/（当前可编辑态，每次全量重拉覆盖）

1. `resolve_model_id` 拿到 modelId（model/list 里已有该 model 的全部信息，可直接用；如需 bpmnXml/simpleModel 用 `GET /admin-api/bpm/model/get?id={modelId}` 取全）。
2. 写 `now/<key>.bpmn` ← `bpmnXml`。
3. 按 `specs/00-common.md` 的字段规则生成 `now/model.json`（剥掉派生/运行时/已拆分字段）。
4. 若 `formType==10` 且有 `formId`：`GET /admin-api/bpm/form/get?id={formId}`，写 `now/form.json`（`{conf,fields,name,remark,status}`）。
5. 若有非空 `simpleModel`：写 `now/simple-model.json`。

### B) vN/（历史版本，增量——已有的跳过）

1. `GET /admin-api/bpm/process-definition/page?key={key}&pageNo=1&pageSize=100` → 拿到所有版本（每项有 `version`、`id`，**无 bpmnXml**）。
2. 对每个 `version`：若本地已存在 `<flow>/v{version}/` 目录则**跳过**（历史冻结不变）。
3. 否则 `GET /admin-api/bpm/process-definition/get?id={版本id}`：
   - 返回 `None`/空 → 打印告警并跳过（老部署可能已被清理，正常现象）。
   - 否则写 `v{version}/<key>.bpmn`、`v{version}/model.json`（同字段规则），动态表单写 `v{version}/form.json`（用冻结的 `formConf`/`formFields`/`formName`）。

## 注意

- 版本 id 形如 `key:version:uuid`，作为 query 参数建议 `urllib.parse.quote(id, safe='')`。
- 打印每个流程的处理结果（now 已更新、新增了哪些 vN、跳过了哪些）。

## 验证（worker 必做）

```bash
python3 -m py_compile scripts/export.py
# 对 dev 拉一个有多版本的流程，核对结构
python3 scripts/export.py --env dev pdp-review_udit2
find dev/'pdp-review_udit2 - '* -maxdepth 2 | sort
```
要求：编译通过；生成 `dev/pdp-review_udit2 - .../now/{...bpmn,model.json}` 且存在多个 `v*/` 目录、每个含 bpmn+model.json；model.json 里**不含** `id/bpmnXml/formConf` 等被剥字段。

**验证后清理**：`rm -rf dev test uat prod`（删掉实测数据，不提交）。

## 提交

`git add scripts/export.py && git commit -m "重写 export：选环境/流程，拉 now 全量 + vN 增量历史(含冻结表单)"`
