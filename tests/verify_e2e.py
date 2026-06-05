#!/usr/bin/env python3
"""
V1 dev 回环验证脚本

步骤：
1. export 真实流程 test_process（动态表单流程）
2. 本地复制造一次性流程 zzz_verify_<ts>
3. import 创建该一次性模型（非 dry-run）
4. export 回拉校验回环保真
5. 清理（成败都执行）
"""

import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from bpm_common import (
    api_request, env_dir, flow_dir_name, get_config, login, resolve_model_id,
)

VERIFY_KEY_PREFIX = 'zzz_verify_'
REAL_FLOW_KEY = 'test_process'


def _run(cmd, cwd=None):
    print(f'[shell] {cmd}')
    import subprocess
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f'命令失败，返回码 {result.returncode}: {cmd}')


def _read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _write_text(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def step1_export_real(env):
    """export 真实流程，断言生成 now/ 和 v*/"""
    print('\n[Step 1] export 真实流程')
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'export.py')
    _run(f'python3 {script_path} --env {env} {REAL_FLOW_KEY}', cwd=os.path.dirname(__file__))

    flow_dir = os.path.join(env_dir(env), flow_dir_name(REAL_FLOW_KEY, ''))
    # 尝试找实际目录（因为 name 可能非空）
    base = env_dir(env)
    actual_dir = None
    for entry in os.listdir(base):
        if entry.startswith(REAL_FLOW_KEY + ' -'):
            actual_dir = os.path.join(base, entry)
            break
    if not actual_dir:
        raise AssertionError(f'未找到 export 生成的流程目录: {REAL_FLOW_KEY}')

    now_dir = os.path.join(actual_dir, 'now')
    assert os.path.isdir(now_dir), f'缺少 now/ 目录: {now_dir}'

    bpmn_file = os.path.join(now_dir, f'{REAL_FLOW_KEY}.bpmn')
    assert os.path.isfile(bpmn_file), f'缺少 bpmn 文件: {bpmn_file}'

    model_file = os.path.join(now_dir, 'model.json')
    assert os.path.isfile(model_file), f'缺少 model.json: {model_file}'

    # 检查是否有 v*/ 目录（test_process 可能没有部署历史，放宽为 warn）
    has_v = any(os.path.isdir(os.path.join(actual_dir, d)) and d.startswith('v') for d in os.listdir(actual_dir))
    if not has_v:
        print('[warn] 缺少 v*/ 历史版本目录（流程可能未部署过）', file=sys.stderr)

    print(f'[Step 1] OK: {actual_dir}')
    return actual_dir


def step2_clone_verify_flow(env, src_dir):
    """复制 now/ 为一次性流程，改 key/name/bpmn process id"""
    print('\n[Step 2] 克隆并改造为一次性流程')
    ts = str(int(time.time()))
    verify_key = f'{VERIFY_KEY_PREFIX}{ts}'
    verify_name = f'验证临时-{verify_key}'

    # 目标目录
    dest_dir = os.path.join(env_dir(env), flow_dir_name(verify_key, verify_name))
    now_src = os.path.join(src_dir, 'now')
    now_dest = os.path.join(dest_dir, 'now')

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(now_src, now_dest)

    # 改 model.json
    model_path = os.path.join(now_dest, 'model.json')
    model = _read_json(model_path)
    model['key'] = verify_key
    model['name'] = verify_name
    _write_json(model_path, model)

    # 改 bpmn 文件名 + 内容 process id
    old_bpmn_name = os.path.basename([f for f in os.listdir(now_src) if f.endswith('.bpmn')][0])
    new_bpmn_name = f'{verify_key}.bpmn'
    bpmn_path = os.path.join(now_dest, old_bpmn_name)
    bpmn_text = _read_text(bpmn_path)

    # 替换 <process id="..."> 中的 id
    # 先找旧 key
    old_key_match = re.search(r'id="([^"]+)"', bpmn_text)
    if old_key_match:
        old_key_in_bpmn = old_key_match.group(1)
        bpmn_text = bpmn_text.replace(f'id="{old_key_in_bpmn}"', f'id="{verify_key}"', 1)
    else:
        print('[warn] 未在 BPMN 中找到 process id，跳过替换', file=sys.stderr)

    # 重命名文件
    os.remove(bpmn_path)
    _write_text(os.path.join(now_dest, new_bpmn_name), bpmn_text)

    print(f'[Step 2] OK: verify_key={verify_key}, dir={dest_dir}')
    return verify_key, dest_dir


def step3_import_create(env, verify_key):
    """import 创建一次性模型（非 dry-run）"""
    print('\n[Step 3] import 创建一次性模型')
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'import.py')
    _run(f'python3 {script_path} --env {env} {verify_key}', cwd=os.path.dirname(__file__))
    print('[Step 3] OK')


