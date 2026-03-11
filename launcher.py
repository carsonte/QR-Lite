from __future__ import annotations

import os
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path


APP_TITLE = "QR Lite"
APP_SUBTITLE = "\u6b63\u5728\u542f\u52a8\uff0c\u8bf7\u7a0d\u5019..."
APP_HINT = "\u9996\u6b21\u542f\u52a8\u6216\u5355\u6587\u4ef6\u7248\u4f1a\u7a0d\u6162\u4e00\u4e9b"
APP_ERROR_TITLE = "\u542f\u52a8\u5931\u8d25"
APP_ERROR_HINT = "\u8bf7\u5173\u95ed\u7a97\u53e3\u540e\u91cd\u8bd5\uff0c\u6216\u628a\u62a5\u9519\u622a\u56fe\u7ed9\u7ef4\u62a4\u8005\u3002"
APP_ERROR_DETAIL = "\u670d\u52a1\u8fdb\u7a0b\u542f\u52a8\u5931\u8d25\u3002"
AUTHOR = "Created by @husky"
POLL_INTERVAL_MS = 250
PROBE_TIMEOUT_SECONDS = 0.35
STARTUP_TIMEOUT_SECONDS = max(15, int(os.getenv("QR_LITE_STARTUP_TIMEOUT_SECONDS", "60")))
PORT_RANGE = range(7860, 7900)
SERVER_ARG = "--qr-lite-server"
LAUNCH_BROWSER = os.getenv("QR_LITE_LAUNCHER_NO_BROWSER", "") != "1"

if getattr(sys, "_MEIPASS", None):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

ICON_ICO = BASE_DIR / "web" / "app-icon.ico"
LOG_ENV_KEY = "QR_LITE_STARTUP_LOG"


