#!/usr/bin/env bash
# 流程端到端测试脚本
# 用法: ./test-flow.sh <processDefinitionKey> <executorUserId> <chargeUserId>
#
# 示例（DFM审核）:
#   ./test-flow.sh pdp_doc_dfm 2637 1
#
# 说明:
#   - executorUserId: 必须在系统中设置了 leaderUserId（上级审核节点自动取直属领导）
#   - chargeUserId:   计划负责人，任意有效用户ID
#   - 脚本用 admin 账号发起流程，逐步打印每个节点的待办任务信息
#   - 每个节点需要你用对应角色的账号去审批（脚本会打印 taskId 供调用）

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

FLOW_KEY="${1:-}"
EXECUTOR_USER_ID="${2:-}"
CHARGE_USER_ID="${3:-}"

if [ -z "$FLOW_KEY" ] || [ -z "$EXECUTOR_USER_ID" ] || [ -z "$CHARGE_USER_ID" ]; then
  echo "用法: $0 <processDefinitionKey> <executorUserId> <chargeUserId>"
  echo "示例: $0 pdp_doc_dfm 2637 1"
  exit 1
fi

# 登录拿 admin token
TOKEN=$(curl -s -X POST "${BPM_BASE_URL}/admin-api/system/auth/login" \
  -H "Content-Type: application/json" -H "tenant-id: ${TENANT_ID}" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\",\"tenantId\":\"${TENANT_ID}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")
AUTH="Authorization: Bearer ${TOKEN}"
TENANT="tenant-id: ${TENANT_ID}"

echo "========================================"
echo "  流程测试: ${FLOW_KEY}"
echo "  执行人ID: ${EXECUTOR_USER_ID}"
echo "  负责人ID: ${CHARGE_USER_ID}"
echo "========================================"

# Step 1: 获取流程定义ID
echo ""
echo "[1] 获取流程定义..."
PROC_DEF=$(curl -s "${BPM_BASE_URL}/admin-api/bpm/process-definition/get?key=${FLOW_KEY}" \
  -H "$AUTH" -H "$TENANT")
PROC_DEF_ID=$(echo "$PROC_DEF" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
PROC_DEF_NAME=$(echo "$PROC_DEF" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['name'])")
echo "    流程定义: ${PROC_DEF_NAME} (${PROC_DEF_ID})"

# Step 2: 发起流程实例
echo ""
echo "[2] 发起流程实例..."
CREATE_BODY=$(python3 -c "
import json
print(json.dumps({
    'processDefinitionId': '${PROC_DEF_ID}',
    'variables': {
        'executorUserId': ${EXECUTOR_USER_ID},
        'PdpPlanChargeUser': ${CHARGE_USER_ID}
    }
}, ensure_ascii=False))
")
CREATE_RESP=$(curl -s -X POST "${BPM_BASE_URL}/admin-api/bpm/process-instance/create" \
  -H "$AUTH" -H "$TENANT" -H "Content-Type: application/json" \
  -d "$CREATE_BODY")
PROCESS_INSTANCE_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'])")
echo "    流程实例ID: ${PROCESS_INSTANCE_ID}"

# Step 3: 轮询各节点任务
echo ""
echo "[3] 流程节点信息（请依次用对应账号审批）"
echo ""

check_tasks() {
  curl -s "${BPM_BASE_URL}/admin-api/bpm/task/list-by-process-instance-id?processInstanceId=${PROCESS_INSTANCE_ID}" \
    -H "$AUTH" -H "$TENANT" | python3 -c "
import sys,json
tasks = json.load(sys.stdin).get('data', [])
for t in tasks:
    status_map = {1:'进行中', 2:'已完成', 3:'未通过', 4:'已取消'}
    status = status_map.get(t.get('status'), str(t.get('status')))
    assignee = t.get('assigneeUser', {}) or {}
    print(f'  节点: {t[\"name\"]:10s}  taskId={t[\"id\"]:30s}  状态={status}  审批人={assignee.get(\"nickname\",\"待分配\")}')
"
}

echo "--- 当前任务状态 ---"
check_tasks

echo ""
echo "========================================"
echo "  审批接口参考（用对应用户的token调用）"
echo "========================================"
echo ""
echo "  通过任务:"
echo '  curl -X PUT "'${BPM_BASE_URL}'/admin-api/bpm/task/approve" \'
echo '    -H "Authorization: Bearer <用户token>" \'
echo '    -H "tenant-id: '${TENANT_ID}'" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"id":"<taskId>","variables":{},"reason":"测试通过"}'"'"
echo ""
echo "  拒绝任务:"
echo '  curl -X PUT "'${BPM_BASE_URL}'/admin-api/bpm/task/reject" \'
echo '    -H "Authorization: Bearer <用户token>" \'
echo '    -H "tenant-id: '${TENANT_ID}'" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"id":"<taskId>","reason":"测试拒绝"}'"'"
echo ""
echo "  查看流程实例状态:"
echo "  curl \"${BPM_BASE_URL}/admin-api/bpm/process-instance/get?id=${PROCESS_INSTANCE_ID}\" \\"
echo "    -H \"Authorization: Bearer <token>\" -H \"tenant-id: ${TENANT_ID}\""
echo ""
echo "========================================"
echo "  流程实例ID: ${PROCESS_INSTANCE_ID}"
echo "  管理后台查看: ${BPM_BASE_URL}/doc.html#/"
echo "========================================"
