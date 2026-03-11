from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import Browser, Page, Playwright, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "images"
TMP_DIR = ROOT / "tmp_test"
PORT = 7888
BASE_URL = f"http://127.0.0.1:{PORT}"
VIEWPORT = {"width": 1440, "height": 1600}
DEMO_GIF = DOCS_DIR / "quick-demo.gif"


def wait_ready(timeout_seconds: float = 30.0) -> None:
    started = time.perf_counter()
    while time.perf_counter() - started < timeout_seconds:
        try:
            response = requests.get(f"{BASE_URL}/", timeout=0.5)
            if response.status_code == 200 and "QR Lite" in response.text:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError("QR Lite did not become ready in time.")


def stop_server(proc: subprocess.Popen[str]) -> None:
    try:
        requests.post(f"{BASE_URL}/api/shutdown", timeout=3)
    except requests.RequestException:
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def open_page(browser: Browser) -> Page:
    page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
    page.goto(BASE_URL, wait_until="networkidle")
    page.locator(".hero").wait_for()
    page.wait_for_timeout(500)
    return page


def screenshot_layout(browser: Browser) -> None:
    page = open_page(browser)
    page.screenshot(path=str(DOCS_DIR / "layout-desktop.png"), full_page=True)
    page.close()


def screenshot_auto_success(browser: Browser) -> None:
    page = open_page(browser)
    page.locator("#source_image").set_input_files(str(TMP_DIR / "source_auto.png"))
    page.locator("#replacement_qr_image").set_input_files(str(TMP_DIR / "new.png"))
    page.locator("#submit_btn").click()
    page.locator("#download").wait_for(state="visible", timeout=30000)
    page.locator("#msg.success").wait_for(timeout=30000)
    page.wait_for_timeout(800)
    page.screenshot(path=str(DOCS_DIR / "auto-success.png"), full_page=True)
    page.close()


def screenshot_manual_success(browser: Browser) -> None:
    page = open_page(browser)
    page.locator("#placement_mode_manual").check()
    page.locator("#source_image").set_input_files(str(TMP_DIR / "source_manual.png"))
    page.locator("#replacement_qr_image").set_input_files(str(TMP_DIR / "new.png"))
    page.locator("#adjust_box").wait_for(state="visible", timeout=15000)
    page.locator("#submit_btn").click()
    page.locator("#download").wait_for(state="visible", timeout=30000)
    page.locator("#msg.success").wait_for(timeout=30000)
    page.wait_for_timeout(800)
    page.screenshot(path=str(DOCS_DIR / "manual-success.png"), full_page=True)
    page.close()


def build_demo_gif() -> None:
    crop_box = (24, 16, 1416, 1140)
    target_size = (1200, 968)
    frame_paths = [
        DOCS_DIR / "layout-desktop.png",
        DOCS_DIR / "auto-success.png",
        DOCS_DIR / "manual-success.png",
    ]
    frames = []
    for path in frame_paths:
        frame = Image.open(path).convert("RGBA").crop(crop_box).resize(target_size, Image.Resampling.LANCZOS)
        frames.append(frame.convert("RGB").quantize(colors=96, method=Image.MEDIANCUT))

    frames[0].save(
        DEMO_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=[1600, 1800, 1800],
        loop=0,
        optimize=True,
        disposal=2,
    )


def capture_all(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    try:
        screenshot_layout(browser)
        screenshot_auto_success(browser)
        screenshot_manual_success(browser)
        build_demo_gif()
    finally:
        browser.close()


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["QR_LITE_NO_BROWSER"] = "1"
    env["QR_LITE_IDLE_EXIT_SECONDS"] = "0"
    proc = subprocess.Popen(
        [sys.executable, "-c", f"import app; app.launch_app(open_browser=False, port={PORT})"],
        cwd=str(ROOT),
        env=env,
    )
    try:
        wait_ready()
        with sync_playwright() as playwright:
            capture_all(playwright)
    finally:
        stop_server(proc)


if __name__ == "__main__":
    main()
