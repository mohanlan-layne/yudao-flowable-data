#!/usr/bin/env bash
# 导出 BPM 中所有已部署的最新流程到本地 flows/ 目录
# 用法: ./export.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/login.sh"

AUTH_HEADER="Authorization: Bearer ${TOKEN}"
TENANT_HEADER="tenant-id: ${TENANT_ID}"

# 获取分类列表，建立 code->name 映射
echo "[export] 获取流程分类..."
CATEGORIES_JSON=$(curl -s "${BPM_BASE_URL}/admin-api/bpm/category/simple-list" \
  -H "$AUTH_HEADER" -H "$TENANT_HEADER")

CATEGORY_TMP=$(mktemp)
trap "rm -f $CATEGORY_TMP" EXIT
echo "$CATEGORIES_JSON" | python3 -c "
import sys,json
data = json.load(sys.stdin).get('data', [])
# code -> name 映射
mapping = {item['code']: item['name'] for item in data if item.get('code')}
print(json.dumps(mapping, ensure_ascii=False))
" > "$CATEGORY_TMP"

get_category_name() {
  local code="$1"
  python3 -c "
import json
m = json.load(open('${CATEGORY_TMP}'))
print(m.get('${code}', '${code}') or '未分类')
"
}

# 获取所有模型列表（返回 list，非分页）
echo "[export] 获取模型列表..."
MODELS_JSON=$(curl -s "${BPM_BASE_URL}/admin-api/bpm/model/list" \
  -H "$AUTH_HEADER" -H "$TENANT_HEADER")

KEYS=$(echo "$MODELS_JSON" | python3 -c "
import sys,json
items = json.load(sys.stdin).get('data', [])
for item in items:
    print(item['key'])
" | tr -d '\r')

total=0
for KEY in $KEYS; do
  echo "[export] 处理流程: $KEY"

  # 获取最新已部署流程定义（含 bpmnXml）
  DEF=$(curl -s "${BPM_BASE_URL}/admin-api/bpm/process-definition/get?key=${KEY}" \
    -H "$AUTH_HEADER" -H "$TENANT_HEADER")

  DATA=$(echo "$DEF" | python3 -c "
import sys,json
d = json.load(sys.stdin).get('data')
if d:
    print(json.dumps(d))
else:
    print('')
")

  if [ -z "$DATA" ]; then
    echo "[export]   跳过 ${KEY}：无已部署版本"
    continue
  fi

  CATEGORY_CODE=$(echo "$DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('category','') or '')")
  CATEGORY_NAME=$(get_category_name "$CATEGORY_CODE")
  SAFE_CATEGORY=$(echo "$CATEGORY_NAME" | tr '/' '-' | tr ' ' '_')

  FLOW_NAME=$(echo "$DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name','') or '')")
  SAFE_NAME=$(echo "${KEY} - ${FLOW_NAME}" | tr '/' '-')
  TARGET_DIR="${FLOWS_DIR}/${SAFE_CATEGORY}/${SAFE_NAME}"
  mkdir -p "$TARGET_DIR"

  # 写 BPMN XML
  echo "$DATA" | python3 -c "
import sys,json
print(json.load(sys.stdin).get('bpmnXml',''))
" > "${TARGET_DIR}/${KEY}.bpmn"

  # 写 meta.json（保留导入时需要的字段）
  echo "$DATA" | python3 -c "
import sys,json
d = json.load(sys.stdin)
exclude = {'bpmnXml','simpleModel','id','suspensionState','deploymentTime',
           'formConf','formFields','formName','modelId','version','categoryName'}
meta = {k:v for k,v in d.items() if k not in exclude and v is not None}
print(json.dumps(meta, ensure_ascii=False, indent=2))
" > "${TARGET_DIR}/meta.json"

  echo "[export]   -> ${SAFE_CATEGORY}/${SAFE_NAME}"
  total=$((total + 1))
done

echo ""
echo "[export] 完成，共导出 ${total} 个流程到 ${FLOWS_DIR}"
