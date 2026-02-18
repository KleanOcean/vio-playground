"""
高精度视差图 — 对应 C++ demo: get_disparity_with_high_accuracy.cpp
使用 HIGH_ACCURACY 模式。按 Q/ESC 退出。
"""
import cv2
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk
from vis_utils import disparity_to_color


def main():
    print("=" * 50)
    print("Indemind 高精度视差图")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    # mode=1 -> HIGH_ACCURACY
    disp_ret = sdk.enable_disparity(1)
    print(f"高精度视差: {'OK' if disp_ret == 0 else f'失败({disp_ret})'}")

    win = "Disparity (High Accuracy)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        disp = sdk.get_disparity()
        if disp is None:
            continue

        colored = disparity_to_color(disp)
        cv2.putText(colored, "HIGH_ACCURACY", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(win, colored)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
