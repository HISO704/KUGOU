@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ====================================================
echo   酷狗音乐转换器 - Windows 便携版构建
echo ====================================================

where py >nul 2>nul
if errorlevel 1 (
  echo 未找到 Python。请先安装 Python 3.11 或更新版本，并勾选 Add python.exe to PATH。
  pause
  exit /b 1
)

py -m pip --version >nul 2>nul
if errorlevel 1 (
  echo Python pip 不可用，请修复 Python 安装后重试。
  pause
  exit /b 1
)

echo 正在安装/更新 PyInstaller...
py -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo PyInstaller 安装失败。请检查网络连接后重试。
  pause
  exit /b 1
)

if exist "ffmpeg\bin\ffmpeg.exe" (
  echo 已找到项目内 FFmpeg。
) else (
  echo 注意：未放入 FFmpeg，程序仍可构建，但转换时需要系统 PATH 中有 ffmpeg。
)

if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "KugouToMP3.spec" del /q "KugouToMP3.spec"

py -m PyInstaller --noconfirm --clean --onedir --windowed --name KugouToMP3 src\app.py
if errorlevel 1 (
  echo 构建失败。请拍下本窗口的错误信息发给助手。
  pause
  exit /b 1
)

if exist "ffmpeg\bin\ffmpeg.exe" (
  if not exist "dist\KugouToMP3\ffmpeg\bin" mkdir "dist\KugouToMP3\ffmpeg\bin"
  copy /y "ffmpeg\bin\ffmpeg.exe" "dist\KugouToMP3\ffmpeg\bin\ffmpeg.exe" >nul
  if exist "ffmpeg\bin\ffprobe.exe" copy /y "ffmpeg\bin\ffprobe.exe" "dist\KugouToMP3\ffmpeg\bin\ffprobe.exe" >nul
)
if exist "THIRD_PARTY_NOTICES.txt" copy /y "THIRD_PARTY_NOTICES.txt" "dist\KugouToMP3\THIRD_PARTY_NOTICES.txt" >nul
if exist "README_DISTRIBUTION.txt" copy /y "README_DISTRIBUTION.txt" "dist\KugouToMP3\README_DISTRIBUTION.txt" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\KugouToMP3\*' -DestinationPath 'dist\KugouToMP3_Portable_Windows.zip' -Force"
if errorlevel 1 echo 警告：ZIP 自动打包失败，但便携文件夹仍在 dist\KugouToMP3 中。

echo.
echo 构建完成：
echo   dist\KugouToMP3\KugouToMP3.exe
echo   dist\KugouToMP3_Portable_Windows.zip
echo 请复制整个文件夹或 ZIP，不要只复制 EXE。
pause
