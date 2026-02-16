"""Indemind OV580 相机管理器 — 提供 JPEG 帧用于 MJPEG 流。"""
import os
import sys
import time
import threading

import cv2
import numpy as np

# 将 test/ 加入路径以复用 imsee_sdk.py
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEST_DIR = os.path.join(_PROJECT_DIR, "test")
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)


class IndemindHandler:
    """封装 ImseeSdk，提供 JPEG 帧输出。"""

    def __init__(self):
        self._sdk = None
        self._running = False
        self._alpha = 0.5
        self._last_frame = None       # numpy grayscale
        self._last_depth = None       # numpy uint16
        self._lock = threading.Lock()
        self._frame_count = 0
        self._start_time = 0.0
        self._resolution = (0, 0)

    def is_running(self) -> bool:
        return self._running

    def start(self) -> dict:
        if self._running:
            return {"success": True, "error": None}

        try:
            from imsee_sdk import ImseeSdk, _preload_deps, _ensure_lib_env
            _ensure_lib_env()
            _preload_deps()

            self._sdk = ImseeSdk()
            ret = self._sdk.init(1, 25)
            if ret != 0:
                self._sdk = None
                return {"success": False, "error": f"SDK init failed: {ret}"}

            depth_ret = self._sdk.enable_depth(0)
            if depth_ret != 0:
                pass  # depth optional, camera still works

            self._running = True
            self._frame_count = 0
            self._start_time = time.time()
            return {"success": True, "error": None}

        except Exception as e:
            self._sdk = None
            return {"success": False, "error": str(e)}

    def stop(self) -> dict:
        if self._sdk is not None:
            try:
                self._sdk.release()
            except Exception:
                pass
            self._sdk = None

        self._running = False
        with self._lock:
            self._last_frame = None
            self._last_depth = None
        self._frame_count = 0
        self._resolution = (0, 0)
        return {"success": True, "error": None}

    def set_alpha(self, alpha: float):
        self._alpha = max(0.0, min(1.0, alpha))

    def get_status(self) -> dict:
        elapsed = time.time() - self._start_time if self._running else 0
        fps = self._frame_count / elapsed if elapsed > 1 else 0
        return {
            "running": self._running,
            "fps": round(fps, 1),
            "resolution": f"{self._resolution[0]}x{self._resolution[1]}",
            "alpha": self._alpha,
        }

    def _poll_frames(self):
        """从 SDK 拉取最新帧（调用方在请求时触发）。"""
        if not self._running or self._sdk is None:
            return

        frame = self._sdk.get_frame()
        depth = self._sdk.get_depth()

        with self._lock:
            if frame is not None:
                h, w = frame.shape[:2]
                # 取左半（立体图像 side-by-side）
                if w > h * 1.5:
                    self._last_frame = frame[:, :w // 2]
                else:
                    self._last_frame = frame
                fh, fw = self._last_frame.shape[:2]
                self._resolution = (fw, fh)
                self._frame_count += 1

            if depth is not None:
                self._last_depth = depth

    def get_frame_jpeg(self, quality: int = 80) -> bytes | None:
        if not self._running:
            return None

        self._poll_frames()

        with self._lock:
            if self._last_frame is None:
                return None
            _, buf = cv2.imencode('.jpg', self._last_frame,
                                  [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    def get_overlay_jpeg(self, quality: int = 80) -> bytes | None:
        if not self._running:
            return None

        self._poll_frames()

        with self._lock:
            if self._last_frame is None:
                return None

            cam = cv2.cvtColor(self._last_frame, cv2.COLOR_GRAY2BGR)

            if self._last_depth is not None:
                colored, clamped, valid = self.depth_to_color(self._last_depth)
                ch, cw = cam.shape[:2]
                dh, dw = colored.shape[:2]

                if (dw, dh) != (cw, ch):
                    colored = cv2.resize(colored, (cw, ch))
                    valid = cv2.resize(valid.astype(np.uint8), (cw, ch),
                                       interpolation=cv2.INTER_NEAREST).astype(bool)

                mask = valid
                cam[mask] = cv2.addWeighted(
                    cam[mask], 1.0 - self._alpha,
                    colored[mask], self._alpha, 0
                )

                # Center distance label
                cx, cy = cw // 2, ch // 2
                raw = cv2.resize(clamped, (cw, ch),
                                 interpolation=cv2.INTER_NEAREST)
                val = raw[cy, cx]
                label = f"{val / 1000:.2f}m" if val > 0 else "N/A"
                cv2.drawMarker(cam, (cx, cy), (255, 255, 255),
                               cv2.MARKER_CROSS, 20, 2)
                cv2.putText(cam, label, (cx + 15, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            _, buf = cv2.imencode('.jpg', cam,
                                  [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    @staticmethod
    def depth_to_color(depth_mm: np.ndarray, max_range: int = 4000):
        """深度(mm) → 彩色图 (近=红, 远=蓝) + clamped + valid mask。"""
        depth_f = cv2.medianBlur(depth_mm, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        filled = cv2.dilate(depth_f, kernel, iterations=1)
        depth_out = np.where(depth_f > 0, depth_f, filled)

        clamped = depth_out.copy()
        clamped[clamped > max_range] = 0
        valid = clamped > 0

        norm = np.zeros_like(clamped, dtype=np.uint8)
        norm[valid] = (255 - (clamped[valid].astype(np.float32)
                              / max_range * 255)).astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        colored[~valid] = 0

        return colored, clamped, valid
