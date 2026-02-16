"""
获取校正图 — 对应 C++ demo: get_rectified_img.cpp
显示校正后的左右图像，并绘制水平极线。按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk


def main():
    print("=" * 50)
    print("Indemind 校正图查看器")
    print("水平线 = 极线 (校正后应对齐)")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    rect_ret = sdk.enable_rectify()
    print(f"校正处理器: {'OK' if rect_ret == 0 else f'失败({rect_ret})'}")

    win = "Rectified (L | R)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        frame = sdk.get_rectified()
        if frame is None:
            continue

        h, w = frame.shape[:2]
        display = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # 绘制水平极线 (每隔30行)
        for y in range(0, h, 30):
            cv2.line(display, (0, y), (w, y), (0, 255, 0), 1)

        # 标记左右
        half = w // 2
        cv2.putText(display, "L", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display, "R", (half + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        # 分割线
        cv2.line(display, (half, 0), (half, h), (0, 0, 255), 1)

        cv2.imshow(win, display)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
