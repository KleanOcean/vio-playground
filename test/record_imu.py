"""
记录 IMU 数据到 CSV — 对应 C++ demo: record_imu.cpp
录制指定时长的 IMU 数据并保存为 CSV 文件。
用法: python record_imu.py [秒数] [输出文件]
默认: 10 秒, imu_record.csv
"""
import csv
import os
import sys
import time

from imsee_sdk import ImseeSdk

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    output = sys.argv[2] if len(sys.argv) > 2 else os.path.join(_SCRIPT_DIR, "imu_record.csv")

    print("=" * 50)
    print(f"Indemind IMU 录制器 ({duration}s)")
    print(f"输出: {output}")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(1, 25)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    imu_ret = sdk.enable_imu()
    print(f"IMU: {'OK' if imu_ret == 0 else f'失败({imu_ret})'}")

    print(f"\n开始录制 {duration} 秒...")
    all_samples = []
    start = time.time()

    while (time.time() - start) < duration:
        time.sleep(0.05)
        imu = sdk.get_imu(max_samples=2000)
        if imu is not None:
            all_samples.extend(imu.tolist())
            elapsed = time.time() - start
            sys.stdout.write(f"\r  已录制 {elapsed:.1f}s / {duration:.1f}s, "
                             f"采样数: {len(all_samples)}")
            sys.stdout.flush()

    print(f"\n\n录制完成, 共 {len(all_samples)} 个采样")

    # 写入 CSV
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "accel_x", "accel_y", "accel_z",
                         "gyro_x", "gyro_y", "gyro_z"])
        for row in all_samples:
            writer.writerow([f"{row[0]:.6f}",
                             f"{row[1]:.6f}", f"{row[2]:.6f}", f"{row[3]:.6f}",
                             f"{row[4]:.6f}", f"{row[5]:.6f}", f"{row[6]:.6f}"])

    print(f"已保存: {output}")

    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
