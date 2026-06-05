#!/usr/bin/env bash
# 从 BPM 拉取流程到本地
# 用法:
#   ./export.sh                        # 全量导出 dev
#   ./export.sh --env uat              # 全量导出 uat
#   ./export.sh --env dev pdp_plan_doc_common pdp-review_udit2   # 只拉取指定流程

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

exec "$PYTHON" "$SCRIPT_DIR/scripts/export.py" "$@"
