"""FastAPI 后端 — Indemind OV580 Webapp MVP."""
import time

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from webapp.indemind_handler import IndemindHandler

app = FastAPI(title="Indemind OV580 Viewer")

handler = IndemindHandler()

# ---------- Static files ----------

import os
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/")
def index():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


# ---------- API ----------

@app.get("/api/status")
def api_status():
    return handler.get_status()


@app.post("/api/start")
def api_start():
    return handler.start()


@app.post("/api/stop")
def api_stop():
    return handler.stop()


class ConfigBody(BaseModel):
    alpha: float | None = None


@app.post("/api/config")
def api_config(body: ConfigBody):
    if body.alpha is not None:
        handler.set_alpha(body.alpha)
    return {"success": True}


# ---------- Snapshot ----------

@app.get("/snapshot")
def snapshot():
    data = handler.get_frame_jpeg(quality=90)
    if data is None:
        return JSONResponse({"error": "no frame"}, status_code=503)
    return Response(content=data, media_type="image/jpeg")


# ---------- MJPEG streams ----------

def _mjpeg_generator(frame_func, quality: int = 80, target_fps: int = 25):
    interval = 1.0 / target_fps
    while True:
        data = frame_func(quality=quality)
        if data is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
            )
        time.sleep(interval)


@app.get("/stream")
def stream():
    return StreamingResponse(
        _mjpeg_generator(handler.get_frame_jpeg),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/stream/overlay")
def stream_overlay():
    return StreamingResponse(
        _mjpeg_generator(handler.get_overlay_jpeg),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
