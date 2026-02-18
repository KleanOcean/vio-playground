"""
共用配置常量 — SDK 初始化参数和可视化默认值。
"""

# SDK 初始化
RESOLUTION = 1        # 1=640x400, 2=1280x800
FPS = 25

# 深度可视化
DEPTH_MAX_RANGE = 4000  # mm

# 检测器类别名称
CLASS_NAMES = {
    0: "BG", 1: "PERSON", 2: "PET_CAT", 3: "PET_DOG",
    4: "SOFA", 5: "TABLE", 6: "BED", 7: "EXCREMENT",
    8: "WIRE", 9: "KEY",
}
