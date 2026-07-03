"""
BPM 公共配置与工具函数
"""
import glob
import json
import os
import sys
import time
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


def api_request(base_url, path, token=None, tenant_id='1', method='GET', body=None,
                timeout=30, retries=2):
    """发起 BPM API 请求。

    timeout: 单次请求超时秒数（默认 30）。
    retries: 网络异常/超时时的额外重试次数（默认 2，即最多尝试 3 次）；
             HTTP 错误码(4xx/5xx，业务/校验失败) 不重试、直接抛出。
    """
    url = f'{base_url}{path}'
    headers = {'Content-Type': 'application/json', 'tenant-id': tenant_id}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            # HTTP 错误码通常不是瞬时问题，不重试
            body_text = e.read().decode('utf-8', errors='replace')
            print(f'[http] {method} {url} -> {e.code}: {body_text}', file=sys.stderr)
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries:
                wait = 2 * (attempt + 1)
                print(f'[http] {method} {url} 网络异常({e})，{wait}s 后重试 '
                      f'({attempt + 1}/{retries})', file=sys.stderr)
                time.sleep(wait)
            else:
                print(f'[http] {method} {url} 网络异常，重试耗尽: {e}', file=sys.stderr)
    raise last_err


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


def list_models(base_url, token, tenant_id) -> dict:
    """一次性拉取全部 model，返回 {key: item} 映射，供批量判断 update/create。"""
    resp = api_request(base_url, '/admin-api/bpm/model/list', token=token, tenant_id=tenant_id)
    data = resp.get('data') or []
    return {item.get('key'): item for item in data if item.get('key')}


def resolve_model_id(base_url, token, tenant_id, key) -> str | None:
    """按 key 反查 modelId（UUID），找不到返回 None"""
    item = list_models(base_url, token, tenant_id).get(key)
    return item.get('id') if item else None


def fetch_model_bpmn(base_url, token, tenant_id, model_id) -> str:
    """按 modelId 拉取服务端当前存储的 bpmnXml（用于推送后回读校验）。"""
    resp = api_request(base_url, f'/admin-api/bpm/model/get?id={model_id}',
                       token=token, tenant_id=tenant_id)
    return (resp.get('data') or {}).get('bpmnXml') or ''


def looks_like_bpmn_xml(text: str) -> bool:
    """判断字符串是否是合法的 BPMN XML（以 < 开头且含 process 元素）。
    服务端 XSS 过滤会把 XML 标签剥光，只剩纯文本——用此判断可识别这种损坏。"""
    if not text:
        return False
    s = text.lstrip('﻿').strip()
    return s.startswith('<') and 'process' in s.lower()


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


# ======================================================================
# 流程模型共享工具（compare.py / check_refs.py / sync.py 复用）
# ======================================================================

# model.json 里的派生/运行时/已拆分字段：export 已剥离，比较/覆盖时应忽略
DERIVED_FIELDS = {
    'id', 'modelId', 'categoryName', 'formName', 'deploymentTime',
    'suspensionState', 'createTime', 'processDefinition', 'startUsers',
    'startDepts', 'bpmnXml', 'simpleModel', 'formConf', 'formFields',
}

# model.json 里引用「实体 ID」的字段（跨环境同步前需核对这些 ID 一致存在）
ID_REF_FIELDS = {
    'managerUserIds': 'user', 'startUserIds': 'user',
    'managerRoleIds': 'role', 'startDeptIds': 'dept',
}

# candidateStrategy / copyStrategy 编码 -> (名称, 参数引用的实体类型)
# 实体类型: role/user/post/dept/group 需按 ID 核对；
#          expr(${var})/form(表单字段)/none(无参) 不核对 ID。
# 来源：yudao-cloud BpmTaskCandidateStrategyEnum（与 SKILL.md 对照表一致）。
CANDIDATE_STRATEGY = {
    1:  ('审批人为空', 'none'),
    10: ('角色', 'role'),
    20: ('部门成员(含负责人)', 'dept'),
    21: ('部门负责人', 'dept'),
    22: ('岗位', 'post'),
    23: ('连续多级部门负责人', 'dept'),
    30: ('用户', 'user'),
    34: ('审批人自身', 'none'),
    35: ('发起人自选', 'none'),
    36: ('发起人自己', 'none'),
    37: ('发起人部门负责人', 'none'),
    38: ('发起人连续多级部门负责人', 'none'),
    39: ('直属领导', 'none'),
    40: ('用户组', 'group'),
    50: ('表单内用户字段', 'form'),
    51: ('表单内部门负责人', 'form'),
    60: ('流程表达式', 'expr'),
    70: ('团队成员(角色字典)', 'role'),
    71: ('虚拟组织', 'none'),
}


