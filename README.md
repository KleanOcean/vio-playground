# VIO Playground

Indemind OV580 双目立体相机 Python 工具集 — 通过 ctypes 封装 IMSEE-SDK，提供图像、深度、视差、点云、IMU、目标检测等功能。

## 文件结构

```
vio-playground/
├── README.md
├── build.sh                  # 编译 C wrapper
├── run_test.sh               # 交互式脚本启动器
├── setup.sh                  # 系统配置 (依赖 + USB 权限)
├── src/
│   └── imsee_wrapper.cpp     # C wrapper 源码 (~780 行)
├── include/                  # SDK 头文件
├── lib/                      # SDK 预编译库 (Git LFS)
├── test/
│   ├── imsee_sdk.py          # 共用 Python wrapper 类
│   ├── get_image.py          # 原始双目图像
│   ├── get_depth.py          # 深度图 (彩色)
│   ├── get_depth_overlay.py  # 深度叠加查看器 (推荐)
│   ├── get_depth_viewer.py   # 深度 + L/R 三排布局
│   ├── get_depth_with_region.py
│   ├── get_disparity.py      # 视差图
│   ├── get_disparity_high_accuracy.py
│   ├── get_disparity_lr_check.py
│   ├── get_rectified_img.py  # 校正图
│   ├── get_points.py         # 3D 点云
│   ├── get_imu.py            # IMU 实时数据
│   ├── record_imu.py         # IMU 录制到 CSV
│   ├── get_detector.py       # 目标检测
│   └── get_device_info.py    # 设备信息 + 标定参数
└── docs/
    └── debug_report_opencv_abi.md  # OpenCV ABI 调试报告
```

## 系统要求

- Ubuntu 22.04+ (x86_64)
- Indemind OV580 双目相机 (USB 3.0)
- Python 3.8+, NumPy, OpenCV

## 快速开始

### 1. 系统配置 (首次)

```bash
sudo ./setup.sh
# 安装完后拔插一次相机
```

### 2. 编译

```bash
./build.sh
```

### 3. 运行

```bash
./run_test.sh
```

显示交互菜单，输入编号即可运行：

```
==================================
  Indemind SDK 测试脚本
==================================

  [ 1] get_depth.py
  [ 2] get_depth_overlay.py
  [ 3] get_depth_viewer.py
  ...
  [15] record_imu.py

请输入编号 (1-15):
```

也可以直接指定：

```bash
./run_test.sh get_depth_overlay.py
```

## 功能一览

| 脚本 | 功能 | 按键 |
|------|------|------|
| `get_image.py` | 左右双目原始画面 | Q 退出 |
| `get_depth_overlay.py` | **深度叠加在摄像头上** | A/D 调透明度, Q 退出 |
| `get_depth_viewer.py` | 深度 + L + R 三排布局 | Q 退出 |
| `get_disparity.py` | 视差图 | Q 退出 |
| `get_rectified_img.py` | 校正后图像 | Q 退出 |
| `get_points.py` | 3D 点云统计 | 自动退出 |
| `get_imu.py` | IMU 实时加速度/陀螺仪 | Ctrl+C 退出 |
| `record_imu.py` | IMU 录制到 CSV | `record_imu.py 10 out.csv` |
| `get_detector.py` | 目标检测 (人/宠物/家具) | Q 退出 |
| `get_device_info.py` | 设备信息 + 标定参数 | 自动退出 |

## 架构

```
Python 脚本 (test/*.py)
    ↓ ctypes
libimsee_wrapper.so (我们的 C wrapper)
    ↓ C++ API
libindemind.so (SDK, OpenCV 3.4)
    ↓ libusb
OV580 相机 (USB 3.0)
```

> **注意**: wrapper 链接系统 OpenCV 4.x，SDK 内部用 OpenCV 3.4，两者通过不同 soname 共存。
> 详见 [docs/debug_report_opencv_abi.md](docs/debug_report_opencv_abi.md)

## 常见问题

### 找不到相机

```bash
lsusb | grep 05a9              # 确认相机连接 (应看到 05a9:f581)
sudo ./setup.sh                # 重新配置 USB 权限
# 拔插相机后再试
```

### 编译报错找不到 OpenCV

```bash
sudo apt install libopencv-dev
pkg-config --modversion opencv4  # 应显示 4.x
```

### 画面卡顿

```bash
lsusb -t | grep 05a9           # 确认 USB 3.0 连接 (5000M)
```

### Segfault

```bash
# 如果之前崩溃过，相机可能卡住，物理拔插一次
# 确认用 run_test.sh 运行（自动设置 LD_LIBRARY_PATH）
```
