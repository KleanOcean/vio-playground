"""
带区域深度的深度图 — 对应 C++ demo: get_depth_with_region.cpp
在深度图上划分区域(3x3网格)，显示每个区域的平均距离。
利用标定参数计算真实距离。按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from imsee_sdk import ImseeSdk


def depth_to_color(depth_mm, max_range=4000):
    valid = depth_mm > 0
    clamped = depth_mm.copy()
    clamped[clamped > max_range] = 0
    valid = clamped > 0
    norm = np.zeros_like(clamped, dtype=np.uint8)
    norm[valid] = (255 - (clamped[valid].astype(np.float32) / max_range * 255)).astype(np.uint8)
    colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    colored[~valid] = 0
    return colored


def main():
    print("=" * 50)
    print("Indemind 区域深度查看器")
    print("3x3 网格显示各区域平均距离")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(1, 25)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")

    # 获取标定参数
    calib = sdk.get_calibration()
    if calib:
        print(f"基线: {calib.get('baseline', 'N/A')} m")
        left = calib.get("left", {})
        print(f"左相机 fx={left.get('fx', 'N/A'):.2f}, fy={left.get('fy', 'N/A'):.2f}")
    else:
        print("警告: 无法获取标定参数")

    depth_ret = sdk.enable_depth(0)
    print(f"深度处理器: {'OK' if depth_ret == 0 else f'失败({depth_ret})'}")

    win = "Depth with Region"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    ROWS, COLS = 3, 3

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        depth = sdk.get_depth()
        if depth is None:
            continue

        h, w = depth.shape
        colored = depth_to_color(depth)

        rh = h // ROWS
        rw = w // COLS

        for r in range(ROWS):
            for c in range(COLS):
                y0, y1 = r * rh, (r + 1) * rh
                x0, x1 = c * rw, (c + 1) * rw
                region = depth[y0:y1, x0:x1]
                valid = region[region > 0]

                # 绘制网格线
                cv2.rectangle(colored, (x0, y0), (x1, y1), (200, 200, 200), 1)

                if len(valid) > 0:
                    avg_mm = np.mean(valid)
                    label = f"{avg_mm / 1000:.2f}m"
                else:
                    label = "N/A"

                tx = x0 + 5
                ty = y0 + rh // 2
                cv2.putText(colored, label, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.imshow(win, colored)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
