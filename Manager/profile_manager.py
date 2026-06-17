"""
AI Agent Deck - Profile 管理器
管理应用对应的按键映射配置
"""

import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class KeyMapping:
    """单个按键映射"""
    id: str             # K1-K6
    display: str        # 屏幕显示名
    action: str         # 动作类型 (key_combo / command / open_url / script)
    value: str          # 动作值 (Ctrl+Z / cursor / https://...)


@dataclass
class Profile:
    """应用 Profile"""
    name: str                           # 显示名
    process_names: list[str]            # 匹配的进程名
    keys: list[KeyMapping] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "process_names": self.process_names,
            "keys": [{"id": k.id, "display": k.display,
                       "action": k.action, "value": k.value}
                      for k in self.keys]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Profile':
        keys = [KeyMapping(**k) for k in data.get("keys", [])]
        return cls(
            name=data["name"],
            process_names=data.get("process_names", []),
            keys=keys
        )


# ── 内置默认 Profile ───────────────────────────────────────

DEFAULT_PROFILES = [
    Profile(
        name="VSCode",
        process_names=["Code.exe"],
        keys=[
            KeyMapping("K1", "Undo",    "key_combo", "ctrl+z"),
            KeyMapping("K2", "Build",   "key_combo", "ctrl+shift+b"),
            KeyMapping("K3", "Debug",   "key_combo", "f5"),
            KeyMapping("K4", "Review",  "key_combo", "ctrl+shift+p"),
            KeyMapping("K5", "Terminal","key_combo", "ctrl+`"),
            KeyMapping("K6", "Explain", "key_combo", "ctrl+k ctrl+i"),
        ]
    ),
    Profile(
        name="Blender",
        process_names=["blender.exe"],
        keys=[
            KeyMapping("K1", "Bevel",   "key_combo", "ctrl+b"),
            KeyMapping("K2", "Extrude", "key_combo", "e"),
            KeyMapping("K3", "Grab",    "key_combo", "g"),
            KeyMapping("K4", "Modifier","key_combo", "ctrl+p"),
            KeyMapping("K5", "Render",  "key_combo", "f12"),
            KeyMapping("K6", "Explain", "key_combo", "f1"),
        ]
    ),
    Profile(
        name="KiCad",
        process_names=["kicad.exe", "pcbnew.exe", "eeschema.exe"],
        keys=[
            KeyMapping("K1", "Route",   "key_combo", "x"),
            KeyMapping("K2", "Move",    "key_combo", "m"),
            KeyMapping("K3", "Rotate",  "key_combo", "r"),
            KeyMapping("K4", "DRC",     "key_combo", "f8"),
            KeyMapping("K5", "Review",  "key_combo", "f9"),
            KeyMapping("K6", "Annotate","key_combo", "f6"),
        ]
    ),
    Profile(
        name="Word",
        process_names=["WINWORD.EXE"],
        keys=[
            KeyMapping("K1", "Save",    "key_combo", "ctrl+s"),
            KeyMapping("K2", "Bold",    "key_combo", "ctrl+b"),
            KeyMapping("K3", "Undo",    "key_combo", "ctrl+z"),
            KeyMapping("K4", "Find",    "key_combo", "ctrl+f"),
            KeyMapping("K5", "Print",   "key_combo", "ctrl+p"),
            KeyMapping("K6", "AI Write","key_combo", "ctrl+shift+i"),
        ]
    ),
    Profile(
        name="Chrome",
        process_names=["chrome.exe", "msedge.exe"],
        keys=[
            KeyMapping("K1", "New Tab",  "key_combo", "ctrl+t"),
            KeyMapping("K2", "Close",    "key_combo", "ctrl+w"),
            KeyMapping("K3", "Reopen",   "key_combo", "ctrl+shift+t"),
            KeyMapping("K4", "Bookmark", "key_combo", "ctrl+d"),
            KeyMapping("K5", "DevTools", "key_combo", "f12"),
            KeyMapping("K6", "Find",     "key_combo", "ctrl+f"),
        ]
    ),
    Profile(
        name="Default",
        process_names=["*"],  # 通配符，匹配所有未配置的应用
        keys=[
            KeyMapping("K1", "Copy",    "key_combo", "ctrl+c"),
            KeyMapping("K2", "Paste",   "key_combo", "ctrl+v"),
            KeyMapping("K3", "Undo",    "key_combo", "ctrl+z"),
            KeyMapping("K4", "Save",    "key_combo", "ctrl+s"),
            KeyMapping("K5", "Select",  "key_combo", "ctrl+a"),
            KeyMapping("K6", "Close",   "key_combo", "alt+f4"),
        ]
    ),
]


class ProfileManager:
    """Profile 管理器"""

    def __init__(self, profiles_dir: str | Path = None):
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent / "profiles"
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        self.profiles: dict[str, Profile] = {}
        self._process_index: dict[str, Profile] = {}
        self._load_all()

    def _load_all(self):
        """加载所有 Profile 文件"""
        # 先检查是否有自定义 Profile
        custom_files = list(self.profiles_dir.glob("*.json"))

        if not custom_files:
            # 首次运行，写入默认 Profile
            print("[ProfileManager] 首次运行，写入默认 Profile...")
            for profile in DEFAULT_PROFILES:
                self._save_to_file(profile)

        # 加载所有 Profile
        for f in self.profiles_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                profile = Profile.from_dict(data)
                self.profiles[profile.name] = profile
                # 建立进程名索引
                for pname in profile.process_names:
                    self._process_index[pname.lower()] = profile
            except Exception as e:
                print(f"[ProfileManager] 加载失败 {f}: {e}")

        print(f"[ProfileManager] 已加载 {len(self.profiles)} 个 Profile")

    def _save_to_file(self, profile: Profile):
        """保存单个 Profile 到文件"""
        path = self.profiles_dir / f"{profile.name.lower()}.json"
        path.write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def save_all(self):
        """保存所有 Profile"""
        for profile in self.profiles.values():
            self._save_to_file(profile)

    def get_profile_by_process(self, process_name: str) -> Profile | None:
        """根据进程名匹配 Profile"""
        pname_lower = process_name.lower()

        # 精确匹配
        if pname_lower in self._process_index:
            return self._process_index[pname_lower]

        # 通配符匹配 (Default)
        if "*" in self._process_index:
            return self._process_index["*"]

        return None

    def add_profile(self, profile: Profile):
        """添加/更新 Profile"""
        self.profiles[profile.name] = profile
        for pname in profile.process_names:
            self._process_index[pname.lower()] = profile
        self._save_to_file(profile)

    def delete_profile(self, name: str):
        """删除 Profile"""
        if name in self.profiles:
            profile = self.profiles.pop(name)
            for pname in profile.process_names:
                self._process_index.pop(pname.lower(), None)
            path = self.profiles_dir / f"{name.lower()}.json"
            path.unlink(missing_ok=True)

    def list_profiles(self) -> list[str]:
        """列出所有 Profile 名称"""
        return list(self.profiles.keys())
