"""
Indemind SDK Python Wrapper (共用类)
通过 ctypes 加载 libimsee_wrapper.so，封装所有 C 函数。
所有 test 脚本均通过此模块访问 SDK。
"""
import ctypes
import json
import os
import sys

import numpy as np

from config import CLASS_NAMES

# 库路径: test/ 的上一级目录下的 lib/
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
_LIB_DIR = os.path.join(_PROJECT_DIR, "lib")


def _ensure_lib_env():
    """确保 LD_LIBRARY_PATH 正确设置，必要时重启进程。
    解决: 1) conda libgcc_s ABI 冲突  2) SDK 运行时 dlopen 依赖"""
    abs_lib = os.path.abspath(_LIB_DIR)
    sys_lib = "/lib/x86_64-linux-gnu"

    # 检查是否已经设置好
    if os.environ.get("_IMSEE_LIB_OK") == "1":
        return

    # 构建正确的 LD_LIBRARY_PATH: 系统库优先(覆盖 conda), 然后项目库
    current = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [p for p in current.split(":") if p]

    need_reexec = False
    if abs_lib not in parts:
        need_reexec = True
    if sys_lib not in parts or (sys_lib in parts and parts.index(sys_lib) > 0):
        need_reexec = True

    if need_reexec:
        # 系统库在前(避免 conda libgcc 冲突), 项目库其次, 保留原有路径
        new_parts = [sys_lib, abs_lib] + [p for p in parts if p not in (sys_lib, abs_lib)]
        os.environ["LD_LIBRARY_PATH"] = ":".join(new_parts)
        os.environ["_IMSEE_LIB_OK"] = "1"
        # 重启进程使 LD_LIBRARY_PATH 生效 (dlopen 需要在进程启动时设置)
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError:
            # execv 在某些环境下可能失败 (非 TTY 等)
            print("[警告] 无法自动设置库路径，请使用:")
            print(f"  LD_LIBRARY_PATH={':'.join(new_parts)} python3 {' '.join(sys.argv)}")
            sys.exit(1)


