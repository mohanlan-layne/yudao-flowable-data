#!/usr/bin/env bash
# 端到端流程测试
# 用法:
#   ./test_flow.sh <flow_key> <executor_user_id> <charge_user_id>
#   ./test_flow.sh --env uat pdp_plan_doc_common 2637 1

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null && "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,6) else 1)" 2>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "[错误] 未检测到 Python 3.6+，正在尝试安装..."
  if command -v brew &>/dev/null; then
    brew install python3
    PYTHON="python3"
  elif command -v apt-get &>/dev/null; then
    sudo apt-get install -y python3
    PYTHON="python3"
  else
    echo "[错误] 无法自动安装，请手动安装 Python 3："
    echo "  https://www.python.org/downloads/"
    exit 1
  fi
fi

exec "$PYTHON" "$SCRIPT_DIR/scripts/test_flow.py" "$@"
