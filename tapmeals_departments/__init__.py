"""
TapMeals Autonomous Operational Departments Package
Milestone 2: Subagents & Department Configurations for TapMeals Yopal.
Includes:
- ChefOps: Kitchen MRP & route clustering (10:30 cut-off)
- TrendRadar: Market intelligence & trend directives
- GrowthLead: Comment-to-DM (<3s) & lead scoring
- RetentionAgent: QA feedback scheduling & subscription upgrade evaluation
"""

from .chef_ops import check_cutoff, calculate_mrp, cluster_routes
from .trend_radar import (
    create_trend_directive,
    scan_trends_omniroute,
    save_active_trend,
    load_active_trends,
)
from .growth_lead import score_lead, route_comment_to_dm
from .retention_agent import (
    schedule_feedback,
    process_rating,
    evaluate_subscription_upgrade,
)

__all__ = [
    "check_cutoff",
    "calculate_mrp",
    "cluster_routes",
    "create_trend_directive",
    "scan_trends_omniroute",
    "save_active_trend",
    "load_active_trends",
    "score_lead",
    "route_comment_to_dm",
    "schedule_feedback",
    "process_rating",
    "evaluate_subscription_upgrade",
]
