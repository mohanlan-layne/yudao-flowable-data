#!/usr/bin/env bash
# 将本地 flows/ 目录下的流程导入到 BPM（只创建/更新模型，不部署）
# 用法:
#   ./import.sh              # 导入所有流程
#   ./import.sh <key>        # 只导入指定 key 的流程

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/login.sh"

AUTH_HEADER="Authorization: Bearer ${TOKEN}"
TENANT_HEADER="tenant-id: ${TENANT_ID}"
FILTER_KEY="${1:-}"

imported=0
skipped=0
failed=0

for META_FILE in "${FLOWS_DIR}"/*/*/meta.json; do
  FLOW_DIR="$(dirname "$META_FILE")"
  DIR_NAME="$(basename "$FLOW_DIR")"

  # 目录名格式：{key} - {name}，从 " - " 前取 key
  KEY="${DIR_NAME%% - *}"
  BPMN_FILE="${FLOW_DIR}/${KEY}.bpmn"

  # 按 key 过滤
  if [ -n "$FILTER_KEY" ] && [ "$KEY" != "$FILTER_KEY" ]; then
    continue
  fi

  if [ ! -f "$BPMN_FILE" ]; then
    echo "[import] 跳过 ${KEY}：缺少 bpmn 文件" >&2
    skipped=$((skipped + 1))
    continue
  fi

  echo "[import] 处理流程: ${KEY}"

  # 构造请求 body（meta.json + bpmnXml）
  BODY=$(python3 -c "
import sys,json
with open('${META_FILE}') as f:
    meta = json.load(f)
meta['bpmnXml'] = open('${BPMN_FILE}').read()
meta['key'] = '${KEY}'
# modelType（导出字段）对应导入的 type 字段
if 'modelType' in meta and 'type' not in meta:
    meta['type'] = meta.pop('modelType')
else:
    meta.pop('modelType', None)
meta.pop('id', None)
meta.pop('version', None)
meta.pop('categoryName', None)
print(json.dumps(meta, ensure_ascii=False))
")

  # 检查模型是否已存在（model/list 返回 list，按 key 过滤）
  EXISTING=$(curl -s "${BPM_BASE_URL}/admin-api/bpm/model/list" \
    -H "$AUTH_HEADER" -H "$TENANT_HEADER")

  MODEL_ID=$(echo "$EXISTING" | python3 -c "
import sys,json
items = json.load(sys.stdin).get('data', [])
match = [x for x in items if x.get('key') == '${KEY}']
print(match[0]['id'] if match else '')
" 2>/dev/null || true)

  if [ -n "$MODEL_ID" ]; then
    # 更新已有模型
    UPDATE_BODY=$(echo "$BODY" | python3 -c "
import sys,json
d = json.load(sys.stdin)
d['id'] = '${MODEL_ID}'
print(json.dumps(d, ensure_ascii=False))
")
    RESP=$(curl -s -X PUT "${BPM_BASE_URL}/admin-api/bpm/model/update" \
      -H "$AUTH_HEADER" -H "$TENANT_HEADER" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_BODY")
    ACTION="更新"
  else
    # 创建新模型
    RESP=$(curl -s -X POST "${BPM_BASE_URL}/admin-api/bpm/model/create" \
      -H "$AUTH_HEADER" -H "$TENANT_HEADER" \
      -H "Content-Type: application/json" \
      -d "$BODY")
    ACTION="创建"
  fi

  CODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',0))" 2>/dev/null || echo "-1")
  if [ "$CODE" = "0" ]; then
    echo "[import]   -> ${ACTION}成功: ${KEY}"
    imported=$((imported + 1))
  else
    MSG=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('msg','unknown'))" 2>/dev/null || echo "unknown")
    echo "[import]   -> ${ACTION}失败: ${KEY} ($MSG)" >&2
    failed=$((failed + 1))
  fi
done

echo ""
echo "[import] 完成：成功 ${imported}，失败 ${failed}，跳过 ${skipped}"
