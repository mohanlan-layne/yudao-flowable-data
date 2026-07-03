#!/usr/bin/env python3
"""bpm —— BPM 流程工具统一入口，把子命令转发到 scripts/ 下对应脚本。

流程管理：
  bpm export     --env dev <keys...>              从环境拉流程到本地
  bpm import     --env dev [--deploy] <keys...>   本地推回环境（--deploy 顺带部署）
  bpm compare    <keys...> [--envs dev,uat]        多环境对比差异（语义+字段）
  bpm check-refs <keys...>                          核对 ID 引用跨环境一致存在
  bpm sync       --from X --to Y[,Z] [--keep ...] <keys...>   任意方向同步+部署

流程操作（转发到 bpm_ops.py）：
  bpm deploy   --env dev <key>
  bpm start    --env dev <key> [--vars '{}']
  bpm tasks    --env dev <processInstanceId>
  bpm approve  --env dev <taskId> [--reason ...]
  bpm reject   --env dev <taskId> --reason ...
  bpm status   --env dev <processInstanceId>
  bpm poll     --url ... [--key data.status] [--expect 3]

测试：
  bpm test     --env dev <key> <executorUserId> <chargeUserId>

典型跨环境同步姿势（务必按序）：
  1) bpm compare <key>            看差异、定"以哪个环境为准"
  2) bpm check-refs <key>         核对角色/用户/岗位ID跨环境一致存在
  3) bpm sync --from A --to B <key>   同步并自动部署
  4) bpm compare <key>            复核四环境一致
"""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 子命令 -> 独立脚本
DIRECT = {
    'export': 'export.py',
    'import': 'import.py',
    'compare': 'compare.py',
    'check-refs': 'check_refs.py',
    'sync': 'sync.py',
    'test': 'test_flow.py',
}
# 转发到 bpm_ops.py 的子命令
OPS = {'deploy', 'start', 'tasks', 'approve', 'reject', 'status', 'poll'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print(__doc__)
        return
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd in DIRECT:
        sys.exit(subprocess.call(['python3', os.path.join(SCRIPT_DIR, DIRECT[cmd]), *rest]))
    if cmd in OPS:
        sys.exit(subprocess.call(['python3', os.path.join(SCRIPT_DIR, 'bpm_ops.py'), cmd, *rest]))
    print(f"未知子命令: {cmd}\n", file=sys.stderr)
    print(__doc__)
    sys.exit(1)


if __name__ == '__main__':
    main()