def bpmn_semantics(xml: str):
    """把 BPMN 解析成规范化语义节点列表（忽略序列化风格/图形坐标/元素顺序）。
    返回排序后的字符串列表；解析失败返回 [('PARSE_ERR', ...)]。
    用于判断两份 BPMN 是否「语义等价」（文本 diff 不可靠，风格差异会误报）。"""
    import re
    import xml.etree.ElementTree as ET
    try:
        t = re.sub(r'xmlns(:\w+)?="[^"]*"', '', xml)       # 去命名空间声明
        t = re.sub(r'(</?)[A-Za-z_][\w.-]*:', r'\1', t)    # 去元素前缀
        t = re.sub(r'(\s)[A-Za-z_][\w.-]*:', r'\1', t)     # 去属性前缀
        proc = ET.fromstring(t).find('.//process')
        out = []
        for el in proc:
            tag = re.sub(r'\{[^}]*\}', '', el.tag)
            if tag == 'extensionElements':
                continue
            if tag == 'sequenceFlow':
                out.append(f"F:{el.get('sourceRef')}>{el.get('targetRef')}")
                continue
            ex = ''
            if tag in ('userTask', 'serviceTask', 'receiveTask'):
                e = el.find('extensionElements')
                if e is not None:
                    for tn in ['candidateStrategy', 'candidateParam', 'approveMethod',
                               'approveType', 'copyStrategy', 'copyParam']:
                        n = e.find(tn)
                        if n is not None and (n.text or '').strip():
                            ex += f" {tn}={n.text.strip()}"
            out.append(f"{tag}:{el.get('name') or el.get('id')}{ex}")
        return sorted(out)
    except Exception as ex:
        return [('PARSE_ERR', str(ex))]


def extract_bpmn_refs(xml: str):
    """提取 BPMN 里所有节点的候选人/抄送引用。
    返回 [(node_name, kind, strategy, entity_type, param), ...]
      kind: 'candidate' | 'copy'
      entity_type: role/user/post/dept/group/form/expr/none/unknown
    仅保留 entity_type 属于 role/user/post/dept/group 的（需核对 ID 的）由调用方过滤。"""
    import re
    import xml.etree.ElementTree as ET
    t = re.sub(r'xmlns(:\w+)?="[^"]*"', '', xml)
    t = re.sub(r'(</?)[A-Za-z_][\w.-]*:', r'\1', t)
    t = re.sub(r'(\s)[A-Za-z_][\w.-]*:', r'\1', t)
    proc = ET.fromstring(t).find('.//process')
    refs = []
    for el in proc:
        e = el.find('extensionElements')
        if e is None:
            continue
        name = el.get('name') or el.get('id')
        for kind, sfield, pfield in [('candidate', 'candidateStrategy', 'candidateParam'),
                                     ('copy', 'copyStrategy', 'copyParam')]:
            sn = e.find(sfield)
            if sn is None or not (sn.text or '').strip():
                continue
            try:
                strat = int(sn.text.strip())
            except ValueError:
                continue
            pn = e.find(pfield)
            param = (pn.text or '').strip() if pn is not None else ''
            etype = CANDIDATE_STRATEGY.get(strat, ('未知', 'unknown'))[1]
            refs.append((name, kind, strat, etype, param))
    return refs


# 各实体类型 -> (拉取列表的候选 API 路径, 该实体在返回项里的显示名字段)
ENTITY_API = {
    'role': (['/admin-api/system/role/list',
              '/admin-api/system/role/page?pageNo=1&pageSize=500'], 'name'),
    'user': (['/admin-api/system/user/simple-list',
              '/admin-api/system/user/list-all-simple',
              '/admin-api/system/user/page?pageNo=1&pageSize=1000'], 'nickname'),
    'post': (['/admin-api/system/post/list-all-simple',
              '/admin-api/system/post/simple-list',
              '/admin-api/system/post/page?pageNo=1&pageSize=300'], 'name'),
    'dept': (['/admin-api/system/dept/list',
              '/admin-api/system/dept/simple-list'], 'name'),
    'group': (['/admin-api/bpm/user-group/simple-list',
               '/admin-api/bpm/user-group/list'], 'name'),
}


def fetch_entity_map(base_url, token, tenant_id, etype):
    """拉取某类实体的 {id(str): name} 映射。用于跨环境核对 ID 引用。"""
    paths, name_field = ENTITY_API.get(etype, (None, None))
    if not paths:
        return {}
    for p in paths:
        try:
            resp = api_request(base_url, p, token=token, tenant_id=tenant_id)
            data = resp.get('data')
            if isinstance(data, dict):
                data = data.get('list')
            if data:
                return {str(x.get('id')): (x.get(name_field) or x.get('name')
                                           or x.get('nickname')) for x in data}
        except Exception:
            continue
    return {}
