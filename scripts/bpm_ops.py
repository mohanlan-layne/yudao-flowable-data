#!/usr/bin/env python3
"""
BPM 流程操作工具 — 部署/启动/审批/监控

使用方法（CLI）：
  python3 scripts/bpm_ops.py deploy  --env dev pdp_quotation_request
  python3 scripts/bpm_ops.py start   --env dev pdp_quotation_request [--vars '{"k":"v"}']
  python3 scripts/bpm_ops.py tasks   --env dev <processInstanceId>
  python3 scripts/bpm_ops.py approve --env dev <taskId> [--reason '意见']
  python3 scripts/bpm_ops.py reject  --env dev <taskId> --reason '原因'
  python3 scripts/bpm_ops.py status  --env dev <processInstanceId>
  python3 scripts/bpm_ops.py poll    --url http://... [--key data.status] [--expect 3] [--timeout 60]
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import api_request, get_config, list_models, login


def cmd_deploy(args):
    """部署流程模型（将草稿/更新激活为可发起的流程定义）"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    models = list_models(base_url, token, tenant_id)
    model = models.get(args.key)
    if not model:
        print(f'[deploy] 错误: 找不到流程 key={args.key}（请先 import）', file=sys.stderr)
        sys.exit(1)

    model_id = model.get('id')
    resp = api_request(base_url, f'/admin-api/bpm/model/deploy?id={model_id}',
                       token=token, tenant_id=tenant_id, method='POST')

    if resp.get('code') != 0:
        print(f'[deploy] 部署失败: {resp.get("msg")}', file=sys.stderr)
        sys.exit(1)

    print(f'[deploy] 成功: key={args.key}  modelId={model_id}')


def cmd_start(args):
    """发起流程实例（自动取最新版本的流程定义）"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    resp = api_request(base_url, f'/admin-api/bpm/process-definition/list?key={args.key}',
                       token=token, tenant_id=tenant_id)
    defs = resp.get('data') or []
    if not defs:
        print(f'[start] 错误: 找不到流程定义 key={args.key}（请先 deploy）', file=sys.stderr)
        sys.exit(1)

    proc_def = max(defs, key=lambda d: d.get('version', 0))
    proc_def_id = proc_def.get('id')

    variables = json.loads(args.vars) if args.vars else {}
    body = {
        'processDefinitionId': proc_def_id,
        'variables': variables,
        'startUserSelectAssignees': {},
    }

    resp = api_request(base_url, '/admin-api/bpm/process-instance/create',
                       token=token, tenant_id=tenant_id, method='POST', body=body)

    if resp.get('code') != 0:
        print(f'[start] 发起失败: {resp.get("msg")}', file=sys.stderr)
        sys.exit(1)

    instance_id = resp.get('data')
    print(f'[start] 成功: processInstanceId={instance_id}')
    print(json.dumps({'processInstanceId': instance_id,
                      'processDefinitionId': proc_def_id}, ensure_ascii=False, indent=2))


def cmd_tasks(args):
    """查询流程实例的所有任务（含待办）"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    resp = api_request(
        base_url,
        f'/admin-api/bpm/task/list-by-process-instance-id?processInstanceId={args.instance_id}',
        token=token, tenant_id=tenant_id,
    )

    tasks = resp.get('data') or []
    pending = [t for t in tasks if not t.get('endTime')]

    print(f'[tasks] processInstanceId={args.instance_id}  总={len(tasks)} 待办={len(pending)}')
    for t in pending:
        assignee = (t.get('assigneeUser') or {}).get('nickname', '未分配')
        print(f'  taskId={t.get("id")}  name={t.get("name")}  assignee={assignee}')

    print(json.dumps(pending, ensure_ascii=False, indent=2))


def cmd_approve(args):
    """审批通过指定任务"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    body = {'id': args.task_id, 'variables': {}, 'reason': args.reason or '同意'}
    resp = api_request(base_url, '/admin-api/bpm/task/approve',
                       token=token, tenant_id=tenant_id, method='PUT', body=body)

    if resp.get('code') != 0:
        print(f'[approve] 失败: {resp.get("msg")}', file=sys.stderr)
        sys.exit(1)

    print(f'[approve] 成功: taskId={args.task_id}')


def cmd_reject(args):
    """审批拒绝指定任务"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    body = {'id': args.task_id, 'reason': args.reason}
    resp = api_request(base_url, '/admin-api/bpm/task/reject',
                       token=token, tenant_id=tenant_id, method='PUT', body=body)

    if resp.get('code') != 0:
        print(f'[reject] 失败: {resp.get("msg")}', file=sys.stderr)
        sys.exit(1)

    print(f'[reject] 成功: taskId={args.task_id}')


