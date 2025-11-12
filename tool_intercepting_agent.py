"""
Permanent Solution: Tool Call Intercepting Educational Agent

This implementation ensures that database tools are properly called
by intercepting the agent response and handling tool calls explicitly.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat

from district_postgres_tools import DistrictAwarePostgresTools

logger = logging.getLogger(__name__)


class ToolCallInterceptingAgent:
    """
    Educational agent that intercepts and properly handles tool calls
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

        # Set logging level
        if self.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info(
            f"Initializing ToolCallInterceptingAgent for district: {district_id}"
        )

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

        # Create a simple agent for analysis (without complex tool calling)
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

    def _call_database_tools_for_query(self, user_query: str) -> Dict[str, Any]:
        """
        Intelligently call database tools based on the user query
        """
        tool_results = {}
        sql_queries = []

        # Determine which tools to call based on query content
        query_lower = user_query.lower()

        # Always call these for comprehensive analysis
        standard_tools = [
            ("get_software_usage_summary", "usage_summary"),
            ("get_top_software_by_usage", "top_software"),
            ("get_usage_trends", "usage_trends"),
            ("get_district_software_count", "software_count"),
        ]

        logger.info(f"ðŸ”§ Calling {len(standard_tools)} database tools...")

        for tool_name, result_key in standard_tools:
            try:
                logger.info(f"   ðŸ“Š Calling {tool_name}()...")
                start_time = time.time()

                if tool_name == "get_software_usage_summary":
                    result = self.postgres_tools.get_software_usage_summary()
                elif tool_name == "get_top_software_by_usage":
                    result = self.postgres_tools.get_top_software_by_usage(10)
                elif tool_name == "get_usage_trends":
                    result = self.postgres_tools.get_usage_trends(30)
                elif tool_name == "get_district_software_count":
                    result = self.postgres_tools.get_district_software_count()

                execution_time = time.time() - start_time

                tool_results[result_key] = result
                sql_queries.append(
                    {
                        "tool": tool_name,
                        "query": f"Executed {tool_name}()",
                        "timestamp": execution_time,
                        "result_length": len(str(result)),
                    }
                )

                logger.info(f"   âœ… {tool_name} completed in {execution_time:.3f}s")

            except Exception as e:
                logger.error(f"   âŒ {tool_name} failed: {e}")
                tool_results[result_key] = f"Error: {str(e)}"

        # Additional specific tools based on query content
        if any(
            keyword in query_lower
            for keyword in ["investment", "cost", "roi", "money", "budget"]
        ):
            logger.info(
                "   ðŸ’° Query mentions investments/costs - gathering additional financial data..."
            )
            try:
                logger.info("   ðŸ’¼ Calling get_investment_analysis()...")
                start_time = time.time()
                investment_result = self.postgres_tools.get_investment_analysis()
                execution_time = time.time() - start_time

                tool_results["investment_analysis"] = investment_result
                sql_queries.append(
                    {
                        "tool": "get_investment_analysis",
                        "query": "Executed get_investment_analysis()",
                        "timestamp": execution_time,
                        "result_length": len(str(investment_result)),
                    }
                )

                logger.info(
                    f"   âœ… get_investment_analysis completed in {execution_time:.3f}s"
                )
            except Exception as e:
                logger.error(f"   âŒ get_investment_analysis failed: {e}")
                tool_results["investment_analysis"] = f"Error: {str(e)}"

        if any(
            keyword in query_lower for keyword in ["trend", "time", "growth", "decline"]
        ):
            logger.info(
                "   ðŸ“ˆ Query mentions trends - gathering additional trend data..."
            )
            # Could add more specific trend queries here

        return {"tool_results": tool_results, "sql_queries": sql_queries}

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process query with guaranteed database tool calling
        """
        execution_log = {
            "district_id": self.district_id,
            "user_query": user_query,
            "sql_queries": [],
            "tool_calls": [],
            "agent_reasoning": [],
            "execution_time": None,
            "error": None,
        }

        start_time = time.time()

        try:
            logger.info(f"=== PROCESSING QUERY FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # STEP 1: Force database tool calls
            logger.info("ðŸ”§ STEP 1: Calling database tools...")
            tool_data = self._call_database_tools_for_query(user_query)

            execution_log["sql_queries"] = tool_data["sql_queries"]
            execution_log["tool_calls"] = [
                {"tool": q["tool"], "timestamp": q["timestamp"]}
                for q in tool_data["sql_queries"]
            ]

            # STEP 2: Generate HTML analysis with real data
            logger.info("ðŸŽ¨ STEP 2: Generating HTML analysis...")

            analysis_prompt = f"""
            User Question: {user_query}
            District: {self.district_id}

            I have gathered the following REAL data from the database:

            1. SOFTWARE USAGE SUMMARY:
            {tool_data["tool_results"].get("usage_summary", "No data available")}

            2. TOP SOFTWARE BY USAGE:
            {tool_data["tool_results"].get("top_software", "No data available")}

            3. USAGE TRENDS (last 30 days):
            {tool_data["tool_results"].get("usage_trends", "No data available")}

            4. TOTAL SOFTWARE COUNT:
            {tool_data["tool_results"].get("software_count", "No data available")}

            5. INVESTMENT ANALYSIS (if applicable):
            {tool_data["tool_results"].get("investment_analysis", "Not applicable for this query")}

            Create a comprehensive HTML response that:
            - Directly answers the user's question using this real data
            - Presents data in clean HTML tables and sections
            - Provides actionable insights based on actual numbers
            - Uses proper HTML structure (div, table, h3, h4, etc.)
            - Does not include any JavaScript, CSS, or client-side code
            - Focuses on educational technology insights and recommendations

            Be specific about the numbers and trends you see in the data.
            """

            response = self.analysis_agent.run(analysis_prompt)
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
                f"âœ… QUERY COMPLETED in {execution_log['execution_time']:.2f}s"
            )
            logger.info(
                f"ðŸ“Š Database Tools Called: {len(execution_log['tool_calls'])}"
            )

            if self.verbose:
                logger.debug(
                    f"ðŸ“‹ Full Execution Log: {json.dumps(execution_log, indent=2)}"
                )

            return {
                "html_response": html_content,
                "execution_log": execution_log if self.verbose else None,
            }

        except Exception as e:
            execution_log["error"] = str(e)
            execution_log["execution_time"] = time.time() - start_time

            logger.error(f"âŒ ERROR processing query: {e}")

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


def create_tool_intercepting_agent(
    district_id: str, postgres_config: dict, verbose: bool = False
) -> ToolCallInterceptingAgent:
    """
    Factory function to create a tool-call intercepting educational agent.
    """
    return ToolCallInterceptingAgent(
        district_id=district_id, postgres_config=postgres_config, verbose=verbose
    )
