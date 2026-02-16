"""
共用可视化工具 — 深度/视差彩色化函数。
所有 test 脚本和 webapp 均通过此模块访问。
"""
import cv2
import numpy as np


def depth_to_color(depth_mm: np.ndarray, max_range: int = 4000,
                   denoise: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """深度(mm) → 彩色图 (近=红, 远=蓝) + clamped + valid mask。

    Args:
        depth_mm: uint16 深度图 (毫米)
        max_range: 最大显示范围 (mm), 超出置零
        denoise: 是否做中值滤波 + 形态学填洞

    Returns:
        colored: (H, W, 3) uint8 BGR 彩色图
        clamped: (H, W) uint16 截断后的深度图
        valid: (H, W) bool 有效像素 mask
    """
    if denoise:
        depth_f = cv2.medianBlur(depth_mm, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        filled = cv2.dilate(depth_f, kernel, iterations=1)
        depth_out = np.where(depth_f > 0, depth_f, filled)
    else:
        depth_out = depth_mm

    clamped = depth_out.copy()
    clamped[clamped > max_range] = 0
    valid = clamped > 0

    norm = np.zeros_like(clamped, dtype=np.uint8)
    norm[valid] = (255 - (clamped[valid].astype(np.float32)
                          / max_range * 255)).astype(np.uint8)
    colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    colored[~valid] = 0

    return colored, clamped, valid


def disparity_to_color(disp: np.ndarray) -> np.ndarray:
    """视差(float32) → 彩色图 (JET colormap, 95th percentile 归一化)。

    Args:
        disp: float32 视差图

    Returns:
        colored: (H, W, 3) uint8 BGR 彩色图
    """
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
