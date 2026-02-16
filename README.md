# Indemind OV580 双目立体相机 - Linux 查看器

## 文件结构

```
indemind_linux/
├── README.md           # 本文档
├── setup.sh            # 系统配置脚本 (安装依赖 + USB权限)
├── build.sh            # 编译 wrapper 动态库
├── camera_viewer.py    # 相机查看器 (左右双目实时显示)
├── lib/
│   ├── libindemind.so      # Indemind SDK 核心库
│   └── libusbdriver.so     # USB 驱动库
├── include/
│   ├── imrsdk.h            # SDK 头文件
│   ├── types.h             # 数据类型定义
│   ├── imrdata.h           # 数据结构定义
│   ├── logging.h
│   ├── svc_config.h
│   └── times.h
└── src/
    └── imsee_wrapper.cpp   # Python ctypes wrapper 源码
```

## 系统要求

- Ubuntu 22.04 / 20.04 (x86_64)
- Indemind OV580 双目相机 (USB)
- Python 3.8+

## 快速开始

### 第一步: 系统配置 (只需运行一次)

```bash
# 安装依赖 + 配置 USB 权限
sudo ./setup.sh
```

这个脚本会:
- 安装 `build-essential`, `libopencv-dev`, `libusb-1.0-0-dev`, `python3-numpy`
- 安装 Python OpenCV (`opencv-python`)
- 创建 udev 规则，让普通用户可以访问相机 (免 sudo)

配置完成后 **拔插一次相机** 让规则生效。

### 第二步: 编译 wrapper

```bash
chmod +x build.sh
./build.sh
```

编译成功后会生成 `lib/libimsee_wrapper.so`。

### 第三步: 运行相机查看器

```bash
LD_LIBRARY_PATH=./lib python3 camera_viewer.py
```

- 窗口会显示左右两个摄像头画面 (标注 L 和 R)
- 5秒后自动保存截图到 `screenshot.png`
- 按 **Q** 或 **ESC** 退出

## 常见问题

### Q: 报错 "找不到相机"
```
检查步骤:
1. lsusb | grep 05a9          # 确认相机已连接 (应该看到 05a9:f581)
2. ls -la /dev/bus/usb/*/*     # 确认 USB 设备权限
3. sudo ./setup.sh             # 重新配置 USB 权限
4. 拔插相机后再试
```

### Q: 报错 "GLIBC_xxx not found"
预编译库是给较旧系统编译的。如果遇到 glibc 兼容问题:
```bash
# 检查库依赖
ldd lib/libindemind.so
# 如果有 "not found"，可能需要安装旧版兼容库或联系 Indemind 获取新版 SDK
```

### Q: 编译报错 "找不到 opencv"
```bash
# 确认 OpenCV 已安装
pkg-config --modversion opencv4
# 如果没有，安装:
sudo apt install libopencv-dev
```

### Q: 画面卡顿或掉帧
```bash
# 确认 USB 3.0 连接 (不要用 USB 2.0 口)
lsusb -t | grep 05a9
# 应该显示 5000M (USB 3.0)
```

## 技术说明

- SDK 通过 USB 直接访问相机 (libusb)，不走 V4L2/UVC
- 回调函数在 SDK 内部线程触发，wrapper 用互斥锁保护共享缓冲区
- 左右相机图像拼接为一张灰度图 (宽度x2)，Python 端再分割显示
- 相机分辨率: 640x400 (每只眼) 或 1280x800 (每只眼)
