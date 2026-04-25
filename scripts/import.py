#!/usr/bin/env python3
"""
将本地 flows/ 目录下的流程推送到 BPM（智能比对，无变化则跳过）

直接运行进入交互模式：
  ./import.sh

带参数直接执行（适合自动化）：
  ./import.sh --env prod pdp_plan_doc_common pdp_plan_doc_dfm
"""

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (FLOWS_DIR, api_request, get_config, is_interactive,
                        list_local_flows, login, prompt_env, prompt_flows)


def normalize_xml(xml: str) -> str:
    return re.sub(r'\s+', ' ', xml).strip()


def run(env: str, filter_keys: set):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    existing_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    existing = {item['key']: item for item in existing_resp.get('data', [])}

    imported = skipped = failed = 0

    for meta_file in sorted(glob.glob(os.path.join(FLOWS_DIR, '*', '*', 'meta.json'))):
        flow_dir = os.path.dirname(meta_file)
        key = os.path.basename(flow_dir).split(' - ')[0]
        bpmn_file = os.path.join(flow_dir, f'{key}.bpmn')

        if filter_keys and key not in filter_keys:
            continue
        if not os.path.exists(bpmn_file):
            print(f'[import] 跳过 {key}：缺少 bpmn 文件')
            skipped += 1
            continue

        print(f'[import] 处理流程: {key}')

        with open(meta_file, encoding='utf-8') as f:
            meta = json.load(f)
        with open(bpmn_file, encoding='utf-8') as f:
            local_bpmn = f.read()

        meta = dict(meta)
        meta['bpmnXml'] = local_bpmn
        meta['key'] = key
        if 'modelType' in meta and 'type' not in meta:
            meta['type'] = meta.pop('modelType')
        else:
            meta.pop('modelType', None)
        for field in ('id', 'version', 'categoryName'):
            meta.pop(field, None)

        try:
            if key in existing:
                model_id = existing[key]['id']
                server_version = existing[key].get('version', '-')
                model_detail = api_request(base_url, f'/admin-api/bpm/model/get?id={model_id}',
                                           token=token, tenant_id=tenant_id)
                server_bpmn = (model_detail.get('data') or {}).get('bpmnXml', '')
                if normalize_xml(server_bpmn) == normalize_xml(local_bpmn):
                    print(f'[import]   -> 无变化，跳过（服务端: v{server_version}）')
                    skipped += 1
                    continue
                meta['id'] = model_id
                resp = api_request(base_url, '/admin-api/bpm/model/update',
                                   token=token, tenant_id=tenant_id, method='PUT', body=meta)
                action = f'更新（服务端原版本: v{server_version}）'
            else:
                resp = api_request(base_url, '/admin-api/bpm/model/create',
                                   token=token, tenant_id=tenant_id, method='POST', body=meta)
                action = '新建'

            if resp.get('code') == 0:
                print(f'[import]   -> {action}成功')
                imported += 1
            else:
                print(f'[import]   -> {action}失败: {resp.get("msg", "unknown")}', file=sys.stderr)
                failed += 1
        except Exception as e:
            print(f'[import]   -> 异常: {e}', file=sys.stderr)
            failed += 1

    print(f'\n[import] 完成：推送 {imported}，跳过 {skipped}（无变化），失败 {failed}')


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程推送')
        print('=' * 44)
        env = prompt_env()
        flows = list_local_flows()
        selected_keys = prompt_flows(flows)
        print()
        run(env, set(selected_keys))
    else:
        parser = argparse.ArgumentParser(description='推送本地流程到 BPM')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('keys', nargs='*')
        args = parser.parse_args()
        run(args.env, set(args.keys))


if __name__ == '__main__':
    main()
