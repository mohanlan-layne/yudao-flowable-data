# V2：验证 dev→test 晋级回环，自修复至全绿

## 工作方式
- 已在 `verify-loop` 分支、共享目录 `/home/mohanlan/code/unknown/yudao-flowable-data`（确认：`git checkout verify-loop`）。
- 读 `specs/00-common.md` 与已有的 `tests/verify_e2e.py`。

## 目标
扩展 `tests/verify_e2e.py`，加上 **dev→test 晋级回环**，并把 **dev 和 test 两个环境**都跑到全绿。失败则修 `scripts/` 直到全绿。

## 新增验证步骤（接在 V1 dev 回环之后，沿用同一个一次性 verify_key）
1. **晋级（模拟用户本地 git copy）**：把 `dev/<verify_key>/now/` 复制到 `test/<verify_key>/now/`。
2. **import 到 test**：`python3 scripts/import.py --env test <verify_key>`（**非 dry-run**）→ 在 test 创建该一次性模型。
3. **export from test 校验**：`python3 scripts/export.py --env test <verify_key>` → 断言 test 上存在，且 BPMN process id / model.json key、name、formType / form.json conf 与从 dev 复制过去的一致。
4. **清理（try/finally）**：dev 和 test **都**按 key 删掉一次性模型；删本地 `dev/ test/` 实测数据目录。

## 自修复 & block 规则
同 V1：明确 bug 就修并重跑；方向不确定就 print 问题 + `sys.exit(2)` 失败、等人。

## 完成 & 提交
- dev 回环 + dev→test 晋级回环全绿。
- `git add scripts tests specs/V2-verify-promote.md && git commit -m "扩展 e2e：dev→test 晋级回环全绿" && git push origin verify-loop`。
