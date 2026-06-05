# T4：test_flow.py 适配 + README 重写 + 入口脚本核对

先读 `specs/00-common.md`。依赖 T1/T2/T3。

## 1. scripts/test_flow.py

适配新结构与 `bpm_common`：
- 沿用 `CONFIGS`/`login`。用法保持 `test_flow.py [--env dev] <key> <其它原有参数>`。
- 发起流程前需要 `processDefinitionId`：用 `GET /admin-api/bpm/process-definition/get?key={key}` 取当前激活版本的 `id`。
- 不依赖老 `flows/` 目录结构（若原实现有读本地文件，改为按 key 走接口）。
- `python3 -m py_compile scripts/test_flow.py` 通过。

## 2. README.md 重写

按新设计重写，覆盖：
- 新目录结构（四环境 / `<key> - <name>` 平铺 / `now/` + `vN/`）。
- 三个脚本用法（export 选环境→选流程；import 选环境→选流程→分类可切换、**不自动发布**、`--dry-run`；test_flow）。
- 跨环境晋级的做法：**本地把 `<src-env>/<flow>/now/` 复制到 `<dst-env>/<flow>/now/`，再对目标环境 import**（工具不做跨环境同步；动态表单/分类一致性由人保证，import 时可切换分类）。
- 环境表（沿用 CONFIGS 里的 dev/test/uat/prod 地址）。
- 保留「依赖 Python 3.6+、脚本自动检测」等仍适用的说明；删掉一切提到老 `flows/分类/` 结构、`meta.json`、`--merge` 的过时内容。

## 3. 入口脚本核对

`export.sh/.bat`、`import.sh/.bat`、`test_flow.sh/.bat` 只是转发到 `scripts/*.py`，确认转发正确、注释/用法说明与新行为一致（如有写死的旧用法示例就更新）。

## 验证

```bash
python3 -m py_compile scripts/test_flow.py
```
README 通读自洽，无残留旧结构描述。

## 提交

`git add scripts/test_flow.py README.md export.sh export.bat import.sh import.bat test_flow.sh test_flow.bat && git commit -m "适配 test_flow + 重写 README + 核对入口脚本"`
