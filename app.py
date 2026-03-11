from __future__ import annotations

import atexit
import mimetypes
import os
import socket
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

if getattr(sys, "_MEIPASS", None):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_HTML = WEB_DIR / "index.html"
IS_PACKAGED = bool(getattr(sys, "frozen", False))

RESULT_TTL_SECONDS = 3600
SESSION_TTL_SECONDS = 3600
IDLE_EXIT_SECONDS = max(0, int(os.getenv("QR_LITE_IDLE_EXIT_SECONDS", "90" if IS_PACKAGED else "0")))
_RESULTS: dict[str, dict[str, float | str]] = {}
_SESSIONS: dict[str, dict[str, float | str]] = {}
_CLIENT_HEARTBEATS: dict[str, float] = {}
_EVER_HAD_CLIENT = False
_SERVER: uvicorn.Server | None = None
_STATE_LOCK = threading.Lock()
_QRCODE_MODULE = None
_REPLACE_QR_FN = None

app = FastAPI(title="QR Lite")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def _safe_remove(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except OSError:
        pass


def _guess_image_media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext == ".bmp":
        return "image/bmp"
    if ext == ".gif":
        return "image/gif"
    if ext in (".tif", ".tiff"):
        return "image/tiff"
    media_type, _ = mimetypes.guess_type(path)
    if media_type and media_type.startswith("image/"):
        return media_type
    return "image/png"


def _cleanup_results() -> None:
    now = time.time()
    expired = [rid for rid, item in _RESULTS.items() if now - float(item["created_at"]) > RESULT_TTL_SECONDS]
    for rid in expired:
        path = str(_RESULTS[rid]["path"])
        _safe_remove(path)
        del _RESULTS[rid]


def _cleanup_sessions() -> None:
    now = time.time()
    expired = [sid for sid, item in _SESSIONS.items() if now - float(item["created_at"]) > SESSION_TTL_SECONDS]
    for sid in expired:
        for key in ("source_path", "qr_path"):
            path = str(_SESSIONS[sid].get(key, ""))
            _safe_remove(path)
        del _SESSIONS[sid]


def _purge_all_temp_files() -> None:
    tracked_paths: set[str] = set()
    for item in _RESULTS.values():
        path = str(item.get("path", ""))
        if path:
            tracked_paths.add(path)
    for item in _SESSIONS.values():
        for key in ("source_path", "qr_path"):
            path = str(item.get(key, ""))
            if path:
                tracked_paths.add(path)

    for path in tracked_paths:
        _safe_remove(path)

    _RESULTS.clear()
    _SESSIONS.clear()


atexit.register(_purge_all_temp_files)


def _mark_client_heartbeat(client_id: str, active: bool) -> None:
    global _EVER_HAD_CLIENT

    cid = (client_id or "").strip()
    if not cid:
        return

    with _STATE_LOCK:
        if active:
            _CLIENT_HEARTBEATS[cid] = time.time()
            _EVER_HAD_CLIENT = True
        else:
            _CLIENT_HEARTBEATS.pop(cid, None)


def _request_shutdown() -> None:
    server = _SERVER
    if server is not None:
        server.should_exit = True


def _auto_exit_monitor() -> None:
    if IDLE_EXIT_SECONDS <= 0:
        return

    while True:
        time.sleep(2.0)
        server = _SERVER
        if server is None or server.should_exit:
            return

        now = time.time()
        should_exit = False
        with _STATE_LOCK:
            expired = [cid for cid, ts in _CLIENT_HEARTBEATS.items() if now - ts > IDLE_EXIT_SECONDS]
            for cid in expired:
                _CLIENT_HEARTBEATS.pop(cid, None)
            if _EVER_HAD_CLIENT and not _CLIENT_HEARTBEATS:
                should_exit = True

        if should_exit:
            _request_shutdown()
            return


def _save_upload_temp(upload: UploadFile, prefix: str) -> str:
    suffix = Path(upload.filename or "").suffix or ".bin"
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return path


def _generate_qr_temp(content: str) -> str:
    text = (content or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="请上传二维码图片，或填写二维码内容（链接/文本）。")

    qrcode = _get_qrcode_module()
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    fd, path = tempfile.mkstemp(prefix="generated_qr_", suffix=".png")
    os.close(fd)
    img.save(path, "PNG")
    return path


def _get_qrcode_module():
    global _QRCODE_MODULE
    if _QRCODE_MODULE is None:
        import qrcode as qrcode_module

        _QRCODE_MODULE = qrcode_module
    return _QRCODE_MODULE


def _get_replace_qr():
    global _REPLACE_QR_FN
    if _REPLACE_QR_FN is None:
        from qr_replace import replace_qr as replace_qr_fn

        _REPLACE_QR_FN = replace_qr_fn
    return _REPLACE_QR_FN


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=500, detail="前端页面不存在：web/index.html")
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    icon_path = WEB_DIR / "app-icon.ico"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail="favicon 不存在。")
    return FileResponse(path=icon_path, media_type="image/x-icon")


