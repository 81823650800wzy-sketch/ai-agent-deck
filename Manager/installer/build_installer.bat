@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo  AI Agent Deck Manager - 安装包构建
echo ========================================
echo.

cd /d "%~dp0\.."

:: ── 1. 检查 PyInstaller 输出 ──
if not exist "dist\AI_Deck_Manager\AI_Deck_Manager.exe" (
    echo [!] 未找到 PyInstaller 打包输出
    echo     请先运行 build.bat 完成打包
    echo.
    pause
    exit /b 1
)

:: ── 2. 查找 Inno Setup 编译器 ──
set "ISCC="
for %%p in (
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 5\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
) do (
    if exist %%p set "ISCC=%%~p"
)

if "%ISCC%"=="" (
    echo [ERROR] 未找到 Inno Setup
    echo     请安装 Inno Setup 6: https://jrsoftware.org/isinfo.php
    echo.
    pause
    exit /b 1
)

echo [1/2] 使用编译器: %ISCC%
echo [2/2] 编译安装脚本...
echo.

:: ── 3. 编译 ──
"%ISCC%" "installer\setup.iss"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 安装包编译失败
    pause
    exit /b 1
)

:: ── 4. 完成 ──
echo.
echo ========================================
echo  安装包构建成功!
echo  输出: installer\output\AI_Deck_Manager_Setup_2.1.0.exe
echo ========================================
echo.

:: 打开输出目录
explorer "installer\output"

pause
