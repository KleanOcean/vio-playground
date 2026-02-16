"""API tests for webapp/server.py — mock handler, no camera needed."""
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def mock_handler():
    h = MagicMock()
    h.is_running.return_value = False
    h.get_status.return_value = {
        "running": False, "fps": 0, "resolution": "0x0", "alpha": 0.5
    }
    h.start.return_value = {"success": True, "error": None}
    h.stop.return_value = {"success": True, "error": None}
    h.get_frame_jpeg.return_value = None
    h.get_overlay_jpeg.return_value = None
    return h


@pytest.fixture
def client(mock_handler):
    with patch("webapp.server.handler", mock_handler):
        from webapp.server import app
        yield TestClient(app)


# ============================================================
# Static / HTML
# ============================================================

def test_index_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ============================================================
# API endpoints
# ============================================================

def test_status_endpoint(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "fps" in data


def test_start_endpoint(client, mock_handler):
    resp = client.post("/api/start")
    assert resp.status_code == 200
    mock_handler.start.assert_called_once()
    data = resp.json()
    assert data["success"] is True


def test_stop_endpoint(client, mock_handler):
    resp = client.post("/api/stop")
    assert resp.status_code == 200
    mock_handler.stop.assert_called_once()


def test_config_alpha(client, mock_handler):
    resp = client.post("/api/config", json={"alpha": 0.7})
    assert resp.status_code == 200
    mock_handler.set_alpha.assert_called_once_with(0.7)


def test_snapshot_not_running(client):
    resp = client.get("/snapshot")
    assert resp.status_code == 503


def test_snapshot_with_frame(client, mock_handler):
    mock_handler.get_frame_jpeg.return_value = b'\xff\xd8fake'
    resp = client.get("/snapshot")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content == b'\xff\xd8fake'


def test_stream_route_exists(client, mock_handler):
    """Verify /stream and /stream/overlay routes are registered."""
    routes = [r.path for r in client.app.routes if hasattr(r, "path")]
    assert "/stream" in routes
    assert "/stream/overlay" in routes
