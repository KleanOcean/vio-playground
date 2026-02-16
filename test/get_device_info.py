"""
获取设备信息 — 对应 C++ demo: get_device_info.cpp
打印设备详细信息和标定参数后退出。
"""
import sys
import time

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk


def main():
    print("=" * 50)
    print("Indemind 设备信息查看器")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    # 等待 SDK 初始化
    time.sleep(1)

    print("\n--- 基本信息 ---")
    print(f"  {sdk.get_module_info()}")

    print("\n--- 详细设备信息 ---")
    info = sdk.get_device_info_detailed()
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n--- 标定参数 ---")
    calib = sdk.get_calibration()
    if calib:
        print(f"  基线 (baseline): {calib.get('baseline', 'N/A')} m")
        for side in ("left", "right"):
            cam = calib.get(side, {})
            if cam:
                print(f"\n  [{side.upper()} 相机]")
                print(f"    分辨率: {cam.get('w', '?')}x{cam.get('h', '?')}")
                print(f"    焦距: fx={cam.get('fx', '?'):.4f}, fy={cam.get('fy', '?'):.4f}")
                print(f"    主点: cx={cam.get('cx', '?'):.4f}, cy={cam.get('cy', '?'):.4f}")
                print(f"    畸变: k1={cam.get('k1', '?'):.6f}, k2={cam.get('k2', '?'):.6f}, "
                      f"t1={cam.get('t1', '?'):.6f}, t2={cam.get('t2', '?'):.6f}")
                P = cam.get("P", [])
                if P:
                    print(f"    投影矩阵 P:")
                    for row in range(3):
                        vals = P[row * 4:(row + 1) * 4]
                        print(f"      [{', '.join(f'{v:10.4f}' for v in vals)}]")
    else:
        print("  无法获取标定参数")

    sdk.release()
    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
