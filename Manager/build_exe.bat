@echo off
echo ========================================
echo   打包 AI Agent Deck 管理软件
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    pause
    exit /b 1
)

REM 安装打包工具
echo [1/3] 安装 PyInstaller...
pip install pyinstaller

REM 打包
echo.
echo [2/3] 正在打包...
pyinstaller --onefile --windowed --name "AI_Deck_Manager" ai_deck_manager.py

echo.
echo [3/3] 完成!
echo.
echo 可执行文件位置: dist\AI_Deck_Manager.exe
echo.
pause
