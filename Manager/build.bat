@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo  AI Agent Deck Manager - 完整构建
echo ========================================
echo.

cd /d "%~dp0"

:: ── 1. 检查 Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: ── 2. 安装依赖 ──
echo [1/5] 安装依赖...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

:: ── 3. 复制固件 ──
echo [2/5] 复制固件文件...
if not exist "firmware" mkdir firmware
set "FIRMWARE_DIR=..\Firmware\build"

if exist "%FIRMWARE_DIR%\ai_agent_deck.bin" (
    copy /Y "%FIRMWARE_DIR%\ai_agent_deck.bin" "firmware\" >nul
    copy /Y "%FIRMWARE_DIR%\bootloader\bootloader.bin" "firmware\" >nul
    copy /Y "%FIRMWARE_DIR%\partition_table\partition-table.bin" "firmware\" >nul
    copy /Y "%FIRMWARE_DIR%\ota_data_initial.bin" "firmware\" >nul
    echo    固件已复制到 firmware\
) else (
    echo    [WARN] 固件未编译，跳过 (先运行 idf.py build)
)

:: ── 4. PyInstaller 打包 ──
echo [3/5] PyInstaller 打包...
if exist "dist\AI_Deck_Manager" rmdir /s /q "dist\AI_Deck_Manager"
if exist "build" rmdir /s /q "build"

pyinstaller AI_Deck_Manager.spec --clean --noconfirm 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller 打包失败
    pause
    exit /b 1
)

:: ── 5. 复制额外文件到 dist ──
echo [4/5] 复制额外文件...
copy /Y "LICENSE" "dist\AI_Deck_Manager\" >nul 2>&1
copy /Y "README.md" "dist\AI_Deck_Manager\" >nul 2>&1
if exist "profiles" xcopy /E /Y /I "profiles" "dist\AI_Deck_Manager\profiles" >nul 2>&1
if exist "firmware" xcopy /E /Y /I "firmware" "dist\AI_Deck_Manager\firmware" >nul 2>&1

:: ── 6. 统计 ──
echo [5/5] 构建完成!
echo.
echo ========================================
echo  输出目录: dist\AI_Deck_Manager\
echo  可执行文件: dist\AI_Deck_Manager\AI_Deck_Manager.exe
echo ========================================

:: 计算大小
for /f %%a in ('powershell -command "(Get-ChildItem -Recurse 'dist\AI_Deck_Manager' | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SIZE=%%a
echo  总大小: %SIZE% MB

echo.
echo  下一步:
echo    1. 运行 dist\AI_Deck_Manager\AI_Deck_Manager.exe 测试
echo    2. 运行 installer\build_installer.bat 创建安装包
echo.
pause
