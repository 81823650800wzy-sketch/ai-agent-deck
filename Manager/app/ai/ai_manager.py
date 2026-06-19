"""
AI Agent Deck - AI 管理器
智能按键映射推荐
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from ..data.data_pool import DataPool, UsageStats
from ..core.profile import Profile, KeyMapping


@dataclass
class KeyRecommendation:
    """按键推荐"""
    key_id: str
    current_action: str
    suggested_action: str
    reason: str
    confidence: float


@dataclass
class WorkflowInsight:
    """工作流洞察"""
    title: str
    description: str
    suggestion: str
    priority: str  # high, medium, low


class AIManager:
    """
    AI 管理器

    功能:
    - 分析用户行为
    - 推荐按键映射
    - 识别工作流模式
    - 生成洞察报告
    """

    def __init__(self, data_pool: Optional[DataPool] = None):
        self.data_pool = data_pool or DataPool()

    def analyze_usage(self, profile_name: str) -> UsageStats:
        """分析使用情况"""
        return self.data_pool.get_usage_stats()

    def recommend_keys(self, profile: Profile) -> List[KeyRecommendation]:
        """推荐按键映射"""
        recommendations = []

        # 获取使用统计
        stats = self.data_pool.get_usage_stats()

        # 分析热门操作
        for key_stat in stats.top_keys:
            key_id = key_stat["key_id"]
            count = key_stat["count"]

            # 查找当前映射
            current_key = None
            for k in profile.keys:
                if k.id == key_id:
                    current_key = k
                    break

            if current_key and count > 10:  # 高频使用
                recommendations.append(KeyRecommendation(
                    key_id=key_id,
                    current_action=current_key.action,
                    suggested_action=current_key.action,  # 保持当前
                    reason="高频使用",
                    confidence=0.9
                ))

        return recommendations

    def get_workflow_insights(self) -> List[WorkflowInsight]:
        """获取工作流洞察"""
        insights = []

        stats = self.data_pool.get_usage_stats()

        # 分析应用使用模式
        if stats.top_apps:
            top_app = stats.top_apps[0]
            insights.append(WorkflowInsight(
                title="最常用应用",
                description=f"您最常使用的应用是 {top_app['app_name']}",
                suggestion="可以为此应用创建专用 Profile",
                priority="medium"
            ))

        # 分析按键使用模式
        if stats.top_keys:
            top_key = stats.top_keys[0]
            insights.append(WorkflowInsight(
                title="最常用按键",
                description=f"您最常使用的按键是 {top_key['key_id']}",
                suggestion="确保此按键映射到最常用的操作",
                priority="low"
            ))

        # 分析会话时长
        if stats.session_duration > 3600:  # 超过1小时
            insights.append(WorkflowInsight(
                title="长会话",
                description="您已经工作了很长时间",
                suggestion="建议适当休息",
                priority="high"
            ))

        return insights

    def generate_profile(self, app_name: str, context: Dict[str, Any]) -> Profile:
        """生成 Profile"""
        # 基于应用类型生成默认映射
        keys = []

        # 通用操作
        keys.append(KeyMapping("K1", "复制", "key_combo", "ctrl+c"))
        keys.append(KeyMapping("K2", "粘贴", "key_combo", "ctrl+v"))
        keys.append(KeyMapping("K3", "撤销", "key_combo", "ctrl+z"))
        keys.append(KeyMapping("K4", "保存", "key_combo", "ctrl+s"))
        keys.append(KeyMapping("K5", "全选", "key_combo", "ctrl+a"))
        keys.append(KeyMapping("K6", "关闭", "key_combo", "ctrl+w"))

        return Profile(
            name=app_name,
            keys=keys,
            process_names=[],
            description=f"AI 生成的 {app_name} Profile",
            theme="default"
        )

    def optimize_profile(self, profile: Profile) -> Profile:
        """优化 Profile"""
        # 获取使用统计
        stats = self.data_pool.get_usage_stats()

        # 根据使用频率调整按键顺序
        key_usage = {k["key_id"]: k["count"] for k in stats.top_keys}

        # 将高频使用的按键放在前面
        sorted_keys = sorted(
            profile.keys,
            key=lambda k: key_usage.get(k.id, 0),
            reverse=True
        )

        return Profile(
            name=profile.name,
            keys=sorted_keys,
            process_names=profile.process_names,
            description=profile.description + " (AI 优化)",
            theme=profile.theme
        )
