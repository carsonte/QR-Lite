# QR Lite Launch Kit

Use this file as the public-facing checklist when you want more real users, more downloads, and more stars.

## GitHub Metadata

Suggested repository description:

`Local QR code replacement tool with auto-detect, manual placement, and CMYK-safe output.`

Suggested topics:

- `qr-code`
- `image-processing`
- `opencv`
- `fastapi`
- `pyinstaller`
- `windows`
- `cmyk`
- `design-tools`
- `marketing-tools`

## Release Setup

Suggested tag:

`v1.0.0`

Suggested release title:

`QR Lite v1.0.0 - Auto Replace, Manual Placement, CMYK-safe Output`

Suggested upload asset:

`QRLite-v1.0.0-windows-x64.zip`

Generate it locally with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release_zip.ps1 -Version v1.0.0
```

Release notes source:

- [v1.0.0 release notes](releases/v1.0.0.md)

## Short Launch Post

### English

QR Lite is a local tool for replacing QR codes in posters, promo graphics, and print-ready images.

- Auto replace when the source image already has a QR code
- Manual placement when the source image only has an empty frame
- CMYK-safe JPEG output for print workflows
- Built for teammates who just want clear buttons and fast results

Repo:
[https://github.com/carsonte/QR-Lite](https://github.com/carsonte/QR-Lite)

### 中文

QR Lite 是一个本地二维码替换工具，适合海报、宣传图、物料图这类需要快速改二维码的场景。

- 图里本来有二维码时，可以自动识别替换
- 图里没有二维码、只有空框时，可以手动画框添加
- 支持 `CMYK JPEG` 原图替换 `RGB` 二维码后继续保持 `CMYK JPEG`
- 按钮和提示词尽量写得直白，方便直接给同事用

仓库地址：
[https://github.com/carsonte/QR-Lite](https://github.com/carsonte/QR-Lite)

## Where To Share

- GitHub Releases
- X / Twitter
- V2EX
- 即刻 / 小红书 / 微信群这类适合发前后对比图的地方
- 设计师、运营、跨境、电商物料相关社群

## Launch Checklist

- Add the repository description
- Add the suggested topics
- Create the `v1.0.0` release
- Upload the Windows zip asset
- Reuse the GIF from `docs/images/quick-demo.gif`
- Post the short launch copy in English and Chinese