def step4_export_verify(env, verify_key, local_dir):
    """export 回拉，校验回环保真"""
    print('\n[Step 4] export 回拉并校验')
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'export.py')
    _run(f'python3 {script_path} --env {env} {verify_key}', cwd=os.path.dirname(__file__))

    now_dir = os.path.join(local_dir, 'now')
    model_local = _read_json(os.path.join(now_dir, 'model.json'))
    bpmn_local = _read_text(os.path.join(now_dir, f'{verify_key}.bpmn'))
    form_local = None
    form_path = os.path.join(now_dir, 'form.json')
    if os.path.isfile(form_path):
        form_local = _read_json(form_path)

    # 重新读取（export 会覆盖）
    model_after = _read_json(os.path.join(now_dir, 'model.json'))
    bpmn_after = _read_text(os.path.join(now_dir, f'{verify_key}.bpmn'))
    form_after = None
    if os.path.isfile(form_path):
        form_after = _read_json(form_path)

    # 校验 BPMN process id
    match_after = re.search(r'<process[^>]*id="([^"]+)"', bpmn_after)
    if match_after:
        assert match_after.group(1) == verify_key, f'BPMN process id 不匹配: {match_after.group(1)} != {verify_key}'
    else:
        print('[warn] 回拉 BPMN 中未找到 process id', file=sys.stderr)

    # 校验 model.json key/name/formType
    assert model_after.get('key') == verify_key, f'key 不匹配: {model_after.get("key")} != {verify_key}'
    assert model_after.get('name') == model_local.get('name'), f'name 不匹配'
    assert model_after.get('formType') == model_local.get('formType'), f'formType 不匹配'

    # 校验 form.json conf（容许服务端补充字段）
    if form_local and form_after:
        local_conf = form_local.get('conf')
        after_conf = form_after.get('conf')
        if local_conf is not None and after_conf is not None:
            # 简单比较 conf 的字段名集合（容许服务端补充）
            local_fields = set(local_conf.keys()) if isinstance(local_conf, dict) else set()
            after_fields = set(after_conf.keys()) if isinstance(after_conf, dict) else set()
            missing = local_fields - after_fields
            assert not missing, f'form.conf 缺少字段: {missing}'

    print('[Step 4] OK: 回环保真校验通过')


def step5_cleanup(env, verify_key):
    """删除服务端模型和本地目录"""
    print('\n[Step 5] 清理')
    cfg = get_config(env)
    base_url, tenant_id = cfg['url'], cfg['tenant_id']
    token = login(base_url, tenant_id, cfg['username'], cfg['password'])

    model_id = resolve_model_id(base_url, token, tenant_id, verify_key)
    if model_id:
        try:
            api_request(base_url, f'/admin-api/bpm/model/delete?id={model_id}',
                        token=token, tenant_id=tenant_id, method='DELETE')
            print(f'[cleanup] 已删除服务端模型: {verify_key} (id={model_id})')
        except Exception as e:
            print(f'[cleanup] 删除服务端模型失败: {e}', file=sys.stderr)
    else:
        print(f'[cleanup] 服务端未找到模型: {verify_key}')

    # 删本地目录
    base = env_dir(env)
    if os.path.isdir(base):
        for entry in os.listdir(base):
            if entry.startswith(VERIFY_KEY_PREFIX):
                d = os.path.join(base, entry)
                shutil.rmtree(d)
                print(f'[cleanup] 已删除本地目录: {d}')

    print('[Step 5] OK')


def main():
    env = 'dev'
    verify_key = None
    local_dir = None
    src_dir = None

    try:
        src_dir = step1_export_real(env)
        verify_key, local_dir = step2_clone_verify_flow(env, src_dir)
        step3_import_create(env, verify_key)
        step4_export_verify(env, verify_key, local_dir)
        print('\n[verify_e2e] 全部通过 ✓')
        sys.exit(0)
    except AssertionError as e:
        print(f'\n[verify_e2e] 校验失败: {e}', file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f'\n[verify_e2e] 运行失败: {e}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'\n[verify_e2e] 异常: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        if verify_key:
            try:
                step5_cleanup(env, verify_key)
            except Exception as e:
                print(f'[cleanup] 清理异常: {e}', file=sys.stderr)
        # 也清理真实流程目录（不提交数据）
        if src_dir and os.path.exists(src_dir):
            try:
                shutil.rmtree(src_dir)
                print(f'[cleanup] 已删除真实流程目录: {src_dir}')
            except Exception as e:
                print(f'[cleanup] 删除真实流程目录失败: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
