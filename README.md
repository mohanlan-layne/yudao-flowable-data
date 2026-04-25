# yudao-flowable-data

BPM 流程定义的版本管理仓库。将 Flowable 流程的 BPMN 文件、元数据、设计文档统一用 Git 管理，并提供脚本与各环境 BPM 服务双向同步。

## 目录结构

```
flows/
  CRM流程/
    crm-fea-audit - 可行性评估审批/
      crm-fea-audit.bpmn   # 流程定义
      meta.json             # 元数据（分类、表单、管理员等）
      design.md             # 流程设计说明
  PDP流程/
    ...
scripts/                   # 内部脚本，无需直接调用
docs/                      # 设计文档
import.sh / import.bat     # 推送流程到 BPM
export.sh / export.bat     # 从 BPM 拉取流程
test_flow.sh / test_flow.bat
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
./import.sh
./export.sh
./test_flow.sh

# Windows
import.bat
export.bat
test_flow.bat
```

**import 交互示例：**
```
============================================
  BPM 流程推送
============================================

选择环境：
  1) dev    http://192.168.1.182:30080
  2) test   http://192.168.1.182:30082
  3) uat    http://192.168.1.182:30084
  4) prod   http://192.168.1.182:30086
请输入序号 [1]: 3

选择流程：
  0) 全量（所有流程）
  1) crm-fea-audit           可行性评估审批
  2) crm-fea-final-audit     可行性评估终审
  3) pdp-review-issue-rectify  问题整改
  ...
输入序号选择（多个用空格分隔），直接回车表示全量：
> 1 3
```

**export 交互示例：**
```
选择环境：...
拉取模式：
  1) 全量覆盖（完全以服务端为准）
  2) 合并更新（只覆盖本地已有流程，不新增不删除）
请输入序号 [2]:
```

---

### 参数模式

适合脚本调用或熟悉命令行的用户：

**推送（import）**

智能比对：BPMN 内容无变化则自动跳过。

```bash
./import.sh                                        # 全量推送到 dev
./import.sh --env prod                             # 全量推送到 prod
./import.sh pdp_plan_doc_common                    # 推送单个流程到 dev
./import.sh pdp_plan_doc_common pdp_plan_doc_dfm   # 推送多个流程到 dev
./import.sh --env prod pdp_plan_doc_common         # 指定环境 + 指定流程
```

**拉取（export）**

```bash
./export.sh                        # 全量导出 dev 到本地
./export.sh --env uat --merge      # 从 UAT 合并更新到本地（只覆盖已有流程）
./export.sh --env prod             # 全量导出 prod
```

> `--merge`：服务端有但本地没有的流程跳过；本地有但服务端没有的保留不动。

**测试流程（test_flow）**

```bash
./test_flow.sh pdp_plan_doc_common 2637 1
./test_flow.sh --env uat pdp_plan_doc_common 2637 1
```

---

## 新增流程

1. 在 `flows/{分类}/` 下创建目录，命名格式：`{key} - {中文名}`
2. 创建三个文件：
   - `{key}.bpmn` — 流程定义 XML（参考已有流程复制修改）
   - `meta.json` — 参考已有流程，修改 `name`、`key`
   - `design.md` — 流程节点说明（可选）
3. 推送到目标环境：
   ```bash
   ./import.sh      # 交互模式选择
   # 或
   ./import.sh --env dev {key}
   ```

## 修改流程

直接编辑 `.bpmn` 或 `meta.json`，然后推送。脚本会自动跳过无变化的流程。

```bash
./import.sh   # 交互模式
```
