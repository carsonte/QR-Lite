# QR Lite

<p align="center">
  <img src="docs/images/layout-desktop.png" alt="QR Lite preview" width="960">
</p>

<p align="center">
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Platform Windows" src="https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white">
  <img alt="Package PyInstaller" src="https://img.shields.io/badge/Package-PyInstaller-5A2D81">
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-green">
</p>

本地二维码替换工具，适合设计、运营、市场这类需要快速改图但不想进复杂设计软件的场景。

QR Lite can replace an existing QR code automatically, or add a new one manually when the source image only has an empty placeholder box.

## Why QR Lite

- 不需要复杂设计软件
- 原图有二维码时可以自动识别并替换
- 原图没有二维码时也能手动画框补上
- 文案和流程都偏“傻瓜式”，适合直接给同事使用
- 对 `CMYK JPEG` 原图更友好，适合印刷类物料修改

## Features

- 自动识别原图中的二维码并替换
- 手动放置模式，适合空框 / 白框 / 占位框
- 拖拽蓝框微调位置和大小
- 上传二维码图片，或直接输入内容生成二维码
- 支持裁掉二维码图片下方说明文字
- 尽量保留 ICC Profile / DPI / EXIF
- `CMYK JPEG` 原图替换 `RGB` 二维码后，输出仍可保持 `CMYK JPEG`
- 大图性能优化，低配笔记本上的等待时间更短

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
    <td align="center">自动替换：适合原图里本来就有二维码</td>
    <td align="center">手动放置：适合只有空框或占位框</td>
  </tr>
</table>

## Two Modes

### Auto Replace

适合原图里本来就有二维码的情况。  
软件会先自动识别二维码位置，再替换成新的二维码。

### Manual Placement

适合原图里没有二维码、只有空框 / 白框 / 占位框的情况。  
你只需要在右侧预览图上把蓝框拖到目标位置，然后开始生成。

## CMYK-Safe Output

当原图是 `CMYK JPEG` 且输出格式保持 `JPEG` 时，程序会走专门的 `CMYK` 处理路径，尽量避免整张图来回转色。  
这让它更适合海报、印刷物料和已经带色彩配置的设计成品图。

## Performance

针对大图场景做过专项优化：

- 自动识别先在缩小图上做，再回推原尺寸坐标
- 透视贴图只处理二维码附近局部区域，不再每次对整张图做大范围混合
- 启动时延后加载重模块，减少打开软件时的卡顿感

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

如果本机没有 `python` 命令，可以改用：

```powershell
py -m pip install -r requirements.txt
py launcher.py
```

启动后会先显示启动窗口，然后自动打开浏览器。  
如果浏览器没有自动打开，可以手动访问终端输出的本地地址，通常是：

```text
http://127.0.0.1:7860
```

## How To Use

1. 先判断原图里有没有原二维码
2. 选择 `自动替换` 或 `手动放一个`
3. 上传原图
4. 上传新二维码图片，或者直接输入二维码内容
5. 手动模式下，先把右侧蓝框拖到目标位置
6. 点击开始处理
7. 不满意就继续微调，再重新生成
8. 下载结果

## Packaging

仓库当前只保留一个正式打包方案：`onedir`

```powershell
.\build_exe.ps1
```

打包完成后，正式版在：

```text
dist\QRLite\QRLite.exe
```

注意：

- 这是目录版，不是单文件版
- 分发给同事时，要发整个 `dist/QRLite` 文件夹
- 更推荐把整个目录打成 zip 再发

## Release Notes

首个正式版本文案已经整理在：

- [v1.0.0 Release Notes](docs/releases/v1.0.0.md)

如果你准备在 GitHub Releases 发正式包，可以直接复用这份文案。

## Repository Layout

```text
app.py                 FastAPI server
launcher.py            Windows launcher window
qr_replace.py          QR detection and replacement core
web/                   Frontend page
branding/              Branding assets
docs/                  Screenshots and release notes
build_exe.ps1          Packaging script
QRLite.spec            PyInstaller spec
```

## GitHub Notes

- `dist/`、`build/`、`tmp_test/`、`output/` 这些构建和测试产物不会提交到仓库
- 正式包更适合放在 GitHub Releases，而不是直接提交进仓库历史
- 当前仓库优先保证稳定性、兼容性和可维护性，其次才是继续压缩体积

## Current Status

当前版本已经包含这些修复和优化：

- 手动添加二维码模式
- 模式切换状态修复
- 启动卡住问题修复
- 关闭时报 `Tcl_AsyncDelete` 修复
- 大图性能优化
- `CMYK + RGB 二维码` 保色处理
- 打包体积与依赖清理优化

## License

This project is licensed under the [MIT License](LICENSE).
