# QR Lite

本地二维码替换工具，适合设计、运营、市场这类需要快速改图但不想进复杂设计软件的场景。

QR Lite can replace an existing QR code automatically, or add a new one manually when the source image only has an empty placeholder box.

## What It Does

- 自动识别原图中的二维码并替换
- 原图没有二维码时，支持手动画框添加
- 支持拖拽蓝框微调位置和大小
- 支持上传二维码图片，或直接输入内容生成二维码
- 支持先裁掉二维码图片下方说明文字
- 尽量保留原图的 ICC Profile / DPI / EXIF
- `CMYK JPEG` 原图替换 `RGB` 二维码后，输出仍可保持 `CMYK JPEG`
- 对大图做了性能优化，低配笔记本上的等待时间更短

## Typical Use Cases

- 海报、易拉宝、宣传图里的二维码换新
- 设计稿里只有空框，需要后补二维码
- 市场物料批量改二维码，但又不想每张图重新排版
- 需要尽量保留原图色彩信息的印刷类 JPEG 文件

## Two Modes

### 1. Auto Replace

适合原图里本来就有二维码的情况。  
软件会先自动识别二维码位置，再替换成新的二维码。

### 2. Manual Placement

适合原图里没有二维码、只有空框 / 白框 / 占位框的情况。  
你只需要在右侧预览图上把蓝框拖到目标位置，然后开始生成。

## Key Features

### Direct, Foolproof UI

界面文案已经按“下一步该做什么”重写，不走抽象产品话术，尽量降低误操作。

### CMYK-Safe Output

当原图是 `CMYK JPEG` 且输出格式保持 `JPEG` 时，程序会走专门的 `CMYK` 处理路径，尽量避免整张图来回转色。

### Performance Optimized

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

## Repository Layout

```text
app.py                 FastAPI server
launcher.py            Windows launcher window
qr_replace.py          QR detection and replacement core
web/                   Frontend page
branding/              Branding assets
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

暂未添加开源许可证。  
如果你准备对外公开分发，建议后续补一个明确的 `LICENSE` 文件。
