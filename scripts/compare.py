#!/usr/bin/env python3
"""多环境流程对比 —— 对比一个/多个流程在各环境的 BPMN 与 model.json 差异。

从各环境服务端实时拉取（不依赖本地文件），因此结果始终是线上真实状态。

用法：
  python3 scripts/compare.py pdp_quotation_request              # 四环境对比该流程
  python3 scripts/compare.py dc_zcd dc_resignation              # 一次对比多个
  python3 scripts/compare.py --envs dev,uat pdp_plan_common     # 只对比指定环境
  python3 scripts/compare.py --all                              # 四环境共有的全部流程(慎用,慢)

关键：判断「一致」看语义而非文本——BPMN 同一语义可有不同 XML 序列化风格
（默认命名空间+CDATA vs bpmn2:前缀），文本 diff 会误报。本工具用语义解析对比，
同时给出字节 MD5 供你判断是否需要统一序列化风格。
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import (
    CONFIGS, ENVS, DERIVED_FIELDS, ID_REF_FIELDS,
    api_request, bpmn_semantics, login,
)


def _load_ctx(envs):
    """登录各环境并拉取 model 列表，返回 {env: (token, {key: item})}"""
    ctx = {}
    for e in envs:
        c = CONFIGS[e]
        tok = login(c['url'], c['tenant_id'], c['username'], c['password'])
        r = api_request(c['url'], '/admin-api/bpm/model/list', token=tok, tenant_id=c['tenant_id'])
        ctx[e] = (tok, {m['key']: m for m in (r.get('data') or []) if m.get('key')})
    return ctx


def _get_model(env, ctx, key):
    tok, mlist = ctx[env]
    it = mlist.get(key)
    if not it:
        return None
    c = CONFIGS[env]
    r = api_request(c['url'], f"/admin-api/bpm/model/get?id={it['id']}",
                    token=tok, tenant_id=c['tenant_id'])
    return r.get('data') or {}


def compare_one(key, envs, ctx):
    """对比单个流程，返回 True=四环境完全一致。"""
    data = {e: _get_model(e, ctx, key) for e in envs}
    present = [e for e in envs if data[e] is not None]
    print(f"\n{'=' * 66}\n### {key}")
    if not present:
        print("  (所有指定环境都不存在此流程)")
        return False
    if len(present) < len(envs):
        print(f"  ⚠ 缺失于: {[e for e in envs if e not in present]}")

    # ---- BPMN 对比：字节 + 语义 ----
    md5 = {e: hashlib.md5((data[e].get('bpmnXml') or '').encode()).hexdigest() for e in present}
    sem = {e: bpmn_semantics(data[e].get('bpmnXml') or '') for e in present}
    byte_ok = len(set(md5.values())) == 1
    sem_ok = len({tuple(v) for v in sem.values()}) == 1
    print(f"  BPMN: 字节[{'一致' if byte_ok else '★不一致(序列化风格或内容不同)'}] "
          f"语义[{'一致' if sem_ok else '★不一致(流程逻辑不同)'}]")
    if not sem_ok:
        base = present[0]
        for e in present:
            if e == base:
                continue
            only_base = set(sem[base]) - set(sem[e])
            only_e = set(sem[e]) - set(sem[base])
            if only_base or only_e:
                print(f"    {base} vs {e}:")
                for x in sorted(only_base):
                    print(f"       仅 {base}: {x}")
                for x in sorted(only_e):
                    print(f"       仅 {e}: {x}")

    # ---- model.json 字段对比（排除派生字段）----
    allf = set()
    for e in present:
        allf |= set(data[e].keys())
    diffs = []
    for f in sorted(allf):
        if f in DERIVED_FIELDS:
            continue
        vals = {e: data[e].get(f) for e in present}
        if len({json.dumps(v, ensure_ascii=False, sort_keys=True) for v in vals.values()}) > 1:
            diffs.append((f, ' [ID引用]' if f in ID_REF_FIELDS else '', vals))
    if diffs:
        print("  字段差异:")
        for f, tag, vals in diffs:
            print(f"    ★ {f}{tag}:")
            for e in present:
                print(f"        {e:5s} = {json.dumps(vals[e], ensure_ascii=False)}")
    else:
        print("  字段差异: 无")

    ok = byte_ok and sem_ok and not diffs
    print(f"  => {'✅ 四环境完全一致' if ok else '有差异，需处理'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description='多环境流程对比')
    ap.add_argument('keys', nargs='*', help='流程 key，可多个')
    ap.add_argument('--envs', default=','.join(ENVS),
                    help='参与对比的环境，逗号分隔（默认 dev,test,uat,prod）')
    ap.add_argument('--all', action='store_true',
                    help='对比所有环境共同存在的流程（慎用，较慢）')
    args = ap.parse_args()

    envs = [e.strip() for e in args.envs.split(',') if e.strip() in CONFIGS]
    if not envs:
        print('无有效环境', file=sys.stderr)
        sys.exit(1)
    ctx = _load_ctx(envs)

    keys = args.keys
    if args.all:
        common = None
        for e in envs:
            ks = set(ctx[e][1].keys())
            common = ks if common is None else (common & ks)
        keys = sorted(common or [])
    if not keys:
        print('未指定流程 key（用 <key ...> 或 --all）', file=sys.stderr)
        sys.exit(1)

    identical = sum(1 for k in keys if compare_one(k, envs, ctx))
    print(f"\n{'=' * 66}\n共 {len(keys)} 个流程：完全一致 {identical}，有差异 {len(keys) - identical}")


if __name__ == '__main__':
    main()
