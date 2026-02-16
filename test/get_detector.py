"""
目标检测 — 对应 C++ demo: get_detector.cpp
显示检测框和类别信息。按 Q/ESC 退出。
"""
import cv2
import numpy as np
import sys

from imsee_sdk import ImseeSdk, CLASS_NAMES

# 每个类别的颜色 (BGR)
CLASS_COLORS = {
    0: (128, 128, 128),  # BG
    1: (0, 255, 0),      # PERSON
    2: (255, 165, 0),    # PET_CAT
    3: (255, 0, 255),    # PET_DOG
    4: (0, 255, 255),    # SOFA
    5: (255, 255, 0),    # TABLE
    6: (128, 0, 255),    # BED
    7: (0, 0, 255),      # EXCREMENT
    8: (255, 128, 0),    # WIRE
    9: (0, 128, 255),    # KEY
}


def main():
    print("=" * 50)
    print("Indemind 目标检测")
    print("按 Q 或 ESC 退出")
    print("=" * 50)

    sdk = ImseeSdk()
    ret = sdk.init(1, 25)
    if ret != 0:
        print(f"初始化失败: {ret}")
        return 1

    print(f"相机: {sdk.get_module_info()}")
    det_ret = sdk.enable_detector()
    print(f"检测处理器: {'OK' if det_ret == 0 else f'失败({det_ret})'}")

    win = "Detector"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    # 也显示原始画面
    last_frame = None

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        # 获取检测结果
        boxes = sdk.get_detector_boxes()

        # 尝试获取检测器图像
        det_img = sdk.get_detector_image()
        if det_img is not None:
            if len(det_img.shape) == 2:
                display = cv2.cvtColor(det_img, cv2.COLOR_GRAY2BGR)
            else:
                display = det_img.copy()
        else:
            # 回退到原始帧
            frame = sdk.get_frame()
            if frame is not None:
                last_frame = frame
            if last_frame is None:
                continue
            h, w = last_frame.shape[:2]
            if w > h * 1.5:
                half = w // 2
                display = cv2.cvtColor(last_frame[:, :half], cv2.COLOR_GRAY2BGR)
            else:
                display = cv2.cvtColor(last_frame, cv2.COLOR_GRAY2BGR)

        # 绘制检测框
        for box in boxes:
            x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
            cls_id = box["class_id"]
            name = box["class_name"]
            score = box["score"]
            color = CLASS_COLORS.get(cls_id, (255, 255, 255))

            cv2.rectangle(display, (x, y), (x + bw, y + bh), color, 2)
            label = f"{name} {score:.2f}"
            cv2.putText(display, label, (x, max(y - 5, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        info = f"detections: {len(boxes)}"
        cv2.putText(display, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow(win, display)

    cv2.destroyAllWindows()
    sdk.release()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
