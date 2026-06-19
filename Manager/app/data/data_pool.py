"""
AI Agent Deck - 数据池
存储和管理用户行为数据
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class KeyEvent:
    """按键事件"""
    timestamp: float
    key_id: str
    profile_name: str
    app_name: str
    action: str
    value: str


@dataclass
class AppSwitchEvent:
    """应用切换事件"""
    timestamp: float
    from_app: str
    to_app: str
    from_profile: str
    to_profile: str


@dataclass
class UsageStats:
    """使用统计"""
    total_keys: int
    total_switches: int
    top_keys: List[Dict[str, Any]]
    top_apps: List[Dict[str, Any]]
    session_duration: float


class DataPool:
    """
    数据池

    功能:
    - 存储按键事件
    - 存储应用切换事件
    - 生成使用统计
    - 数据导出
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(__file__).parent.parent.parent / "data" / "usage.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建按键事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                key_id TEXT,
                profile_name TEXT,
                app_name TEXT,
                action TEXT,
                value TEXT
            )
        ''')

        # 创建应用切换事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_switches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                from_app TEXT,
                to_app TEXT,
                from_profile TEXT,
                to_profile TEXT
            )
        ''')

        # 创建会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time REAL,
                end_time REAL,
                total_keys INTEGER,
                total_switches INTEGER
            )
        ''')

        conn.commit()
        conn.close()

    def log_key_event(self, event: KeyEvent):
        """记录按键事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO key_events (timestamp, key_id, profile_name, app_name, action, value)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event.timestamp, event.key_id, event.profile_name, event.app_name, event.action, event.value))

        conn.commit()
        conn.close()

    def log_app_switch(self, event: AppSwitchEvent):
        """记录应用切换事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO app_switches (timestamp, from_app, to_app, from_profile, to_profile)
            VALUES (?, ?, ?, ?, ?)
        ''', (event.timestamp, event.from_app, event.to_app, event.from_profile, event.to_profile))

        conn.commit()
        conn.close()

    def get_key_events(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[KeyEvent]:
        """获取按键事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if start_time and end_time:
            cursor.execute('''
                SELECT timestamp, key_id, profile_name, app_name, action, value
                FROM key_events
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            ''', (start_time, end_time))
        else:
            cursor.execute('''
                SELECT timestamp, key_id, profile_name, app_name, action, value
                FROM key_events
                ORDER BY timestamp DESC
            ''')

        events = []
        for row in cursor.fetchall():
            events.append(KeyEvent(
                timestamp=row[0],
                key_id=row[1],
                profile_name=row[2],
                app_name=row[3],
                action=row[4],
                value=row[5]
            ))

        conn.close()
        return events

    def get_app_switches(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[AppSwitchEvent]:
        """获取应用切换事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if start_time and end_time:
            cursor.execute('''
                SELECT timestamp, from_app, to_app, from_profile, to_profile
                FROM app_switches
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            ''', (start_time, end_time))
        else:
            cursor.execute('''
                SELECT timestamp, from_app, to_app, from_profile, to_profile
                FROM app_switches
                ORDER BY timestamp DESC
            ''')

        events = []
        for row in cursor.fetchall():
            events.append(AppSwitchEvent(
                timestamp=row[0],
                from_app=row[1],
                to_app=row[2],
                from_profile=row[3],
                to_profile=row[4]
            ))

        conn.close()
        return events

    def get_usage_stats(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> UsageStats:
        """获取使用统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总按键数
        if start_time and end_time:
            cursor.execute('''
                SELECT COUNT(*) FROM key_events
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))
        else:
            cursor.execute('SELECT COUNT(*) FROM key_events')
        total_keys = cursor.fetchone()[0]

        # 总切换数
        if start_time and end_time:
            cursor.execute('''
                SELECT COUNT(*) FROM app_switches
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))
        else:
            cursor.execute('SELECT COUNT(*) FROM app_switches')
        total_switches = cursor.fetchone()[0]

        # 热门按键
        if start_time and end_time:
            cursor.execute('''
                SELECT key_id, COUNT(*) as count
                FROM key_events
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY key_id
                ORDER BY count DESC
                LIMIT 10
            ''', (start_time, end_time))
        else:
            cursor.execute('''
                SELECT key_id, COUNT(*) as count
                FROM key_events
                GROUP BY key_id
                ORDER BY count DESC
                LIMIT 10
            ''')
        top_keys = [{"key_id": row[0], "count": row[1]} for row in cursor.fetchall()]

        # 热门应用
        if start_time and end_time:
            cursor.execute('''
                SELECT app_name, COUNT(*) as count
                FROM key_events
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY app_name
                ORDER BY count DESC
                LIMIT 10
            ''', (start_time, end_time))
        else:
            cursor.execute('''
                SELECT app_name, COUNT(*) as count
                FROM key_events
                GROUP BY app_name
                ORDER BY count DESC
                LIMIT 10
            ''')
        top_apps = [{"app_name": row[0], "count": row[1]} for row in cursor.fetchall()]

        # 会话时长
        if start_time and end_time:
            session_duration = end_time - start_time
        else:
            cursor.execute('''
                SELECT MIN(timestamp), MAX(timestamp) FROM key_events
            ''')
            row = cursor.fetchone()
            session_duration = row[1] - row[0] if row[0] and row[1] else 0

        conn.close()

        return UsageStats(
            total_keys=total_keys,
            total_switches=total_switches,
            top_keys=top_keys,
            top_apps=top_apps,
            session_duration=session_duration
        )

    def export_json(self, file_path: str, start_time: Optional[float] = None, end_time: Optional[float] = None):
        """导出为 JSON"""
        data = {
            "key_events": [asdict(e) for e in self.get_key_events(start_time, end_time)],
            "app_switches": [asdict(e) for e in self.get_app_switches(start_time, end_time)],
            "stats": asdict(self.get_usage_stats(start_time, end_time))
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def clear(self):
        """清空数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM key_events')
        cursor.execute('DELETE FROM app_switches')
        cursor.execute('DELETE FROM sessions')

        conn.commit()
        conn.close()
