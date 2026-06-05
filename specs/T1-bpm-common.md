# T1：重构 scripts/bpm_common.py（适配四环境新结构）

先读 `specs/00-common.md`。本任务只改 `scripts/bpm_common.py`，不碰 export/import。

## 保留（不要删）

`CONFIGS`、`get_config`、`api_request`、`login`、`is_interactive`。

## 新增 / 修改

1. **环境与路径常量**
   - `ENVS = ['dev','test','uat','prod']`（取自 CONFIGS 的键即可）。
   - `ROOT_DIR` = 仓库根（`scripts/` 的上一级）。
   - `env_dir(env)` → `os.path.join(ROOT_DIR, env)`。
   - 删除旧的 `FLOWS_DIR` 相关逻辑（老 `flows/` 已不存在）。

2. **本地流程遍历** `list_local_flows(env) -> list[(key, name, flow_dir)]`
   - 扫描 `env_dir(env)` 下、**含 `now/` 子目录**的流程目录。
   - 目录名格式 `{key} - {name}`；用 `' - '` 分隔解析 key 与 name（参考老 `list_local_flows`）。
   - 按 key 排序返回。

3. **目录名/文件名工具**
   - `flow_dir_name(key, name) -> '{key} - {name}'`，把 `/` 替换成 `-`。
   - `safe(s)` 把文件名里的 `/` 替换掉。

4. **按 key 反查 modelId** `resolve_model_id(base_url, token, tenant_id, key) -> str|None`
   - `GET /admin-api/bpm/model/list`，在返回数组里找 `item['key']==key`，返回其 `id`（UUID）；找不到返回 None。

5. **分类映射** `get_category_map(base_url, token, tenant_id) -> dict[code,name]`
   - `GET /admin-api/bpm/category/simple-list`，返回 `{code: name}`。

6. **交互选择**
   - `prompt_env()` 已有则保留/微调，确保返回 env 字符串。
   - `prompt_flows(flows, category_of=None)`：在已有基础上，**按分类分组展示**——`flows` 为 `[(key,name,category_or_dir...)]`，展示时按 category 名分组打印（拿不到分类就放「未分类」）。返回选中的 key 列表，空列表=全量。保持「0=全量、空格/逗号分隔多选、回车=全量」的交互习惯。

## 验证（worker 必做）

```bash
python3 -m py_compile scripts/bpm_common.py
python3 -c "import sys; sys.path.insert(0,'scripts'); import bpm_common as c; \
print('ENVS', c.ENVS); \
from bpm_common import get_config, login; cfg=get_config('dev'); \
tok=login(cfg['url'],cfg['tenant_id'],cfg['username'],cfg['password']); \
print('login ok', bool(tok)); \
print('mid', c.resolve_model_id(cfg['url'],tok,cfg['tenant_id'],'pdp-review_udit2')); \
print('cats', c.get_category_map(cfg['url'],tok,cfg['tenant_id'])); \
print('local dev flows', c.list_local_flows('dev'))"
```
要求：编译通过、login ok、能反查到 modelId（非 None）、分类 map 非空、`list_local_flows('dev')` 不报错（当前为空列表正常）。

## 提交

`git add scripts/bpm_common.py && git commit -m "重构 bpm_common：四环境目录遍历 + key 反查 modelId + 分类分组选择"`