def detect_server_url(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            if resp.status == 200 and "QR Lite" in body:
                return url
    except Exception:
        pass
    return None


def summarize_exception(detail: str) -> str:
    lines = [line.strip() for line in detail.splitlines() if line.strip()]
    for line in reversed(lines):
        if line != "Traceback (most recent call last):" and not line.startswith("File "):
            return line[:180]
    return APP_ERROR_DETAIL


def run_server_mode() -> None:
    os.environ["QR_LITE_NO_BROWSER"] = "1"
    log_path = os.getenv(LOG_ENV_KEY, "")
    try:
        import app as qr_app

        qr_app.launch_app(open_browser=False)
    except Exception:
        if log_path:
            try:
                Path(log_path).write_text(traceback.format_exc(), encoding="utf-8")
            except OSError:
                pass
        raise


class LauncherWindow:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("460x220")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f7fb")
        self.root.protocol("WM_DELETE_WINDOW", self.cancel_launch)
        self.root.attributes("-topmost", True)

        if ICON_ICO.exists():
            try:
                self.root.iconbitmap(default=str(ICON_ICO))
            except Exception:
                pass

        self.status_var = tk.StringVar(value=APP_SUBTITLE)
        self.detail_var = tk.StringVar(value=APP_HINT)
        self.error_var = tk.StringVar(value="")
        self.server_thread: threading.Thread | None = None
        self.server_error = ""
        self.expected_url: str | None = None
        self.browser_opened = False
        self.probe_thread: threading.Thread | None = None
        self.pending_probe = False
        self.detected_url: str | None = None
        self.startup_deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        self.launch_succeeded = False

        self.build_ui()

    def build_ui(self) -> None:
        tk = self.tk

        frame = tk.Frame(self.root, bg="#ffffff", highlightbackground="#d9e8ff", highlightthickness=1)
        frame.place(x=18, y=18, width=424, height=184)

        title = tk.Label(frame, text=APP_TITLE, bg="#ffffff", fg="#174ea6", font=("Microsoft YaHei UI", 20, "bold"))
        title.place(x=26, y=24)

        subtitle = tk.Label(frame, textvariable=self.status_var, bg="#ffffff", fg="#35507f", font=("Microsoft YaHei UI", 11))
        subtitle.place(x=28, y=72)

        detail = tk.Label(frame, textvariable=self.detail_var, bg="#ffffff", fg="#6b778d", font=("Microsoft YaHei UI", 10))
        detail.place(x=28, y=98)

        self.progress = self.ttk.Progressbar(frame, mode="indeterminate", length=368)
        self.progress.place(x=28, y=132)
        self.progress.start(12)

        self.error_label = tk.Label(frame, textvariable=self.error_var, bg="#ffffff", fg="#b42318", font=("Microsoft YaHei UI", 9))
        self.error_label.place(x=28, y=158)

        author = tk.Label(frame, text=AUTHOR, bg="#ffffff", fg="#7b8798", font=("Segoe UI", 9))
        author.place(x=286, y=24)

    def start_server(self) -> None:
        if self.server_thread is not None:
            return
        self.server_thread = threading.Thread(target=self._run_server, name="qr-lite-server", daemon=False)
        self.server_thread.start()

    def show_start_error(self, detail: str = APP_ERROR_DETAIL) -> None:
        self.progress.stop()
        self.status_var.set(APP_ERROR_TITLE)
        self.detail_var.set(APP_ERROR_HINT)
        self.error_var.set(detail)

    def poll_ready(self) -> None:
        if self.server_error:
            self.show_start_error(detail=summarize_exception(self.server_error))
            return

        url = self.detected_url
        if url:
            if LAUNCH_BROWSER and not self.browser_opened:
                self.browser_opened = True
                webbrowser.open(url)
            self.launch_succeeded = True
            self.close_window()
            return

        if time.monotonic() >= self.startup_deadline:
            self.show_start_error(detail="\u542f\u52a8\u8d85\u65f6\uff0c\u8bf7\u5173\u95ed\u540e\u91cd\u8bd5\uff1b\u5efa\u8bae\u4f18\u5148\u4f7f\u7528 onedir \u7248\u672c\u3002")
            return

        if self.expected_url and not self.pending_probe:
            self.pending_probe = True
            self.probe_thread = threading.Thread(target=self._probe_server_url, daemon=True)
            self.probe_thread.start()

        self.root.after(POLL_INTERVAL_MS, self.poll_ready)

    def _run_server(self) -> None:
        os.environ["QR_LITE_NO_BROWSER"] = "1"
        try:
            import app as qr_app

            port = qr_app.find_free_port(start=PORT_RANGE.start, end=PORT_RANGE.stop - 1)
            if port == 0:
                raise RuntimeError("7860-7899 \u7aef\u53e3\u90fd\u88ab\u5360\u7528\uff0c\u8bf7\u5148\u5173\u95ed\u5360\u7528\u8fdb\u7a0b\u540e\u91cd\u8bd5\u3002")

            self.expected_url = f"http://127.0.0.1:{port}/"
            qr_app.launch_app(open_browser=False, port=port)
        except Exception:
            self.server_error = traceback.format_exc()

    def _probe_server_url(self) -> None:
        url = self.expected_url
        try:
            if url:
                self.detected_url = detect_server_url(url)
        finally:
            self.pending_probe = False

    def close_window(self) -> None:
        if self.progress is not None:
            self.progress.stop()

        # Keep Tk objects on the main thread so they are finalized there too.
        self.status_var = None
        self.detail_var = None
        self.error_var = None

        try:
            self.root.destroy()
        except Exception:
            pass

    def cancel_launch(self) -> None:
        self.close_window()
        os._exit(0)

    def run(self) -> None:
        self.root.after(80, self.start_server)
        self.root.after(POLL_INTERVAL_MS, self.poll_ready)
        self.root.mainloop()
        if self.launch_succeeded and self.server_thread is not None:
            self.server_thread.join()


def main() -> None:
    if SERVER_ARG in sys.argv:
        run_server_mode()
        return

    launcher = LauncherWindow()
    launcher.run()


if __name__ == "__main__":
    main()
