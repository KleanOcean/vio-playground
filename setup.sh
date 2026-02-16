#!/bin/bash
# Indemind OV580 - Linux 环境配置脚本 (需要 sudo)
# 用法: sudo ./setup.sh

set -e

echo "=== Indemind OV580 Linux 环境配置 ==="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "[错误] 请用 sudo 运行: sudo ./setup.sh"
    exit 1
fi

# 1. 安装依赖
echo ""
echo "[1/3] 安装系统依赖..."
apt update
apt install -y build-essential libopencv-dev libusb-1.0-0-dev python3 python3-pip python3-numpy

# 2. 安装 Python OpenCV
echo ""
echo "[2/3] 安装 Python OpenCV..."
pip3 install opencv-python --break-system-packages 2>/dev/null || pip3 install opencv-python

# 3. USB 权限 (免 sudo 访问相机)
echo ""
echo "[3/3] 配置 USB 权限..."
RULES_FILE="/etc/udev/rules.d/99-indemind.rules"
cat > "$RULES_FILE" << 'EOF'
# Indemind OV580 stereo camera (VID:05a9 PID:f581)
SUBSYSTEM=="usb", ATTR{idVendor}=="05a9", ATTR{idProduct}=="f581", MODE="0666", GROUP="plugdev"
EOF

udevadm control --reload-rules
udevadm trigger

echo ""
echo "=== 配置完成! ==="
echo ""
echo "下一步:"
echo "  1. 拔插相机 (让 udev 规则生效)"
echo "  2. 运行 ./build.sh 编译 wrapper"
echo "  3. 运行 LD_LIBRARY_PATH=./lib python3 camera_viewer.py"
