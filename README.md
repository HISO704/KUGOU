# 酷狗音乐转换器（Windows 便携版项目）

这是一个 Windows 桌面应用项目，界面使用 Python/Tkinter，普通音频转换使用 FFmpeg。

## 当前功能
- 添加多个音频文件，或递归扫描一个文件夹
- 显示文件格式、大小、处理状态
- 自定义 MP3 输出目录
- 选择三档 MP3 VBR 音质
- 批量转换、进度条、成功/失败统计和日志
- 输出文件自动避让同名文件，不覆盖已有结果
- 支持从应用旁边的 `ffmpeg\\bin\\ffmpeg.exe` 调用 FFmpeg
- 使用 PyInstaller `--onedir` 构建 Windows 便携目录

## 重要限制
- **本版本不解码 KGM/KGMA/KGG**。这些可能是酷狗专有或加密格式，应用会明确报告当前不支持，不会仅修改扩展名伪造 MP3。
- 目前可处理 FFmpeg 能正常解码的常见音频，例如 WAV、FLAC、M4A、AAC、OGG、OPUS、WMA 等。具体取决于所用 FFmpeg 构建。
- 这是便携文件夹，不是安装程序。分享或搬到另一台电脑时，请复制/压缩整个 `dist\\KugouToMP3` 文件夹，不能只复制 EXE。

## 在 Windows 11 上构建
1. 安装 Python 3.11 或更新的 Python 3，并在安装器中勾选 `Add python.exe to PATH`。
2. 解压本项目 ZIP。
3. 双击 `build.bat` 并等待完成。首次构建需要网络下载 PyInstaller。
4. 生成文件位于 `dist\\KugouToMP3\\KugouToMP3.exe`。
5. 将整个 `dist\\KugouToMP3` 文件夹复制到另一台 Windows 电脑测试。

## FFmpeg
如果希望便携目录无需用户另行安装 FFmpeg，请将**允许再分发且已审查许可的 Windows FFmpeg 构建**放到：

`ffmpeg\\bin\\ffmpeg.exe`

重新运行 `build.bat`。构建脚本会复制该文件到发布目录。若该构建使用了额外 DLL，也必须按对应发行说明一并携带。请根据实际 FFmpeg 二进制的构建配置填写 `THIRD_PARTY_NOTICES.txt`；模板不是许可合规证明。

官方许可说明：https://ffmpeg.org/legal.html
官方 PyInstaller 文档：https://pyinstaller.org/en/latest/operating-mode.html

## 测试建议
- 先用自己拥有且未加密的 WAV/FLAC/M4A 小文件测试。
- 检查输出 MP3 能否播放，文件大小是否合理。
- 在干净的 Windows 11 电脑或虚拟机测试，确认不依赖开发电脑已安装的 Python/FFmpeg。
- 如果 Windows 提示缺少系统运行库，请按报错检查相应 Microsoft Visual C++ Redistributable；不要从第三方 DLL 下载站下载单个 DLL。