def _preload_deps():
    """预加载系统库和 SDK 依赖 (RTLD_GLOBAL)，解决:
    1) conda libgcc_s ABI 冲突
    2) libindemind.so 运行时 dlopen 依赖"""
    # 系统 libgcc/libstdc++ 优先 (覆盖 conda 旧版本)
    for sl in ("/lib/x86_64-linux-gnu/libgcc_s.so.1",
               "/lib/x86_64-linux-gnu/libstdc++.so.6"):
        if os.path.exists(sl):
            try:
                ctypes.CDLL(sl, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass

    # SDK 运行时 dlopen 依赖
    for dep in ("libusbdriver.so", "libMNN.so", "libindemind.so"):
        p = os.path.join(_LIB_DIR, dep)
        if os.path.exists(p):
            try:
                ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


class ImseeSdk:
    """Indemind SDK ctypes wrapper。"""

    def __init__(self):
        so_path = os.path.join(_LIB_DIR, "libimsee_wrapper.so")
        if not os.path.exists(so_path):
            print(f"[错误] 找不到 {so_path}")
            print("请先运行 ./build.sh 编译 wrapper")
            sys.exit(1)

        _ensure_lib_env()
        _preload_deps()
        self._lib = ctypes.CDLL(so_path)
        self._declare_functions()

        # 预分配缓冲区
        self._cam_buf = None
        self._cam_buf_size = 0
        self._depth_buf = None
        self._depth_buf_size = 0
        self._disp_buf = None
        self._disp_buf_size = 0
        self._rect_buf = None
        self._rect_buf_size = 0
        self._pts_buf = None
        self._pts_buf_size = 0
        self._imu_buf = None
        self._det_box_buf = None
        self._det_img_buf = None
        self._det_img_size = 0

    def _declare_functions(self):
        lib = self._lib
        INT = ctypes.c_int
        PINT = ctypes.POINTER(INT)
        UBYTE_P = ctypes.POINTER(ctypes.c_ubyte)
        USHORT_P = ctypes.POINTER(ctypes.c_ushort)
        FLOAT_P = ctypes.POINTER(ctypes.c_float)
        DOUBLE_P = ctypes.POINTER(ctypes.c_double)

        # --- Init / Release ---
        lib.imsee_init.argtypes = [INT, INT]
        lib.imsee_init.restype = INT
        lib.imsee_release.argtypes = []
        lib.imsee_release.restype = None
        lib.imsee_is_initialized.argtypes = []
        lib.imsee_is_initialized.restype = INT
        lib.imsee_get_callback_count.argtypes = []
        lib.imsee_get_callback_count.restype = INT

        # --- Raw image ---
        lib.imsee_get_image_info.argtypes = [PINT, PINT, PINT]
        lib.imsee_get_image_info.restype = None
        lib.imsee_get_frame.argtypes = [UBYTE_P, INT]
        lib.imsee_get_frame.restype = INT

        # --- Depth ---
        lib.imsee_enable_depth.argtypes = [INT]
        lib.imsee_enable_depth.restype = INT
        lib.imsee_get_depth.argtypes = [USHORT_P, INT]
        lib.imsee_get_depth.restype = INT
        lib.imsee_get_depth_size.argtypes = [PINT, PINT]
        lib.imsee_get_depth_size.restype = None

        # --- Disparity ---
        lib.imsee_enable_disparity.argtypes = [INT]
        lib.imsee_enable_disparity.restype = INT
        lib.imsee_get_disparity.argtypes = [FLOAT_P, INT]
        lib.imsee_get_disparity.restype = INT
        lib.imsee_get_disparity_size.argtypes = [PINT, PINT]
        lib.imsee_get_disparity_size.restype = None

        # --- Rectified ---
        lib.imsee_enable_rectify.argtypes = []
        lib.imsee_enable_rectify.restype = INT
        lib.imsee_get_rectified.argtypes = [UBYTE_P, INT]
        lib.imsee_get_rectified.restype = INT
        lib.imsee_get_rectified_info.argtypes = [PINT, PINT, PINT]
        lib.imsee_get_rectified_info.restype = None

        # --- Point cloud ---
        lib.imsee_enable_points.argtypes = []
        lib.imsee_enable_points.restype = INT
        lib.imsee_get_points.argtypes = [FLOAT_P, INT]
        lib.imsee_get_points.restype = INT
        lib.imsee_get_points_size.argtypes = [PINT, PINT, PINT]
        lib.imsee_get_points_size.restype = None

        # --- IMU ---
        lib.imsee_enable_imu.argtypes = []
        lib.imsee_enable_imu.restype = INT
        lib.imsee_get_imu.argtypes = [DOUBLE_P, INT]
        lib.imsee_get_imu.restype = INT
        lib.imsee_get_imu_count.argtypes = []
        lib.imsee_get_imu_count.restype = INT

        # --- Detector ---
        lib.imsee_enable_detector.argtypes = []
        lib.imsee_enable_detector.restype = INT
        lib.imsee_get_detector_boxes.argtypes = [PINT, INT]
        lib.imsee_get_detector_boxes.restype = INT
        lib.imsee_get_detector_image.argtypes = [UBYTE_P, INT]
        lib.imsee_get_detector_image.restype = INT
        lib.imsee_get_detector_image_info.argtypes = [PINT, PINT, PINT]
        lib.imsee_get_detector_image_info.restype = None

        # --- Calibration / device info ---
        lib.imsee_get_calibration.argtypes = []
        lib.imsee_get_calibration.restype = ctypes.c_char_p
        lib.imsee_get_device_info_detailed.argtypes = []
        lib.imsee_get_device_info_detailed.restype = ctypes.c_char_p
        lib.imsee_get_module_info.argtypes = []
        lib.imsee_get_module_info.restype = ctypes.c_char_p

    # ==========================================================
    # Context manager
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    # ==========================================================
    # Init / Release
    # ==========================================================

    def init(self, resolution=1, fps=25):
        """初始化相机。resolution: 1=640x400, 2=1280x800"""
        return self._lib.imsee_init(resolution, fps)

    def release(self):
        self._lib.imsee_release()

    def is_initialized(self):
        return self._lib.imsee_is_initialized() == 1

    def get_callback_count(self):
        return self._lib.imsee_get_callback_count()

    def get_module_info(self):
        return self._lib.imsee_get_module_info().decode("utf-8", errors="replace")

    # ==========================================================
    # Raw camera frame
    # ==========================================================

    def get_image_info(self):
        """返回 (width, height, channels)"""
        w, h, ch = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_image_info(ctypes.byref(w), ctypes.byref(h), ctypes.byref(ch))
        return w.value, h.value, ch.value

    def get_frame(self):
        """返回 numpy 图像或 None (无新帧)"""
        w, h, ch = self.get_image_info()
        if w <= 0 or h <= 0:
            return None
        needed = w * h * max(ch, 1)
        if self._cam_buf is None or self._cam_buf_size != needed:
            self._cam_buf = (ctypes.c_ubyte * needed)()
            self._cam_buf_size = needed
        got = self._lib.imsee_get_frame(self._cam_buf, needed)
        if got <= 0:
            return None
        return np.frombuffer(self._cam_buf, dtype=np.uint8, count=got).reshape((h, w))

    # ==========================================================
    # Depth
    # ==========================================================

    def enable_depth(self, mode=0):
        """mode: 0=default, 1=high_accuracy+LR_check"""
        return self._lib.imsee_enable_depth(mode)

    def get_depth_size(self):
        w, h = ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_depth_size(ctypes.byref(w), ctypes.byref(h))
        return w.value, h.value

    def get_depth(self):
        """返回 uint16 深度图 (mm) 或 None"""
        w, h = self.get_depth_size()
        if w <= 0 or h <= 0:
            return None
        needed = w * h
        if self._depth_buf is None or self._depth_buf_size != needed:
            self._depth_buf = (ctypes.c_ushort * needed)()
            self._depth_buf_size = needed
        got = self._lib.imsee_get_depth(self._depth_buf, needed)
        if got <= 0:
            return None
        return np.frombuffer(self._depth_buf, dtype=np.uint16, count=got).reshape((h, w)).copy()

    # ==========================================================
    # Disparity
    # ==========================================================

    def enable_disparity(self, mode=0):
        """mode: 0=default, 1=high_accuracy, 2=LR_check, 3=both"""
        return self._lib.imsee_enable_disparity(mode)

    def get_disparity_size(self):
        w, h = ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_disparity_size(ctypes.byref(w), ctypes.byref(h))
        return w.value, h.value

    def get_disparity(self):
        """返回 float32 视差图或 None"""
        w, h = self.get_disparity_size()
        if w <= 0 or h <= 0:
            return None
        needed = w * h
        if self._disp_buf is None or self._disp_buf_size != needed:
            self._disp_buf = (ctypes.c_float * needed)()
            self._disp_buf_size = needed
        got = self._lib.imsee_get_disparity(self._disp_buf, needed)
        if got <= 0:
            return None
        return np.frombuffer(self._disp_buf, dtype=np.float32, count=got).reshape((h, w)).copy()

    # ==========================================================
    # Rectified images
    # ==========================================================

    def enable_rectify(self):
        return self._lib.imsee_enable_rectify()

    def get_rectified_info(self):
        w, h, ch = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_rectified_info(ctypes.byref(w), ctypes.byref(h), ctypes.byref(ch))
        return w.value, h.value, ch.value

    def get_rectified(self):
        """返回校正后图像 (左右 side-by-side) 或 None"""
        w, h, ch = self.get_rectified_info()
        if w <= 0 or h <= 0:
            return None
        needed = w * h * max(ch, 1)
        if self._rect_buf is None or self._rect_buf_size != needed:
            self._rect_buf = (ctypes.c_ubyte * needed)()
            self._rect_buf_size = needed
        got = self._lib.imsee_get_rectified(self._rect_buf, needed)
        if got <= 0:
            return None
        return np.frombuffer(self._rect_buf, dtype=np.uint8, count=got).reshape((h, w)).copy()

    # ==========================================================
    # Point cloud
    # ==========================================================

    def enable_points(self):
        return self._lib.imsee_enable_points()

    def get_points_size(self):
        w, h, c = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_points_size(ctypes.byref(w), ctypes.byref(h), ctypes.byref(c))
        return w.value, h.value, c.value

    def get_points(self):
        """返回 (N, 3) float32 点云或 None"""
        w, h, count = self.get_points_size()
        if count <= 0:
            return None
        needed = count * 3
        if self._pts_buf is None or self._pts_buf_size != needed:
            self._pts_buf = (ctypes.c_float * needed)()
            self._pts_buf_size = needed
        got = self._lib.imsee_get_points(self._pts_buf, needed)
        if got <= 0:
            return None
        return np.frombuffer(self._pts_buf, dtype=np.float32, count=got * 3).reshape((got, 3)).copy()

    # ==========================================================
    # IMU
    # ==========================================================

    def enable_imu(self):
        return self._lib.imsee_enable_imu()

    def get_imu_count(self):
        return self._lib.imsee_get_imu_count()

    def get_imu(self, max_samples=2000):
        """返回 (N, 7) float64 数组: [timestamp, ax, ay, az, gx, gy, gz] 或 None"""
        if self._imu_buf is None or len(self._imu_buf) < max_samples * 7:
            self._imu_buf = (ctypes.c_double * (max_samples * 7))()
        got = self._lib.imsee_get_imu(self._imu_buf, max_samples)
        if got <= 0:
            return None
        return np.frombuffer(self._imu_buf, dtype=np.float64, count=got * 7).reshape((got, 7)).copy()

    # ==========================================================
    # Detector
    # ==========================================================

    def enable_detector(self):
        return self._lib.imsee_enable_detector()

    def get_detector_boxes(self, max_boxes=100):
        """返回列表 [{x,y,w,h,class_id,class_name,score}, ...] 或 []"""
        if self._det_box_buf is None:
            self._det_box_buf = (ctypes.c_int * (max_boxes * 6))()
        got = self._lib.imsee_get_detector_boxes(self._det_box_buf, max_boxes)
        if got <= 0:
            return []
        result = []
        for i in range(got):
            off = i * 6
            result.append({
                "x": self._det_box_buf[off],
                "y": self._det_box_buf[off + 1],
                "w": self._det_box_buf[off + 2],
                "h": self._det_box_buf[off + 3],
                "class_id": self._det_box_buf[off + 4],
                "class_name": CLASS_NAMES.get(self._det_box_buf[off + 4], "UNKNOWN"),
                "score": self._det_box_buf[off + 5] / 1000.0,
            })
        return result

    def get_detector_image_info(self):
        w, h, ch = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        self._lib.imsee_get_detector_image_info(ctypes.byref(w), ctypes.byref(h), ctypes.byref(ch))
        return w.value, h.value, ch.value

    def get_detector_image(self):
        """返回检测器图像或 None"""
        w, h, ch = self.get_detector_image_info()
        if w <= 0 or h <= 0:
            return None
        needed = w * h * ch
        if self._det_img_buf is None or self._det_img_size != needed:
            self._det_img_buf = (ctypes.c_ubyte * needed)()
            self._det_img_size = needed
        got = self._lib.imsee_get_detector_image(self._det_img_buf, needed)
        if got <= 0:
            return None
        if ch == 1:
            return np.frombuffer(self._det_img_buf, dtype=np.uint8, count=got).reshape((h, w)).copy()
        return np.frombuffer(self._det_img_buf, dtype=np.uint8, count=got).reshape((h, w, ch)).copy()

    # ==========================================================
    # Calibration / Device info
    # ==========================================================

    def get_calibration(self):
        """返回标定参数 dict"""
        raw = self._lib.imsee_get_calibration().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def get_device_info_detailed(self):
        """返回详细设备信息 dict"""
        raw = self._lib.imsee_get_device_info_detailed().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
