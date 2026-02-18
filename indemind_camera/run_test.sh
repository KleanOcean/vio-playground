#!/bin/bash
# 运行 test/ 下的脚本，自动设置库路径
# 用法: ./run_test.sh get_image.py
#       ./run_test.sh get_depth.py
#       ./run_test.sh record_imu.py 10 output.csv

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:$SCRIPT_DIR/lib:${LD_LIBRARY_PATH:-}"
export _IMSEE_LIB_OK=1

# 如果有参数，直接运行指定脚本
if [ -n "$1" ]; then
    SCRIPT="$SCRIPT_DIR/test/$1"
    shift
    if [ ! -f "$SCRIPT" ]; then
        echo "[错误] 找不到: $SCRIPT"
        exit 1
    fi
    exec python3 "$SCRIPT" "$@"
fi

# 无参数: 显示交互式菜单
SCRIPTS=()
for f in "$SCRIPT_DIR"/test/get_*.py "$SCRIPT_DIR"/test/record_*.py; do
    [ -f "$f" ] && SCRIPTS+=("$f")
done

echo "=================================="
echo "  Indemind SDK 测试脚本"
echo "=================================="
echo ""
for i in "${!SCRIPTS[@]}"; do
    printf "  [%2d] %s\n" $((i+1)) "$(basename "${SCRIPTS[$i]}")"
done
echo ""
read -rp "请输入编号 (1-${#SCRIPTS[@]}): " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#SCRIPTS[@]}" ]; then
    echo "[错误] 无效选择: $choice"
    exit 1
fi

SCRIPT="${SCRIPTS[$((choice-1))]}"
echo ""
echo ">>> 运行: $(basename "$SCRIPT")"
echo ""
exec python3 "$SCRIPT"
