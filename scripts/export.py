#!/usr/bin/env python3
"""
从 BPM 服务拉取流程到本地 <env>/<key> - <name>/ 目录

直接运行进入交互模式：
  ./export.py

带参数直接执行（适合自动化）：
  ./export.py --env dev
  ./export.py --env dev pdp_plan_doc_common pdp_plan_doc_dfm
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (
    ENVS, ROOT_DIR, api_request, env_dir, flow_dir_name, get_category_map,
    get_config, is_interactive, login, prompt_env, prompt_flows, resolve_model_id,
)

# 从 model.json / process-definition 返回里剥掉的字段
EXCLUDE_FIELDS = {
    'id', 'modelId', 'categoryName', 'formName', 'deploymentTime',
    'suspensionState', 'createTime', 'processDefinition',
    'startUsers', 'startDepts',
    'bpmnXml', 'simpleModel', 'formConf', 'formFields',
}


def _write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _strip_model(data):
    """剥掉派生/运行时/已拆分字段，保留其余非 null 字段"""
    return {k: v for k, v in data.items() if k not in EXCLUDE_FIELDS and v is not None}


def _ensure_flow_dir(env, key, name):
    """确保流程目录存在，返回绝对路径"""
    d = os.path.join(env_dir(env), flow_dir_name(key, name))
    os.makedirs(d, exist_ok=True)
    return d


def _fetch_model_full(base_url, token, tenant_id, model_id):
    """GET /admin-api/bpm/model/get?id={modelId}"""
    return api_request(base_url, f'/admin-api/bpm/model/get?id={model_id}', token=token, tenant_id=tenant_id)


def _fetch_form(base_url, token, tenant_id, form_id):
    """GET /admin-api/bpm/form/get?id={formId}，返回 {conf,fields,name,remark,status}"""
    resp = api_request(base_url, f'/admin-api/bpm/form/get?id={form_id}', token=token, tenant_id=tenant_id)
    data = resp.get('data')
    if not data:
        return None
    return {k: v for k, v in data.items() if k in {'conf', 'fields', 'name', 'remark', 'status'} and v is not None}


def _write_now(flow_dir, key, model_data, form_data, simple_model_data):
    """写入 now/ 目录（全量覆盖）"""
    now_dir = os.path.join(flow_dir, 'now')
    os.makedirs(now_dir, exist_ok=True)

    # 1. bpmn
    bpmn = model_data.get('bpmnXml') or ''
    with open(os.path.join(now_dir, f'{key}.bpmn'), 'w', encoding='utf-8') as f:
        f.write(bpmn)

    # 2. model.json
    _write_json(os.path.join(now_dir, 'model.json'), _strip_model(model_data))

    # 3. form.json（仅动态表单）
    if form_data:
        _write_json(os.path.join(now_dir, 'form.json'), form_data)

    # 4. simple-model.json
    if simple_model_data:
        _write_json(os.path.join(now_dir, 'simple-model.json'), simple_model_data)


def _write_version(flow_dir, key, version, def_data, form_data):
    """写入 v{version}/ 目录"""
    v_dir = os.path.join(flow_dir, f'v{version}')
    os.makedirs(v_dir, exist_ok=True)

    # bpmn
    bpmn = def_data.get('bpmnXml') or ''
    with open(os.path.join(v_dir, f'{key}.bpmn'), 'w', encoding='utf-8') as f:
        f.write(bpmn)

    # model.json
    _write_json(os.path.join(v_dir, 'model.json'), _strip_model(def_data))

    # form.json（冻结态）
    if form_data:
        _write_json(os.path.join(v_dir, 'form.json'), form_data)


def _process_flow(env, base_url, token, tenant_id, key, name, model_info):
    """处理单个流程：拉 now/ + 增量 vN/"""
    flow_dir = _ensure_flow_dir(env, key, name)

    # ---------- A) now/ 当前可编辑态 ----------
    model_id = model_info.get('id')
    if not model_id:
        print(f'[export] {key}: 无法获取 modelId，跳过')
        return False

    # model/list 里已有完整信息，但 bpmnXml/simpleModel 可能不全，取 get
    full_resp = _fetch_model_full(base_url, token, tenant_id, model_id)
    model_data = full_resp.get('data') or {}
    if not model_data:
        print(f'[export] {key}: 获取 model 详情失败，跳过')
        return False

    form_type = model_data.get('formType')
    form_id = model_data.get('formId')

    # 动态表单(formType==10) 且 formId 存在 → 拉表单
    form_data = None
    if form_type == 10 and form_id:
        form_data = _fetch_form(base_url, token, tenant_id, form_id)

    # simpleModel
    simple_model_data = model_data.get('simpleModel')

    _write_now(flow_dir, key, model_data, form_data, simple_model_data)

    # ---------- B) vN/ 历史版本（增量） ----------
    versions_resp = api_request(
        base_url,
        f'/admin-api/bpm/process-definition/page?key={urllib.parse.quote(key, safe="")}&pageNo=1&pageSize=100',
        token=token, tenant_id=tenant_id,
    )
    versions = versions_resp.get('data') or []
    if isinstance(versions, dict):
        versions = versions.get('list') or []

    added_versions = []
    skipped_versions = []
    warned_versions = []

    for v_item in versions:
        version = v_item.get('version')
        version_id = v_item.get('id')
        if version is None or not version_id:
            continue

        v_dir = os.path.join(flow_dir, f'v{version}')
        if os.path.isdir(v_dir):
            skipped_versions.append(version)
            continue

        # 拉取该版本详情
        def_resp = api_request(
            base_url,
            f'/admin-api/bpm/process-definition/get?id={urllib.parse.quote(version_id, safe="")}',
            token=token, tenant_id=tenant_id,
        )
        def_data = def_resp.get('data')
        if not def_data:
            warned_versions.append(version)
            continue

        # 冻结态表单（用流程定义里的 formConf/formFields/formName）
        v_form_data = None
        fc = def_data.get('formConf')
        ff = def_data.get('formFields')
        fn = def_data.get('formName')
        if fc is not None or ff is not None or fn is not None:
            v_form_data = {}
            if fc is not None:
                v_form_data['conf'] = fc
            if ff is not None:
                v_form_data['fields'] = ff
            if fn is not None:
                v_form_data['name'] = fn

        _write_version(flow_dir, key, version, def_data, v_form_data)
        added_versions.append(version)

    # 打印结果
    parts = [f'now 已更新']
    if added_versions:
        parts.append(f"新增 v{','.join(str(v) for v in sorted(added_versions))}")
    if skipped_versions:
        parts.append(f"跳过 v{','.join(str(v) for v in sorted(skipped_versions))}(已存在)")
    if warned_versions:
        parts.append(f"告警 v{','.join(str(v) for v in sorted(warned_versions))}(无详情)")
    print(f'[export] {key}: {"; ".join(parts)}')
    return True


def run(env: str, filter_keys: set):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    # 获取分类映射（用于交互式分组展示）
    category_map = get_category_map(base_url, token, tenant_id)

    print('[export] 获取模型列表...')
    models_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    models = models_resp.get('data') or []

    # 构建 key -> model_info 映射
    model_map = {}
    for item in models:
        k = item.get('key')
        if k:
            model_map[k] = item

    # 过滤
    keys_to_process = []
    if filter_keys:
        for k in filter_keys:
            if k in model_map:
                keys_to_process.append(k)
            else:
                print(f'[export] 警告: 服务端不存在流程 {k}')
    else:
        keys_to_process = list(model_map.keys())

    total = ok = 0
    for key in keys_to_process:
        model_info = model_map[key]
        name = model_info.get('name') or ''
        if _process_flow(env, base_url, token, tenant_id, key, name, model_info):
            ok += 1
        total += 1

    print(f'\n[export] 完成：处理 {total} 个流程，成功 {ok} 个')


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程拉取')
        print('=' * 44)
        env = prompt_env()

        cfg = get_config(env)
        base_url, tenant_id = cfg['url'], cfg['tenant_id']
        print('\n正在获取服务端流程列表...', end='', flush=True)
        token = login(base_url, tenant_id, cfg['username'], cfg['password'])
        models_resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
        models = models_resp.get('data') or []
        print(f' 共 {len(models)} 个流程')

        # 获取分类映射
        category_map = get_category_map(base_url, token, tenant_id)

        # 准备 prompt_flows 需要的数据
        flows = []
        for item in models:
            key = item.get('key', '')
            name = item.get('name', '')
            cat_code = item.get('category') or ''
            cat_name = category_map.get(cat_code) or cat_code or '未分类'
            flows.append((key, name, cat_name))

        selected_keys = prompt_flows(flows, category_of=lambda k: next((c for a, b, c in flows if a == k), '未分类'))
        print()
        run(env, set(selected_keys))
    else:
        parser = argparse.ArgumentParser(description='从 BPM 拉取流程到本地')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('keys', nargs='*', help='只拉取指定 key 的流程，不填则全量')
        args = parser.parse_args()
        run(args.env, set(args.keys))


if __name__ == '__main__':
    main()
