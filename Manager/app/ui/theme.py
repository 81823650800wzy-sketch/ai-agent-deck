"""
AI Agent Deck - 主题管理器
管理应用程序主题和样式
"""

import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class Theme:
    """主题配置"""
    name: str
    description: str
    colors: Dict[str, str]
    fonts: Dict[str, str]
    styles: Dict[str, str]


class ThemeManager:
    """
    主题管理器

    功能:
    - 加载/保存主题
    - 应用主题到 UI
    - 主题切换
    """

    def __init__(self, themes_dir: Optional[str] = None):
        if themes_dir:
            self.themes_dir = Path(themes_dir)
        else:
            self.themes_dir = Path(__file__).parent.parent.parent / "themes"

        self.themes: Dict[str, Theme] = {}
        self.current_theme: Optional[Theme] = None

        self._load_themes()

    def _load_themes(self):
        """加载所有主题"""
        if not self.themes_dir.exists():
            self.themes_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_themes()

        for file in self.themes_dir.glob("*.json"):
            try:
                theme = self._load_theme(file)
                if theme:
                    self.themes[theme.name] = theme
            except Exception as e:
                print(f"[ThemeManager] Load error {file}: {e}")

        # 设置默认主题
        if "Dark" in self.themes:
            self.current_theme = self.themes["Dark"]
        elif self.themes:
            self.current_theme = list(self.themes.values())[0]

    def _load_theme(self, file: Path) -> Optional[Theme]:
        """加载单个主题"""
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Theme(
            name=data['name'],
            description=data.get('description', ''),
            colors=data.get('colors', {}),
            fonts=data.get('fonts', {}),
            styles=data.get('styles', {})
        )

    def _create_default_themes(self):
        """创建默认主题"""
        defaults = [
            {
                "name": "Dark",
                "description": "深色主题",
                "colors": {
                    "background": "#1e1e1e",
                    "foreground": "#ffffff",
                    "accent": "#007acc",
                    "success": "#4caf50",
                    "warning": "#ff9800",
                    "error": "#f44336",
                    "card_bg": "#2d2d2d",
                    "card_border": "#404040",
                    "text_primary": "#ffffff",
                    "text_secondary": "#b0b0b0"
                },
                "fonts": {
                    "family": "Segoe UI",
                    "size": 10,
                    "title_size": 16,
                    "header_size": 12
                },
                "styles": {
                    "border_radius": 8,
                    "padding": 10,
                    "spacing": 5
                }
            },
            {
                "name": "Light",
                "description": "浅色主题",
                "colors": {
                    "background": "#f5f5f5",
                    "foreground": "#333333",
                    "accent": "#2196f3",
                    "success": "#4caf50",
                    "warning": "#ff9800",
                    "error": "#f44336",
                    "card_bg": "#ffffff",
                    "card_border": "#e0e0e0",
                    "text_primary": "#333333",
                    "text_secondary": "#666666"
                },
                "fonts": {
                    "family": "Segoe UI",
                    "size": 10,
                    "title_size": 16,
                    "header_size": 12
                },
                "styles": {
                    "border_radius": 8,
                    "padding": 10,
                    "spacing": 5
                }
            },
            {
                "name": "Neon",
                "description": "霓虹主题",
                "colors": {
                    "background": "#0a0a0a",
                    "foreground": "#00ff00",
                    "accent": "#ff00ff",
                    "success": "#00ff00",
                    "warning": "#ffff00",
                    "error": "#ff0000",
                    "card_bg": "#1a1a1a",
                    "card_border": "#00ff00",
                    "text_primary": "#00ff00",
                    "text_secondary": "#00cc00"
                },
                "fonts": {
                    "family": "Consolas",
                    "size": 10,
                    "title_size": 16,
                    "header_size": 12
                },
                "styles": {
                    "border_radius": 0,
                    "padding": 10,
                    "spacing": 5
                }
            }
        ]

        for theme_data in defaults:
            file = self.themes_dir / f"{theme_data['name'].lower()}.json"
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

    def get_theme(self, name: str) -> Optional[Theme]:
        """获取主题"""
        return self.themes.get(name)

    def set_theme(self, name: str):
        """设置当前主题"""
        theme = self.get_theme(name)
        if theme:
            self.current_theme = theme

    def list_themes(self) -> list:
        """列出所有主题"""
        return list(self.themes.keys())

    def get_stylesheet(self) -> str:
        """获取 Qt 样式表"""
        if not self.current_theme:
            return ""

        colors = self.current_theme.colors
        fonts = self.current_theme.fonts

        return f"""
        QMainWindow {{
            background-color: {colors.get('background', '#1e1e1e')};
        }}

        QLabel {{
            color: {colors.get('foreground', '#ffffff')};
            font-family: {fonts.get('family', 'Segoe UI')};
            font-size: {fonts.get('size', 10)}px;
        }}

        QPushButton {{
            background-color: {colors.get('accent', '#007acc')};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-family: {fonts.get('family', 'Segoe UI')};
            font-size: {fonts.get('size', 10)}px;
        }}

        QPushButton:hover {{
            background-color: {colors.get('accent', '#007acc')}dd;
        }}

        QPushButton:pressed {{
            background-color: {colors.get('accent', '#007acc')}aa;
        }}

        QFrame[frameShape="4"] {{
            color: {colors.get('card_border', '#404040')};
        }}

        QListWidget {{
            background-color: {colors.get('card_bg', '#2d2d2d')};
            color: {colors.get('foreground', '#ffffff')};
            border: 1px solid {colors.get('card_border', '#404040')};
            border-radius: 4px;
        }}

        QListWidget::item:selected {{
            background-color: {colors.get('accent', '#007acc')};
        }}

        QTextEdit {{
            background-color: {colors.get('card_bg', '#2d2d2d')};
            color: {colors.get('foreground', '#ffffff')};
            border: 1px solid {colors.get('card_border', '#404040')};
            border-radius: 4px;
            font-family: Consolas;
            font-size: 9px;
        }}
        """
