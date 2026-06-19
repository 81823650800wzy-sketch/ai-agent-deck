@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================
echo  AI Agent Deck Manager 启动
echo ================================
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 安装依赖（仅首次）
if not exist ".deps_installed" (
    echo [*] 首次运行，安装依赖...
    pip install -r requirements.txt
    if %errorlevel% equ 0 (
        echo installed > .deps_installed
    ) else (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 启动应用
echo [*] 启动 AI Agent Deck...
python run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 程序异常退出 (code: %errorlevel%)
    pause
)
