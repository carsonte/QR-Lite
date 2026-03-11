# QR Lite

给设计、运营和市场同事用的本地二维码替换工具。  
Created by @husky

上传原图后，软件可以自动识别原二维码并替换；如果原图里没有二维码、只有空框或占位框，也可以直接手动画框放一个新的二维码。

## 现在这版包含什么

- 自动替换模式：适合原图里本来就有二维码的图片
- 手动添加模式：适合原图里没有二维码、只有空框/白框/占位框的图片
- 右侧蓝框拖拽微调：支持移动、缩放，并联动重新生成
- 上传二维码图片裁切：可以先把二维码下面的说明文字裁掉
- 直接输入内容生成二维码：不上传二维码图片也能用
- 保留原图输出信息：尽量保留 ICC Profile / DPI / EXIF
- `CMYK JPEG` 原图支持：替换 `RGB` 二维码后，输出仍可保持 `CMYK JPEG`
- 大图性能优化：4K 级原图的处理等待时间明显下降
- 启动和关闭优化：修复了关闭时报 `Tcl_AsyncDelete` 的问题

## 本地运行

```powershell
cd C:\Users\yanxiang2\Desktop\QR_lite
python -m pip install -r requirements.txt
python launcher.py
```

如果这台电脑里 `python` 命令不可用，就改成：

```powershell
py -m pip install -r requirements.txt
py launcher.py
```

启动后会先出现一个启动窗口，然后自动打开浏览器。  
如果浏览器没有自动打开，就手动访问终端里显示的本地地址，通常是：

```text
http://127.0.0.1:7860
```

## 页面使用

1. 先选模式
`图里有原二维码，帮我自动替换`
`图里没有原二维码，我手动放一个`

2. 上传原图

3. 上传新二维码图片，或者直接输入二维码内容

4. 手动模式下，先把右边蓝框拖到要放二维码的位置

5. 点开始处理
自动模式：`开始自动替换`
手动模式：`开始手动添加`

6. 看右边结果，不满意就继续拖蓝框或改参数再生成

7. 下载结果

## 输出和色彩说明

- 原图是 `RGB` 时，输出按当前选择的格式保存
- 原图是 `CMYK JPEG`，并且输出格式是 `SAME/JPEG` 时：
  - 新二维码就算是 `RGB` 图片，最终输出也会保持 `CMYK JPEG`
  - 软件会尽量沿用原图的 ICC Profile
- 如果你把输出格式改成 `PNG`，那就不保证还是 `CMYK`

## 正式打包

当前仓库只保留一个正式版打包方案：`onedir`

执行：

```powershell
cd C:\Users\yanxiang2\Desktop\QR_lite
.\build_exe.ps1
```

打包完成后，正式版在：

```text
dist\QRLite\QRLite.exe
```

## 打包版特点

- 只保留 `QRLite` 正式版，不再保留旧的多套打包变体
- 启动器会先显示启动窗口，再自动打开浏览器
- 空闲一段时间后，打包版会自动退出后台服务
- 打包后会自动清理一批没用的 OpenCV / reload / websocket 文件，减小体积

## GitHub 仓库建议

建议提交到 GitHub 的内容：

- `app.py`
- `launcher.py`
- `qr_replace.py`
- `web/`
- `branding/`
- `build_brand_assets.py`
- `build_exe.ps1`
- `QRLite.spec`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `.gitattributes`

建议不要提交到 GitHub 的内容：

- `dist/`
- `build/`
- `output/`
- `tmp_test/`
- `__pycache__/`
- `.gradio/`

这些已经写进 `.gitignore` 了，所以直接 `git add .` 也不会把它们带上去。

如果你要在 GitHub 发正式包，建议把 `dist/QRLite` 放到 GitHub Releases，不要直接提交进仓库历史。

## 说明

- 这是本地网页应用，不上传云端
- 双击 `QRLite.exe` 后，会在本机启动一个本地服务，再自动打开浏览器
- 因为包含 Python、OpenCV、NumPy 和图像依赖，体积不会特别小
- 当前版本优先保证稳定性、兼容性和处理效果，其次再继续压体积
