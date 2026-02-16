"""
深度叠加查看器 — 彩色深度图半透明叠加在摄像头画面上
按 A/D 调整透明度, 按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk
from vis_utils import depth_to_color


def main():
    print("=" * 50)
    print("Indemind 深度叠加查看器")
    print("A/D: 调整深度透明度  Q/ESC: 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(RESOLUTION, FPS)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    depth_ret = sdk.enable_depth(0)
    print(f"深度处理器: {'OK' if depth_ret == 0 else f'失败({depth_ret})'}")

    win = "Depth Overlay"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 1280, 800)

    alpha = 0.5  # 深度图透明度
    last_cam = None
    last_depth_color = None
    last_depth_raw = None
    last_valid = None

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("a"):
            alpha = max(0.0, alpha - 0.1)
            print(f"深度透明度: {alpha:.1f}")
        elif key == ord("d"):
            alpha = min(1.0, alpha + 0.1)
            print(f"深度透明度: {alpha:.1f}")

        # --- 左摄像头 ---
        frame = sdk.get_frame()
        if frame is not None:
            h, w = frame.shape[:2]
            if w > h * 1.5:
                left = frame[:, :w // 2]
            else:
                left = frame
            last_cam = cv2.cvtColor(left, cv2.COLOR_GRAY2BGR)

        # --- 深度图 ---
        if depth_ret == 0:
            depth = sdk.get_depth()
            if depth is not None:
                last_depth_color, last_depth_raw, last_valid = depth_to_color(depth)

        # --- 叠加显示 ---
        if last_cam is None:
            continue

        cam = last_cam.copy()
        ch, cw = cam.shape[:2]

        if last_depth_color is not None:
            # 深度图 resize 到与摄像头同尺寸
            depth_resized = cv2.resize(last_depth_color, (cw, ch))
            valid_resized = cv2.resize(
                last_valid.astype(np.uint8), (cw, ch),
                interpolation=cv2.INTER_NEAREST
            ).astype(bool)

            # 只在有效深度区域叠加
            mask = valid_resized
            cam[mask] = cv2.addWeighted(
                cam[mask], 1.0 - alpha,
                depth_resized[mask], alpha, 0
            )

            # 中心距离
            raw_resized = cv2.resize(last_depth_raw, (cw, ch),
                                     interpolation=cv2.INTER_NEAREST)
            cx, cy = cw // 2, ch // 2
            val = raw_resized[cy, cx]
            label = f"{val / 1000:.2f}m" if val > 0 else "N/A"
            cv2.drawMarker(cam, (cx, cy), (255, 255, 255),
                           cv2.MARKER_CROSS, 20, 2)
            cv2.putText(cam, label, (cx + 15, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # HUD
        cv2.putText(cam, f"Depth: {alpha:.0%}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(cam, "A/D: opacity  Q: quit", (10, ch - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # 放大 2 倍显示
        cam = cv2.resize(cam, (cw * 2, ch * 2), interpolation=cv2.INTER_LINEAR)
        cv2.imshow(win, cam)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
