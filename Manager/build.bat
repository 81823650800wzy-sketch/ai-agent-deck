@echo off
chcp 65001 >nul
echo ================================
echo  AI Agent Deck - 打包构建
echo ================================
echo.

cd /d "%~dp0"

:: 检查 PyInstaller
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller 未安装，正在安装...
    pip install pyinstaller
)

:: 清理旧构建
if exist dist\AI_Deck_Manager rmdir /s /q dist\AI_Deck_Manager
if exist build rmdir /s /q build

echo [*] 开始打包...
pyinstaller AI_Deck_Manager.spec --clean --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo [OK] 打包完成！
    echo 输出目录: dist\AI_Deck_Manager\
    echo 可执行文件: dist\AI_Deck_Manager\AI_Deck_Manager.exe
) else (
    echo.
    echo [ERROR] 打包失败，请检查错误信息
)

pause
