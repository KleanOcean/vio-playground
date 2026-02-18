"""
综合查看器 — 彩色深度图 + 左右摄像头
第一排: 彩色深度图 (近=红, 远=蓝, 中心十字准星显示距离)
第二排: 左摄像头 (L) | 右摄像头 (R)
按 Q 或 ESC 退出。
"""
import cv2
import numpy as np
import sys

from config import RESOLUTION, FPS
from imsee_sdk import ImseeSdk
from vis_utils import depth_to_color


def main():
    print("=" * 50)
    print("Indemind 综合查看器")
    print("第一排: 彩色深度图  第二排: L | R")
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

    win = "Indemind Depth + Camera"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last_left = None
    last_right = None
    last_depth_color = None
    display_w = 640

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        # --- 摄像头帧 ---
        frame = sdk.get_frame()
        if frame is not None:
            h, w = frame.shape[:2]
            if w > h * 1.5:
                half = w // 2
                left = frame[:, :half]
                right = frame[:, half:]
                display_w = half
            else:
                left = frame
                right = None
                display_w = w
            last_left = cv2.cvtColor(left, cv2.COLOR_GRAY2BGR)
            if right is not None:
                last_right = cv2.cvtColor(right, cv2.COLOR_GRAY2BGR)

        # --- 深度图 ---
        if depth_ret == 0:
            depth = sdk.get_depth()
            if depth is not None:
                colored, clamped, _valid = depth_to_color(depth)
                dh, dw = depth.shape
                cx, cy = dw // 2, dh // 2
                val = clamped[cy, cx]
                label = f"{val / 1000:.2f}m" if val > 0 else "N/A"
                cv2.drawMarker(colored, (cx, cy), (255, 255, 255),
                               cv2.MARKER_CROSS, 20, 1)
                cv2.putText(colored, f"Depth: {label}", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                last_depth_color = colored

        # --- 拼接显示 ---
        rows = []
        sep = np.full((3, display_w, 3), 40, dtype=np.uint8)

        # 第一排: 深度图
        if last_depth_color is not None:
            dh, dw = last_depth_color.shape[:2]
            scale = display_w / dw
            row_h = int(dh * scale)
            rows.append(cv2.resize(last_depth_color, (display_w, row_h)))

        # 第二排: L | R 并排
        if last_left is not None:
            lh, lw = last_left.shape[:2]
            if last_right is not None:
                rh, rw = last_right.shape[:2]
                # 各占一半宽度
                half_w = display_w // 2
                l_h = int(lh * (half_w / lw))
                left_resized = cv2.resize(last_left, (half_w, l_h))
                right_resized = cv2.resize(last_right, (half_w, l_h))
                cv2.putText(left_resized, "L", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(right_resized, "R", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                gap = np.full((l_h, 2, 3), 40, dtype=np.uint8)
                cam_row = np.hstack([left_resized, gap, right_resized])
                # 补齐宽度差异 (2px gap)
                if cam_row.shape[1] < display_w:
                    pad = np.zeros((l_h, display_w - cam_row.shape[1], 3), dtype=np.uint8)
                    cam_row = np.hstack([cam_row, pad])
                elif cam_row.shape[1] > display_w:
                    cam_row = cam_row[:, :display_w]
            else:
                scale = display_w / lw
                l_h = int(lh * scale)
                cam_row = cv2.resize(last_left, (display_w, l_h))
                cv2.putText(cam_row, "L", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            if rows:
                rows.append(sep)
            rows.append(cam_row)

        if rows:
            display = np.vstack(rows)
            cv2.imshow(win, display)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
