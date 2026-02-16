"""
获取 IMU 数据 — 对应 C++ demo: get_imu.cpp
实时打印加速度和陀螺仪数据。按 Ctrl+C 退出。
"""
import sys
import time

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk


def main():
    print("=" * 50)
    print("Indemind IMU 数据查看器")
    print("按 Ctrl+C 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    imu_ret = sdk.enable_imu()
    print(f"IMU: {'OK' if imu_ret == 0 else f'失败({imu_ret})'}")

    print("\n等待 IMU 数据...\n")
    print(f"{'时间戳':>14s}  {'加速度 (m/s²)':^30s}  {'陀螺仪 (rad/s)':^30s}")
    print(f"{'':>14s}  {'X':>8s}  {'Y':>8s}  {'Z':>8s}  {'X':>8s}  {'Y':>8s}  {'Z':>8s}")
    print("-" * 90)

    total_samples = 0

    try:
        while True:
            time.sleep(0.1)  # 100ms 间隔读取

            imu = sdk.get_imu(max_samples=100)
            if imu is None:
                continue

            # 只打印最后几条 (避免刷屏)
            show = imu[-5:] if len(imu) > 5 else imu
            for sample in show:
                ts = sample[0]
                ax, ay, az = sample[1], sample[2], sample[3]
                gx, gy, gz = sample[4], sample[5], sample[6]
                print(f"{ts:14.4f}  {ax:8.3f}  {ay:8.3f}  {az:8.3f}  "
                      f"{gx:8.4f}  {gy:8.4f}  {gz:8.4f}")

            total_samples += len(imu)

    except KeyboardInterrupt:
        print(f"\n\n总采样数: {total_samples}")

    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
