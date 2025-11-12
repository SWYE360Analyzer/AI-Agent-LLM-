"""
Intelligent Tool Selection Agent
This agent analyzes user queries and selects relevant database tools dynamically
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat

from district_postgres_tools import DistrictAwarePostgresTools

logger = logging.getLogger(__name__)


class IntelligentToolAgent:
    """
    Educational agent that intelligently selects database tools based on user queries
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

        logger.info(f"Initializing IntelligentToolAgent for district: {district_id}")

        # Initialize database tools
        self.postgres_tools = DistrictAwarePostgresTools(
            host=postgres_config.get("host"),
            port=postgres_config.get("port", 5432),
            db_name=postgres_config.get("database"),
            user=postgres_config.get("user"),
            password=postgres_config.get("password"),
            schema=postgres_config.get("schema", "public"),
            district_id=district_id,
        )

        # Create a simple agent for analysis
        self.analysis_agent = Agent(
            name="Educational Analytics Generator",
            model=OpenAIChat(
                id="gpt-4o-mini", api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
            ),
            instructions=[
                "You are an educational analytics specialist.",
                "You will receive real data from database queries.",
                "Create comprehensive HTML analysis using the provided data.",
                "Use proper HTML structure: tables, divs, headers, etc.",
                "Do not include CSS, JavaScript, or client-side code.",
                "Return pure HTML suitable for React's dangerouslySetInnerHTML.",
                "Focus on actionable insights and clear data presentation.",
            ],
            markdown=True,
        )

        logger.info(f"Agent initialized successfully for district: {district_id}")

    def _analyze_query_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine what data/tools are needed
        """
        query_lower = user_query.lower()

        intent = {"type": "general", "focus": [], "entities": [], "tools_needed": []}

        # Determine query type
        if any(
            word in query_lower for word in ["student", "students", "learner", "pupil"]
        ):
            intent["type"] = "student_analysis"
            intent["focus"].append("students")

        elif any(
            word in query_lower
            for word in ["teacher", "educator", "instructor", "staff"]
        ):
            intent["type"] = "teacher_analysis"
            intent["focus"].append("teachers")

        elif any(
            word in query_lower
            for word in ["user", "users", "profile", "profiles", "people"]
        ):
            intent["type"] = "user_analysis"
            intent["focus"].append("users")

        elif any(
            word in query_lower
            for word in ["investment", "cost", "money", "budget", "roi", "spend"]
        ):
            intent["type"] = "financial_analysis"
            intent["focus"].append("investment")

        elif any(
            word in query_lower
            for word in ["trend", "time", "daily", "weekly", "monthly", "recent"]
        ):
            intent["type"] = "trend_analysis"
            intent["focus"].append("trends")

        elif any(
            word in query_lower
            for word in ["dashboard", "summary", "overview", "executive"]
        ):
            intent["type"] = "dashboard"
            intent["focus"].append("overview")

        elif any(
            word in query_lower
            for word in ["software", "app", "application", "tool", "platform"]
        ):
            intent["type"] = "software_analysis"
            intent["focus"].append("software")

        # Determine specific tools needed based on intent
        if intent["type"] == "student_analysis":
            intent["tools_needed"] = ["get_user_analytics", "get_student_usage_data"]

        elif intent["type"] == "teacher_analysis":
            intent["tools_needed"] = ["get_user_analytics", "get_teacher_usage_data"]

        elif intent["type"] == "user_analysis":
            intent["tools_needed"] = ["get_user_analytics", "get_top_users_by_usage"]

        elif intent["type"] == "financial_analysis":
            intent["tools_needed"] = [
                "get_investment_analysis",
                "get_software_usage_summary",
            ]

        elif intent["type"] == "trend_analysis":
            intent["tools_needed"] = ["get_usage_trends", "get_daily_usage_patterns"]

        elif intent["type"] == "software_analysis":
            intent["tools_needed"] = [
                "get_top_software_by_usage",
                "get_software_usage_summary",
            ]

        elif intent["type"] == "dashboard":
            intent["tools_needed"] = [
                "get_software_usage_summary",
                "get_top_software_by_usage",
                "get_usage_trends",
            ]

        else:
            # Default to basic overview
            intent["tools_needed"] = [
                "get_software_usage_summary",
                "get_district_software_count",
            ]

        return intent

    def _get_user_analytics(self) -> str:
        """Get user analytics data using materialized views"""
        query = """
        SELECT
            user_type,
            total_users,
            active_users_30d,
            active_users_all_time,
            total_usage_minutes_90d
        FROM mv_dashboard_user_analytics
        WHERE district_id = %s
        ORDER BY total_users DESC
        """
        return self.postgres_tools.run_district_query(query)

    def _get_top_users_by_usage(self, limit: int = 20) -> str:
        """Get top users by usage using user utilization view"""
        query = """
        SELECT
            user_email,
            first_name,
            last_name,
            grade,
            school_name,
            software_name,
            software_category,
            total_minutes,
            sessions_count,
            avg_weekly_minutes,
            last_active
        FROM mv_user_software_utilization
        WHERE district_id = %s
        ORDER BY total_minutes DESC
        LIMIT %s
        """

        try:
            conn = self.postgres_tools._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, (self.district_id, limit))
                results = cursor.fetchall()

                if not results:
                    return "No user usage data found."

                html = f"<div class='top-users'>\n"
                html += f"<h3>👥 Top {limit} Users by Usage (Real Data)</h3>\n"
                html += "<table class='table table-striped'>\n"
                html += "<thead><tr><th>User</th><th>Grade</th><th>School</th><th>Top Software</th><th>Total Minutes</th><th>Sessions</th></tr></thead>\n"
                html += "<tbody>\n"

                for row in results:
                    name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
                    if not name:
                        name = row["user_email"].split("@")[0]

                    html += f"<tr>\n"
                    html += f"<td><strong>{name}</strong><br><small>{row['user_email']}</small></td>\n"
                    html += f"<td>{row['grade'] or 'N/A'}</td>\n"
                    html += f"<td>{row['school_name'] or 'N/A'}</td>\n"
                    html += f"<td>{row['software_name']}<br><small>{row['software_category'] or 'N/A'}</small></td>\n"
                    html += f"<td>{row['total_minutes']:,.0f}</td>\n"
                    html += f"<td>{row['sessions_count']}</td>\n"
                    html += f"</tr>\n"

                html += "</tbody>\n</table>\n</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return f"Error retrieving top users: {str(e)}"

    def _call_intelligent_tools(self, user_query: str) -> Dict[str, Any]:
        """
        Intelligently call database tools based on query analysis
        """
        tool_results = {}
        sql_queries = []

        # Analyze the query to determine intent
        intent = self._analyze_query_intent(user_query)

        logger.info(f"🧠 Query Intent Analysis:")
        logger.info(f"   Type: {intent['type']}")
        logger.info(f"   Focus: {intent['focus']}")
        logger.info(f"   Tools Needed: {intent['tools_needed']}")

        # Call only the relevant tools
        for tool_name in intent["tools_needed"]:
            try:
                logger.info(f"   📊 Calling {tool_name}()...")
                start_time = time.time()

                if tool_name == "get_software_usage_summary":
                    result = self.postgres_tools.get_software_usage_summary()
                elif tool_name == "get_top_software_by_usage":
                    result = self.postgres_tools.get_top_software_by_usage(10)
                elif tool_name == "get_usage_trends":
                    result = self.postgres_tools.get_usage_trends(30)
                elif tool_name == "get_district_software_count":
                    result = self.postgres_tools.get_district_software_count()
                elif tool_name == "get_investment_analysis":
                    result = self.postgres_tools.get_investment_analysis()
                elif tool_name == "get_user_analytics":
                    result = self._get_user_analytics()
                elif tool_name == "get_top_users_by_usage":
                    result = self._get_top_users_by_usage(20)
                else:
                    logger.warning(f"   ⚠️  Unknown tool: {tool_name}")
                    continue

                execution_time = time.time() - start_time

                tool_results[tool_name] = result
                sql_queries.append(
                    {
                        "tool": tool_name,
                        "query": f"Executed {tool_name}()",
                        "timestamp": execution_time,
                        "result_length": len(str(result)),
                    }
                )

                logger.info(f"   ✅ {tool_name} completed in {execution_time:.3f}s")

            except Exception as e:
                logger.error(f"   ❌ {tool_name} failed: {e}")
                tool_results[tool_name] = f"Error: {str(e)}"

        return {
            "tool_results": tool_results,
            "sql_queries": sql_queries,
            "intent": intent,
        }

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process query with intelligent tool selection
        """
        execution_log = {
            "district_id": self.district_id,
            "user_query": user_query,
            "sql_queries": [],
            "tool_calls": [],
            "query_intent": {},
            "execution_time": None,
            "error": None,
        }

        start_time = time.time()

        try:
            logger.info(
                f"=== INTELLIGENT PROCESSING FOR DISTRICT {self.district_id} ==="
            )
            logger.info(f"User Query: {user_query}")

            # STEP 1: Intelligent tool selection and execution
            logger.info("🧠 STEP 1: Analyzing query and selecting relevant tools...")
            tool_data = self._call_intelligent_tools(user_query)

            execution_log["sql_queries"] = tool_data["sql_queries"]
            execution_log["tool_calls"] = [
                {"tool": q["tool"], "timestamp": q["timestamp"]}
                for q in tool_data["sql_queries"]
            ]
            execution_log["query_intent"] = tool_data["intent"]

            # STEP 2: Generate HTML analysis with relevant data
            logger.info("🎨 STEP 2: Generating targeted HTML analysis...")

            # Build context based on what tools were called
            data_context = f"User Question: {user_query}\n\n"
            data_context += f"Query Intent: {tool_data['intent']['type']} (Focus: {', '.join(tool_data['intent']['focus'])})\n\n"
            data_context += "REAL DATA from database:\n\n"

            for tool_name, result in tool_data["tool_results"].items():
                data_context += f"{tool_name.upper()}:\n{result}\n\n"

            html_prompt = f"""
            {data_context}

            Create a targeted HTML response that:
            - Directly answers the user's specific question
            - Uses only the relevant data provided above
            - Presents data in clean HTML tables and sections
            - Provides insights specific to the user's intent ({tool_data["intent"]["type"]})
            - Uses proper HTML structure (div, table, h3, etc.)
            - Does not include any JavaScript, CSS, or client-side code

            Focus on the user's specific request rather than providing a generic overview.
            """

            response = self.analysis_agent.run(html_prompt)
            html_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Clean up any remaining markdown
            if html_content.startswith("```html\n"):
                html_content = html_content[8:]
            if html_content.endswith("\n```"):
                html_content = html_content[:-4]

            execution_log["execution_time"] = time.time() - start_time

            logger.info(
                f"✅ INTELLIGENT PROCESSING COMPLETED in {execution_log['execution_time']:.2f}s"
            )
            logger.info(f"🧠 Intent: {tool_data['intent']['type']}")
            logger.info(f"📊 Relevant Tools Called: {len(execution_log['tool_calls'])}")

            if self.verbose:
                logger.debug(
                    f"📋 Full Execution Log: {json.dumps(execution_log, indent=2)}"
                )

            return {
                "html_response": html_content,
                "execution_log": execution_log if self.verbose else None,
            }

        except Exception as e:
            execution_log["error"] = str(e)
            execution_log["execution_time"] = time.time() - start_time

            logger.error(f"❌ INTELLIGENT PROCESSING FAILED: {e}")

            return {
                "html_response": f"<div class='alert alert-danger'>Error: {str(e)}</div>",
                "execution_log": execution_log if self.verbose else None,
            }

    def get_district_dashboard(self) -> Dict[str, Any]:
        """Generate a comprehensive district dashboard."""
        return self.process_query(
            "Generate a comprehensive executive dashboard showing overall metrics, top software, usage trends, and actionable recommendations"
        )

    def analyze_software_roi(self) -> Dict[str, Any]:
        """Analyze software return on investment."""
        return self.process_query(
            "Analyze the ROI and cost-effectiveness of our educational software, identifying high-value and underutilized applications"
        )

    def get_security_insights(self) -> Dict[str, Any]:
        """Get security and compliance insights."""
        return self.process_query(
            "Provide security and compliance insights including unauthorized usage patterns and risk indicators"
        )


def create_intelligent_agent(
    district_id: str, postgres_config: dict, verbose: bool = False
) -> IntelligentToolAgent:
    """
    Factory function to create an intelligent tool selection agent.
    """
    return IntelligentToolAgent(
        district_id=district_id, postgres_config=postgres_config, verbose=verbose
    )
