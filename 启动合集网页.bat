@echo off
cd /d "%~dp0"
title 裁判学习平台 - 本地服务
echo ================================================
echo   裁判学习平台 - 本地服务已启动
echo ================================================
echo.
echo   本机访问:  http://127.0.0.1:8808/index.html
echo.
echo   手机/教室其他设备(连同一个Wi-Fi)访问:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do echo             http:%%a:8808/index.html
echo.
echo   停止服务: 直接关闭本窗口即可
echo   (平时不上网分享的话, 其实不用本服务, 直接双击 index.html 就能看)
echo.
echo 正在打开浏览器...
start "" "http://127.0.0.1:8808/index.html"
python scripts/range_server.py 8808
if errorlevel 1 (
  echo.
  echo [提示] 8808端口被占用, 可能服务已经在运行。若浏览器能打开页面, 无需处理。
  pause
)
