# T3：重写 scripts/import.py（回推 now/，不发布）

先读 `specs/00-common.md`。依赖 T1/T2。本任务只改 `scripts/import.py`。

## 行为

交互模式：`prompt_env()` 选环境 → `list_local_flows(env)` 列本地有 `now/` 的流程 → `prompt_flows` 选流程。
参数模式：`--env dev` + 可选 `keys...`；`--dry-run` 只打印不推送。

对每个选中流程：

1. 读 `<env>/<key> - <name>/now/`：`model.json`、`<key>.bpmn`、`form.json`(可选)。
2. **分类可切换**：`get_category_map` 取目标环境分类；展示「当前 model.json 里的 category（默认）+ 可选其它分类」，让用户回车沿用或选新分类。`--dry-run`/非交互时直接用 model.json 里的 category。
3. `resolve_model_id(key)`：
   - 找到 → 走 `PUT /admin-api/bpm/model/update`，body = model.json 的字段 + `id`=modelId + `bpmnXml`=读自 .bpmn + `category`=上一步结果。
   - 没找到 → 走 `POST /admin-api/bpm/model/create`，body 同上但不带 id。
4. **绝不调用 `model/deploy`**——发布交给用户去 BPM 后台。
5. `--dry-run`：打印将要执行的 方法/路径/body 摘要（key、name、category、formId、bpmnXml 长度、是 update 还是 create），**不发请求**。

## body 字段

直接透传 model.json 里保留的字段（它们本就来自同一接口），再补上 `bpmnXml`、（update 时）`id`、最终 `category`。`BpmModelSaveReqVO` 关键字段见 `bpm-api-index.md`（key/name/category/type/formType/formId/bpmnXml/managerUserIds/visible...）。

## 验证（worker 必做，全程 --dry-run，不真改环境）

```bash
python3 -m py_compile scripts/import.py
# 先用 export 造一个本地 now/ 出来（验证后会删）
python3 scripts/export.py --env dev pdp-review_udit2
# dry-run 回推，确认识别为 update、body 摘要正确、未发任何写请求
python3 scripts/import.py --env dev --dry-run pdp-review_udit2
rm -rf dev test uat prod
```
要求：编译通过；dry-run 输出显示「update（已存在 modelId）」、带正确 key/category/bpmnXml 长度；**确认代码在 --dry-run 下不会调用 update/create/deploy**。

## 提交

`git add scripts/import.py && git commit -m "重写 import：回推 now（update/create，分类可切换，不发布），支持 --dry-run"`
