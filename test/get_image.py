"""
获取原始图像 — 对应 C++ demo: get_image.cpp
显示左右双目原始画面，按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk


def main():
    print("=" * 50)
    print("Indemind 获取原始图像")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")

    win = "Raw Image (L | R)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    frame_count = 0

    print("等待帧数据...")
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        frame = sdk.get_frame()
        if frame is None:
            continue

        h, w = frame.shape[:2]
        if w > h * 1.5:
            half = w // 2
            left = frame[:, :half]
            right = frame[:, half:]
            cv2.putText(left, "L", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 2)
            cv2.putText(right, "R", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 2)
            gap = np.zeros((h, 4), dtype=np.uint8)
            display = np.hstack([left, gap, right])
        else:
            display = frame

        cv2.imshow(win, display)
        frame_count += 1

    print(f"帧数: {frame_count}, 回调: {sdk.get_callback_count()}")
    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
