# V1：验证 export/import 在 dev 的回环，自修复至全绿

## 工作方式
- 共享目录：`/home/mohanlan/code/unknown/yudao-flowable-data`。
- **第一步切工作分支（基于已实现代码）**：`git checkout -b verify-loop flow-redesign-dev`（若已存在则 `git checkout verify-loop`）。之后所有改动都在 `verify-loop` 上累积。
- 先读 `specs/00-common.md` 了解目录结构与字段规则。

## 目标
写一个端到端自动验证脚本 `tests/verify_e2e.py`，并把 **dev 回环**跑到全绿。失败时：定位是 `scripts/` 里的 bug 就修，修完重跑，直到全绿。

## tests/verify_e2e.py（dev 部分）
全程使用**唯一的一次性 key**（形如 `zzz_verify_<时间戳>`，明显是垃圾、排最后），**只动这个 key，绝不碰任何真实流程**：

1. **export 真实流程**：`python3 scripts/export.py --env dev test_process`（一个动态表单流程）→ 断言生成 `dev/test_process - */now/{*.bpmn,model.json,form.json}` 且有 `v*/` 目录。
2. **本地造一次性新流程**：把上面 flow 的 `now/` 复制成 `dev/<verify_key>/now/`；改 `model.json` 的 `key`=verify_key、`name`="验证临时-verify_key"；把 `.bpmn` 文件名改成 `<verify_key>.bpmn`，并把 BPMN 里 `<process id="...">` 改成 verify_key。
3. **import 创建**：`python3 scripts/import.py --env dev <verify_key>`（**非 dry-run**）→ 在 dev 创建该一次性模型（走 create 路径）。
4. **export 回拉校验**：`python3 scripts/export.py --env dev <verify_key>` → 断言**回环保真**：BPMN 的 process id、`model.json` 的 key/name/formType、`form.json` 的 conf 与推上去的一致（容许服务端补充字段的差异）。
5. 任一步失败 → print 清晰诊断 + `sys.exit(1)`。
6. **清理（try/finally，成败都跑）**：在 dev 按 key 反查 modelId，`DELETE /admin-api/bpm/model/delete?id=` 删掉这个一次性模型；并删掉本地 `dev/` 实测数据目录。

## 自修复循环
- 跑 `python3 tests/verify_e2e.py`。失败 → 读输出定位根因 → 改 `scripts/bpm_common.py|export.py|import.py` 的 bug → 重跑。最多约 6 轮。
- **遇到「方向不确定/属于设计取舍」的问题（不是明确 bug），不要瞎猜**：把问题描述清楚 print 出来并 `sys.exit(2)` 让任务失败（会微信通知用户），等人决策。

## 完成 & 提交
- dev 回环全绿。
- 提交并推送（**自己 push**）：`git add scripts tests specs/V1-verify-dev.md && git commit -m "新增 e2e 验证脚本并跑通 dev 回环" && git push -u origin verify-loop`。
