@echo off
REM 一键启动：Windows 版

REM 切到脚本所在目录（项目根目录）
cd /d "%~dp0"

REM 使用固定端口 5001
set PORT=5001

echo 正在启动 무신사 收藏价格监测...
echo 启动后请在浏览器打开: http://127.0.0.1:5001
echo.

REM 运行应用（需要已安装 Python 3）
py -3 app.py

echo.
echo 程序已退出，可以关闭此窗口。
pause

