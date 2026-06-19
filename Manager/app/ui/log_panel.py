"""
AI Agent Deck - 增强日志面板
支持展开/折叠详情、日志级别过滤、搜索
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QComboBox, QTextEdit,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QColor, QTextCursor

from .modern_theme import ModernColors


class LogEntry(QFrame):
    """单条日志条目（可展开）"""

    def __init__(self, level: str, tag: str, message: str, detail: str = "", parent=None):
        super().__init__(parent)
        self.level = level
        self.tag = tag
        self.message = message
        self.detail = detail
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            LogEntry {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {ModernColors.BG_TERTIARY};
            }}
            LogEntry:hover {{
                background-color: {ModernColors.BG_TERTIARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 主行
        header = QHBoxLayout()
        header.setSpacing(8)

        # 时间
        time_str = QDateTime.currentDateTime().toString("HH:mm:ss")
        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_TERTIARY};
            font-family: "Cascadia Code", "Consolas", monospace;
            font-size: 10px;
        """)
        time_label.setFixedWidth(60)
        header.addWidget(time_label)

        # 级别标签
        level_colors = {
            "OK": ("#48C78E", "#1a2e1a"),
            "INFO": ("#3B82F6", "#1a1e2e"),
            "WARN": ("#F59E0B", "#2e2a1a"),
            "ERROR": ("#EF4444", "#2e1a1a"),
            "DEBUG": ("#8B5CF6", "#1e1a2e"),
        }
        fg, bg = level_colors.get(self.level, (ModernColors.TEXT_TERTIARY, ModernColors.BG_INPUT))

        level_badge = QLabel(self.level)
        level_badge.setFixedWidth(48)
        level_badge.setAlignment(Qt.AlignCenter)
        level_badge.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {fg}40;
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 10px;
            font-weight: bold;
            font-family: "Cascadia Code", "Consolas", monospace;
        """)
        header.addWidget(level_badge)

        # 标签
        if self.tag:
            tag_label = QLabel(f"[{self.tag}]")
            tag_label.setStyleSheet(f"""
                color: {ModernColors.TEXT_ACCENT};
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 10px;
            """)
            tag_label.setFixedWidth(70)
            header.addWidget(tag_label)

        # 消息
        msg_label = QLabel(self.message)
        msg_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_PRIMARY};
            font-size: 11px;
            font-family: "Cascadia Code", "Consolas", monospace;
        """)
        msg_label.setWordWrap(True)
        msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header.addWidget(msg_label)

        # 展开按钮（如果有详情）
        if self.detail:
            self.expand_btn = QPushButton("▼")
            self.expand_btn.setFixedSize(20, 20)
            self.expand_btn.setCursor(Qt.PointingHandCursor)
            self.expand_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {ModernColors.TEXT_TERTIARY};
                    border: none;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    color: {ModernColors.PRIMARY};
                }}
            """)
            self.expand_btn.clicked.connect(self._toggle_detail)
            header.addWidget(self.expand_btn)

        layout.addLayout(header)

        # 详情区域（默认隐藏）
        if self.detail:
            self.detail_widget = QTextEdit()
            self.detail_widget.setReadOnly(True)
            self.detail_widget.setMaximumHeight(150)
            self.detail_widget.setVisible(False)
            self.detail_widget.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {ModernColors.BG_INPUT};
                    color: {ModernColors.TEXT_SECONDARY};
                    border: 1px solid {ModernColors.BORDER};
                    border-radius: 6px;
                    padding: 8px;
                    font-family: "Cascadia Code", "Consolas", monospace;
                    font-size: 10px;
                }}
            """)
            self.detail_widget.setPlainText(self.detail)
            layout.addWidget(self.detail_widget)

    def _toggle_detail(self):
        """展开/折叠详情"""
        self._expanded = not self._expanded
        if hasattr(self, 'detail_widget'):
            self.detail_widget.setVisible(self._expanded)
            self.expand_btn.setText("▲" if self._expanded else "▼")


