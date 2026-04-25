#!/usr/bin/env python3
"""
流程端到端测试

直接运行进入交互模式：
  ./test_flow.sh

带参数直接执行（适合自动化）：
  ./test_flow.sh --env uat pdp_plan_doc_common 2637 1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (api_request, get_config, is_interactive,
                        list_local_flows, login, prompt_env)


def prompt_flow(flows: list) -> str:
    print('\n选择流程：')
    for i, (key, name, _) in enumerate(flows, 1):
        print(f'  {i}) {key}  {name}')
    while True:
        raw = input('请输入序号: ').strip()
        if raw.isdigit() and 1 <= int(raw) <= len(flows):
            chosen = flows[int(raw) - 1][0]
            print(f'  已选择: {chosen}')
            return chosen
        print(f'  请输入 1-{len(flows)} 之间的序号')


def prompt_user_id(label: str) -> int:
    while True:
        raw = input(f'{label}: ').strip()
        if raw.isdigit():
            return int(raw)
        print('  请输入有效的用户 ID（数字）')


def run(env: str, flow_key: str, executor_user_id: int, charge_user_id: int):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    sep = '=' * 44
    print(f'\n{sep}')
    print(f'  流程测试: {flow_key}')
    print(f'  执行人ID: {executor_user_id}')
    print(f'  负责人ID: {charge_user_id}')
    print(sep)

    print('\n[1] 获取流程定义...')
    proc_def_resp = api_request(base_url, f'/admin-api/bpm/process-definition/get?key={flow_key}',
                                token=token, tenant_id=tenant_id)
    proc_def = proc_def_resp.get('data')
    if not proc_def:
        print(f'错误：流程定义不存在: {flow_key}', file=sys.stderr)
        sys.exit(1)
    print(f'    流程定义: {proc_def["name"]} ({proc_def["id"]})')

    print('\n[2] 发起流程实例...')
    create_resp = api_request(
        base_url, '/admin-api/bpm/process-instance/create',
        token=token, tenant_id=tenant_id, method='POST',
        body={
            'processDefinitionId': proc_def['id'],
            'variables': {
                'executorUserId': executor_user_id,
                'PdpPlanChargeUser': charge_user_id,
            },
        },
    )
    instance_id = create_resp.get('data')
    print(f'    流程实例ID: {instance_id}')

    print('\n[3] 当前任务状态\n')
    tasks_resp = api_request(
        base_url, f'/admin-api/bpm/task/list-by-process-instance-id?processInstanceId={instance_id}',
        token=token, tenant_id=tenant_id,
    )
    status_map = {1: '进行中', 2: '已完成', 3: '未通过', 4: '已取消'}
    for t in tasks_resp.get('data', []):
        status = status_map.get(t.get('status'), str(t.get('status')))
        assignee = (t.get('assigneeUser') or {}).get('nickname', '待分配')
        print(f'  节点: {t["name"]:12s}  taskId={t["id"]}  状态={status}  审批人={assignee}')

    print(f'\n{sep}')
    print('  审批接口参考（替换 <token> 和 <taskId>）')
    print(sep)
    print(f'''
  通过任务:
  curl -X PUT "{base_url}/admin-api/bpm/task/approve" \\
    -H "Authorization: Bearer <token>" \\
    -H "tenant-id: {tenant_id}" \\
    -H "Content-Type: application/json" \\
    -d \'{{"id":"<taskId>","variables":{{}},"reason":"测试通过"}}\'

  拒绝任务:
  curl -X PUT "{base_url}/admin-api/bpm/task/reject" \\
    -H "Authorization: Bearer <token>" \\
    -H "tenant-id: {tenant_id}" \\
    -H "Content-Type: application/json" \\
    -d \'{{"id":"<taskId>","reason":"测试拒绝"}}\'
''')
    print(sep)
    print(f'  流程实例ID: {instance_id}')
    print(f'  管理后台: {base_url}/doc.html#/')
    print(sep)


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程测试')
        print('=' * 44)
        env = prompt_env()
        flows = list_local_flows()
        flow_key = prompt_flow(flows)
        executor_user_id = prompt_user_id('\n执行人用户 ID')
        charge_user_id = prompt_user_id('计划负责人用户 ID')
        run(env, flow_key, executor_user_id, charge_user_id)
    else:
        parser = argparse.ArgumentParser(description='流程端到端测试')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('flow_key')
        parser.add_argument('executor_user_id', type=int)
        parser.add_argument('charge_user_id', type=int)
        args = parser.parse_args()
        run(args.env, args.flow_key, args.executor_user_id, args.charge_user_id)


if __name__ == '__main__':
    main()
