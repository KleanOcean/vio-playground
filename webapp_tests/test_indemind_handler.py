"""TDD tests for IndemindHandler — 纯逻辑测试不需要相机。"""
import numpy as np
import pytest

from webapp.indemind_handler import IndemindHandler


# ============================================================
# Init / lifecycle
# ============================================================

def test_handler_init():
    h = IndemindHandler()
    assert h.is_running() is False


def test_handler_stop_without_start():
    h = IndemindHandler()
    result = h.stop()
    assert result["success"] is True  # no-op is fine


def test_handler_double_stop():
    h = IndemindHandler()
    h.stop()
    result = h.stop()
    assert result["success"] is True


# ============================================================
# Frame getters when not running
# ============================================================

def test_get_frame_not_running():
    h = IndemindHandler()
    assert h.get_frame_jpeg() is None


def test_get_overlay_not_running():
    h = IndemindHandler()
    assert h.get_overlay_jpeg() is None


# ============================================================
# Status
# ============================================================

def test_get_status_not_running():
    h = IndemindHandler()
    s = h.get_status()
    assert s["running"] is False
    assert "fps" in s
    assert "resolution" in s
    assert "alpha" in s


# ============================================================
# Alpha config
# ============================================================

def test_set_alpha():
    h = IndemindHandler()
    h.set_alpha(0.7)
    assert abs(h.get_status()["alpha"] - 0.7) < 0.01


def test_set_alpha_clamp_high():
    h = IndemindHandler()
    h.set_alpha(1.5)
    assert h.get_status()["alpha"] == 1.0


def test_set_alpha_clamp_low():
    h = IndemindHandler()
    h.set_alpha(-0.3)
    assert h.get_status()["alpha"] == 0.0


# ============================================================
# depth_to_color — static, no camera needed
# ============================================================

def test_depth_to_color_shape():
    depth = np.full((100, 200), 2000, dtype=np.uint16)
    colored, clamped, valid = IndemindHandler.depth_to_color(depth)
    assert colored.shape == (100, 200, 3)
    assert colored.dtype == np.uint8


def test_depth_to_color_zeros():
    depth = np.zeros((50, 50), dtype=np.uint16)
    colored, clamped, valid = IndemindHandler.depth_to_color(depth)
    # All invalid → all black
    assert np.all(colored == 0)
    assert not np.any(valid)


def test_depth_to_color_near_red():
    """Near objects (500mm) should have high red channel (JET colormap: near=red)."""
    depth = np.full((10, 10), 500, dtype=np.uint16)
    colored, _, _ = IndemindHandler.depth_to_color(depth, max_range=4000)
    avg_r = colored[:, :, 2].mean()  # OpenCV BGR → channel 2 is R
    avg_b = colored[:, :, 0].mean()  # channel 0 is B
    assert avg_r > avg_b, f"Near should be red: R={avg_r} B={avg_b}"


def test_depth_to_color_far_blue():
    """Far objects (3500mm) should have high blue channel."""
    depth = np.full((10, 10), 3500, dtype=np.uint16)
    colored, _, _ = IndemindHandler.depth_to_color(depth, max_range=4000)
    avg_r = colored[:, :, 2].mean()
    avg_b = colored[:, :, 0].mean()
    assert avg_b > avg_r, f"Far should be blue: B={avg_b} R={avg_r}"


# ============================================================
# Camera-required tests (skip without hardware)
# ============================================================

@pytest.mark.camera
def test_start_with_camera():
    import time
    h = IndemindHandler()
    result = h.start()
    assert result["success"] is True
    assert h.is_running() is True
    time.sleep(2)
    h.stop()


@pytest.mark.camera
def test_get_frame_jpeg_magic():
    import time
    h = IndemindHandler()
    h.start()
    time.sleep(3)
    data = h.get_frame_jpeg()
    h.stop()
    assert data is not None
    assert data[:2] == b'\xff\xd8', "Should be JPEG"


@pytest.mark.camera
def test_get_overlay_jpeg_magic():
    import time
    h = IndemindHandler()
    h.start()
    time.sleep(3)
    data = h.get_overlay_jpeg()
    h.stop()
    assert data is not None
    assert data[:2] == b'\xff\xd8', "Should be JPEG"


@pytest.mark.camera
def test_start_stop_cycle():
    import time
    h = IndemindHandler()
    h.start()
    time.sleep(2)
    assert h.get_frame_jpeg() is not None
    h.stop()
    assert h.is_running() is False
    assert h.get_frame_jpeg() is None