@app.post("/api/heartbeat")
def api_heartbeat(client_id: str = Form(default=""), active: bool = Form(default=True)) -> JSONResponse:
    _mark_client_heartbeat(client_id=client_id, active=bool(active))
    return JSONResponse({"ok": True, "idle_exit_seconds": IDLE_EXIT_SECONDS})


@app.post("/api/shutdown")
def api_shutdown() -> JSONResponse:
    threading.Timer(0.2, _request_shutdown).start()
    return JSONResponse({"ok": True})


@app.post("/api/replace")
def api_replace(
    session_id: str = Form(default=""),
    source_image: UploadFile | None = File(default=None),
    replacement_qr_image: UploadFile | None = File(default=None),
    replacement_qr_text: str = Form(default=""),
    placement_mode: str = Form(default="auto"),
    replace_all: bool = Form(default=False),
    feather_ratio: float = Form(default=0.012),
    output_format: str = Form(default="SAME"),
    offset_x_px: float = Form(default=0.0),
    offset_y_px: float = Form(default=0.0),
    scale_percent: float = Form(default=100.0),
    rotation_deg: float = Form(default=0.0),
    quiet_zone_percent: float = Form(default=2.5),
    replacement_crop_x_px: float | None = Form(default=None),
    replacement_crop_y_px: float | None = Form(default=None),
    replacement_crop_w_px: float | None = Form(default=None),
    replacement_crop_h_px: float | None = Form(default=None),
    target_box_x_px: float | None = Form(default=None),
    target_box_y_px: float | None = Form(default=None),
    target_box_w_px: float | None = Form(default=None),
    target_box_h_px: float | None = Form(default=None),
) -> JSONResponse:
    _cleanup_results()
    _cleanup_sessions()

    source_path = ""
    qr_path = ""
    generated_qr_path = ""
    created_session = False
    session = _SESSIONS.get(session_id) if session_id else None
    qr_source_kind = "generated"
    mode = (placement_mode or "auto").strip().lower()
    effective_replace_all = bool(replace_all and mode == "auto")
    replacement_crop_box: tuple[float, float, float, float] | None = None
    target_box: tuple[float, float, float, float] | None = None

    if (
        replacement_crop_x_px is not None
        and replacement_crop_y_px is not None
        and replacement_crop_w_px is not None
        and replacement_crop_h_px is not None
    ):
        replacement_crop_box = (
            float(replacement_crop_x_px),
            float(replacement_crop_y_px),
            float(replacement_crop_w_px),
            float(replacement_crop_h_px),
        )

    if (
        target_box_x_px is not None
        and target_box_y_px is not None
        and target_box_w_px is not None
        and target_box_h_px is not None
    ):
        target_box = (
            float(target_box_x_px),
            float(target_box_y_px),
            float(target_box_w_px),
            float(target_box_h_px),
        )

    try:
        if session is not None:
            source_path = str(session["source_path"])
            qr_path = str(session["qr_path"])
            qr_source_kind = str(session.get("qr_kind", "generated"))
        else:
            if source_image is None:
                raise HTTPException(status_code=400, detail="请先上传原图。")
            source_path = _save_upload_temp(source_image, "src_")

            if replacement_qr_image and replacement_qr_image.filename:
                qr_path = _save_upload_temp(replacement_qr_image, "qr_")
                qr_source_kind = "uploaded"
            else:
                generated_qr_path = _generate_qr_temp(replacement_qr_text)
                qr_path = generated_qr_path
                qr_source_kind = "generated"

            session_id = uuid.uuid4().hex
            _SESSIONS[session_id] = {
                "source_path": source_path,
                "qr_path": qr_path,
                "qr_kind": qr_source_kind,
                "created_at": time.time(),
            }
            created_session = True

        result = _get_replace_qr()(
            source_image_path=source_path,
            replacement_qr_path=qr_path,
            placement_mode=mode,
            replace_all=effective_replace_all,
            feather_ratio=float(feather_ratio),
            output_format=output_format,
            offset_x_px=float(offset_x_px),
            offset_y_px=float(offset_y_px),
            scale_ratio=float(scale_percent) / 100.0,
            rotation_deg=float(rotation_deg),
            quiet_zone_ratio=float(quiet_zone_percent) / 100.0,
            replacement_crop_box=replacement_crop_box,
            target_box=target_box,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if not created_session:
            for p in [generated_qr_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    result_id = uuid.uuid4().hex
    _RESULTS[result_id] = {"path": result.output_path, "created_at": time.time()}

    report = {
        "placement_mode": mode,
        "qr_count": result.qr_count,
        "original_mode": result.original_mode,
        "original_format": result.original_format,
        "output_format": result.output_format,
        "image_width": result.image_width,
        "image_height": result.image_height,
        "selected_quad": result.selected_quad,
        "replace_all": effective_replace_all,
        "offset_x_px": offset_x_px,
        "offset_y_px": offset_y_px,
        "scale_percent": scale_percent,
        "rotation_deg": rotation_deg,
        "quiet_zone_percent": quiet_zone_percent,
        "replacement_qr_box": result.replacement_qr_box,
        "target_box": result.target_box,
        "qr_source_kind": qr_source_kind,
    }
    return JSONResponse(
        {
            "ok": True,
            "session_id": session_id,
            "result_id": result_id,
            "qr_source_kind": qr_source_kind,
            "preview_url": f"/api/result/{result_id}",
            "download_url": f"/api/result/{result_id}?download=1",
            "source_url": f"/api/session/{session_id}/source",
            "qr_preview_url": f"/api/session/{session_id}/qr",
            "report": report,
        }
    )


@app.get("/api/result/{result_id}")
def api_result(result_id: str, download: int = 0) -> FileResponse:
    _cleanup_results()
    item = _RESULTS.get(result_id)
    if not item:
        raise HTTPException(status_code=404, detail="结果已过期，请重新处理。")
    path = str(item["path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="结果文件不存在。")

    filename = Path(path).name
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    if download:
        return FileResponse(path=path, media_type=media_type, filename=filename)
    return FileResponse(path=path, media_type=media_type)


@app.get("/api/session/{session_id}/source")
def api_session_source(session_id: str) -> FileResponse:
    _cleanup_sessions()
    item = _SESSIONS.get(session_id)
    if not item:
        raise HTTPException(status_code=404, detail="编辑会话已过期，请重新上传。")
    path = str(item["source_path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="原图文件不存在。")

    filename = Path(path).name.lower()
    media_type = _guess_image_media_type(filename)
    return FileResponse(path=path, media_type=media_type)


@app.get("/api/session/{session_id}/qr")
def api_session_qr(session_id: str) -> FileResponse:
    _cleanup_sessions()
    item = _SESSIONS.get(session_id)
    if not item:
        raise HTTPException(status_code=404, detail="编辑会话已过期，请重新上传。")
    path = str(item["qr_path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="二维码文件不存在。")

    filename = Path(path).name.lower()
    media_type = _guess_image_media_type(filename)
    return FileResponse(path=path, media_type=media_type)


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(start: int = 7860, end: int = 7899) -> int:
    for port in range(start, end + 1):
        if _is_port_available(port):
            return port
    return 0


def launch_app(open_browser: bool = True, port: int | None = None) -> None:
    global _SERVER

    if port is None:
        port = find_free_port()
    elif not _is_port_available(port):
        raise RuntimeError(f"端口 {port} 已被占用，请重试。")

    if port == 0:
        raise RuntimeError("7860-7899 端口都被占用，请先关闭占用进程后重试。")

    url = f"http://127.0.0.1:{port}"
    if open_browser and os.getenv("QR_LITE_NO_BROWSER", "") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"QR Lite running: {url}")
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        reload=False,
        loop="asyncio",
        http="h11",
        ws="none",
        lifespan="on",
        log_config=None,
        access_log=False,
    )
    _SERVER = uvicorn.Server(config)
    if IDLE_EXIT_SECONDS > 0:
        threading.Thread(target=_auto_exit_monitor, daemon=True).start()
    try:
        _SERVER.run()
    finally:
        _purge_all_temp_files()
        _SERVER = None


if __name__ == "__main__":
    launch_app(open_browser=True)
