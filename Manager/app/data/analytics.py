"""
AI Agent Deck - 数据分析
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .data_pool import DataPool, UsageStats


@dataclass
class DailyReport:
    """每日报告"""
    date: str
    total_keys: int
    total_switches: int
    top_keys: List[Dict[str, Any]]
    top_apps: List[Dict[str, Any]]
    session_duration: float


@dataclass
class WeeklyReport:
    """每周报告"""
    start_date: str
    end_date: str
    daily_reports: List[DailyReport]
    total_keys: int
    total_switches: int
    average_session_duration: float


class Analytics:
    """
    数据分析

    功能:
    - 生成每日报告
    - 生成每周报告
    - 趋势分析
    - 模式识别
    """

    def __init__(self, data_pool: Optional[DataPool] = None):
        self.data_pool = data_pool or DataPool()

    def get_daily_report(self, date: Optional[datetime] = None) -> DailyReport:
        """获取每日报告"""
        if date is None:
            date = datetime.now()

        # 计算时间范围
        start_time = datetime(date.year, date.month, date.day).timestamp()
        end_time = start_time + 86400  # 24小时

        # 获取统计
        stats = self.data_pool.get_usage_stats(start_time, end_time)

        return DailyReport(
            date=date.strftime("%Y-%m-%d"),
            total_keys=stats.total_keys,
            total_switches=stats.total_switches,
            top_keys=stats.top_keys,
            top_apps=stats.top_apps,
            session_duration=stats.session_duration
        )

    def get_weekly_report(self, start_date: Optional[datetime] = None) -> WeeklyReport:
        """获取每周报告"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        daily_reports = []
        total_keys = 0
        total_switches = 0
        total_duration = 0

        for i in range(7):
            date = start_date + timedelta(days=i)
            report = self.get_daily_report(date)
            daily_reports.append(report)

            total_keys += report.total_keys
            total_switches += report.total_switches
            total_duration += report.session_duration

        average_duration = total_duration / 7 if total_duration > 0 else 0

        return WeeklyReport(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=(start_date + timedelta(days=6)).strftime("%Y-%m-%d"),
            daily_reports=daily_reports,
            total_keys=total_keys,
            total_switches=total_switches,
            average_session_duration=average_duration
        )

    def get_usage_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取使用趋势"""
        trend = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            report = self.get_daily_report(date)

            trend.append({
                "date": report.date,
                "keys": report.total_keys,
                "switches": report.total_switches
            })

        return trend

    def get_peak_hours(self) -> List[int]:
        """获取高峰时段"""
        # 获取所有按键事件
        events = self.data_pool.get_key_events()

        # 统计每小时的事件数
        hour_counts = [0] * 24
        for event in events:
            dt = datetime.fromtimestamp(event.timestamp)
            hour_counts[dt.hour] += 1

        # 返回高峰时段
        peak_hours = []
        for hour, count in enumerate(hour_counts):
            if count > sum(hour_counts) / 24:
                peak_hours.append(hour)

        return peak_hours

    def export_report(self, file_path: str, report_type: str = "daily"):
        """导出报告"""
        if report_type == "daily":
            report = self.get_daily_report()
        elif report_type == "weekly":
            report = self.get_weekly_report()
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        # 转换为字典
        if isinstance(report, DailyReport):
            data = {
                "type": "daily",
                "date": report.date,
                "total_keys": report.total_keys,
                "total_switches": report.total_switches,
                "top_keys": report.top_keys,
                "top_apps": report.top_apps,
                "session_duration": report.session_duration
            }
        elif isinstance(report, WeeklyReport):
            data = {
                "type": "weekly",
                "start_date": report.start_date,
                "end_date": report.end_date,
                "total_keys": report.total_keys,
                "total_switches": report.total_switches,
                "average_session_duration": report.average_session_duration,
                "daily_reports": [
                    {
                        "date": r.date,
                        "total_keys": r.total_keys,
                        "total_switches": r.total_switches
                    }
                    for r in report.daily_reports
                ]
            }
        else:
            data = {}

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
