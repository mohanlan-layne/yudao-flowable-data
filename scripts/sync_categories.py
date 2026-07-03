#!/usr/bin/env python3
"""
sync_categories.py — 把 UAT 的 id125-132 共 8 个分类幂等 INSERT 到 PROD，保留原 id。

铁律：
- 只 INSERT 这 8 个 id；绝不 UPDATE/DELETE PROD 任何行；绝不动 bpm_category 以外任何表。
- 先自动 dry-run 预览，再真执行。
"""

import argparse
import sys

import pymysql

DB_CONFIG = {
    "host": "192.168.1.190",
    "port": 3306,
    "user": "yudao",
    "password": "Yudao@2025",
    "charset": "utf8mb4",
}

SOURCE_DB = "yudao_uat"
TARGET_DB = "yudao_prod"
TABLE = "bpm_category"
IDS = (125, 126, 127, 128, 129, 130, 131, 132)


def fetch_source_rows(conn):
    sql = f"""
        SELECT * FROM {SOURCE_DB}.{TABLE}
        WHERE id IN %s AND deleted = 0
    """
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, (IDS,))
        return cur.fetchall()


def fetch_existing_ids(conn):
    sql = f"""
        SELECT id FROM {TARGET_DB}.{TABLE}
        WHERE id IN %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (IDS,))
        return {row[0] for row in cur.fetchall()}


def build_insert_sql(row: dict):
    # 过滤掉 pymysql 可能带来的额外键
    cols = [k for k in row.keys() if not k.startswith("_")]
    col_str = ", ".join(f"`{c}`" for c in cols)
    val_str = ", ".join(f"%({c})s" for c in cols)
    return f"INSERT INTO {TARGET_DB}.{TABLE} ({col_str}) VALUES ({val_str})"


def run(dry_run: bool):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        rows = fetch_source_rows(conn)
        if len(rows) != 8:
            print(f"[WARN] UAT 中符合 deleted=0 且 id IN {IDS} 的行数为 {len(rows)}，预期 8 行。", file=sys.stderr)

        existing = fetch_existing_ids(conn)

        to_insert = [r for r in rows if r["id"] not in existing]
        skipped = [r for r in rows if r["id"] in existing]

        print(f"UAT 源数据共 {len(rows)} 行，PROD 已存在 {len(skipped)} 行，待插入 {len(to_insert)} 行。\n")

        for r in rows:
            status = "SKIP (已存在)" if r["id"] in existing else "INSERT"
            print(f"  id={r['id']:>3}  code={r.get('code','?')!r:<20}  name={r.get('name','?')!r:<20}  [{status}]")

        if dry_run:
            print("\n[Dry-run] 以上仅为预览，未写入数据库。")
            return

        if not to_insert:
            print("\n无需插入，PROD 已包含全部目标行。")
            return

        print(f"\n开始写入 {len(to_insert)} 行到 {TARGET_DB}.{TABLE} ...")
        with conn.cursor() as cur:
            for r in to_insert:
                sql = build_insert_sql(r)
                cur.execute(sql, r)
        conn.commit()
        print("提交成功。")

        # 校验
        print("\n校验 PROD 数据 ...")
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, code, name, deleted
                FROM {TARGET_DB}.{TABLE}
                WHERE id IN %s
                """,
                (IDS,),
            )
            prod_rows = {r["id"]: r for r in cur.fetchall()}

        missing = [i for i in IDS if i not in prod_rows]
        if missing:
            print(f"[FAIL] PROD 缺失 id: {missing}", file=sys.stderr)
            sys.exit(1)

        bad_deleted = [i for i in IDS if prod_rows[i]["deleted"] not in (0, b'\x00')]
        if bad_deleted:
            print(f"[FAIL] PROD 中 deleted != 0 的 id: {bad_deleted}", file=sys.stderr)
            sys.exit(1)

        print(f"校验通过：PROD 中 id {IDS} 共 8 行全部存在且 deleted=0。")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Sync UAT categories 125-132 into PROD")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    parser.add_argument("--yes", action="store_true", help="跳过自动 dry-run，直接执行")
    args = parser.parse_args()

    if args.dry_run:
        run(dry_run=True)
        return

    if not args.yes:
        print("=== 自动 Dry-run 预览 ===\n")
        run(dry_run=True)
        print("\n" + "=" * 40)
        ans = input("确认执行真实写入? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("已取消。")
            sys.exit(0)

    run(dry_run=False)


if __name__ == "__main__":
    main()
