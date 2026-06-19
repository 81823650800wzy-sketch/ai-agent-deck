@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo  AI Agent Deck - 创建安装包
echo ========================================
echo.

cd /d "%~dp0"

:: 检查 Inno Setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
    echo [ERROR] 未找到 Inno Setup 6
    echo.
    echo 请先安装 Inno Setup 6:
    echo  https://jrsoftware.org/isinfo.php
    echo.
    pause
    exit /b 1
)

:: 检查 PyInstaller 输出
if not exist "..\Manager\dist\AI_Deck_Manager\AI_Deck_Manager.exe" (
    echo [ERROR] 未找到 PyInstaller 输出
    echo  请先运行 Manager\build.bat
    echo.
    pause
    exit /b 1
)

:: 创建输出目录
if not exist "..\dist" mkdir "..\dist"

:: 编译安装包
echo [*] 编译安装包...
"%ISCC%" /Q "AI_Deck_Manager.iss"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  安装包创建成功!
    echo  输出: dist\AI_Deck_Manager_Setup_2.1.0.exe
    echo ========================================
) else (
    echo.
    echo [ERROR] 安装包创建失败
)

pause
