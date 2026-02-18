#!/bin/bash
# Indemind OV580 - Linux wrapper 编译脚本
# 用法: ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Indemind Linux Wrapper 编译 ==="

# 检查 g++
if ! command -v g++ &> /dev/null; then
    echo "[错误] 找不到 g++，请先运行: sudo apt install build-essential"
    exit 1
fi

# 检查 OpenCV
if ! pkg-config --exists opencv4 2>/dev/null && ! pkg-config --exists opencv 2>/dev/null; then
    echo "[错误] 找不到 OpenCV，请先运行: sudo apt install libopencv-dev"
    exit 1
fi

# 检测 OpenCV 版本
if pkg-config --exists opencv4 2>/dev/null; then
    OPENCV_PKG="opencv4"
else
    OPENCV_PKG="opencv"
fi
echo "OpenCV: $(pkg-config --modversion $OPENCV_PKG)"

echo "编译 libimsee_wrapper.so ..."
# 关键: 显式指定系统 OpenCV 路径在前, 避免 -L lib 让链接器找到 3.4
# 运行时: wrapper 用 OpenCV 4.x (.so.406), libindemind 用 3.4 (.so.3.4), soname 不同可共存
SYSLIB="/lib/x86_64-linux-gnu"
g++ -shared -fPIC -O2 \
    -o "$SCRIPT_DIR/lib/libimsee_wrapper.so" \
    "$SCRIPT_DIR/src/imsee_wrapper.cpp" \
    -I"$SCRIPT_DIR/include" \
    $(pkg-config --cflags $OPENCV_PKG) \
    -L"$SYSLIB" -lopencv_imgproc -lopencv_core \
    -L"$SCRIPT_DIR/lib" -lindemind \
    -Wl,-rpath,'$ORIGIN' \
    -lpthread

echo "=== 编译完成: lib/libimsee_wrapper.so ==="
echo ""
echo "运行相机查看器:"
echo "  LD_LIBRARY_PATH=$SCRIPT_DIR/lib python3 camera_viewer.py"
