"""
Materialized View Knowledge Registry

This module contains comprehensive knowledge about all 16 materialized views
in the system, including their schemas, purposes, and query mapping logic.

This enables the AI agent to intelligently route queries to the most efficient
materialized view instead of querying raw tables.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class QueryIntent(Enum):
    """Categories of user query intents"""
    DASHBOARD_OVERVIEW = "dashboard_overview"
    SOFTWARE_USAGE = "software_usage"
    SOFTWARE_ROI = "software_roi"
    SOFTWARE_INVESTMENT = "software_investment"
    USER_ANALYTICS = "user_analytics"
    STUDENT_ANALYSIS = "student_analysis"
    TEACHER_ANALYSIS = "teacher_analysis"
    UNAUTHORIZED_SOFTWARE = "unauthorized_software"
    SCHOOL_ANALYSIS = "school_analysis"
    GRADE_ANALYSIS = "grade_analysis"
    USAGE_TRENDS = "usage_trends"
    USAGE_RANKINGS = "usage_rankings"
    REPORT_GENERATION = "report_generation"
    ACTIVE_USERS = "active_users"
    COST_ANALYSIS = "cost_analysis"
    UTILIZATION_ANALYSIS = "utilization_analysis"


@dataclass
class MaterializedViewInfo:
    """Information about a materialized view"""
    name: str
    description: str
    primary_intents: List[QueryIntent]
    key_columns: List[str]
    aggregations: List[str]
    filters_available: List[str]
    performance_notes: str
    sample_queries: List[str] = field(default_factory=list)
    priority: int = 1  # 1 = highest priority for its intent


# Complete registry of all 16 materialized views
MATERIALIZED_VIEW_REGISTRY: Dict[str, MaterializedViewInfo] = {

    # ============================================================================
    # 1. mv_dashboard_software_metrics - Primary dashboard view for software metrics
    # ============================================================================
    "mv_dashboard_software_metrics": MaterializedViewInfo(
        name="mv_dashboard_software_metrics",
        description="Pre-computed dashboard metrics for authorized/district-purchased software including ROI, costs, and usage statistics",
        primary_intents=[
            QueryIntent.DASHBOARD_OVERVIEW,
            QueryIntent.SOFTWARE_USAGE,
            QueryIntent.SOFTWARE_ROI,
            QueryIntent.COST_ANALYSIS
        ],
        key_columns=[
            "software_id", "name", "district_id", "school_name", "category",
            "funding_source", "total_cost", "user_type", "authorized",
            "district_purchased", "students_licensed", "purchase_date",
            "grade_range", "roi_percentage", "cost_per_student",
            "active_users_30d", "active_users_all_time", "total_minutes_90d",
            "last_usage_date", "utilization", "roi_status"
        ],
        aggregations=["active_users_30d", "active_users_all_time", "total_minutes_90d", "utilization", "roi_percentage"],
        filters_available=["district_id", "school_name", "category", "roi_status", "authorized"],
        performance_notes="Best for dashboard cards, software overview, ROI status checks. Pre-joined with software_metrics and software_usage.",
        sample_queries=[
            "SELECT * FROM mv_dashboard_software_metrics WHERE district_id = '{district_id}' AND roi_status = 'high'",
            "SELECT name, total_cost, roi_percentage, utilization FROM mv_dashboard_software_metrics WHERE district_id = '{district_id}' ORDER BY total_cost DESC LIMIT 10"
        ],
        priority=1
    ),

    # ============================================================================
    # 2. mv_dashboard_user_analytics - User analytics aggregated by role and grade
    # ============================================================================
    "mv_dashboard_user_analytics": MaterializedViewInfo(
        name="mv_dashboard_user_analytics",
        description="User analytics grouped by district, school, role (student/teacher), and grade with usage aggregations",
        primary_intents=[
            QueryIntent.USER_ANALYTICS,
            QueryIntent.STUDENT_ANALYSIS,
            QueryIntent.TEACHER_ANALYSIS,
            QueryIntent.ACTIVE_USERS
        ],
        key_columns=[
            "row_id", "district_id", "school_id", "school_name", "user_type",
            "grade", "total_users", "active_users_30d", "active_users_all_time",
            "total_usage_minutes_90d"
        ],
        aggregations=["total_users", "active_users_30d", "active_users_all_time", "total_usage_minutes_90d"],
        filters_available=["district_id", "school_id", "user_type", "grade"],
        performance_notes="Best for user count dashboards, role-based analysis, grade-level breakdowns. Pre-aggregated from profiles and software_usage.",
        sample_queries=[
            "SELECT user_type, SUM(total_users) as users, SUM(active_users_30d) as active FROM mv_dashboard_user_analytics WHERE district_id = '{district_id}' GROUP BY user_type",
            "SELECT grade, total_users, active_users_30d FROM mv_dashboard_user_analytics WHERE district_id = '{district_id}' AND user_type = 'student'"
        ],
        priority=1
    ),

    # ============================================================================
    # 3. mv_software_usage_analytics_v4 - Comprehensive software usage analytics
    # ============================================================================
    "mv_software_usage_analytics_v4": MaterializedViewInfo(
        name="mv_software_usage_analytics_v4",
        description="Most comprehensive software analytics view with ROI calculations, usage ratios, engagement rates, and compliance metrics grouped by software name and district",
        primary_intents=[
            QueryIntent.SOFTWARE_USAGE,
            QueryIntent.SOFTWARE_ROI,
            QueryIntent.UTILIZATION_ANALYSIS,
            QueryIntent.DASHBOARD_OVERVIEW
        ],
        key_columns=[
            "name", "district_id", "ids", "categories", "school_names", "user_types",
            "grades", "grade_ranges", "funding_sources", "total_cost", "students_licensed",
            "authorized", "district_purchased", "url", "icon", "applicable_grade_bands",
            "sub_population", "program_population", "primary_category", "category_type",
            "total_minutes", "active_users", "usage_days", "first_use_date", "last_use_date",
            "active_students", "active_teachers", "expected_daily_minutes", "cost_per_student",
            "days_since_start", "expected_minutes_to_date", "usage_ratio", "avg_minutes_per_day",
            "avg_roi_percentage", "roi_status", "engagement_rate", "usage_compliance",
            "avg_usage_compliance"
        ],
        aggregations=[
            "total_minutes", "active_users", "active_students", "active_teachers",
            "usage_ratio", "avg_roi_percentage", "engagement_rate", "usage_compliance"
        ],
        filters_available=["district_id", "authorized", "district_purchased", "roi_status", "category_type"],
        performance_notes="MOST COMPREHENSIVE VIEW - use for detailed analytics, ROI analysis, engagement metrics. Groups by software name so multiple software records are consolidated.",
        sample_queries=[
            "SELECT name, total_minutes, active_users, roi_status, avg_roi_percentage FROM mv_software_usage_analytics_v4 WHERE district_id = '{district_id}' ORDER BY total_minutes DESC",
            "SELECT roi_status, COUNT(*) as count, SUM(total_cost) as investment FROM mv_software_usage_analytics_v4 WHERE district_id = '{district_id}' GROUP BY roi_status"
        ],
        priority=1
    ),

    # ============================================================================
    # 4. mv_unauthorized_software_analytics_v3 - Unauthorized software tracking
    # ============================================================================
    "mv_unauthorized_software_analytics_v3": MaterializedViewInfo(
        name="mv_unauthorized_software_analytics_v3",
        description="Analytics for unauthorized software including usage metrics, user counts by type, and last usage tracking",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE
        ],
        key_columns=[
            "id", "name", "category", "url", "district_id", "school_name",
            "user_type", "district_name", "total_usage_minutes", "unique_users",
            "student_users", "teacher_users", "usage_count", "last_used_date",
            "avg_minutes_per_user", "refreshed_at"
        ],
        aggregations=["total_usage_minutes", "unique_users", "student_users", "teacher_users", "usage_count"],
        filters_available=["district_id", "category", "school_name"],
        performance_notes="Best for security/compliance dashboards, unauthorized software monitoring. Automatically filtered to authorized=false.",
        sample_queries=[
            "SELECT name, total_usage_minutes, unique_users, student_users FROM mv_unauthorized_software_analytics_v3 WHERE district_id = '{district_id}' ORDER BY total_usage_minutes DESC",
            "SELECT category, COUNT(*) as apps, SUM(unique_users) as users FROM mv_unauthorized_software_analytics_v3 WHERE district_id = '{district_id}' GROUP BY category"
        ],
        priority=1
    ),

    # ============================================================================
    # 5. mv_unauthorized_usage_dashboard - Dashboard-ready unauthorized usage data
    # ============================================================================
    "mv_unauthorized_usage_dashboard": MaterializedViewInfo(
        name="mv_unauthorized_usage_dashboard",
        description="Dashboard-optimized view for unauthorized software with in-school vs out-of-school usage breakdown (90-day window)",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE,
            QueryIntent.DASHBOARD_OVERVIEW
        ],
        key_columns=[
            "software_id", "software_name", "category", "url", "district_id",
            "district_name", "user_type", "total_minutes", "in_school_minutes",
            "out_of_school_minutes", "active_users", "usage_count", "last_used_date",
            "school_name", "in_school_percentage", "out_of_school_percentage", "refreshed_at"
        ],
        aggregations=["total_minutes", "in_school_minutes", "out_of_school_minutes", "active_users"],
        filters_available=["district_id", "category", "school_name"],
        performance_notes="Best for unauthorized software dashboard cards with location-based breakdown. Limited to 90-day window.",
        sample_queries=[
            "SELECT software_name, total_minutes, in_school_percentage, active_users FROM mv_unauthorized_usage_dashboard WHERE district_id = '{district_id}' ORDER BY total_minutes DESC LIMIT 10"
        ],
        priority=2
    ),

    # ============================================================================
    # 6. mv_software_investment_summary - Investment analysis view
    # ============================================================================
    "mv_software_investment_summary": MaterializedViewInfo(
        name="mv_software_investment_summary",
        description="Software investment analysis with ROI metrics, utilization rates, and cost-per-student calculations",
        primary_intents=[
            QueryIntent.SOFTWARE_INVESTMENT,
            QueryIntent.COST_ANALYSIS,
            QueryIntent.SOFTWARE_ROI
        ],
        key_columns=[
            "software_id", "software_name", "display_name", "district_id", "school_name",
            "category", "funding_source", "grade_ranges", "user_type", "latest_purchase_date",
            "last_usage_date", "created_at", "total_investment", "total_licensed_users",
            "active_users", "avg_utilization", "total_minutes", "avg_cost_per_student",
            "avg_roi_percentage", "roi_status", "roi_status_priority", "authorized", "district_purchased"
        ],
        aggregations=["total_investment", "total_licensed_users", "active_users", "avg_utilization", "avg_roi_percentage"],
        filters_available=["district_id", "school_name", "category", "funding_source", "roi_status"],
        performance_notes="Best for financial reports, budget analysis, ROI comparisons. Built on mv_dashboard_software_metrics.",
        sample_queries=[
            "SELECT software_name, total_investment, active_users, avg_roi_percentage, roi_status FROM mv_software_investment_summary WHERE district_id = '{district_id}' ORDER BY total_investment DESC",
            "SELECT funding_source, SUM(total_investment) as total, AVG(avg_roi_percentage) as avg_roi FROM mv_software_investment_summary WHERE district_id = '{district_id}' GROUP BY funding_source"
        ],
        priority=1
    ),

    # ============================================================================
    # 7. mv_user_software_utilization_v2 - User-level software utilization
    # ============================================================================
    "mv_user_software_utilization_v2": MaterializedViewInfo(
        name="mv_user_software_utilization_v2",
        description="Detailed user-level software utilization with session counts, location breakdown, and weekly averages",
        primary_intents=[
            QueryIntent.USER_ANALYTICS,
            QueryIntent.STUDENT_ANALYSIS,
            QueryIntent.TEACHER_ANALYSIS,
            QueryIntent.UTILIZATION_ANALYSIS
        ],
        key_columns=[
            "software_id", "user_id", "user_email", "first_name", "last_name",
            "grade", "school_id", "district_id", "user_role", "school_name",
            "district_name", "software_name", "software_category", "sessions_count",
            "total_minutes", "minutes_in_school", "minutes_at_home", "first_active",
            "last_active", "days_active", "avg_weekly_minutes"
        ],
        aggregations=["sessions_count", "total_minutes", "minutes_in_school", "minutes_at_home", "avg_weekly_minutes"],
        filters_available=["district_id", "school_id", "user_role", "grade", "software_id"],
        performance_notes="Best for individual user reports, top users analysis, per-user software breakdowns. Detailed granularity.",
        sample_queries=[
            "SELECT first_name, last_name, software_name, total_minutes, avg_weekly_minutes FROM mv_user_software_utilization_v2 WHERE district_id = '{district_id}' ORDER BY total_minutes DESC LIMIT 20",
            "SELECT user_role, COUNT(DISTINCT user_id) as users, SUM(total_minutes) as minutes FROM mv_user_software_utilization_v2 WHERE district_id = '{district_id}' GROUP BY user_role"
        ],
        priority=1
    ),

    # ============================================================================
    # 8. mv_active_users_summary - Active users summary with grade bands
    # ============================================================================
    "mv_active_users_summary": MaterializedViewInfo(
        name="mv_active_users_summary",
        description="Summary of active users with total usage, session counts, and grade band classification",
        primary_intents=[
            QueryIntent.ACTIVE_USERS,
            QueryIntent.USER_ANALYTICS,
            QueryIntent.GRADE_ANALYSIS
        ],
        key_columns=[
            "user_id", "email", "first_name", "last_name", "role", "grade",
            "school_id", "district_id", "school_name", "district_name",
            "total_usage_minutes", "total_sessions", "first_active_date",
            "last_active_date", "grade_band", "full_name"
        ],
        aggregations=["total_usage_minutes", "total_sessions"],
        filters_available=["district_id", "school_id", "role", "grade", "grade_band"],
        performance_notes="Best for user activity reports, grade band analysis, last-active tracking. Includes computed grade_band field.",
        sample_queries=[
            "SELECT grade_band, COUNT(*) as users, SUM(total_usage_minutes) as minutes FROM mv_active_users_summary WHERE district_id = '{district_id}' GROUP BY grade_band",
            "SELECT full_name, role, total_usage_minutes, last_active_date FROM mv_active_users_summary WHERE district_id = '{district_id}' ORDER BY total_usage_minutes DESC LIMIT 20"
        ],
        priority=1
    ),

    # ============================================================================
    # 9. mv_software_details_metrics - Detailed software metrics with weekly usage
    # ============================================================================
    "mv_software_details_metrics": MaterializedViewInfo(
        name="mv_software_details_metrics",
        description="Detailed software metrics including weekly usage patterns, user day statistics, and cost efficiency calculations",
        primary_intents=[
            QueryIntent.SOFTWARE_USAGE,
            QueryIntent.UTILIZATION_ANALYSIS,
            QueryIntent.COST_ANALYSIS
        ],
        key_columns=[
            "name", "district_id", "ids", "categories", "primary_category",
            "school_names", "user_types", "grades", "grade_ranges", "funding_sources",
            "total_cost", "students_licensed", "authorized", "district_purchased",
            "url", "icon", "total_minutes", "active_users", "usage_days",
            "first_use_date", "last_use_date", "cost_per_student", "roi_status",
            "engagement_rate", "usage_compliance", "avg_weekly_minutes_per_user",
            "total_weekly_minutes_all_users", "users_with_weekly_data",
            "min_weekly_minutes_per_user", "max_weekly_minutes_per_user",
            "median_weekly_minutes_per_user", "total_user_day_combinations",
            "days_with_10min_usage", "days_with_15min_usage", "days_with_20min_usage",
            "cost_per_user_hour_per_week", "utilization_rate_percentage"
        ],
        aggregations=["avg_weekly_minutes_per_user", "total_weekly_minutes_all_users", "utilization_rate_percentage"],
        filters_available=["district_id", "authorized", "district_purchased", "roi_status"],
        performance_notes="Best for detailed software analysis, weekly usage patterns, usage threshold analysis (10/15/20 min days).",
        sample_queries=[
            "SELECT name, avg_weekly_minutes_per_user, utilization_rate_percentage, roi_status FROM mv_software_details_metrics WHERE district_id = '{district_id}' ORDER BY total_minutes DESC"
        ],
        priority=2
    ),

    # ============================================================================
    # 10. mv_report_data_unified_v4 - Unified report data by school
    # ============================================================================
    "mv_report_data_unified_v4": MaterializedViewInfo(
        name="mv_report_data_unified_v4",
        description="Unified report data for authorized software grouped by software name and school, with comprehensive metrics",
        primary_intents=[
            QueryIntent.REPORT_GENERATION,
            QueryIntent.SCHOOL_ANALYSIS,
            QueryIntent.SOFTWARE_USAGE
        ],
        key_columns=[
            "software_name", "software_ids", "software_record_count", "school_id",
            "school_name", "district_id", "category", "funding_source", "grade_range",
            "authorized", "approval_status", "purchase_date", "url", "total_cost",
            "students_licensed", "cost_per_student", "active_students", "active_teachers",
            "total_minutes", "total_usage_hours", "usage_days", "average_session_time",
            "usage_frequency", "avg_weekly_usage_hours", "first_use_date", "last_use_date",
            "user_satisfaction", "technical_metrics", "expected_daily_minutes", "usage_compliance"
        ],
        aggregations=["total_minutes", "total_usage_hours", "active_students", "active_teachers", "avg_weekly_usage_hours"],
        filters_available=["district_id", "school_id", "school_name", "category", "funding_source"],
        performance_notes="Best for generating school-level reports, comparing software across schools. Authorized software only.",
        sample_queries=[
            "SELECT software_name, school_name, total_usage_hours, active_students FROM mv_report_data_unified_v4 WHERE district_id = '{district_id}' ORDER BY total_usage_hours DESC",
            "SELECT school_name, COUNT(DISTINCT software_name) as apps, SUM(total_cost) as investment FROM mv_report_data_unified_v4 WHERE district_id = '{district_id}' GROUP BY school_name"
        ],
        priority=1
    ),

    # ============================================================================
    # 11. mv_unauthorized_software_by_school - Unauthorized usage by school
    # ============================================================================
    "mv_unauthorized_software_by_school": MaterializedViewInfo(
        name="mv_unauthorized_software_by_school",
        description="Unauthorized software usage aggregated by school (90-day window)",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE,
            QueryIntent.SCHOOL_ANALYSIS
        ],
        key_columns=[
            "software_id", "school_name", "total_minutes", "unique_users", "session_count"
        ],
        aggregations=["total_minutes", "unique_users", "session_count"],
        filters_available=["software_id", "school_name"],
        performance_notes="Best for school-level unauthorized software breakdown. Limited to 90-day window.",
        sample_queries=[
            "SELECT school_name, SUM(total_minutes) as minutes, SUM(unique_users) as users FROM mv_unauthorized_software_by_school GROUP BY school_name ORDER BY minutes DESC"
        ],
        priority=2
    ),

    # ============================================================================
    # 12. mv_unauthorized_software_by_grade - Unauthorized usage by grade
    # ============================================================================
    "mv_unauthorized_software_by_grade": MaterializedViewInfo(
        name="mv_unauthorized_software_by_grade",
        description="Unauthorized software usage aggregated by grade level (90-day window)",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE,
            QueryIntent.GRADE_ANALYSIS
        ],
        key_columns=[
            "software_id", "grade", "total_minutes", "unique_users", "session_count"
        ],
        aggregations=["total_minutes", "unique_users", "session_count"],
        filters_available=["software_id", "grade"],
        performance_notes="Best for grade-level unauthorized software analysis. Limited to 90-day window.",
        sample_queries=[
            "SELECT grade, SUM(total_minutes) as minutes, SUM(unique_users) as users FROM mv_unauthorized_software_by_grade GROUP BY grade ORDER BY grade"
        ],
        priority=2
    ),

    # ============================================================================
    # 13. mv_unauthorized_software_by_hour - Unauthorized usage by hour
    # ============================================================================
    "mv_unauthorized_software_by_hour": MaterializedViewInfo(
        name="mv_unauthorized_software_by_hour",
        description="Unauthorized software usage aggregated by hour of day (90-day window)",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE,
            QueryIntent.USAGE_TRENDS
        ],
        key_columns=[
            "software_id", "hour", "session_count", "total_minutes"
        ],
        aggregations=["session_count", "total_minutes"],
        filters_available=["software_id", "hour"],
        performance_notes="Best for hourly usage pattern analysis of unauthorized software.",
        sample_queries=[
            "SELECT hour, SUM(session_count) as sessions, SUM(total_minutes) as minutes FROM mv_unauthorized_software_by_hour GROUP BY hour ORDER BY hour"
        ],
        priority=3
    ),

    # ============================================================================
    # 14. mv_unauthorized_software_timeline - Unauthorized usage timeline
    # ============================================================================
    "mv_unauthorized_software_timeline": MaterializedViewInfo(
        name="mv_unauthorized_software_timeline",
        description="Daily timeline of unauthorized software usage",
        primary_intents=[
            QueryIntent.UNAUTHORIZED_SOFTWARE,
            QueryIntent.USAGE_TRENDS
        ],
        key_columns=[
            "software_id", "date", "total_minutes", "unique_users", "session_count"
        ],
        aggregations=["total_minutes", "unique_users", "session_count"],
        filters_available=["software_id", "date"],
        performance_notes="Best for trend analysis of unauthorized software over time.",
        sample_queries=[
            "SELECT date, SUM(total_minutes) as minutes FROM mv_unauthorized_software_timeline WHERE date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY date ORDER BY date"
        ],
        priority=2
    ),

    # ============================================================================
    # 15. mv_software_usage_by_school_v2 - Software usage by school
    # ============================================================================
    "mv_software_usage_by_school_v2": MaterializedViewInfo(
        name="mv_software_usage_by_school_v2",
        description="Software usage metrics broken down by school with ROI calculations",
        primary_intents=[
            QueryIntent.SCHOOL_ANALYSIS,
            QueryIntent.SOFTWARE_USAGE,
            QueryIntent.SOFTWARE_ROI
        ],
        key_columns=[
            "software_id", "software_name", "school_id", "school_name", "district_id",
            "total_cost", "category", "authorized", "district_purchased",
            "students_licensed", "funding_source", "user_type", "grade",
            "applicable_grade_bands", "active_users", "active_students", "active_teachers",
            "total_minutes", "usage_days", "first_use_date", "last_use_date",
            "days_since_start", "expected_daily_minutes", "category_type",
            "cost_per_student", "expected_minutes_to_date", "usage_ratio",
            "avg_minutes_per_day", "avg_roi_percentage", "roi_status",
            "engagement_rate", "usage_compliance", "avg_usage_compliance"
        ],
        aggregations=["active_users", "active_students", "active_teachers", "total_minutes", "avg_roi_percentage"],
        filters_available=["district_id", "school_id", "school_name", "category", "roi_status"],
        performance_notes="Best for school-level software comparisons, ROI by school analysis.",
        sample_queries=[
            "SELECT school_name, software_name, total_minutes, roi_status FROM mv_software_usage_by_school_v2 WHERE district_id = '{district_id}' ORDER BY total_minutes DESC"
        ],
        priority=1
    ),

    # ============================================================================
    # 16. mv_software_usage_rankings_v4 - Software usage rankings
    # ============================================================================
    "mv_software_usage_rankings_v4": MaterializedViewInfo(
        name="mv_software_usage_rankings_v4",
        description="Software usage rankings with percentage calculations, supporting filtering by grade band, user type, school, and funding source",
        primary_intents=[
            QueryIntent.USAGE_RANKINGS,
            QueryIntent.SOFTWARE_USAGE,
            QueryIntent.GRADE_ANALYSIS
        ],
        key_columns=[
            "id", "name", "category", "district_id", "user_type", "school_name",
            "funding_source", "grade_band", "total_cost", "total_minutes",
            "instance_count", "software_ids", "context_total_minutes", "usage_percentage"
        ],
        aggregations=["total_minutes", "total_cost", "usage_percentage"],
        filters_available=["district_id", "user_type", "school_name", "funding_source", "grade_band"],
        performance_notes="Best for ranking software by usage percentage within context (grade band, school, etc.).",
        sample_queries=[
            "SELECT name, grade_band, total_minutes, usage_percentage FROM mv_software_usage_rankings_v4 WHERE district_id = '{district_id}' AND grade_band = 'elementary' ORDER BY usage_percentage DESC",
            "SELECT name, user_type, total_minutes, usage_percentage FROM mv_software_usage_rankings_v4 WHERE district_id = '{district_id}' ORDER BY total_minutes DESC LIMIT 20"
        ],
        priority=1
    ),
}


# ============================================================================
# Query Intent Mapping - Maps keywords to intents
# ============================================================================
INTENT_KEYWORDS: Dict[QueryIntent, Set[str]] = {
    QueryIntent.DASHBOARD_OVERVIEW: {
        "dashboard", "overview", "summary", "executive", "overall", "metrics",
        "kpi", "snapshot", "at a glance", "highlights"
    },
    QueryIntent.SOFTWARE_USAGE: {
        "software", "usage", "app", "application", "tool", "platform", "minutes",
        "sessions", "active", "used", "using", "utilization"
    },
    QueryIntent.SOFTWARE_ROI: {
        "roi", "return on investment", "value", "effectiveness", "performance",
        "worth", "benefit", "payoff", "high roi", "low roi", "moderate roi"
    },
    QueryIntent.SOFTWARE_INVESTMENT: {
        "investment", "cost", "spend", "spending", "budget", "expense", "money",
        "purchase", "license", "pricing", "financial"
    },
    QueryIntent.USER_ANALYTICS: {
        "user", "users", "profile", "profiles", "people", "person", "individual",
        "active users", "unique users"
    },
    QueryIntent.STUDENT_ANALYSIS: {
        "student", "students", "learner", "learners", "pupil", "pupils", "kids",
        "children", "enrolled"
    },
    QueryIntent.TEACHER_ANALYSIS: {
        "teacher", "teachers", "educator", "educators", "instructor", "staff",
        "faculty", "teaching"
    },
    QueryIntent.UNAUTHORIZED_SOFTWARE: {
        "unauthorized", "unapproved", "blocked", "banned", "restricted",
        "not approved", "shadow it", "security", "compliance", "risk"
    },
    QueryIntent.SCHOOL_ANALYSIS: {
        "school", "schools", "campus", "building", "location", "site",
        "by school", "per school", "each school"
    },
    QueryIntent.GRADE_ANALYSIS: {
        "grade", "grades", "grade level", "elementary", "middle", "high school",
        "k-5", "6-8", "9-12", "kindergarten", "by grade"
    },
    QueryIntent.USAGE_TRENDS: {
        "trend", "trends", "over time", "daily", "weekly", "monthly", "history",
        "growth", "decline", "pattern", "timeline", "recent"
    },
    QueryIntent.USAGE_RANKINGS: {
        "top", "ranking", "ranked", "best", "worst", "most", "least", "highest",
        "lowest", "compare", "comparison", "vs"
    },
    QueryIntent.REPORT_GENERATION: {
        "report", "reports", "generate", "export", "document", "analysis",
        "detailed", "comprehensive"
    },
    QueryIntent.ACTIVE_USERS: {
        "active", "engagement", "engaged", "participating", "logged in",
        "last active", "recently active"
    },
    QueryIntent.COST_ANALYSIS: {
        "cost", "price", "expensive", "cheap", "cost per student", "cost per user",
        "cost effective", "efficiency", "waste", "savings"
    },
    QueryIntent.UTILIZATION_ANALYSIS: {
        "utilization", "utilized", "underutilized", "overutilized", "unused",
        "adoption", "penetration", "coverage", "compliance"
    }
}


def detect_query_intents(query: str) -> List[QueryIntent]:
    """
    Detect the intents from a user query based on keywords.
    Returns a list of detected intents ordered by relevance.
    """
    query_lower = query.lower()
    intent_scores: Dict[QueryIntent, int] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in query_lower)
        if score > 0:
            intent_scores[intent] = score

    # Sort by score descending
    sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

    # Return intents with scores > 0
    if sorted_intents:
        return [intent for intent, score in sorted_intents]

    # Default to dashboard overview if no specific intent detected
    return [QueryIntent.DASHBOARD_OVERVIEW]


def get_best_materialized_view(intents: List[QueryIntent]) -> MaterializedViewInfo:
    """
    Get the best materialized view for the given intents.
    Considers intent priority and view priority.
    """
    candidates: Dict[str, int] = {}

    for intent in intents:
        for view_name, view_info in MATERIALIZED_VIEW_REGISTRY.items():
            if intent in view_info.primary_intents:
                # Score based on intent position and view priority
                intent_weight = len(intents) - intents.index(intent)
                view_weight = 4 - view_info.priority  # Higher for lower priority number
                score = intent_weight * view_weight

                if view_name in candidates:
                    candidates[view_name] += score
                else:
                    candidates[view_name] = score

    if candidates:
        best_view = max(candidates.items(), key=lambda x: x[1])
        return MATERIALIZED_VIEW_REGISTRY[best_view[0]]

    # Default to the comprehensive analytics view
    return MATERIALIZED_VIEW_REGISTRY["mv_software_usage_analytics_v4"]


def get_recommended_views_for_query(query: str, max_views: int = 3) -> List[MaterializedViewInfo]:
    """
    Get a ranked list of recommended materialized views for a query.
    """
    intents = detect_query_intents(query)
    candidates: Dict[str, int] = {}

    for intent in intents:
        for view_name, view_info in MATERIALIZED_VIEW_REGISTRY.items():
            if intent in view_info.primary_intents:
                intent_weight = len(intents) - intents.index(intent)
                view_weight = 4 - view_info.priority
                score = intent_weight * view_weight

                if view_name in candidates:
                    candidates[view_name] += score
                else:
                    candidates[view_name] = score

    # Sort by score and return top views
    sorted_views = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    return [MATERIALIZED_VIEW_REGISTRY[name] for name, _ in sorted_views[:max_views]]


def generate_mv_query_suggestion(query: str, district_id: str) -> str:
    """
    Generate a SQL query suggestion based on the user's question.
    """
    intents = detect_query_intents(query)
    best_view = get_best_materialized_view(intents)

    # Generate appropriate query based on intent
    if QueryIntent.UNAUTHORIZED_SOFTWARE in intents:
        return f"""SELECT name, category, total_usage_minutes, unique_users, student_users, teacher_users
