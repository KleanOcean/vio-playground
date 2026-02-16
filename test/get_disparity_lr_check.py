"""
左右一致性检查视差图 — 对应 C++ demo: get_disparity_with_lr_check.cpp
使用 LR consistency check 模式。按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from imsee_sdk import ImseeSdk


def disparity_to_color(disp):
    valid = disp > 0
    if not np.any(valid):
        return np.zeros((*disp.shape, 3), dtype=np.uint8)
    max_val = np.percentile(disp[valid], 95)
    if max_val <= 0:
        max_val = 1.0
    norm = np.zeros_like(disp, dtype=np.uint8)
    norm[valid] = np.clip(disp[valid] / max_val * 255, 0, 255).astype(np.uint8)
    colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    colored[~valid] = 0
    return colored


def main():
    print("=" * 50)
    print("Indemind 左右一致性检查视差图")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(1, 25)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    # mode=2 -> LR_check
    disp_ret = sdk.enable_disparity(2)
    print(f"LR一致性检查视差: {'OK' if disp_ret == 0 else f'失败({disp_ret})'}")

    win = "Disparity (LR Check)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        disp = sdk.get_disparity()
        if disp is None:
            continue

        colored = disparity_to_color(disp)
        cv2.putText(colored, "LR_CHECK", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(win, colored)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
