"""
Proper Phi-based Educational Analytics Agent
Uses phi's native PostgreSQL tools for dynamic query generation
"""

import logging
import os
from typing import Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.postgres import PostgresTools

logger = logging.getLogger(__name__)


class PhiEducationalAgent:
    """
    Educational agent using phi's native PostgreSQL tools for dynamic query generation
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

        # Create PostgreSQL tools with district-aware context
        self.postgres_tools = PostgresTools(
            db_name=postgres_config.get("database"),
            user=postgres_config.get("user"),
            password=postgres_config.get("password"),
            host=postgres_config.get("host"),
            port=postgres_config.get("port", 5432),
            run_queries=True,
            inspect_queries=verbose,  # Show query plans in verbose mode
            summarize_tables=True,
        )

        # Create the agent with comprehensive instructions
        self.agent = Agent(
            name="Educational Data Analytics Agent",
            model=OpenAIChat(
                id="gpt-4o-mini", api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
            ),
            tools=[self.postgres_tools],
            instructions=self._get_comprehensive_instructions(),
            show_tool_calls=False,  # Hide tool calls from user response
            markdown=True,
            description=f"AI agent for educational software analytics in district {district_id}",
            debug_mode=verbose,
        )

        logger.info(
            f"PhiEducationalAgent initialized successfully for district: {district_id}"
        )

    def _get_comprehensive_instructions(self) -> list:
        """Get comprehensive instructions for the agent including schema knowledge"""
        return [
            f"You are an AI assistant specialized in educational software analytics for district {self.district_id}.",
            "IMPORTANT: You have access to a PostgreSQL database with educational software data.",
            "You MUST use the run_query function to execute SQL queries to get real data.",
            "NEVER provide mock or example data - always query the database first.",
            "DATABASE SCHEMA KNOWLEDGE:",
            "The database contains these key tables:",
            "- software: Contains software applications with columns like id, name, category, district_id, total_cost, students_licensed, authorized",
            "- software_usage: Contains usage records with columns like software_id, user_id, date, minutes_used, user_type",
            "- profiles: Contains user profiles with columns like id, email, first_name, last_name, role, grade, district_id, school_id",
            "- schools: Contains school information with columns like id, name, district_id",
            "- districts: Contains district information",
            "MATERIALIZED VIEWS AVAILABLE (use these for better performance):",
            "- mv_software_usage_analytics_v3: Comprehensive software analytics with ROI data",
            "- mv_software_investment_summary: Investment analysis by software",
            "- mv_dashboard_software_metrics: Dashboard-ready software metrics",
            "- mv_user_software_utilization: User-level software utilization data",
            "- mv_dashboard_user_analytics: User analytics by district",
            "CRITICAL DISTRICT FILTERING:",
            f"- ALL queries MUST include 'WHERE district_id = '{self.district_id}' to ensure data security",
            "- Never show data from other districts",
            "- Always verify district_id in WHERE clauses",
            "QUERY GENERATION GUIDELINES:",
            "1. Analyze the user's question to understand what data they need",
            "2. Choose the most appropriate table/view for the query",
            "3. Always include district_id filter in WHERE clause",
            "4. Use efficient queries with proper JOINs when needed",
            "5. Limit results to reasonable amounts (use LIMIT for large datasets)",
            "RESPONSE FORMAT:",
            "- Convert all responses to clean HTML (no CSS, JavaScript, or styling)",
            "- Use proper HTML elements: tables, divs, headers, lists",
            "- Present data in tables when showing multiple records",
            "- Provide insights and recommendations based on real data",
            "- Never wrap responses in markdown code blocks",
            "- Return pure HTML suitable for React dangerouslySetInnerHTML",
            "- IMPORTANT: Use user-friendly titles and headings",
            "- Never show technical district IDs in titles or headings",
            "- Use descriptive titles like 'District Executive Summary' instead of 'Executive Summary for District 3ef51192-1070-4090-908d-ef3ab03b4325'",
            "- Focus on business-friendly language that administrators and educators would understand",
            "- Avoid technical jargon, UUIDs, or database terminology in user-facing content",
            "EXAMPLE QUERY PATTERNS:",
            "- For user questions: JOIN software_usage with profiles and software tables",
            "- For investment analysis: Use mv_software_investment_summary view",
            "- For usage trends: Query software_usage grouped by date",
            "- For top software: Use mv_software_usage_analytics_v3 ordered by usage metrics",
            "- For student data: Filter profiles where role = 'student'",
            "- For teacher data: Filter profiles where role = 'teacher'",
            "IMPORTANT: When the user asks about students, users, teachers, or specific people,",
            "you MUST query the relevant user/profile tables, not just software tables.",
            "Use JOINs to connect software_usage, profiles, and software tables as needed.",
            "SAMPLE QUERIES FOR COMMON REQUESTS:",
            "- 'Top students by usage': SELECT p.first_name, p.last_name, SUM(su.minutes_used) FROM profiles p JOIN software_usage su ON p.id = su.user_id WHERE p.district_id = '{district_id}' AND p.role = 'student' GROUP BY p.id ORDER BY SUM(su.minutes_used) DESC",
            "- 'Software investments': SELECT * FROM mv_software_investment_summary WHERE district_id = '{district_id}' ORDER BY total_investment DESC",
            "- 'Usage trends': SELECT date, SUM(minutes_used) FROM software_usage su JOIN software s ON su.software_id = s.id WHERE s.district_id = '{district_id}' GROUP BY date ORDER BY date DESC",
            "SECURITY & PRIVACY:",
            "- Never expose data from other districts",
            "- Maintain student and user privacy",
            "- Always verify district authorization",
            "- NEVER show technical district IDs (UUIDs) in user-facing content",
            "- Replace district ID references with user-friendly terms like 'Your District' or 'District Overview'",
            "USER-FRIENDLY CONTENT GUIDELINES:",
            "- Use business-friendly language appropriate for school administrators and educators",
            "- Avoid technical database terms, UUIDs, or system identifiers in responses",
            "- Use descriptive titles like 'District Executive Summary', 'Student Usage Report', 'Software Investment Analysis'",
            "- Focus on actionable insights rather than technical data details",
            "- Present information in a way that helps decision-making",
            "Remember: Your goal is to provide accurate, data-driven insights about educational technology usage in this specific district.",
        ]

    def process_query(self, user_query: str) -> dict:
        """
        Process user query using phi's native PostgreSQL tools
        """
        try:
            logger.info(f"=== PHI AGENT PROCESSING FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # Add district context to the query
            contextual_query = f"""
            District Context: {self.district_id}

            User Question: {user_query}

            Please analyze this question and use the run_query function to get the relevant data from the database.
            Remember to:
            1. Always filter by district_id = '{self.district_id}' in your SQL queries
            2. Use appropriate JOINs when connecting tables
            3. Choose the most relevant tables/views for the question
            4. Present results in clean HTML format
            5. Provide insights based on the real data returned

            Generate and execute the appropriate SQL query to answer this question with real data.
            """

            # Let phi agent handle the query generation and execution
            response = self.agent.run(contextual_query)

            # Extract HTML content
            html_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Clean up any tool call output and markdown formatting
            if html_content.startswith("```html\n"):
                html_content = html_content[8:]
            if html_content.endswith("\n```"):
                html_content = html_content[:-4]

            # Remove any phi tool call output patterns
            import re

            # Remove patterns like "\nRunning:\n - run_query(query=...)\n - run_query(query=...)\n"
            html_content = re.sub(
                r"\n*Running:\s*\n(\s*-\s*\w+\([^)]*\)\s*\n)*", "", html_content
            )
            # Remove any standalone tool execution traces
            html_content = re.sub(
                r"Running:\s*\n(\s*-\s*\w+\([^)]*\)\s*\n)*", "", html_content
            )
            # Remove any remaining tool call patterns
            html_content = re.sub(r"\s*-\s*run_query\([^)]*\)\s*", "", html_content)
            html_content = re.sub(r"\s*-\s*\w+\([^)]*\)\s*", "", html_content)
            # Clean up extra newlines
            html_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", html_content)
            # Remove leading/trailing whitespace
            html_content = html_content.strip()

            logger.info(f"âœ… PHI AGENT COMPLETED successfully")

            # Note: phi agent handles tool calling internally, so we don't track individual SQL queries
            return {
                "html_response": html_content,
                "execution_log": {
                    "district_id": self.district_id,
                    "user_query": user_query,
                    "agent_type": "phi_native",
                    "tools_available": ["PostgresTools with run_query capability"],
                    "note": "Phi agent handles dynamic SQL generation based on natural language",
                }
                if self.verbose
                else None,
            }

        except Exception as e:
            logger.error(f"âŒ PHI AGENT ERROR: {e}")
            return {
                "html_response": f"<div class='alert alert-danger'>Error: {str(e)}</div>",
                "execution_log": {
                    "error": str(e),
                    "district_id": self.district_id,
                    "user_query": user_query,
                }
                if self.verbose
                else None,
            }

    def get_district_dashboard(self) -> dict:
        """Generate a comprehensive district dashboard"""
        return self.process_query(
            "Generate a comprehensive executive dashboard showing overall software usage metrics, "
            "top software by usage, recent trends, and key insights for district decision making"
        )

    def analyze_software_roi(self) -> dict:
        """Analyze software return on investment"""
        return self.process_query(
            "Analyze the ROI and cost-effectiveness of our educational software investments, "
            "showing which software provides the best value and identifying underutilized applications"
        )

    def get_security_insights(self) -> dict:
        """Get security and compliance insights"""
        return self.process_query(
            "Provide security insights including unauthorized software usage patterns, "
            "unusual access patterns, and compliance status summary"
        )


def create_phi_educational_agent(
    district_id: str, postgres_config: dict, verbose: bool = False
) -> PhiEducationalAgent:
    """
    Factory function to create a phi-based educational agent
    """
    return PhiEducationalAgent(
        district_id=district_id, postgres_config=postgres_config, verbose=verbose
    )
