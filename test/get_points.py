"""
获取点云 — 对应 C++ demo: get_points.cpp
获取 3D 点云并显示俯视投影图。按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from imsee_sdk import ImseeSdk


def points_to_topview(pts, img_size=400, range_m=5.0):
    """将 (N,3) 点云投影到俯视图 (XZ 平面)"""
    img = np.zeros((img_size, img_size, 3), dtype=np.uint8)

    valid = np.isfinite(pts).all(axis=1) & (np.abs(pts) < 100).all(axis=1)
    pts = pts[valid]
    if len(pts) == 0:
        return img

    x = pts[:, 0]  # 左右
    z = pts[:, 2]  # 前后

    # 过滤范围
    mask = (np.abs(x) < range_m) & (z > 0) & (z < range_m * 2)
    x, z = x[mask], z[mask]
    if len(x) == 0:
        return img

    px = ((x / range_m * 0.5 + 0.5) * img_size).astype(int)
    pz = ((1.0 - z / (range_m * 2)) * img_size).astype(int)
    px = np.clip(px, 0, img_size - 1)
    pz = np.clip(pz, 0, img_size - 1)

    img[pz, px] = (0, 255, 0)
    return img


def main():
    print("=" * 50)
    print("Indemind 点云查看器")
    print("俯视投影 (XZ 平面)")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(1, 25)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    pts_ret = sdk.enable_points()
    print(f"点云处理器: {'OK' if pts_ret == 0 else f'失败({pts_ret})'}")

    win = "Point Cloud (Top View)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    count = 0

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        pts = sdk.get_points()
        if pts is None:
            continue

        topview = points_to_topview(pts)

        info = f"points: {len(pts)}"
        cv2.putText(topview, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        # 画十字(相机位置)
        center = topview.shape[0] // 2
        cv2.drawMarker(topview, (center, topview.shape[0] - 10),
                       (0, 0, 255), cv2.MARKER_DIAMOND, 10, 2)

        cv2.imshow(win, topview)
        count += 1

    print(f"点云帧数: {count}")
    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
