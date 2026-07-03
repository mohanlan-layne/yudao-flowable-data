#!/usr/bin/env python3
"""ID 引用核对 —— 检查流程引用的角色/用户/岗位/部门/用户组 ID 在各环境是否一致存在。

**跨环境同步流程前必跑。** BPMN 里的 candidateParam/copyParam、model.json 里的
managerUserIds/managerRoleIds/startUserIds/startDeptIds，引用的都是「实体 ID」，
而实体 ID 是跟环境走的。盲目把一个环境的流程推到另一个环境，可能引用到目标环境
不存在的、或名称不同的实体（本仓库踩过：角色 817 其实是"条码查询"、
candidateStrategy=30 是「用户」却被误当岗位）。

本工具按 candidateStrategy 判断实体类型（见 bpm_common.CANDIDATE_STRATEGY），
逐一在各环境查该 ID 的名称并对比。

用法：
  python3 scripts/check_refs.py system-it-request
  python3 scripts/check_refs.py --envs dev,uat,prod dc_zcd pdm_bom_enc
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (
    CONFIGS, ENVS, ID_REF_FIELDS,
    api_request, extract_bpmn_refs, fetch_entity_map, login,
)


def _load_ctx(envs):
    ctx = {}
    for e in envs:
        c = CONFIGS[e]
        tok = login(c['url'], c['tenant_id'], c['username'], c['password'])
        r = api_request(c['url'], '/admin-api/bpm/model/list', token=tok, tenant_id=c['tenant_id'])
        ctx[e] = (tok, {m['key']: m for m in (r.get('data') or []) if m.get('key')})
    return ctx


def _get_model(env, ctx, key):
    tok, ml = ctx[env]
    it = ml.get(key)
    if not it:
        return None
    c = CONFIGS[env]
    return api_request(c['url'], f"/admin-api/bpm/model/get?id={it['id']}",
                       token=tok, tenant_id=c['tenant_id']).get('data') or {}


def check_one(key, envs, ctx, entity_cache):
    print(f"\n{'=' * 66}\n### {key}")
    models = {e: _get_model(e, ctx, key) for e in envs}
    present = [e for e in envs if models[e] is not None]
    if not present:
        print("  (指定环境都不存在此流程)")
        return True

    # 汇总所有环境出现过的引用 {(entity_type, id): set(来源描述)}
    refs = {}

    def add(etype, raw, src):
        for i in str(raw).split(','):
            i = i.strip()
            if i.isdigit():            # 只核对数字 ID；表达式/表单字段跳过
                refs.setdefault((etype, i), set()).add(src)

    for e in present:
        m = models[e]
        for name, kind, strat, etype, param in extract_bpmn_refs(m.get('bpmnXml') or ''):
            if etype in ('role', 'user', 'post', 'dept', 'group'):
                add(etype, param, f"节点[{name}]{'-抄送' if kind == 'copy' else ''}(策略{strat})")
        for fld, etype in ID_REF_FIELDS.items():
            v = m.get(fld)
            if isinstance(v, list):
                for i in v:
                    add(etype, i, fld)

    if not refs:
        print("  ✅ 无需核对的 ID 引用（全是发起人自选/表达式/表单字段等）")
        return True

    hdr = f"  {'实体':>5} {'ID':>6} | " + " ".join(f"{e:^12}" for e in envs) + " | 状态"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    all_ok = True
    for (etype, i) in sorted(refs.keys()):
        names = {}
        for e in envs:
            cache_key = (e, etype)
            if cache_key not in entity_cache:
                c = CONFIGS[e]
                entity_cache[cache_key] = fetch_entity_map(c['url'], ctx[e][0], c['tenant_id'], etype)
            names[e] = entity_cache[cache_key].get(i)
        missing = [e for e in envs if names[e] is None]
        distinct = {names[e] for e in envs if names[e] is not None}
        if missing:
            status = f"★缺失于 {','.join(missing)}"
            all_ok = False
        elif len(distinct) > 1:
            status = "★名称不一致"
            all_ok = False
        else:
            status = "✓"
        row = " ".join(f"{(names[e] or '—'):^12}" for e in envs)
        print(f"  {etype:>5} {i:>6} | {row} | {status}")

    print(f"  => {'✅ 所有引用四环境一致存在' if all_ok else '⚠ 有引用缺失/名称不一致，同步前先处理'}")
    return all_ok


def main():
    ap = argparse.ArgumentParser(description='流程 ID 引用跨环境核对')
    ap.add_argument('keys', nargs='+', help='流程 key，可多个')
    ap.add_argument('--envs', default=','.join(ENVS), help='参与核对的环境，逗号分隔')
    args = ap.parse_args()
    envs = [e.strip() for e in args.envs.split(',') if e.strip() in CONFIGS]
    ctx = _load_ctx(envs)
    entity_cache = {}
    ok = sum(1 for k in args.keys if check_one(k, envs, ctx, entity_cache))
    print(f"\n{'=' * 66}\n共 {len(args.keys)} 个流程：全部引用一致 {ok}，有问题 {len(args.keys) - ok}")


if __name__ == '__main__':
    main()
