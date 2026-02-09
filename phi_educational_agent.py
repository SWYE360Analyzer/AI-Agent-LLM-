"""
Phi-based Educational Analytics Agent with Materialized View Knowledge

This agent uses robust PostgreSQL tools with comprehensive knowledge
of all 16 materialized views for optimal query performance.

IMPORTANT: Uses RobustPostgresTools with autocommit to prevent
"current transaction is aborted" errors.
"""

import logging
import os
import re
from typing import Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat

# Use our robust postgres tools instead of phi's native one
from robust_postgres_tools import RobustPostgresTools

logger = logging.getLogger(__name__)


class PhiEducationalAgent:
    """
    Educational agent using phi's native PostgreSQL tools with MV knowledge.

    IMPORTANT: This agent is configured with comprehensive knowledge of all
    materialized views to ensure optimal query performance.
    """

    def __init__(
        self,
        district_id: str,
        postgres_config: dict,
        openai_api_key: Optional[str] = None,
        verbose: bool = False,
    ):
        self.district_id = district_id
        self.postgres_config = postgres_config
        self.verbose = verbose

        if self.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info(f"Initializing PhiEducationalAgent for district: {district_id}")

        # Create Robust PostgreSQL tools with autocommit to prevent transaction errors
        # This fixes "current transaction is aborted, commands ignored" errors
        self.postgres_tools = RobustPostgresTools(
            db_name=postgres_config.get("database"),
            user=postgres_config.get("user"),
            password=postgres_config.get("password"),
            host=postgres_config.get("host"),
            port=postgres_config.get("port", 5432),
            schema=postgres_config.get("schema", "public"),
            district_id=district_id,
            run_queries=True,
            inspect_queries=verbose,
        )

        # Create the agent with comprehensive MV instructions
        self.agent = Agent(
            name="Educational Data Analytics Agent",
            model=OpenAIChat(
                id="gpt-4o-mini",
                api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
            ),
            tools=[self.postgres_tools],
            instructions=self._get_mv_aware_instructions(),
            show_tool_calls=False,
            markdown=True,
            description=f"AI agent for educational software analytics in district {district_id}",
            debug_mode=verbose,
        )

        logger.info(f"PhiEducationalAgent initialized with MV knowledge for district: {district_id}")

    def _get_mv_aware_instructions(self) -> list:
        """Get comprehensive instructions with complete MV schema knowledge."""
        return [
            f"You are an AI assistant specialized in educational software analytics for district {self.district_id}.",
            "",
            "=" * 80,
            "CRITICAL: ALWAYS USE MATERIALIZED VIEWS - NEVER RAW TABLES",
            "=" * 80,
            "",
            "You MUST use materialized views (mv_*) for ALL queries. They are 10-100x faster.",
            "The ROI data is PRE-CALCULATED in the views - do NOT try to calculate ROI yourself.",
            "",
            "=" * 80,
            "MATERIALIZED VIEW SCHEMA - EXACT COLUMN NAMES",
            "=" * 80,
            "",
            "### 1. mv_software_usage_analytics_v4 (PRIMARY - Use for most software queries)",
            "Columns: name, district_id, ids, categories, school_names, user_types, grades,",
            "         grade_ranges, funding_sources, total_cost, students_licensed, authorized,",
            "         district_purchased, url, icon, primary_category, category_type,",
            "         total_minutes, active_users, usage_days, first_use_date, last_use_date,",
            "         active_students, active_teachers, expected_daily_minutes, cost_per_student,",
            "         days_since_start, expected_minutes_to_date, usage_ratio, avg_minutes_per_day,",
            "         roi_status, engagement_rate, usage_compliance",
            "",
            "USE THIS FOR: Software usage, investment return analysis, top software",
            "INVESTMENT METRICS (computed by agent from total_cost and usage_compliance):",
            "  investment_return = (total_cost * usage_compliance) / 100  — show as dollar amount",
            "  unrealized_value  = total_cost - investment_return         — show as dollar amount",
            "NEVER show avg_roi_percentage. Always show Investment Return and Unrealized Value.",
            f"EXAMPLE: SELECT name, total_cost, total_minutes, active_users, usage_compliance, roi_status FROM mv_software_usage_analytics_v4 WHERE district_id = '{self.district_id}' ORDER BY usage_compliance DESC LIMIT 20",
            "",
            "### 2. mv_software_investment_summary (Use for investment/cost analysis)",
            "Columns: software_id, software_name, display_name, district_id, school_name,",
            "         category, funding_source, grade_ranges, user_type, latest_purchase_date,",
            "         last_usage_date, created_at, total_investment, total_licensed_users,",
            "         active_users, avg_utilization, total_minutes, avg_cost_per_student,",
            "         avg_roi_percentage, roi_status, roi_status_priority, authorized, district_purchased",
            "",
            "USE THIS FOR: Investment analysis, budget reports, cost-per-student",
            f"EXAMPLE: SELECT software_name, total_investment, active_users, roi_status FROM mv_software_investment_summary WHERE district_id = '{self.district_id}' AND total_investment > 0 ORDER BY total_investment DESC LIMIT 20",
            "",
            "### 3. mv_dashboard_software_metrics (Use for dashboard overview)",
            "Columns: software_id, name, district_id, school_name, category, funding_source,",
            "         total_cost, user_type, authorized, district_purchased, students_licensed,",
            "         purchase_date, grade_range, created_at, roi_percentage, cost_per_student,",
            "         active_users_30d, active_users_all_time, total_minutes_90d, last_usage_date,",
            "         utilization, roi_status",
            "",
            "USE THIS FOR: Dashboard metrics, overview cards, quick stats",
            f"EXAMPLE: SELECT name, total_cost, roi_percentage, utilization, roi_status FROM mv_dashboard_software_metrics WHERE district_id = '{self.district_id}' ORDER BY total_minutes_90d DESC LIMIT 10",
            "",
            "### 4. mv_dashboard_user_analytics (Use for user counts)",
            "Columns: row_id, district_id, school_id, school_name, user_type, grade,",
            "         total_users, active_users_30d, active_users_all_time, total_usage_minutes_90d",
            "",
            "USE THIS FOR: User counts, student/teacher breakdown, grade-level analysis",
            f"EXAMPLE: SELECT user_type, SUM(total_users) as total, SUM(active_users_30d) as active FROM mv_dashboard_user_analytics WHERE district_id = '{self.district_id}' GROUP BY user_type",
            "",
            "### 5. mv_user_software_utilization_v2 (Use for individual user data)",
            "Columns: software_id, user_id, user_email, first_name, last_name, grade,",
            "         school_id, district_id, user_role, school_name, district_name,",
            "         software_name, software_category, sessions_count, total_minutes,",
            "         minutes_in_school, minutes_at_home, first_active, last_active,",
            "         days_active, avg_weekly_minutes",
            "",
            "USE THIS FOR: Top users, individual usage reports, user-level analysis",
            f"EXAMPLE: SELECT first_name, last_name, software_name, total_minutes FROM mv_user_software_utilization_v2 WHERE district_id = '{self.district_id}' ORDER BY total_minutes DESC LIMIT 20",
            "",
            "### 6. mv_unauthorized_software_analytics_v3 (Use for security/compliance)",
            "Columns: id, name, category, url, district_id, school_name, user_type,",
            "         district_name, total_usage_minutes, unique_users, student_users,",
            "         teacher_users, usage_count, last_used_date, avg_minutes_per_user, refreshed_at",
            "",
            "USE THIS FOR: Unauthorized software monitoring, security dashboards",
            f"EXAMPLE: SELECT name, category, total_usage_minutes, unique_users, student_users FROM mv_unauthorized_software_analytics_v3 WHERE district_id = '{self.district_id}' ORDER BY total_usage_minutes DESC",
            "",
            "### 7. mv_software_usage_by_school_v2 (Use for school-level analysis)",
            "Columns: software_id, software_name, school_id, school_name, district_id,",
            "         total_cost, category, authorized, district_purchased, students_licensed,",
            "         funding_source, user_type, grade, applicable_grade_bands, active_users,",
            "         active_students, active_teachers, total_minutes, usage_days,",
            "         first_use_date, last_use_date, days_since_start, expected_daily_minutes,",
            "         category_type, avg_roi_percentage, roi_status, usage_compliance",
            "",
            "USE THIS FOR: School comparisons, per-school investment return",
            f"EXAMPLE: SELECT school_name, software_name, total_minutes, usage_compliance, roi_status FROM mv_software_usage_by_school_v2 WHERE district_id = '{self.district_id}' ORDER BY total_minutes DESC",
            "",
            "### 8. mv_software_usage_rankings_v4 (Use for rankings/top lists)",
            "Columns: id, name, category, district_id, user_type, school_name,",
            "         funding_source, grade_band, total_cost, total_minutes,",
            "         instance_count, software_ids, context_total_minutes, usage_percentage",
            "",
            "USE THIS FOR: Top software rankings, usage percentage, grade band comparisons",
            f"EXAMPLE: SELECT name, grade_band, total_minutes, usage_percentage FROM mv_software_usage_rankings_v4 WHERE district_id = '{self.district_id}' ORDER BY total_minutes DESC LIMIT 20",
            "",
            "### 9. mv_active_users_summary (Use for active user reports)",
            "Columns: user_id, email, first_name, last_name, role, grade, school_id,",
            "         district_id, school_name, district_name, total_usage_minutes,",
            "         total_sessions, first_active_date, last_active_date, grade_band, full_name",
            "",
            "USE THIS FOR: Active user lists, user engagement reports",
            f"EXAMPLE: SELECT full_name, role, total_usage_minutes, last_active_date FROM mv_active_users_summary WHERE district_id = '{self.district_id}' ORDER BY total_usage_minutes DESC LIMIT 20",
            "",
            "=" * 80,
            "QUERY ROUTING RULES - WHICH MV TO USE",
            "=" * 80,
            "",
            "• 'ROI', 'return on investment', 'best value' → mv_software_usage_analytics_v4 or mv_software_investment_summary",
            "  Show investment_return and unrealized_value (computed from total_cost & usage_compliance). roi_status for categorization only.",
            "",
            "• 'paid software', 'investment', 'cost' → mv_software_investment_summary",
            "  COLUMN: total_investment, avg_cost_per_student",
            "",
            "• 'top software', 'most used', 'usage' → mv_software_usage_analytics_v4",
            "  COLUMN: total_minutes, active_users",
            "",
            "• 'students', 'teachers', 'users count' → mv_dashboard_user_analytics",
            "  COLUMN: total_users, active_users_30d",
            "",
            "• 'top users', 'individual usage' → mv_user_software_utilization_v2",
            "",
            "• 'unauthorized', 'security', 'compliance' → mv_unauthorized_software_analytics_v3",
            "",
            "• 'by school', 'school comparison' → mv_software_usage_by_school_v2",
            "",
            "• 'dashboard', 'overview' → mv_dashboard_software_metrics",
            "",
            "=" * 80,
            "CRITICAL RULES",
            "=" * 80,
            "",
            f"1. ALWAYS filter by district_id = '{self.district_id}'",
            "2. Show Investment Return and Unrealized Value (dollar amounts), NOT avg_roi_percentage",
            "   investment_return = (total_cost * usage_compliance) / 100",
            "   unrealized_value  = total_cost - investment_return",
            "3. Cost column is called 'total_investment' or 'total_cost' NOT 'cost'",
            "4. NEVER show avg_roi_percentage or roi_percentage to the user",
            "5. NEVER join raw tables when a materialized view has the data",
            "6. Use LIMIT for large result sets",
            "7. For paid software with ROI: total_investment > 0",
            "",
            "=" * 80,
            "COMMON QUERY EXAMPLES",
            "=" * 80,
            "",
            "### Paid software sorted by investment value:",
            f"SELECT software_name, total_investment, active_users, roi_status",
            f"FROM mv_software_investment_summary",
            f"WHERE district_id = '{self.district_id}' AND total_investment > 0",
            f"ORDER BY total_investment DESC LIMIT 20;",
            "",
            "### Top software by usage:",
            f"SELECT name, primary_category, total_cost, total_minutes, active_users, usage_compliance, roi_status",
            f"FROM mv_software_usage_analytics_v4",
            f"WHERE district_id = '{self.district_id}'",
            f"ORDER BY total_minutes DESC LIMIT 20;",
            "",
            "### User counts by role:",
            f"SELECT user_type, SUM(total_users) as total, SUM(active_users_30d) as active",
            f"FROM mv_dashboard_user_analytics",
            f"WHERE district_id = '{self.district_id}'",
            f"GROUP BY user_type;",
            "",
            "### Unauthorized software:",
            f"SELECT name, category, total_usage_minutes, unique_users, student_users",
            f"FROM mv_unauthorized_software_analytics_v3",
            f"WHERE district_id = '{self.district_id}'",
            f"ORDER BY total_usage_minutes DESC LIMIT 20;",
            "",
            "=" * 80,
            "RESPONSE FORMAT",
            "=" * 80,
            "",
            "- Return clean HTML (no CSS, JavaScript, markdown code blocks)",
            "- Use <table>, <div>, <h3>, <h4> for structure",
            "- Use user-friendly language (no UUIDs or technical jargon)",
            "- Focus on actionable insights for educators",
            "- Show Investment Return and Unrealized Value as dollar amounts, NOT ROI percentages",
            "- roi_status is for categorization only: High = Good, Moderate = OK, Low = Needs attention",
        ]

    def process_query(self, user_query: str) -> dict:
        """Process user query with MV-aware SQL generation."""
        try:
            logger.info(f"=== PHI AGENT (MV-AWARE) FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # Build contextual query with explicit MV guidance
            contextual_query = f"""
User Question: {user_query}

IMPORTANT INSTRUCTIONS:
1. Use ONLY materialized views (mv_*) for this query - they are 10-100x faster
2. The district_id is: {self.district_id}
3. For ROI queries, use column 'avg_roi_percentage' and 'roi_status' - NOT 'roi'
4. For investment/cost queries, use 'total_investment' or 'total_cost'
5. For paid software with ROI, filter: total_investment > 0

RECOMMENDED MVs for this query:
- For ROI/investment: mv_software_investment_summary or mv_software_usage_analytics_v4
- For usage analytics: mv_software_usage_analytics_v4
- For user counts: mv_dashboard_user_analytics
- For individual users: mv_user_software_utilization_v2
- For unauthorized: mv_unauthorized_software_analytics_v3

Generate and execute the SQL query, then present results in clean HTML format.
Remember: avg_roi_percentage (not roi), total_investment (not cost), roi_status values are 'high', 'moderate', 'low'.
"""

            # Execute with phi agent
            response = self.agent.run(contextual_query)

            # Extract content
            html_content = response.content if hasattr(response, "content") else str(response)

            # Clean up markdown and tool output
            if html_content.startswith("```html\n"):
                html_content = html_content[8:]
            if html_content.endswith("\n```"):
                html_content = html_content[:-4]

            # Remove tool execution traces
            html_content = re.sub(r"\n*Running:\s*\n(\s*-\s*\w+\([^)]*\)\s*\n)*", "", html_content)
            html_content = re.sub(r"Running:\s*\n(\s*-\s*\w+\([^)]*\)\s*\n)*", "", html_content)
            html_content = re.sub(r"\s*-\s*run_query\([^)]*\)\s*", "", html_content)
            html_content = re.sub(r"\s*-\s*\w+\([^)]*\)\s*", "", html_content)
            html_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", html_content)
            html_content = html_content.strip()

            logger.info("✅ PHI AGENT (MV-AWARE) COMPLETED successfully")

            return {
                "html_response": html_content,
                "execution_log": {
                    "district_id": self.district_id,
                    "user_query": user_query,
                    "agent_type": "phi_native",
                    "mv_aware": True,
                } if self.verbose else None,
            }

        except Exception as e:
            logger.error(f"❌ PHI AGENT ERROR: {e}")
            return {
                "html_response": f"<div class='alert alert-danger'>Error: {str(e)}</div>",
                "execution_log": {"error": str(e)} if self.verbose else None,
            }

    def get_district_dashboard(self) -> dict:
        """Generate a comprehensive district dashboard using MVs."""
        return self.process_query(
            "Generate a comprehensive executive dashboard showing overall software usage metrics, "
            "investment summary with investment return and unrealized value for each software, "
            "and key insights for district decision making"
        )

    def analyze_software_roi(self) -> dict:
        """Analyze software investment return using MVs."""
        return self.process_query(
            "Analyze the investment return and unrealized value of our educational software investments. "
            "Use mv_software_usage_analytics_v4 with usage_compliance and total_cost columns. "
            "Show paid software (total_cost > 0) sorted by usage_compliance DESC. "
            "Compute investment_return = (total_cost * usage_compliance) / 100 and unrealized_value = total_cost - investment_return."
        )

    def get_security_insights(self) -> dict:
        """Get security and compliance insights using MVs."""
        return self.process_query(
            "Provide security insights using mv_unauthorized_software_analytics_v3. "
            "Show unauthorized software sorted by total_usage_minutes, including student_users and teacher_users counts."
        )


def create_phi_educational_agent(
    district_id: str, postgres_config: dict, verbose: bool = False
) -> PhiEducationalAgent:
    """Factory function to create a phi-based educational agent with MV knowledge."""
    return PhiEducationalAgent(
        district_id=district_id, postgres_config=postgres_config, verbose=verbose
    )
