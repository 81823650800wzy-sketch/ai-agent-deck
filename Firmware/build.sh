#!/bin/bash
# AI Agent Deck V1.0 - 构建脚本
# 用法: bash build.sh [flash] [monitor]

set -e

# ESP-IDF 环境
export IDF_PATH="/d/Espressif/frameworks/esp-idf-v5.5.4"
export IDF_PYTHON_ENV_PATH="/d/Espressif/python_env/idf5.5_py3.12_env"
export ESP_ROM_ELF_DIR="/d/Espressif/tools/esp-rom-elfs"

# 工具路径
export PATH="/d/Espressif/tools/cmake/3.30.2/bin:/d/Espressif/tools/ninja/1.12.1:/d/Espressif/tools/xtensa-esp-elf/esp-14.2.0_20260121/xtensa-esp-elf/bin:/d/Espressif/python_env/idf5.5_py3.12_env/Scripts:$PATH"

cd "$(dirname "$0")"

echo "========================================"
echo " AI Agent Deck V1.0 - Build"
echo "========================================"

# 检查参数
case "${1:-build}" in
    build)
        echo "[1/2] Setting target to ESP32-S3..."
        python "$IDF_PATH/tools/idf.py" set-target esp32s3
        echo "[2/2] Building..."
        python "$IDF_PATH/tools/idf.py" build
        echo ""
        echo "✅ 构建成功!"
        echo "固件: build/ai_agent_deck.bin"
        echo ""
        echo "烧录: bash build.sh flash"
        echo "烧录+监控: bash build.sh flash_monitor"
        ;;
    flash)
        echo "烧录中... (按住BOOT键插入USB)"
        python "$IDF_PATH/tools/idf.py" -p "${2:-COM3}" flash
        echo "✅ 烧录完成!"
        ;;
    monitor)
        echo "串口监控 (Ctrl+C 退出)"
        python "$IDF_PATH/tools/idf.py" -p "${2:-COM3}" monitor
        ;;
    flash_monitor)
        echo "烧录+监控 (按住BOOT键插入USB)"
        python "$IDF_PATH/tools/idf.py" -p "${2:-COM3}" flash monitor
        ;;
    clean)
        echo "清理构建目录..."
        rm -rf build
        echo "✅ 清理完成!"
        ;;
    *)
        echo "用法: bash build.sh [build|flash|monitor|flash_monitor|clean] [COM端口]"
        echo ""
        echo "  build          - 编译固件 (默认)"
        echo "  flash [COMx]   - 烧录固件"
        echo "  monitor [COMx] - 串口监控"
        echo "  flash_monitor  - 烧录+监控"
        echo "  clean          - 清理构建目录"
        ;;
esac