class LogPanel(QWidget):
    """增强日志面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._max_entries = 500
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)
        toolbar.setSpacing(8)

        # 标题
        title = QLabel("日志")
        title.setStyleSheet(f"""
            font-size: 13px;
            font-weight: bold;
            color: {ModernColors.TEXT_PRIMARY};
        """)
        toolbar.addWidget(title)

        # 级别过滤
        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部", "ERROR", "WARN", "INFO", "OK", "DEBUG"])
        self.level_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
        """)
        self.level_filter.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self.level_filter)

        # 搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernColors.BG_INPUT};
                color: {ModernColors.TEXT_PRIMARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
            QLineEdit:focus {{
                border-color: {ModernColors.PRIMARY};
            }}
        """)
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ModernColors.TEXT_TERTIARY};
                border: 1px solid {ModernColors.BORDER};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {ModernColors.TEXT_PRIMARY};
                border-color: {ModernColors.PRIMARY};
            }}
        """)
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        # 复制按钮
        copy_btn = QPushButton("复制全部")
        copy_btn.setStyleSheet(clear_btn.styleSheet())
        copy_btn.clicked.connect(self._copy_all)
        toolbar.addWidget(copy_btn)

        # 导出按钮
        export_btn = QPushButton("导出")
        export_btn.setStyleSheet(clear_btn.styleSheet())
        export_btn.clicked.connect(self._export_log)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # 日志列表
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {ModernColors.BG_PRIMARY};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {ModernColors.BG_PRIMARY};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {ModernColors.BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_layout.setSpacing(0)
        self.log_layout.addStretch()

        self.scroll_area.setWidget(self.log_container)
        layout.addWidget(self.scroll_area)

        # 统计栏
        stats_bar = QHBoxLayout()
        stats_bar.setContentsMargins(8, 4, 8, 4)

        self.stats_label = QLabel("0 条日志")
        self.stats_label.setStyleSheet(f"""
            color: {ModernColors.TEXT_TERTIARY};
            font-size: 10px;
        """)
        stats_bar.addWidget(self.stats_label)

        stats_bar.addStretch()

        self.error_count = QLabel("")
        self.error_count.setStyleSheet(f"color: #EF4444; font-size: 10px; font-weight: bold;")
        stats_bar.addWidget(self.error_count)

        self.warn_count = QLabel("")
        self.warn_count.setStyleSheet(f"color: #F59E0B; font-size: 10px; font-weight: bold;")
        stats_bar.addWidget(self.warn_count)

        layout.addLayout(stats_bar)

    def add_log(self, level: str, tag: str, message: str, detail: str = ""):
        """添加日志条目"""
        entry = LogEntry(level, tag, message, detail)
        self._entries.append(entry)

        # 插入到 stretch 之前
        self.log_layout.insertWidget(self.log_layout.count() - 1, entry)

        # 限制条目数
        while len(self._entries) > self._max_entries:
            old = self._entries.pop(0)
            old.deleteLater()

        # 应用过滤
        self._apply_filter()

        # 更新统计
        self._update_stats()

        # 自动滚动到底部
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _apply_filter(self):
        """应用过滤条件"""
        level_filter = self.level_filter.currentText()
        search_text = self.search_input.text().lower()

        for entry in self._entries:
            visible = True

            # 级别过滤
            if level_filter != "全部" and entry.level != level_filter:
                visible = False

            # 搜索过滤
            if search_text and search_text not in entry.message.lower() and search_text not in entry.tag.lower():
                visible = False

            entry.setVisible(visible)

    def _update_stats(self):
        """更新统计"""
        total = len(self._entries)
        errors = sum(1 for e in self._entries if e.level == "ERROR")
        warns = sum(1 for e in self._entries if e.level == "WARN")

        self.stats_label.setText(f"{total} 条日志")

        if errors:
            self.error_count.setText(f"● {errors} 错误")
        else:
            self.error_count.setText("")

        if warns:
            self.warn_count.setText(f"● {warns} 警告")
        else:
            self.warn_count.setText("")

    def clear(self):
        """清空日志"""
        for entry in self._entries:
            entry.deleteLater()
        self._entries.clear()
        self._update_stats()

    def _copy_all(self):
        """复制全部日志到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        lines = []
        for entry in self._entries:
            line = f"[{entry.level}] [{entry.tag}] {entry.message}"
            if entry.detail:
                line += f"\n  详情: {entry.detail}"
            lines.append(line)

        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            # 显示提示
            self.stats_label.setText("已复制到剪贴板！")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, self._update_stats)

    def _export_log(self):
        """导出日志"""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "ai-deck-log.txt", "Text Files (*.txt)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for entry in self._entries:
                    f.write(f"[{entry.level}] [{entry.tag}] {entry.message}\n")
                    if entry.detail:
                        f.write(f"  详情: {entry.detail}\n")

    def log(self, message: str, level: str = "INFO", tag: str = "", detail: str = ""):
        """便捷方法：添加日志"""
        self.add_log(level, tag, message, detail)

    def log_ok(self, message: str, tag: str = "", detail: str = ""):
        self.add_log("OK", tag, message, detail)

    def log_info(self, message: str, tag: str = "", detail: str = ""):
        self.add_log("INFO", tag, message, detail)

    def log_warn(self, message: str, tag: str = "", detail: str = ""):
        self.add_log("WARN", tag, message, detail)

    def log_error(self, message: str, tag: str = "", detail: str = ""):
        self.add_log("ERROR", tag, message, detail)

    def log_debug(self, message: str, tag: str = "", detail: str = ""):
        self.add_log("DEBUG", tag, message, detail)
