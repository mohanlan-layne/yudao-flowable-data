#!/usr/bin/env python3
"""跨环境同步 —— 以源环境为基准，把流程同步到一个/多个目标环境并部署。

**方向不固定**：--from / --to 可任意组合（dev→test、uat→prod、prod→dev 皆可），
因为同步方向由每次需求决定，以你指定的为准。

流程：export 源(拉最新) → 用源 now 覆盖目标(可选保留目标专属字段) →
      import 目标 → deploy 目标 → 只对确有变化的目标推送。

用法：
  # dev 完全一致同步到 test 和 uat
  python3 scripts/sync.py --from dev --to test,uat pdp_quotation_request
  # uat 同步到 prod，但保留 prod 的可管理人/排序（只同步流程逻辑，不动环境专属配置）
  python3 scripts/sync.py --from uat --to prod --keep managerUserIds,managerRoleIds,sort dc_zcd
  python3 scripts/sync.py --from dev --to test --dry-run xxx      # 预览不推送
  python3 scripts/sync.py --from dev --to test --no-deploy xxx    # 只更新草稿不部署

⚠ 同步前务必先跑：check_refs.py 核对 ID 引用、compare.py 看清差异。
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpm_common import CONFIGS, env_dir, flow_dir_name

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _run(cmd, ok_kw):
    """跑子命令，成功判定为 returncode==0 且输出含 ok_kw；失败重试一次。"""
    out = ''
    for _ in range(2):
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = r.stdout + r.stderr
        if r.returncode == 0 and ok_kw in out:
            return True, out
        time.sleep(2)
    return False, out


def _flow_dir(env, key):
    """返回该环境下匹配 key 的流程目录，找不到返回 None。"""
    hits = glob.glob(os.path.join(env_dir(env), f"{key} - *"))
    hits = [h for h in hits if os.path.isdir(os.path.join(h, 'now'))]
    return hits[0] if hits else None


def _read_now(flow_dir):
    model = json.load(open(os.path.join(flow_dir, 'now', 'model.json'), encoding='utf-8'))
    bpmns = glob.glob(os.path.join(flow_dir, 'now', '*.bpmn'))
    bpmn = open(bpmns[0], encoding='utf-8').read() if bpmns else ''
    return model, bpmn


def sync_key(key, src, targets, keep, dry_run):
    """把 src 的 key 同步到各 targets（写本地）。返回需要推送的 target 列表。"""
    src_dir = _flow_dir(src, key)
    if not src_dir:
        print(f"  ✗ 源 {src} 不存在流程 {key}，跳过")
        return []
    src_model, src_bpmn = _read_now(src_dir)
    name = src_model.get('name') or key
    bpmn_name = f"{key}.bpmn"

    to_push = []
    for t in targets:
        tdir = _flow_dir(t, key)
        cur_model, cur_bpmn = ({}, None)
        if tdir:
            cur_model, cur_bpmn = _read_now(tdir)
        else:
            # 目标没有该流程 → 新建目录（import 时会走 create）
            tdir = os.path.join(env_dir(t), flow_dir_name(key, name))
            os.makedirs(os.path.join(tdir, 'now'), exist_ok=True)

        target_model = dict(src_model)
        kept = []
        for kf in keep:
            if kf in cur_model:
                target_model[kf] = cur_model[kf]
                kept.append(kf)

        if cur_model == target_model and cur_bpmn == src_bpmn:
            print(f"  · {t}/{key}: 已一致，跳过")
            continue

        note = f"（保留 {','.join(kept)}）" if kept else ""
        if dry_run:
            print(f"  [dry-run] {t}/{key}: 将以 {src} 覆盖{note}")
            continue

        json.dump(target_model, open(os.path.join(tdir, 'now', 'model.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        open(os.path.join(tdir, 'now', bpmn_name), 'w', encoding='utf-8').write(src_bpmn)
        print(f"  ✎ {t}/{key}: 已写入本地{note}")
        to_push.append(t)
    return to_push


def main():
    ap = argparse.ArgumentParser(description='跨环境同步流程（任意方向）')
    ap.add_argument('keys', nargs='+', help='流程 key，可多个')
    ap.add_argument('--from', dest='src', required=True, help='源环境（基准）')
    ap.add_argument('--to', dest='to', required=True, help='目标环境，逗号分隔')
    ap.add_argument('--keep', default='', help='覆盖时保留目标环境的字段，逗号分隔'
                                              '（如 managerUserIds,managerRoleIds,sort）')
    ap.add_argument('--dry-run', action='store_true', help='只预览，不写本地、不推送')
    ap.add_argument('--no-deploy', action='store_true', help='推送后不自动部署（只更新草稿）')
    ap.add_argument('--no-export', action='store_true', help='跳过拉取源最新（直接用本地源 now）')
    args = ap.parse_args()

    src = args.src
    targets = [t.strip() for t in args.to.split(',') if t.strip() in CONFIGS]
    keep = [k.strip() for k in args.keep.split(',') if k.strip()]
    if src not in CONFIGS or not targets:
        print('源或目标环境无效', file=sys.stderr)
        sys.exit(1)
    if src in targets:
        print('源和目标不能相同', file=sys.stderr)
        sys.exit(1)

    # 1) 拉取源最新（确保基准是线上真实状态）
    if not args.no_export and not args.dry_run:
        print(f"[sync] 拉取源 {src} 最新 ...")
        _run(['python3', os.path.join(SCRIPT_DIR, 'export.py'), '--env', src, *args.keys], '完成')

    # 2) 覆盖本地 + 收集待推送
    print(f"[sync] {src} → {','.join(targets)}  流程: {' '.join(args.keys)}"
          + (f"  保留字段: {keep}" if keep else ""))
    push_plan = {t: [] for t in targets}
    for k in args.keys:
        for t in sync_key(k, src, targets, keep, args.dry_run):
            push_plan[t].append(k)

    if args.dry_run:
        print("\n[sync] dry-run 结束，未做任何推送")
        return

    # 3) 推送 + 部署
    print("\n[sync] 推送 + 部署：")
    fail = []
    for t in targets:
        for k in push_plan[t]:
            ok1, o1 = _run(['python3', os.path.join(SCRIPT_DIR, 'import.py'), '--env', t, k], '更新成功')
            st = f"import={'✓' if ok1 else '✗'}"
            if not ok1:
                # create 场景 import 输出是「新建成功」
                ok1 = '新建成功' in o1
                st = f"import={'✓' if ok1 else '✗'}"
            st2 = 'deploy=skip'
            if ok1 and not args.no_deploy:
                ok2, o2 = _run(['python3', os.path.join(SCRIPT_DIR, 'bpm_ops.py'), 'deploy', '--env', t, k],
                               '[deploy] 成功')
                st2 = f"deploy={'✓' if ok2 else '✗'}"
                if not ok2:
                    fail.append((t, k, 'deploy', o2[-200:]))
            print(f"  [{t}] {k}: {st} {st2}")
            if not ok1:
                fail.append((t, k, 'import', o1[-200:]))

    if fail:
        print("\n★ 失败项：")
        for t, k, stage, msg in fail:
            print(f"  [{t}] {k} {stage}: {msg}")
    else:
        print("\n✅ 全部成功。建议跑 compare.py 复核四环境一致性。")


if __name__ == '__main__':
    main()
