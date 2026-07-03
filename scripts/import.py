#!/usr/bin/env python3
"""
将本地 <env>/<key> - <name>/now/ 回推到 BPM（不发布）

直接运行进入交互模式：
  ./import.py

带参数直接执行（适合自动化）：
  ./import.py --env dev pdp-review_udit2
  ./import.py --env dev --dry-run pdp-review_udit2
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (
    api_request, env_dir, fetch_model_bpmn, get_category_map, get_config,
    is_interactive, list_local_flows, list_models, login, looks_like_bpmn_xml,
    prompt_env, prompt_flows,
)


def _read_now(flow_dir, key):
    """读取 now/ 目录下的 model.json、bpmn、form.json(可选)。
    返回 (model_dict, bpmn_str, form_dict_or_None)
    """
    now_dir = os.path.join(flow_dir, 'now')
    model_path = os.path.join(now_dir, 'model.json')
    bpmn_path = os.path.join(now_dir, f'{key}.bpmn')

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f'缺少 model.json: {model_path}')
    if not os.path.isfile(bpmn_path):
        raise FileNotFoundError(f'缺少 bpmn 文件: {bpmn_path}')

    with open(model_path, encoding='utf-8') as f:
        model = json.load(f)

    with open(bpmn_path, encoding='utf-8') as f:
        bpmn = f.read()

    form = None
    form_path = os.path.join(now_dir, 'form.json')
    if os.path.isfile(form_path):
        with open(form_path, encoding='utf-8') as f:
            form = json.load(f)

    return model, bpmn, form


def _prompt_category(current_category, category_map):
    """交互式让用户选择分类。返回最终 category code。
    category_map: {code: name}
    """
    print(f'\n  当前分类: {current_category or "(空)"}')
    codes = sorted(category_map.keys())
    if codes:
        print('  可选分类（回车保持当前）：')
        for i, code in enumerate(codes, 1):
            marker = ' *' if code == current_category else ''
            print(f'    {i}) {code} ({category_map[code]}){marker}')
    else:
        print('  目标环境暂无分类，回车保持当前')

    while True:
        raw = input('  请输入序号或分类 code [回车保持]: ').strip()
        if not raw:
            return current_category
        if raw in category_map:
            return raw
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(codes):
                return codes[idx]
        print(f'    无效输入，请重试')


def _build_body(model, bpmn, category, model_id=None):
    """构造 update/create 的 body。透传 model.json 字段，补上 bpmnXml/category，update 时加 id。"""
    body = dict(model)
    body['bpmnXml'] = bpmn
    body['category'] = category
    if model_id:
        body['id'] = model_id
    return body


def _dry_run_summary(key, name, category, form_id, bpmn_len, is_update):
    action = 'update' if is_update else 'create'
    form_info = f', formId={form_id}' if form_id else ''
    print(f'  [dry-run] {action}: key={key}, name={name}, category={category}{form_info}, bpmnXml={bpmn_len} chars')


def _verify_pushed_bpmn(base_url, token, tenant_id, model_id, pushed_bpmn):
    """推送后回读服务端 BPMN，确认未被损坏（如目标环境 XSS 过滤剥除了 XML 标签）。
    返回 True=完好，False=损坏。"""
    try:
        stored = fetch_model_bpmn(base_url, token, tenant_id, model_id)
    except Exception as e:
        print(f'  -> [警告] 推送后回读校验失败（无法获取，跳过校验）: {e}', file=sys.stderr)
        return True
    if not looks_like_bpmn_xml(stored):
        print(f'  -> [严重] 服务端 BPMN 已损坏（长度 {len(stored)}，不是合法 XML）！'
              f'\n        极可能是目标环境 yudao.xss 过滤剥除了 XML 标签。'
              f'\n        请确认目标环境 yudao.xss.exclude-urls 包含 /admin-api/bpm/model/create|update。',
              file=sys.stderr)
        return False
    if len(stored.strip()) < len(pushed_bpmn.strip()) * 0.5:
        print(f'  -> [警告] 服务端 BPMN 长度异常缩水（推送 {len(pushed_bpmn)} → 存储 {len(stored)}）',
              file=sys.stderr)
    return True


def _import_flow(base_url, token, tenant_id, key, name, flow_dir,
                 category_map, existing_models, dry_run=False, interactive=False):
    """处理单个流程：读本地 now/ → 判断 update/create → 推送（或 dry-run 打印）。
    existing_models: 预取的 {key: model_item} 映射，避免逐个拉取。"""
    model, bpmn, form = _read_now(flow_dir, key)

    # 推送前校验本地 BPMN 完整性，避免把损坏数据推上去
    if not looks_like_bpmn_xml(bpmn):
        print(f'  -> [跳过] 本地 BPMN 不是合法 XML（长度 {len(bpmn)}），疑似文件损坏，拒绝推送',
              file=sys.stderr)
        return False

    # 当前 model.json 里的分类
    current_category = model.get('category') or ''

    # 分类选择
    if interactive and category_map is not None:
        final_category = _prompt_category(current_category, category_map)
    else:
        final_category = current_category

    # 判断 update 还是 create（用预取映射）
    existing = existing_models.get(key)
    model_id = existing.get('id') if existing else None
    is_update = model_id is not None

    # formId：动态表单(formType==10) 且本地有 form.json 时，model.json 里应已有 formId（来自 export）
    # 这里不做额外处理，透传即可
    form_id = model.get('formId')

    body = _build_body(model, bpmn, final_category, model_id)

    if dry_run:
        _dry_run_summary(key, name, final_category, form_id, len(bpmn), is_update)
        return True

    # 真正发请求
    if is_update:
        resp = api_request(base_url, '/admin-api/bpm/model/update',
                           token=token, tenant_id=tenant_id, method='PUT', body=body)
        action = '更新'
    else:
        resp = api_request(base_url, '/admin-api/bpm/model/create',
                           token=token, tenant_id=tenant_id, method='POST', body=body)
        action = '新建'

    if resp.get('code') != 0:
        print(f'  -> {action}失败: {resp.get("msg", "unknown")}', file=sys.stderr)
        return False

    # 推送后回读校验：确认服务端 BPMN 没被损坏
    new_model_id = model_id if is_update else resp.get('data')
    if new_model_id and not _verify_pushed_bpmn(base_url, token, tenant_id, new_model_id, bpmn):
        print(f'  -> {action}已提交但校验未通过（数据损坏）', file=sys.stderr)
        return False

    print(f'  -> {action}成功')
    return True


def _deploy_keys(base_url, token, tenant_id, keys):
    """推送成功后自动部署这些 key（激活为可发起的流程定义）。"""
    if not keys:
        return
    print(f'\n[import] 自动部署 {len(keys)} 个流程...')
    models = list_models(base_url, token, tenant_id)
    for k in keys:
        it = models.get(k)
        if not it:
            print(f'  -> {k}: 部署跳过（找不到 model）', file=sys.stderr)
            continue
        resp = api_request(base_url, f"/admin-api/bpm/model/deploy?id={it['id']}",
                           token=token, tenant_id=tenant_id, method='POST')
        if resp.get('code') == 0:
            print(f'  -> {k}: 部署成功')
        else:
            print(f'  -> {k}: 部署失败 {resp.get("msg")}', file=sys.stderr)


def run(env: str, filter_keys: set, dry_run=False, deploy=False):
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    # 获取目标环境分类映射（用于交互式切换）+ 预取 model 映射（判断 update/create）
    category_map = get_category_map(base_url, token, tenant_id)
    existing_models = list_models(base_url, token, tenant_id)

    # 扫描本地含 now/ 的流程
    flows = list_local_flows(env)
    if not flows:
        print('[import] 本地无可用流程（缺少 now/ 目录）')
        return

    # 过滤
    if filter_keys:
        flows = [(k, n, d) for k, n, d in flows if k in filter_keys]
        missing = filter_keys - {k for k, _, _ in flows}
        for k in missing:
            print(f'[import] 警告: 本地不存在流程 {k}')

    if not flows:
        print('[import] 无匹配流程')
        return

    total = ok = failed = 0
    ok_keys = []
    for key, name, flow_dir in flows:
        print(f'[import] 处理: {key} - {name}')
        try:
            if _import_flow(base_url, token, tenant_id, key, name, flow_dir,
                            category_map, existing_models, dry_run=dry_run, interactive=False):
                ok += 1
                ok_keys.append(key)
            else:
                failed += 1
        except Exception as e:
            print(f'  -> 异常: {e}', file=sys.stderr)
            failed += 1
        total += 1

    mode_str = '（dry-run，未实际推送）' if dry_run else ''
    print(f'\n[import] 完成{mode_str}：处理 {total}，成功 {ok}，失败 {failed}')

    if deploy and not dry_run:
        _deploy_keys(base_url, token, tenant_id, ok_keys)


def main():
    if is_interactive():
        print('=' * 44)
        print('  BPM 流程回推（import）')
        print('=' * 44)
        env = prompt_env()

        cfg = get_config(env)
        base_url, tenant_id = cfg['url'], cfg['tenant_id']
        token = login(base_url, tenant_id, cfg['username'], cfg['password'])
        category_map = get_category_map(base_url, token, tenant_id)
        existing_models = list_models(base_url, token, tenant_id)

        flows = list_local_flows(env)
        if not flows:
            print('[import] 本地无可用流程')
            return

        selected_keys = prompt_flows(flows, category_of=lambda k: next(
            (cat for a, b, cat in flows if a == k), '未分类'))

        dry_run = False
        raw = input('\n是否只预览不推送？(y/N): ').strip().lower()
        if raw == 'y':
            dry_run = True
            print('  已选择: dry-run 模式')

        deploy = False
        if not dry_run:
            raw = input('推送成功后自动部署？(Y/n): ').strip().lower()
            deploy = raw != 'n'

        print()
        # 交互模式下逐个处理，支持逐个分类切换
        total = ok = failed = 0
        ok_keys = []
        for key, name, flow_dir in flows:
            if selected_keys and key not in selected_keys:
                continue
            print(f'[import] 处理: {key} - {name}')
            try:
                if _import_flow(base_url, token, tenant_id, key, name, flow_dir,
                                category_map, existing_models, dry_run=dry_run, interactive=True):
                    ok += 1
                    ok_keys.append(key)
                else:
                    failed += 1
            except Exception as e:
                print(f'  -> 异常: {e}', file=sys.stderr)
                failed += 1
            total += 1

        mode_str = '（dry-run，未实际推送）' if dry_run else ''
        print(f'\n[import] 完成{mode_str}：处理 {total}，成功 {ok}，失败 {failed}')

        if deploy and not dry_run:
            _deploy_keys(base_url, token, tenant_id, ok_keys)
    else:
        parser = argparse.ArgumentParser(description='将本地 now/ 回推到 BPM')
        parser.add_argument('--env', default=os.environ.get('ENV', 'dev'))
        parser.add_argument('--dry-run', action='store_true', help='只打印，不实际推送')
        parser.add_argument('--deploy', action='store_true', help='推送成功后自动部署')
        parser.add_argument('keys', nargs='*', help='指定流程 key，不填则处理本地全部')
        args = parser.parse_args()
        run(args.env, set(args.keys), dry_run=args.dry_run, deploy=args.deploy)


if __name__ == '__main__':
    main()
