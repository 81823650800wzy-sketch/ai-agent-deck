"""
AI Agent Deck - Profile 管理器
管理按键映射配置
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class KeyMapping:
    """按键映射"""
    id: str
    display: str
    action: str
    value: str = ""


@dataclass
class Profile:
    """Profile 配置"""
    name: str
    keys: List[KeyMapping] = field(default_factory=list)
    process_names: List[str] = field(default_factory=list)
    description: str = ""
    icon: str = ""
    theme: str = "default"


class ProfileManager:
    """
    Profile 管理器

    功能:
    - 加载/保存 Profile 配置
    - 根据进程名匹配 Profile
    - Profile 导入/导出
    """

    def __init__(self, profiles_dir: Optional[str] = None):
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            self.profiles_dir = Path(__file__).parent.parent.parent / "profiles"

        self.profiles: Dict[str, Profile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """加载所有 Profile"""
        if not self.profiles_dir.exists():
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_profiles()

        for file in self.profiles_dir.glob("*.json"):
            try:
                profile = self._load_profile(file)
                if profile:
                    self.profiles[profile.name] = profile
            except Exception as e:
                print(f"[ProfileManager] Load error {file}: {e}")

    def _load_profile(self, file: Path) -> Optional[Profile]:
        """加载单个 Profile"""
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        keys = []
        for k in data.get('keys', []):
            keys.append(KeyMapping(
                id=k['id'],
                display=k['display'],
                action=k.get('action', 'key_combo'),
                value=k.get('value', '')
            ))

        return Profile(
            name=data['name'],
            keys=keys,
            process_names=data.get('process_names', []),
            description=data.get('description', ''),
            icon=data.get('icon', ''),
            theme=data.get('theme', 'default')
        )

    def _create_default_profiles(self):
        """创建默认 Profile"""
        defaults = [
            {
                "name": "Default",
                "description": "默认按键映射",
                "process_names": [],
                "keys": [
                    {"id": "K1", "display": "Copy", "action": "key_combo", "value": "ctrl+c"},
                    {"id": "K2", "display": "Paste", "action": "key_combo", "value": "ctrl+v"},
                    {"id": "K3", "display": "Undo", "action": "key_combo", "value": "ctrl+z"},
                    {"id": "K4", "display": "Save", "action": "key_combo", "value": "ctrl+s"},
                    {"id": "K5", "display": "Select All", "action": "key_combo", "value": "ctrl+a"},
                    {"id": "K6", "display": "Close", "action": "key_combo", "value": "ctrl+w"}
                ]
            },
            {
                "name": "VSCode",
                "description": "Visual Studio Code",
                "process_names": ["Code.exe"],
                "keys": [
                    {"id": "K1", "display": "Undo", "action": "key_combo", "value": "ctrl+z"},
                    {"id": "K2", "display": "Build", "action": "key_combo", "value": "ctrl+b"},
                    {"id": "K3", "display": "Debug", "action": "key_combo", "value": "F5"},
                    {"id": "K4", "display": "Format", "action": "key_combo", "value": "shift+alt+f"},
                    {"id": "K5", "display": "Terminal", "action": "key_combo", "value": "ctrl+`"},
                    {"id": "K6", "display": "Explorer", "action": "key_combo", "value": "ctrl+shift+e"}
                ]
            },
            {
                "name": "Blender",
                "description": "Blender 3D",
                "process_names": ["blender.exe"],
                "keys": [
                    {"id": "K1", "display": "Play", "action": "key_combo", "value": "space"},
                    {"id": "K2", "display": "Stop", "action": "key_combo", "value": "esc"},
                    {"id": "K3", "display": "Frame-", "action": "key_combo", "value": "left"},
                    {"id": "K4", "display": "Frame+", "action": "key_combo", "value": "right"},
                    {"id": "K5", "display": "Render", "action": "key_combo", "value": "F12"},
                    {"id": "K6", "display": "Save", "action": "key_combo", "value": "ctrl+s"}
                ]
            },
            {
                "name": "Chrome",
                "description": "Google Chrome",
                "process_names": ["chrome.exe"],
                "keys": [
                    {"id": "K1", "display": "Back", "action": "key_combo", "value": "alt+left"},
                    {"id": "K2", "display": "Forward", "action": "key_combo", "value": "alt+right"},
                    {"id": "K3", "display": "Refresh", "action": "key_combo", "value": "F5"},
                    {"id": "K4", "display": "Bookmark", "action": "key_combo", "value": "ctrl+d"},
                    {"id": "K5", "display": "New Tab", "action": "key_combo", "value": "ctrl+t"},
                    {"id": "K6", "display": "DevTools", "action": "key_combo", "value": "F12"}
                ]
            }
        ]

        for profile_data in defaults:
            file = self.profiles_dir / f"{profile_data['name'].lower()}.json"
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)

    def get_profile_by_name(self, name: str) -> Optional[Profile]:
        """根据名称获取 Profile"""
        return self.profiles.get(name)

    def get_profile_by_process(self, process_name: str) -> Optional[Profile]:
        """根据进程名获取 Profile"""
        for profile in self.profiles.values():
            if process_name in profile.process_names:
                return profile
        return self.get_profile_by_name("Default")

    def list_profiles(self) -> List[str]:
        """列出所有 Profile 名称"""
        return list(self.profiles.keys())

    def save_profile(self, profile: Profile):
        """保存 Profile"""
        self.profiles[profile.name] = profile

        file = self.profiles_dir / f"{profile.name.lower()}.json"
        data = {
            "name": profile.name,
            "description": profile.description,
            "process_names": profile.process_names,
            "keys": [
                {"id": k.id, "display": k.display, "action": k.action, "value": k.value}
                for k in profile.keys
            ]
        }

        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def delete_profile(self, name: str):
        """删除 Profile"""
        if name in self.profiles:
            del self.profiles[name]

            file = self.profiles_dir / f"{name.lower()}.json"
            if file.exists():
                file.unlink()

    def export_profile(self, name: str, file_path: str):
        """导出 Profile"""
        profile = self.get_profile_by_name(name)
        if profile:
            data = {
                "name": profile.name,
                "description": profile.description,
                "process_names": profile.process_names,
                "keys": [
                    {"id": k.id, "display": k.display, "action": k.action, "value": k.value}
                    for k in profile.keys
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def import_profile(self, file_path: str) -> Optional[Profile]:
        """导入 Profile"""
        try:
            profile = self._load_profile(Path(file_path))
            if profile:
                self.profiles[profile.name] = profile
                self.save_profile(profile)
            return profile
        except Exception as e:
            print(f"[ProfileManager] Import error: {e}")
            return None