def cmd_status(args):
    """查询流程实例当前状态"""
    cfg = get_config(args.env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    resp = api_request(base_url, f'/admin-api/bpm/process-instance/get?id={args.instance_id}',
                       token=token, tenant_id=tenant_id)

    if resp.get('code') != 0:
        print(f'[status] 失败: {resp.get("msg")}', file=sys.stderr)
        sys.exit(1)

    data = resp.get('data') or {}
    status = data.get('status')
    STATUS_NAMES = {1: '进行中', 2: '已完成', 3: '已驳回', 4: '已取消'}
    print(f'[status] processInstanceId={args.instance_id}  '
          f'status={status}({STATUS_NAMES.get(status, "未知")})')
    print(json.dumps({
        'id': data.get('id'),
        'status': status,
        'statusName': STATUS_NAMES.get(status),
        'startTime': data.get('createTime'),
        'endTime': data.get('endTime'),
    }, ensure_ascii=False, indent=2))


def cmd_poll(args):
    """轮询 HTTP 接口，直到 JSON 响应中某字段匹配期望值（超时则退出码 1）

    典型用途：等待 BPM 回调将业务单据状态更新到指定值。

    示例：
      python3 scripts/bpm_ops.py poll \\
        --url 'http://192.168.1.182:30080/admin-api/pdp/quotation-request/get?id=123' \\
        --token <accessToken> \\
        --key data.status \\
        --expect 3 \\
        --timeout 60
    """
    timeout = args.timeout
    interval = 3
    elapsed = 0

    headers = {'Content-Type': 'application/json', 'tenant-id': args.tenant_id or '1'}
    if args.token:
        headers['Authorization'] = f'Bearer {args.token}'

    def get_nested(obj, key_path):
        for k in key_path.split('.'):
            if not isinstance(obj, dict):
                return None
            obj = obj.get(k)
        return obj

    print(f'[poll] 轮询: {args.url}')
    print(f'[poll] 期望 {args.key} == {args.expect}，间隔 {interval}s，超时 {timeout}s')

    last_data = None
    while elapsed < timeout:
        try:
            req = urllib.request.Request(args.url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                last_data = json.loads(r.read().decode('utf-8'))
            actual = get_nested(last_data, args.key)
            print(f'[poll] t={elapsed:3d}s  {args.key}={actual}')
            if args.expect is not None and str(actual) == str(args.expect):
                print('[poll] 条件满足，退出')
                print(json.dumps(last_data, ensure_ascii=False, indent=2))
                return
        except Exception as e:
            print(f'[poll] t={elapsed:3d}s  请求异常: {e}', file=sys.stderr)

        time.sleep(interval)
        elapsed += interval

    print(f'[poll] 超时 ({timeout}s)，条件未满足', file=sys.stderr)
    if last_data:
        print(json.dumps(last_data, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='BPM 流程操作工具')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('deploy', help='部署流程模型（import 之后必须 deploy 才能发起）')
    p.add_argument('--env', default='dev')
    p.add_argument('key', help='流程 key，如 pdp_quotation_request')

    p = sub.add_parser('start', help='发起流程实例')
    p.add_argument('--env', default='dev')
    p.add_argument('key', help='流程 key')
    p.add_argument('--vars', default='{}', help='变量 JSON，如 \'{"requestId": 123}\'')

    p = sub.add_parser('tasks', help='查询流程实例的待办任务')
    p.add_argument('--env', default='dev')
    p.add_argument('instance_id', metavar='processInstanceId')

    p = sub.add_parser('approve', help='审批通过任务')
    p.add_argument('--env', default='dev')
    p.add_argument('task_id', metavar='taskId')
    p.add_argument('--reason', default='同意')

    p = sub.add_parser('reject', help='审批拒绝任务')
    p.add_argument('--env', default='dev')
    p.add_argument('task_id', metavar='taskId')
    p.add_argument('--reason', required=True)

    p = sub.add_parser('status', help='查询流程实例状态')
    p.add_argument('--env', default='dev')
    p.add_argument('instance_id', metavar='processInstanceId')

    p = sub.add_parser('poll', help='轮询 URL 直到字段满足期望值（验证 BPM 回调）')
    p.add_argument('--url', required=True)
    p.add_argument('--token', help='Bearer Token（可通过 bpm_common.login() 获取）')
    p.add_argument('--tenant-id', dest='tenant_id', default='1')
    p.add_argument('--key', default='data.status', help='JSON 路径，如 data.status')
    p.add_argument('--expect', help='期望值（字符串比较），如 3')
    p.add_argument('--timeout', type=int, default=60, help='超时秒数（默认 60）')

    args = parser.parse_args()
    {'deploy': cmd_deploy, 'start': cmd_start, 'tasks': cmd_tasks,
     'approve': cmd_approve, 'reject': cmd_reject,
     'status': cmd_status, 'poll': cmd_poll}[args.cmd](args)


if __name__ == '__main__':
    main()
