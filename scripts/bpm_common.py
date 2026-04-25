"""
BPM 公共配置与工具函数
"""
import glob
import json
import os
import sys
import urllib.error
import urllib.request

CONFIGS = {
    'dev':  {'url': 'http://192.168.1.182:30080', 'tenant_id': '1', 'username': 'admin', 'password': 'admin123'},
    'test': {'url': 'http://192.168.1.182:30082', 'tenant_id': '1', 'username': 'admin', 'password': 'admin123'},
    'uat':  {'url': 'http://192.168.1.182:30084', 'tenant_id': '1', 'username': 'admin', 'password': 'admin123'},
    'prod': {'url': 'http://192.168.1.182:30086', 'tenant_id': '1', 'username': 'admin', 'password': 'admin123'},
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLOWS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'flows')


def get_config(env):
    if env not in CONFIGS:
        print(f'[config] 未知环境: {env}（支持: {", ".join(CONFIGS)}）', file=sys.stderr)
        sys.exit(1)
    cfg = CONFIGS[env]
    print(f'[config] 当前环境: {env} ({cfg["url"]})', file=sys.stderr)
    return cfg


def api_request(base_url, path, token=None, tenant_id='1', method='GET', body=None):
    url = f'{base_url}{path}'
    headers = {'Content-Type': 'application/json', 'tenant-id': tenant_id}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', errors='replace')
        print(f'[http] {method} {url} -> {e.code}: {body_text}', file=sys.stderr)
        raise


def is_interactive() -> bool:
    """无命令行参数且在终端中运行时进入交互模式"""
    return len(sys.argv) == 1 and sys.stdin.isatty()


def prompt_env() -> str:
    """交互式选择环境"""
    envs = list(CONFIGS.keys())
    print('\n选择环境：')
    for i, name in enumerate(envs, 1):
        print(f'  {i}) {name:<6} {CONFIGS[name]["url"]}')
    while True:
        raw = input('请输入序号 [1]: ').strip() or '1'
        if raw.isdigit() and 1 <= int(raw) <= len(envs):
            chosen = envs[int(raw) - 1]
            print(f'  已选择: {chosen}')
            return chosen
        print(f'  请输入 1-{len(envs)} 之间的序号')


def list_local_flows() -> list:
    """返回本地流程列表 [(key, name, dir_path), ...]"""
    result = []
    for meta_file in sorted(glob.glob(os.path.join(FLOWS_DIR, '*', '*', 'meta.json'))):
        flow_dir = os.path.dirname(meta_file)
        dir_name = os.path.basename(flow_dir)
        key = dir_name.split(' - ')[0]
        name = dir_name[len(key):].lstrip(' -').strip()
        result.append((key, name, flow_dir))
    return result


def prompt_flows(flows: list) -> list:
    """交互式选择流程，返回选中的 key 列表；空列表表示全量"""
    print('\n选择流程：')
    print('  0) 全量（所有流程）')
    for i, (key, name, _) in enumerate(flows, 1):
        print(f'  {i}) {key}  {name}')
    print('\n输入序号选择（多个用空格分隔），直接回车表示全量：')
    raw = input('> ').strip()
    if not raw:
        print('  已选择: 全量')
        return []
    selected_keys = []
    for token in raw.replace(',', ' ').split():
        if token == '0':
            print('  已选择: 全量')
            return []
        if token.isdigit() and 1 <= int(token) <= len(flows):
            selected_keys.append(flows[int(token) - 1][0])
        else:
            print(f'  忽略无效输入: {token}')
    print(f'  已选择: {", ".join(selected_keys)}')
    return selected_keys


def login(base_url, tenant_id, username, password):
    print(f'[login] 正在登录 {base_url} ...', file=sys.stderr)
    try:
        result = api_request(
            base_url, '/admin-api/system/auth/login',
            tenant_id=tenant_id, method='POST',
            body={'username': username, 'password': password, 'tenantId': tenant_id},
        )
        token = (result.get('data') or {}).get('accessToken')
        if not token:
            print(f'[login] 登录失败: {result}', file=sys.stderr)
            sys.exit(1)
        print('[login] 登录成功', file=sys.stderr)
        return token
    except Exception as e:
        print(f'[login] 登录异常: {e}', file=sys.stderr)
        sys.exit(1)
