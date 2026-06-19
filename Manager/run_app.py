"""
AI Agent Deck - 应用程序启动脚本
现代化桌面应用
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from app.main import main

if __name__ == "__main__":
    main()
