@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ContentPilot

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没有找到 Python。请先去 https://www.python.org 安装 Python 3.10 或以上，安装时勾选 "Add Python to PATH"。
    pause
    exit /b 1
)

echo [1/2] 正在安装依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请把上面的报错信息截图反馈。
    pause
    exit /b 1
)

echo.
echo [2/2] 正在启动，稍后浏览器打开 http://127.0.0.1:8000
echo 关闭此窗口即可停止服务。
echo.
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
python -m uvicorn app.main:app
pause
