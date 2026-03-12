# QR Lite 图片二维码自动替换

[English](README.md) | [简体中文](README.zh-CN.md)

<p align="center">
  <a href="https://github.com/carsonte/QR-Lite/releases">
    <img alt="Download latest release" src="https://img.shields.io/badge/Download-Windows%20Release-1677FF?logo=github&logoColor=white">
  </a>
  <a href="https://github.com/carsonte/QR-Lite/stargazers">
    <img alt="GitHub stars" src="https://img.shields.io/github/stars/carsonte/QR-Lite?style=social">
  </a>
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Platform Windows" src="https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white">
  <img alt="Package PyInstaller" src="https://img.shields.io/badge/Package-PyInstaller-5A2D81">
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-green">
</p>

<p align="center">
  Replace QR codes in posters, marketing assets, and print-ready images locally.
  <br>
  Auto replace existing QR codes or manually place a new one into an empty frame.
</p>

<p align="center">
  <a href="https://github.com/carsonte/QR-Lite/releases"><strong>Download for Windows</strong></a>
  &middot;
  <a href="docs/releases/v1.0.0.md"><strong>Release Notes</strong></a>
  &middot;
  <a href="docs/launch-kit.md"><strong>Launch Kit</strong></a>
</p>

<p align="center">
  <img src="docs/images/quick-demo.gif" alt="QR Lite quick demo" width="960">
</p>

If QR Lite saves you time, a GitHub star helps more people discover it.

## Why QR Lite

- Fast QR replacement for posters, promo graphics, and print assets
- Two workflows: auto replace and manual placement
- Direct, simple UI copy designed for non-technical teammates
- Better support for `CMYK JPEG` source images
- Optimized for large images and lower-end laptops

## Features

- Automatically detects and replaces QR codes in source images
- Manual placement mode for empty boxes, white boxes, and placeholders
- Drag-and-resize blue box for placement fine-tuning
- Upload a QR image or generate one from text
- Crop away extra text under the uploaded QR image
- Preserves ICC profile / DPI / EXIF whenever possible
- Keeps output as `CMYK JPEG` when replacing an `RGB` QR code inside a `CMYK JPEG` source
- Large-image performance improvements for weaker machines

## Screenshots

<table>
  <tr>
    <td width="50%">
      <img src="docs/images/auto-success.png" alt="Auto replace mode">
    </td>
    <td width="50%">
      <img src="docs/images/manual-success.png" alt="Manual placement mode">
    </td>
  </tr>
  <tr>
    <td align="center">Auto replace mode</td>
    <td align="center">Manual placement mode</td>
  </tr>
</table>

## Download

For teammates, the recommended distribution format is a zipped `onedir` build from GitHub Releases.

Create the release zip locally with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release_zip.ps1 -Version v1.0.0
```

That command creates:

```text
output\release\QRLite-v1.0.0-windows-x64.zip
```

## Quick Start

### Requirements

- Python 3.11
- Windows recommended

### Run From Source

```powershell
git clone https://github.com/carsonte/QR-Lite.git
cd QR-Lite
python -m pip install -r requirements.txt
python launcher.py
```

If `python` is not available on your machine, use:

```powershell
py -m pip install -r requirements.txt
py launcher.py
```

After launch, a startup window appears first and then opens the browser automatically.
If the browser does not open, visit the local URL printed in the terminal, usually:

```text
http://127.0.0.1:7860
```

## How To Use

1. Decide whether the source image already has a QR code
2. Choose `Auto Replace` or `Manual Placement`
3. Upload the source image
4. Upload a new QR image or enter QR content as text
5. In manual mode, drag the blue box to the target area
6. Generate the result
7. Fine-tune and regenerate if needed
8. Download the final image

## Modes

### Auto Replace

Use this when the source image already contains a QR code.
QR Lite detects the QR region first, then replaces it with the new QR code.

### Manual Placement

Use this when the source image does not contain a QR code and only has an empty frame or placeholder.
Place the blue box where the new QR code should go, then generate the result.

## CMYK-Safe Output

When the source image is a `CMYK JPEG` and the output stays in `JPEG`, QR Lite uses a dedicated `CMYK` processing path to avoid unnecessary full-image round-trip color conversion.

This makes it more suitable for posters, print-ready graphics, and JPEG assets with embedded color profiles.

## Performance

QR Lite includes several optimizations for large images:

- QR detection runs on a downscaled preview first, then maps coordinates back
- Perspective blending only processes the local QR region instead of the whole image
- Heavy modules are loaded lazily to reduce startup stalls

## Packaging

The repository keeps one official packaging format: `onedir`

```powershell
.\build_exe.ps1
```

The packaged app is generated at:

```text
dist\QRLite\QRLite.exe
```

Notes:

- This is a directory-based build, not a single-file executable
- Share the whole `dist/QRLite` folder with teammates
- Zipping the full folder is the recommended distribution method

## Release Notes

- [v1.0.0 Release Notes](docs/releases/v1.0.0.md)

## Launch Support

- [Launch Kit](docs/launch-kit.md)
- [README screenshot generator](scripts/capture_readme_screenshots.py)

## Repository Layout

```text
app.py                 FastAPI server
launcher.py            Windows launcher window
qr_replace.py          QR detection and replacement core
web/                   Frontend page
branding/              Branding assets
docs/                  Screenshots and release notes
scripts/               Screenshot and release helpers
build_exe.ps1          Packaging script
QRLite.spec            PyInstaller spec
```

## GitHub Notes

- Build and test artifacts such as `dist/`, `build/`, `tmp_test/`, and `output/` are ignored
- Packaged builds should go to GitHub Releases, not repository history
- The project currently prioritizes stability, compatibility, and maintainability over maximum size reduction

## License

This project is licensed under the [MIT License](LICENSE).
