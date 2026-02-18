#!/bin/bash
# Indemind OV580 Webapp — 一键启动
# 用法: ./run_webapp.sh [--port PORT]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8080}"

# 设置库路径（SDK 依赖）
export LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:$SCRIPT_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export _IMSEE_LIB_OK=1

echo "=================================="
echo "  Indemind OV580 Webapp"
echo "  http://localhost:$PORT"
echo "=================================="
echo ""

cd "$SCRIPT_DIR"
exec python3 -m uvicorn webapp.server:app --host 0.0.0.0 --port "$PORT"
