#!/usr/bin/env python3
"""
从 BPM 服务拉取流程到本地 flows/ 目录

直接运行进入交互模式：
  ./export.sh

带参数直接执行（适合自动化）：
  ./export.sh --env uat --merge
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


def prompt_merge() -> bool:
    print('\n拉取模式：')
    print('  1) 全量覆盖（完全以服务端为准）')
    print('  2) 合并更新（新增+修改，本地独有的流程保留不删）')
    while True:
        raw = input('请输入序号 [2]: ').strip() or '2'
        if raw == '1':
            print('  已选择: 全量覆盖')
            return False
        if raw == '2':
            print('  已选择: 合并更新')
            return True
        print('  请输入 1 或 2')


def run(env: str, merge: bool):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    local_dirs = get_local_flow_dirs()
    if merge:
        print(f'[export] 合并模式：新增+修改，本地独有流程保留不删（当前本地 {len(local_dirs)} 个）')

    print('[export] 获取流程分类...')
    cat_resp = api_request(base_url, '/admin-api/bpm/category/simple-list', token=token, tenant_id=tenant_id)
    category_map = {item['code']: item['name'] for item in cat_resp.get('data', []) if item.get('code')}

    print('[export] 获取模型列表...')
    models_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    all_keys = [item['key'] for item in models_resp.get('data', [])]

    total = skipped = 0
    for key in all_keys:
        print(f'[export] 处理流程: {key}')
        def_resp = api_request(base_url, f'/admin-api/bpm/process-definition/get?key={key}',
                               token=token, tenant_id=tenant_id)
        data = def_resp.get('data')
        if not data:
            print(f'[export]   跳过 {key}：无已部署版本')
            skipped += 1
            continue

        if merge and key in local_dirs:
            # 已有流程：写入本地原有目录，保留本地目录结构
            target_dir = local_dirs[key]
        else:
            # 新增流程（或全量模式）：按服务端分类创建目录
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
        print(f'[export]   -> {os.path.relpath(target_dir, FLOWS_DIR)} (v{version})')
        total += 1

    print(f'\n[export] 完成：导出 {total}，跳过 {skipped}')


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程拉取')
        print('=' * 44)
        env = prompt_env()
        merge = prompt_merge()
        print()
        run(env, merge)
    else:
        parser = argparse.ArgumentParser(description='从 BPM 导出流程到本地')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('--merge', action='store_true')
        args = parser.parse_args()
        run(args.env, args.merge)


if __name__ == '__main__':
    main()
