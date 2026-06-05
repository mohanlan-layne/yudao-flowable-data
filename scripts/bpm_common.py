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

ENVS = list(CONFIGS.keys())

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)


def env_dir(env):
    """返回指定环境的数据目录路径"""
    return os.path.join(ROOT_DIR, env)


def safe(s):
    """将字符串中的 / 替换为 -，保证可作为文件名/目录名"""
    return s.replace('/', '-')


def flow_dir_name(key, name):
    """生成流程目录名: '{key} - {name}'，key 中的 / 会被替换"""
    return f"{safe(key)} - {name}"


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


def list_local_flows(env) -> list:
    """扫描指定环境下含 now/ 子目录的流程目录。
    返回 [(key, name, flow_dir), ...]，按 key 排序。
    """
    result = []
    base = env_dir(env)
    if not os.path.isdir(base):
        return result
    for entry in sorted(os.listdir(base)):
        flow_path = os.path.join(base, entry)
        if not os.path.isdir(flow_path):
            continue
        now_path = os.path.join(flow_path, 'now')
        if not os.path.isdir(now_path):
            continue
        # 解析 "key - name"
        if ' - ' in entry:
            key, name = entry.split(' - ', 1)
        else:
            key = entry
            name = ''
        result.append((key, name, flow_path))
    return sorted(result, key=lambda x: x[0])


def prompt_flows(flows: list, category_of=None) -> list:
    """交互式选择流程，返回选中的 key 列表；空列表表示全量。
    flows: [(key, name, category_or_dir...), ...]
    category_of: 可选函数/字典，key -> category_name；拿不到则放「未分类」。
    """
    print('\n选择流程：')
    print('  0) 全量（所有流程）')

    # 按分类分组
    groups = {}
    for i, item in enumerate(flows, 1):
        key = item[0]
        name = item[1] if len(item) > 1 else ''
        if callable(category_of):
            cat = category_of(key) or '未分类'
        elif isinstance(category_of, dict):
            cat = category_of.get(key) or '未分类'
        else:
            cat = '未分类'
        groups.setdefault(cat, []).append((i, key, name))

    idx = 1
    index_map = {}
    for cat in sorted(groups.keys(), key=lambda c: (c == '未分类', c)):
        print(f'\n  [{cat}]')
        for _, key, name in groups[cat]:
            print(f'    {idx}) {key}  {name}')
            index_map[idx] = key
            idx += 1

    print('\n输入序号选择（多个用空格或逗号分隔），直接回车表示全量：')
    raw = input('> ').strip()
    if not raw:
        print('  已选择: 全量')
        return []
    selected_keys = []
    for token in raw.replace(',', ' ').split():
        if token == '0':
            print('  已选择: 全量')
            return []
        if token.isdigit():
            num = int(token)
            if num in index_map:
                selected_keys.append(index_map[num])
            else:
                print(f'  忽略无效输入: {token}')
        else:
            print(f'  忽略无效输入: {token}')
    print(f'  已选择: {", ".join(selected_keys)}')
    return selected_keys


def resolve_model_id(base_url, token, tenant_id, key) -> str | None:
    """按 key 反查 modelId（UUID），找不到返回 None"""
    resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    data = resp.get('data') or []
    for item in data:
        if item.get('key') == key:
            return item.get('id')
    return None


def get_category_map(base_url, token, tenant_id) -> dict:
    """获取分类映射: {code: name}"""
    resp = api_request(base_url, '/admin-api/bpm/category/simple-list', token=token, tenant_id=tenant_id)
    data = resp.get('data') or []
    return {item.get('code'): item.get('name') for item in data if item.get('code')}


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