FROM {best_view.name}
WHERE district_id = '{district_id}'
ORDER BY total_usage_minutes DESC
LIMIT 20"""

    elif QueryIntent.SOFTWARE_INVESTMENT in intents or QueryIntent.COST_ANALYSIS in intents:
        return f"""SELECT software_name, total_investment, active_users, avg_roi_percentage, roi_status
FROM {best_view.name}
WHERE district_id = '{district_id}'
ORDER BY total_investment DESC
LIMIT 20"""

    elif QueryIntent.USER_ANALYTICS in intents or QueryIntent.ACTIVE_USERS in intents:
        return f"""SELECT user_type, SUM(total_users) as total, SUM(active_users_30d) as active_30d
FROM {best_view.name}
WHERE district_id = '{district_id}'
GROUP BY user_type"""

    elif QueryIntent.STUDENT_ANALYSIS in intents:
        return f"""SELECT grade, total_users, active_users_30d, total_usage_minutes_90d
FROM mv_dashboard_user_analytics
WHERE district_id = '{district_id}' AND user_type = 'student'
ORDER BY grade"""

    elif QueryIntent.TEACHER_ANALYSIS in intents:
        return f"""SELECT school_name, total_users, active_users_30d, total_usage_minutes_90d
FROM mv_dashboard_user_analytics
WHERE district_id = '{district_id}' AND user_type = 'teacher'
ORDER BY total_users DESC"""

    elif QueryIntent.SCHOOL_ANALYSIS in intents:
        return f"""SELECT school_name, software_name, total_minutes, active_users, roi_status
