@echo off
echo ========================================
echo   AI Agent Deck 管理软件
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 pynput 是否安装
python -c "import pynput" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install pynput
)

echo 启动管理软件...
echo.
python ai_deck_manager.py

pause
