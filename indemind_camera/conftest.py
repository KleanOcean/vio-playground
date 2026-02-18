"""项目级 pytest 配置。"""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "camera: 需要物理相机的测试")
