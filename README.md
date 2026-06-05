# yudao-flowable-data

BPM 流程定义的版本管理仓库。将 Flowable 流程的 BPMN、元数据、表单统一用 Git 管理，并提供脚本与各环境 BPM 服务双向同步。

## 目录结构

```
dev/                          # 四环境平铺（dev / test / uat / prod）
  pdp_plan_doc_common - 通用文档审批/
    now/                      # 当前可编辑态
      pdp_plan_doc_common.bpmn
      model.json              # 元数据（key/name/category/formId 等）
      form.json               # 动态表单（如有）
      simple-model.json       # 简单模型（如有）
    v1/                       # 历史已发布版本（只增不删）
      pdp_plan_doc_common.bpmn
      model.json
      form.json
    v2/
      ...
  pdp-review_udit2 - 问题整改/
    now/
    v1/
    ...
test/
  ...
uat/
  ...
prod/
  ...

scripts/                      # 内部脚本，无需直接调用
  bpm_common.py               # 公共配置与工具
  export.py                   # 拉取
  import.py                   # 推送
  test_flow.py                # 流程测试
export.sh / export.bat        # 拉取入口
import.sh / import.bat        # 推送入口
test_flow.sh / test_flow.bat  # 测试入口
```

## 环境

| 环境 | 地址 |
|------|------|
| dev  | http://192.168.1.182:30080 |
| test | http://192.168.1.182:30082 |
| uat  | http://192.168.1.182:30084 |
| prod | http://192.168.1.182:30086 |

## 依赖

Python 3.6+。脚本会自动检测，未安装时尝试自动安装（Mac 用 brew，Windows 用 winget），或提示手动下载地址。

---

## 使用方式

脚本支持两种使用方式：**交互模式**（推荐）和**参数模式**（适合自动化）。

### 交互模式

直接运行脚本，按提示选择环境和流程：

```bash
# Mac / Linux
./export.sh
./import.sh
./test_flow.sh

# Windows
export.bat
import.bat
test_flow.bat
```

**export 交互示例：**
```
============================================
  BPM 流程拉取
============================================

选择环境：
  1) dev    http://192.168.1.182:30080
  2) test   http://192.168.1.182:30082
  3) uat    http://192.168.1.182:30084
  4) prod   http://192.168.1.182:30086
请输入序号 [1]: 1

正在获取服务端流程列表... 共 10 个流程

选择流程：
  0) 全量（所有流程）

  [PDP流程]
    1) pdp_plan_doc_common    通用文档审批
    2) pdp-review_udit2       问题整改
  ...
输入序号选择（多个用空格或逗号分隔），直接回车表示全量：
> 1 2
```

**import 交互示例：**
```
============================================
  BPM 流程回推（import）
============================================

选择环境：
  ...

选择流程：
  0) 全量（所有流程）
  ...
输入序号选择（多个用空格或逗号分隔），直接回车表示全量：
> 1

  当前分类: PDP流程
  可选分类（回车保持当前）：
    1) PDP流程 (PDP流程)
    2) CRM流程 (CRM流程)
  请输入序号或分类 code [回车保持]:

是否只预览不推送？(y/N): y
  已选择: dry-run 模式
```

> import **不会自动发布**流程，推送后请在 BPM 后台手动部署。

**test_flow 交互示例：**
```
============================================
  BPM 流程测试
============================================

选择环境：
  ...

选择流程：
  0) 全量（所有流程）
  ...
> 1

执行人用户 ID: 2637
计划负责人用户 ID: 1
```

---

### 参数模式

适合脚本调用或熟悉命令行的用户：

**拉取（export）**

```bash
./export.sh                        # 全量导出 dev
./export.sh --env uat              # 全量导出 uat
./export.sh --env dev pdp_plan_doc_common pdp-review_udit2   # 只拉取指定流程
```

> export 会写入 `<env>/<key> - <name>/now/`（全量覆盖），并增量写入 `vN/`（跳过已存在目录）。

**推送（import）**

```bash
./import.sh                                       # 全量推送到 dev
./import.sh --env prod                            # 全量推送到 prod
./import.sh pdp_plan_doc_common                   # 推送单个流程到 dev
./import.sh pdp_plan_doc_common pdp-review_udit2  # 推送多个流程到 dev
./import.sh --env prod --dry-run pdp_plan_doc_common   # 只预览，不实际推送
```

> import 读取本地 `now/` 目录，按 key 判断 update / create，**不会调用 deploy 发布**。

**测试流程（test_flow）**

```bash
./test_flow.sh pdp_plan_doc_common 2637 1
./test_flow.sh --env uat pdp_plan_doc_common 2637 1
```

---

## 跨环境晋级

工具**不做跨环境自动同步**。推荐做法：

1. 本地把 `<src-env>/<flow>/now/` 复制到 `<dst-env>/<flow>/now/`
2. 对目标环境执行 import

```bash
# 示例：dev → uat 晋级
mkdir -p "uat/pdp_plan_doc_common - 通用文档审批"
cp -r "dev/pdp_plan_doc_common - 通用文档审批/now" \
      "uat/pdp_plan_doc_common - 通用文档审批/"
./import.sh --env uat pdp_plan_doc_common
```

> 动态表单、分类一致性由人保证；import 交互模式下可切换分类。

---

## 新增流程

1. 在目标环境的目录下创建流程目录，命名格式：`<key> - <中文名>`
2. 在 `now/` 下放置：
   - `<key>.bpmn` — 流程定义 XML
   - `model.json` — 元数据（参考已有流程，至少包含 `key`、`name`、`category`）
   - `form.json` — 动态表单（如有）
3. 推送到目标环境：
   ```bash
   ./import.sh --env dev <key>
   ```

## 修改流程

直接编辑目标环境 `now/` 下的 `.bpmn` 或 `model.json`，然后推送：

```bash
./import.sh --env dev <key>
```
