#!/usr/bin/env python3
"""
从 BPM 服务拉取流程到本地 flows/ 目录

直接运行进入交互模式：
  ./export.sh

带参数直接执行（适合自动化）：
  ./export.sh --env uat --merge
  ./export.sh --env uat --merge pdp_plan_doc_common pdp_plan_doc_dfm
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (FLOWS_DIR, api_request, get_config, is_interactive,
                        login, prompt_env)

EXCLUDE_FIELDS = {
    'bpmnXml', 'simpleModel', 'id', 'suspensionState', 'deploymentTime',
    'formConf', 'formFields', 'formName', 'modelId', 'categoryName',
}


def get_local_flow_dirs() -> dict:
    result = {}
    for meta_file in glob.glob(os.path.join(FLOWS_DIR, '*', '*', 'meta.json')):
        flow_dir = os.path.dirname(meta_file)
        key = os.path.basename(flow_dir).split(' - ')[0]
        result[key] = flow_dir
    return result


def prompt_server_flows(server_flows: list) -> list:
    """从服务端流程列表中选择，返回选中的 key 列表；空列表表示全量"""
    print('\n选择要拉取的流程：')
    print('  0) 全量（所有流程）')
    for i, (key, name) in enumerate(server_flows, 1):
        print(f'  {i}) {key}  {name}')
    print('\n输入序号选择（多个用空格分隔），直接回车表示全量：')
    raw = input('> ').strip()
    if not raw:
        print('  已选择: 全量')
        return []
    selected = []
    for token in raw.replace(',', ' ').split():
        if token == '0':
            print('  已选择: 全量')
            return []
        if token.isdigit() and 1 <= int(token) <= len(server_flows):
            selected.append(server_flows[int(token) - 1][0])
        else:
            print(f'  忽略无效输入: {token}')
    print(f'  已选择: {", ".join(selected)}')
    return selected


def run(env: str, filter_keys: set):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    local_dirs = get_local_flow_dirs()

    print('[export] 获取流程分类...')
    cat_resp = api_request(base_url, '/admin-api/bpm/category/simple-list', token=token, tenant_id=tenant_id)
    category_map = {item['code']: item['name'] for item in cat_resp.get('data', []) if item.get('code')}

    print('[export] 获取模型列表...')
    models_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    all_keys = [item['key'] for item in models_resp.get('data', [])]

    total = skipped = 0
    for key in all_keys:
        if filter_keys and key not in filter_keys:
            continue

        print(f'[export] 处理流程: {key}')
        def_resp = api_request(base_url, f'/admin-api/bpm/process-definition/get?key={key}',
                               token=token, tenant_id=tenant_id)
        data = def_resp.get('data')
        if not data:
            print(f'[export]   跳过 {key}：无已部署版本')
            skipped += 1
            continue

        if key in local_dirs:
            # 已有流程：写入本地原有目录，保留本地目录结构
            target_dir = local_dirs[key]
        else:
            # 新增流程：按服务端分类创建目录
            cat_code = data.get('category') or ''
            cat_name = category_map.get(cat_code, cat_code) or '未分类'
            safe_cat = cat_name.replace('/', '-').replace(' ', '_')
            flow_name = data.get('name') or ''
            safe_name = f'{key} - {flow_name}'.replace('/', '-')
            target_dir = os.path.join(FLOWS_DIR, safe_cat, safe_name)
            os.makedirs(target_dir, exist_ok=True)

        with open(os.path.join(target_dir, f'{key}.bpmn'), 'w', encoding='utf-8') as f:
            f.write(data.get('bpmnXml') or '')

        meta = {k: v for k, v in data.items() if k not in EXCLUDE_FIELDS and v is not None}
        with open(os.path.join(target_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        version = data.get('version', '-')
        action = '更新' if key in local_dirs else '新增'
        print(f'[export]   -> [{action}] {os.path.relpath(target_dir, FLOWS_DIR)} (v{version})')
        total += 1

    print(f'\n[export] 完成：拉取 {total}，跳过 {skipped}（无已部署版本）')
    if not filter_keys:
        print(f'         本地独有流程保留不动（未被覆盖或删除）')


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程拉取')
        print('=' * 44)
        env = prompt_env()

        # 连接服务端获取流程列表供用户选择
        cfg = get_config(env)
        base_url, tenant_id = cfg['url'], cfg['tenant_id']
        print('\n正在获取服务端流程列表...', end='', flush=True)
        token = login(base_url, tenant_id, cfg['username'], cfg['password'])
        models_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
        server_flows = [(item['key'], item.get('name', '')) for item in models_resp.get('data', [])]
        print(f' 共 {len(server_flows)} 个流程')

        selected_keys = prompt_server_flows(server_flows)
        print()
        run(env, set(selected_keys))
    else:
        parser = argparse.ArgumentParser(description='从 BPM 拉取流程到本地')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('--merge', action='store_true', help='（已废弃，现在默认即为合并逻辑）')
        parser.add_argument('keys', nargs='*', help='只拉取指定 key 的流程，不填则全量')
        args = parser.parse_args()
        run(args.env, set(args.keys))


if __name__ == '__main__':
    main()
