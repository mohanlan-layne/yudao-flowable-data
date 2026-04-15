#!/usr/bin/env bash
# 登录并返回 token，供其他脚本 source 使用
# 用法: source login.sh 后使用 $TOKEN

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "[login] 正在登录 $BPM_BASE_URL ..." >&2

RESPONSE=$(curl -s -X POST "${BPM_BASE_URL}/admin-api/system/auth/login" \
  -H "Content-Type: application/json" \
  -H "tenant-id: ${TENANT_ID}" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\",\"tenantId\":\"${TENANT_ID}\"}")

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['accessToken'])" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
  echo "[login] 登录失败: $RESPONSE" >&2
  exit 1
fi

echo "[login] 登录成功" >&2
export TOKEN
