"""
获取视差图 — 对应 C++ demo: get_disparity.cpp
默认模式，显示彩色视差图。按 Q/ESC 退出。
"""
import cv2
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk
from vis_utils import disparity_to_color


def main():
    print("=" * 50)
    print("Indemind 视差图查看器 (默认模式)")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    disp_ret = sdk.enable_disparity(0)
    print(f"视差处理器: {'OK' if disp_ret == 0 else f'失败({disp_ret})'}")

    win = "Disparity"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    count = 0

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        disp = sdk.get_disparity()
        if disp is None:
            continue

        colored = disparity_to_color(disp)
        h, w = disp.shape
        cx, cy = w // 2, h // 2
        val = disp[cy, cx]
        label = f"disp: {val:.1f}" if val > 0 else "N/A"
        cv2.putText(colored, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.drawMarker(colored, (cx, cy), (255, 255, 255), cv2.MARKER_CROSS, 20, 1)
        cv2.imshow(win, colored)
        count += 1

    print(f"视差帧数: {count}")
    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
