"""
获取深度图 — 对应 C++ demo: get_depth.cpp
显示彩色深度图 + 中心点距离。按 Q/ESC 退出。
"""
import cv2
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk
from vis_utils import depth_to_color


def main():
    print("=" * 50)
    print("Indemind 深度图查看器")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    depth_ret = sdk.enable_depth(0)
    print(f"深度处理器: {'OK' if depth_ret == 0 else f'失败({depth_ret})'}")

    win = "Depth"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        depth = sdk.get_depth()
        if depth is None:
            continue

        colored, clamped, valid = depth_to_color(depth, denoise=False)
        h, w = depth.shape
        cx, cy = w // 2, h // 2
        val = depth[cy, cx]
        label = f"{val / 1000:.2f}m" if val > 0 else "N/A"
        cv2.drawMarker(colored, (cx, cy), (255, 255, 255), cv2.MARKER_CROSS, 20, 1)
        cv2.putText(colored, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(win, colored)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
