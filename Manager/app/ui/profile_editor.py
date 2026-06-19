"""
AI Agent Deck - Profile 编辑器 (PyQt5)
可视化创建和编辑按键映射 Profile
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QComboBox, QPushButton, QListWidget,
                              QListWidgetItem, QGroupBox, QFormLayout, QGridLayout,
                              QMessageBox, QFileDialog, QFrame, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

import json
import os
from pathlib import Path


class KeyEditorRow(QFrame):
    """单个按键编辑行"""
    def __init__(self, key_id: str, parent=None):
        super().__init__(parent)
        self.key_id = key_id
        self.setFrameStyle(QFrame.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Key ID label
        id_label = QLabel(self.key_id)
        id_label.setFixedWidth(30)
        id_label.setFont(QFont("Consolas", 10, QFont.Bold))
        layout.addWidget(id_label)

        # Display name
        self.display_edit = QLineEdit()
        self.display_edit.setPlaceholderText("显示名称")
        self.display_edit.setFixedWidth(100)
        layout.addWidget(self.display_edit)

        # Action type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["key_combo", "open_url", "command", "script"])
        self.type_combo.setFixedWidth(90)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        # Action value
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("如: ctrl+c, https://..., notepad")
        layout.addWidget(self.value_edit, 1)

    def _on_type_changed(self, action_type):
        placeholders = {
            "key_combo": "ctrl+c, alt+tab, f5",
            "open_url": "https://...",
            "command": "notepad, calc",
            "script": "path/to/script.py",
        }
        self.value_edit.setPlaceholderText(placeholders.get(action_type, ""))

    def get_data(self) -> dict:
        return {
            "id": self.key_id,
            "display": self.display_edit.text() or self.key_id,
            "action": self.type_combo.currentText(),
            "value": self.value_edit.text(),
        }

    def set_data(self, data: dict):
        self.display_edit.setText(data.get("display", ""))
        idx = self.type_combo.findText(data.get("action", "key_combo"))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.value_edit.setText(data.get("value", ""))


class ProfileEditorDialog(QDialog):
    """Profile 编辑对话框"""

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)
        self.profile = profile  # Profile object or None for new
        self.setWindowTitle("编辑 Profile" if profile else "新建 Profile")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self._setup_ui()
        if profile:
            self._load_profile(profile)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 基本信息
        info_group = QGroupBox("基本信息")
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Profile 名称")
        form.addRow("名称:", self.name_edit)

        self.process_edit = QLineEdit()
        self.process_edit.setPlaceholderText("用逗号分隔，如: code.exe, chrome.exe")
        form.addRow("进程名:", self.process_edit)
        info_group.setLayout(form)
        layout.addWidget(info_group)

        # 按键映射
        keys_group = QGroupBox("按键映射 (K1-K6)")
        keys_layout = QVBoxLayout()
        self.key_editors = []
        for i in range(6):
            editor = KeyEditorRow(f"K{i+1}")
            self.key_editors.append(editor)
            keys_layout.addWidget(editor)
        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        preview_btn = QPushButton("预览 JSON")
        preview_btn.clicked.connect(self._preview)
        btn_layout.addWidget(preview_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("保存")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _load_profile(self, profile):
        self.name_edit.setText(profile.name)
        if hasattr(profile, 'process_names'):
            self.process_edit.setText(", ".join(profile.process_names))
        for i, key in enumerate(profile.keys):
            if i < 6:
                self.key_editors[i].set_data({
                    "id": key.id,
                    "display": key.display,
                    "action": key.action,
                    "value": key.value,
                })

    def get_profile_data(self) -> dict:
        return {
            "name": self.name_edit.text() or "Untitled",
            "process_names": [p.strip() for p in self.process_edit.text().split(",") if p.strip()],
            "keys": [e.get_data() for e in self.key_editors],
        }

    def _preview(self):
        data = self.get_profile_data()
        text = json.dumps(data, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "JSON 预览", text)


class ProfileListManager(QDialog):
    """Profile 列表管理对话框"""

    profile_changed = pyqtSignal()  # Profile 被修改时发射

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self.pm = profile_manager
        self.setWindowTitle("Profile 管理")
        self.setMinimumSize(600, 450)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # 左侧列表
        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_edit)
        left.addWidget(self.list_widget)

        # 列表按钮
        btn_row = QHBoxLayout()

        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self._on_new)
        btn_row.addWidget(new_btn)

        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._on_edit)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(del_btn)

        left.addLayout(btn_row)

        io_row = QHBoxLayout()

        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._on_import)
        io_row.addWidget(import_btn)

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._on_export)
        io_row.addWidget(export_btn)

        left.addLayout(io_row)
        layout.addLayout(left, 2)

        # 右侧预览
        right = QVBoxLayout()
        right.addWidget(QLabel("Profile 预览"))
        self.preview_text = QLabel("选择一个 Profile 查看详情")
        self.preview_text.setWordWrap(True)
        self.preview_text.setAlignment(Qt.AlignTop)
        self.preview_text.setFrameStyle(QFrame.StyledPanel)
        right.addWidget(self.preview_text, 1)
        layout.addLayout(right, 1)

    def _refresh_list(self):
        self.list_widget.clear()
        if not self.pm:
            return
        for name in self.pm.list_profiles():
            self.list_widget.addItem(name)

    def _get_selected_name(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def _on_new(self):
        dlg = ProfileEditorDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_profile_data()
            if self.pm:
                from ..core.profile import Profile, KeyMapping
                keys = [KeyMapping(**k) for k in data["keys"]]
                profile = Profile(name=data["name"], keys=keys, process_names=data.get("process_names", []))
                self.pm.save_profile(profile)
                self._refresh_list()
                self.profile_changed.emit()

    def _on_edit(self):
        name = self._get_selected_name()
        if not name:
            return
        profile = self.pm.get_profile_by_name(name) if self.pm else None
        dlg = ProfileEditorDialog(profile=profile, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_profile_data()
            if self.pm:
                from ..core.profile import Profile, KeyMapping
                keys = [KeyMapping(**k) for k in data["keys"]]
                profile = Profile(name=data["name"], keys=keys, process_names=data.get("process_names", []))
                self.pm.save_profile(profile)
                self._refresh_list()
                self.profile_changed.emit()

    def _on_delete(self):
        name = self._get_selected_name()
        if not name:
            return
        reply = QMessageBox.question(self, "确认删除", f"确定删除 Profile '{name}'？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes and self.pm:
            self.pm.delete_profile(name)
            self._refresh_list()
            self.profile_changed.emit()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 Profile", "", "JSON (*.json)")
        if path and self.pm:
            try:
                self.pm.import_profile(path)
                self._refresh_list()
                self.profile_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "导入失败", str(e))

    def _on_export(self):
        name = self._get_selected_name()
        if not name or not self.pm:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 Profile", f"{name}.json", "JSON (*.json)")
        if path:
            try:
                self.pm.export_profile(name, path)
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))
