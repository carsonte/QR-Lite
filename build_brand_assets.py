from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
SOURCE_ICON = BASE_DIR / "branding" / "source-icon.png"
WEB_DIR = BASE_DIR / "web"
OUTPUT_PNG = WEB_DIR / "app-icon.png"
OUTPUT_ICO = WEB_DIR / "app-icon.ico"
OUTPUT_SPLASH = BASE_DIR / "branding" / "startup-splash.png"


def _prepare_square_icon(source: Image.Image, canvas_size: int = 1024) -> Image.Image:
    src = source.convert("RGBA")
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    scale = min(canvas_size / float(src.width), canvas_size / float(src.height))
    new_w = max(1, int(round(src.width * scale)))
    new_h = max(1, int(round(src.height * scale)))
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)

    offset_x = (canvas_size - new_w) // 2
    offset_y = (canvas_size - new_h) // 2
    canvas.alpha_composite(resized, (offset_x, offset_y))
    return canvas


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def _build_splash(icon: Image.Image) -> Image.Image:
    splash = Image.new("RGBA", (960, 540), (244, 247, 253, 255))
    draw = ImageDraw.Draw(splash)

    draw.rounded_rectangle((48, 48, 912, 492), radius=36, fill=(255, 255, 255, 255), outline=(217, 232, 255, 255), width=2)

    icon_large = icon.resize((220, 220), Image.Resampling.LANCZOS)
    splash.alpha_composite(icon_large, (110, 160))

    title_font = _load_font(54)
    body_font = _load_font(24)
    small_font = _load_font(20)

    draw.text((390, 175), "QR Lite", font=title_font, fill=(23, 78, 166, 255))
    draw.text((390, 248), "正在启动，请稍候...", font=body_font, fill=(63, 87, 126, 255))
    draw.text((390, 290), "启动时可能需要几秒钟", font=body_font, fill=(99, 118, 153, 255))
    draw.text((390, 356), "Created by @carsonte", font=small_font, fill=(109, 121, 145, 255))
    return splash


def main() -> None:
    if not SOURCE_ICON.exists():
        raise FileNotFoundError(f"Source icon not found: {SOURCE_ICON}")

    WEB_DIR.mkdir(parents=True, exist_ok=True)

    icon = _prepare_square_icon(Image.open(SOURCE_ICON))
    web_png = icon.resize((512, 512), Image.Resampling.LANCZOS)
    web_png.save(OUTPUT_PNG, format="PNG")

    icon.save(
        OUTPUT_ICO,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    splash = _build_splash(icon)
    splash.save(OUTPUT_SPLASH, format="PNG")

    print(f"Created {OUTPUT_PNG}")
    print(f"Created {OUTPUT_ICO}")
    print(f"Created {OUTPUT_SPLASH}")


if __name__ == "__main__":
    main()