FROM mv_software_usage_by_school_v2
WHERE district_id = '{district_id}'
ORDER BY total_minutes DESC
LIMIT 30"""

    elif QueryIntent.USAGE_RANKINGS in intents:
        return f"""SELECT name, total_minutes, usage_percentage, grade_band
FROM mv_software_usage_rankings_v4
WHERE district_id = '{district_id}'
ORDER BY total_minutes DESC
LIMIT 20"""

    elif QueryIntent.SOFTWARE_ROI in intents:
        return f"""SELECT name, total_cost, total_minutes, active_users, avg_roi_percentage, roi_status
FROM {best_view.name}
WHERE district_id = '{district_id}'
ORDER BY avg_roi_percentage DESC
LIMIT 20"""

    else:
        # Default comprehensive query
        return f"""SELECT name, primary_category, total_cost, total_minutes, active_users, roi_status, avg_roi_percentage
FROM mv_software_usage_analytics_v4
WHERE district_id = '{district_id}'
ORDER BY total_minutes DESC
LIMIT 20"""


# ============================================================================
# Agent Instructions Generator
# ============================================================================
def get_mv_aware_instructions(district_id: str) -> List[str]:
    """
    Generate comprehensive agent instructions that include MV knowledge.
    """
    instructions = [
        f"You are an AI assistant specialized in educational software analytics for district {district_id}.",
        "",
        "=" * 80,
        "CRITICAL: MATERIALIZED VIEW PRIORITY SYSTEM",
        "=" * 80,
        "",
        "ALWAYS use materialized views (mv_*) instead of raw tables for queries.",
        "Materialized views contain pre-computed aggregations that are 10-100x faster.",
        "",
        "PRIMARY MATERIALIZED VIEWS TO USE:",
        "",
        "1. mv_software_usage_analytics_v4 - MOST COMPREHENSIVE",
        "   - Use for: Software usage, ROI analysis, engagement metrics",
        "   - Contains: total_minutes, active_users, roi_status, avg_roi_percentage, usage_compliance",
        "   - Groups software by name (consolidates multiple records)",
        "",
        "2. mv_dashboard_software_metrics - DASHBOARD METRICS",
        "   - Use for: Dashboard cards, quick overview, utilization rates",
        "   - Contains: roi_percentage, cost_per_student, active_users_30d, utilization",
        "",
        "3. mv_software_investment_summary - FINANCIAL ANALYSIS",
        "   - Use for: Investment reports, cost analysis, budget reviews",
        "   - Contains: total_investment, avg_cost_per_student, roi_status_priority",
        "",
        "4. mv_dashboard_user_analytics - USER COUNTS",
        "   - Use for: User statistics, student/teacher counts, grade-level breakdowns",
        "   - Contains: total_users, active_users_30d, active_users_all_time by role and grade",
        "",
        "5. mv_user_software_utilization_v2 - INDIVIDUAL USER DATA",
        "   - Use for: Top users, per-user reports, individual utilization",
        "   - Contains: user_email, total_minutes, sessions_count, avg_weekly_minutes",
        "",
        "6. mv_unauthorized_software_analytics_v3 - SECURITY/COMPLIANCE",
        "   - Use for: Unauthorized software monitoring, security dashboards",
        "   - Contains: unauthorized apps with student_users, teacher_users counts",
        "",
        "7. mv_software_usage_by_school_v2 - SCHOOL-LEVEL ANALYSIS",
        "   - Use for: School comparisons, per-school ROI, school reports",
        "   - Contains: software metrics broken down by school_id and school_name",
        "",
        "8. mv_software_usage_rankings_v4 - RANKINGS/COMPARISONS",
        "   - Use for: Top software lists, usage percentage, grade band comparisons",
        "   - Contains: usage_percentage, supports grade_band filtering",
        "",
        "=" * 80,
        "QUERY MAPPING RULES",
        "=" * 80,
        "",
        "QUESTION → MATERIALIZED VIEW:",
        "",
        "• 'Show me software usage/analytics' → mv_software_usage_analytics_v4",
        "• 'What is the ROI of our software?' → mv_software_usage_analytics_v4 or mv_software_investment_summary",
        "• 'Dashboard/overview/summary' → mv_dashboard_software_metrics",
        "• 'How many students/teachers?' → mv_dashboard_user_analytics",
        "• 'Top users by usage' → mv_user_software_utilization_v2",
        "• 'Unauthorized/unapproved software' → mv_unauthorized_software_analytics_v3",
        "• 'Compare schools' → mv_software_usage_by_school_v2",
        "• 'Software rankings/top software' → mv_software_usage_rankings_v4",
        "• 'Investment/cost analysis' → mv_software_investment_summary",
        "• 'Grade-level breakdown' → mv_dashboard_user_analytics or mv_software_usage_rankings_v4",
        "",
        "=" * 80,
        "SAMPLE OPTIMIZED QUERIES",
        "=" * 80,
        "",
        "-- Top software by usage (USE THIS, NOT raw tables)",
        f"SELECT name, primary_category, total_minutes, active_users, roi_status",
        f"FROM mv_software_usage_analytics_v4",
        f"WHERE district_id = '{district_id}'",
        f"ORDER BY total_minutes DESC LIMIT 10;",
        "",
        "-- User summary (USE THIS for user counts)",
        f"SELECT user_type, SUM(total_users) as total, SUM(active_users_30d) as active",
        f"FROM mv_dashboard_user_analytics",
        f"WHERE district_id = '{district_id}'",
        f"GROUP BY user_type;",
        "",
        "-- Investment analysis (USE THIS for financial reports)",
        f"SELECT software_name, total_investment, active_users, avg_roi_percentage, roi_status",
        f"FROM mv_software_investment_summary",
        f"WHERE district_id = '{district_id}'",
        f"ORDER BY total_investment DESC LIMIT 15;",
        "",
        "-- Unauthorized software (USE THIS for security)",
        f"SELECT name, category, total_usage_minutes, unique_users, student_users",
        f"FROM mv_unauthorized_software_analytics_v3",
        f"WHERE district_id = '{district_id}'",
        f"ORDER BY total_usage_minutes DESC;",
        "",
        "=" * 80,
        "NEVER DO THIS (SLOW - uses raw tables)",
        "=" * 80,
        "",
        "-- DON'T: Join raw tables when MV exists",
        "-- SELECT s.name, COUNT(su.id) FROM software s JOIN software_usage su...",
        "-- INSTEAD USE: mv_software_usage_analytics_v4",
        "",
        "-- DON'T: Aggregate profiles table directly",
        "-- SELECT role, COUNT(*) FROM profiles WHERE district_id = ...",
        "-- INSTEAD USE: mv_dashboard_user_analytics",
        "",
        "=" * 80,
        "RESPONSE FORMAT",
        "=" * 80,
        "",
        "- Convert all responses to clean HTML (no CSS, JavaScript, or styling)",
        "- Use proper HTML elements: tables, divs, headers, lists",
        "- Present data in tables when showing multiple records",
        "- Provide insights and recommendations based on real data",
        "- Never wrap responses in markdown code blocks",
        "- Use user-friendly titles (not technical IDs)",
        "",
        f"CRITICAL: ALL queries MUST filter by district_id = '{district_id}'",
    ]

    return instructions
