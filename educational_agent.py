import json
import logging
import os
from typing import Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat

from district_postgres_tools import DistrictAwarePostgresTools

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Add file handler for persistent logs
        logging.FileHandler("educational_agent.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


class EducationalDataAgent:
    """
    District-aware AI agent for educational software analytics.
    Enforces district-level data access and provides insights on software usage.
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

        # Set logging level based on verbose mode
        if self.verbose:
            logger.setLevel(logging.DEBUG)
            # Also set the phi logger to debug
            phi_logger = logging.getLogger("phi")
            phi_logger.setLevel(logging.DEBUG)

        logger.info(f"Initializing EducationalDataAgent for district: {district_id}")
        logger.debug(f"Postgres config: {self._sanitize_config(postgres_config)}")

        # Initialize district-aware PostgreSQL tools with verbose logging
        self.postgres_tools = DistrictAwarePostgresTools(
            host=postgres_config.get("host"),
            port=postgres_config.get("port", 5432),
            db_name=postgres_config.get("database"),
            user=postgres_config.get("user"),
            password=postgres_config.get("password"),
            schema=postgres_config.get("schema", "public"),
            district_id=district_id,
        )

        # Initialize the AI agent with proper tool configuration
        self.agent = Agent(
            name="Educational Data Analytics Agent",
            model=OpenAIChat(
                id="gpt-4o-mini", api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
            ),
            tools=[self.postgres_tools],
            instructions=self._get_agent_instructions(),
            show_tool_calls=True,  # Show tool execution details
            markdown=True,
            description=f"AI agent specialized in educational software analytics for district {district_id}",
            debug_mode=self.verbose,  # Enable debug mode for detailed logging
            use_tools=True,  # Explicitly enable tool usage
            max_tool_calls=10,  # Allow multiple tool calls per response
        )

        logger.info(f"Agent initialized successfully for district: {district_id}")

    def _sanitize_config(self, config: dict) -> dict:
        """Sanitize config for logging (remove sensitive data)."""
        sanitized = config.copy()
        if "password" in sanitized:
            sanitized["password"] = "***"
        return sanitized

    def _get_agent_instructions(self) -> list:
        """Get comprehensive instructions for the educational data agent."""

        # HTML conversion instruction similar to text processing agent
        html_conversion_instruction = (
            "IMPORTANT: Convert all responses into clean, well-structured HTML. "
            "Remove any CSS styles, JavaScript code, or script tags. "
            "Use appropriate semantic HTML elements such as tables, lists, paragraphs, and divs. "
            "Do not include any styling or interactive elements. "
            "Never wrap your HTML response in markdown code blocks (```html). "
            "Return pure HTML that can be directly used with React's dangerouslySetInnerHTML."
        )

        return [
            f"You are an AI assistant specialized in educational software analytics for district {self.district_id}.",
            "CORE RESPONSIBILITIES:",
            "- Analyze software usage patterns and trends in educational settings",
            "- Provide insights on software ROI, adoption rates, and utilization",
            "- Help identify underused or overused software applications",
            "- Generate actionable recommendations for software management",
            "- Answer questions about district-specific educational technology data",
            "DATA ACCESS RULES:",
            f"- You can ONLY access data for district {self.district_id}",
            "- All database queries are automatically filtered by district_id",
            "- You can only perform read-only operations (SELECT, COUNT, SUM, etc.)",
            "- Never attempt to modify, delete, or insert data",
            "CRITICAL DATABASE USAGE REQUIREMENT:",
            "- You MUST ALWAYS call the database tools DIRECTLY in your response",
            "- NEVER generate JavaScript code or async functions",
            "- NEVER provide mock, fake, or example data in your responses",
            "- For ANY data analysis request, you MUST call these tools FIRST:",
            "  * get_software_usage_summary() - Call this tool to get overall metrics",
            "  * get_top_software_by_usage(10) - Call this tool to get most used software",
            "  * get_usage_trends(30) - Call this tool to get recent trends",
            "  * get_district_software_count() - Call this tool to get total count",
            "- After calling the tools and getting the data, THEN create HTML with the results",
            "- If no data is found, explicitly state that no data is available",
            "- Example: First call get_top_software_by_usage(10), wait for results, then create HTML table with those results",
            # Use the same pattern as text processing agent
            html_conversion_instruction,
            "TOOL CALLING WORKFLOW:",
            "- BEFORE creating any HTML, you must call the appropriate database tools",
            "- DO NOT generate JavaScript, async functions, or client-side code",
            "- Call tools like: get_top_software_by_usage(10) and wait for the result",
            "- Use the actual data returned from tools to create your HTML response",
            "- Example workflow: 1) Call get_top_software_by_usage(10) 2) Get results 3) Create HTML table with actual data",
            "HTML STRUCTURE GUIDELINES:",
            "- Use <div class='dashboard'> for main containers",
            "- Use <table class='table table-striped'> for data tables",
            "- Use <h3> or <h4> tags for section headers",
            "- Use <div class='alert alert-info'> for insights and recommendations",
            "- Use <span class='badge badge-success'> for positive metrics",
            "- Use <span class='badge badge-warning'> for concerning metrics",
            "- Use <div class='row'> and <div class='col-md-*'> for layout",
            "QUERY OPTIMIZATION:",
            "- Prefer using materialized views when available for faster performance",
            "- Use efficient SQL queries with proper filtering",
            "- Limit large result sets to prevent performance issues",
            "- Always include district_id in WHERE clauses",
            "EDUCATIONAL CONTEXT:",
            "- Understand common educational software categories (LMS, productivity, STEM, etc.)",
            "- Consider academic calendars and seasonal usage patterns",
            "- Relate insights to educational outcomes when possible",
            "- Provide context-aware recommendations for educators and administrators",
            "WORKFLOW FOR EXECUTIVE SUMMARIES:",
            "1. FIRST: Use get_software_usage_summary() to get overall metrics",
            "2. SECOND: Use get_top_software_by_usage(10) to get most used software",
            "3. THIRD: Use get_usage_trends(30) to get recent trends",
            "4. FOURTH: Use run_district_query() for any additional specific data needed",
            "5. FINALLY: Analyze the real data and provide insights based on actual numbers",
            "SAMPLE QUERIES YOU CAN HELP WITH:",
            "- 'Show me software with declining usage this quarter'",
            "- 'Which schools have the highest ROI software?'",
            "- 'What unauthorized software is being used most?'",
            "- 'Which licenses are expiring soon?'",
            "- 'Compare math software ROI across grade levels'",
            "- 'Generate an executive summary of software usage'",
            "SAFETY & PRIVACY:",
            "- Never expose data from other districts",
            "- Maintain student and user privacy in all responses",
            "- Flag any unusual query patterns or potential security issues",
            "- Always verify district authorization before processing requests",
        ]

    def process_query(self, user_query: str) -> dict:
        """
        Process a user query about educational software analytics.

        Args:
            user_query: Natural language question about software usage/analytics

        Returns:
            Dict containing HTML response and execution details
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

        import time

        start_time = time.time()

        try:
            logger.info(f"=== PROCESSING QUERY FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # Add district context to the query
            contextual_query = f"""
            District Context: {self.district_id}

            User Question: {user_query}

            MANDATORY WORKFLOW - Follow these exact steps:
            1. FIRST: Call get_software_usage_summary() to get real usage data
            2. SECOND: Call get_top_software_by_usage(10) to get top software data
            3. THIRD: Call get_usage_trends(30) to get trend data
            4. FOURTH: Use the ACTUAL results from these tool calls to create your HTML response

            DO NOT:
            - Generate JavaScript or async code
            - Use mock/fake data
            - Create client-side function calls

            DO:
            - Call the database tools directly and immediately
            - Wait for real results from each tool call
            - Create HTML tables/content using the actual returned data

            Please analyze the educational software data for this district and provide insights.
            Focus on actionable recommendations and clear data visualization using REAL data from tool calls.
            """

            logger.debug(f"Contextual Query: {contextual_query}")

            # Create a custom handler to capture SQL queries and tool calls
            if self.verbose:
                # Monkey patch the postgres tools to capture SQL queries
                original_run_query = self.postgres_tools.run_district_query

                def logged_run_query(query):
                    logger.info(f"🔍 EXECUTING SQL: {query}")
                    execution_log["sql_queries"].append(
                        {"query": query, "timestamp": time.time() - start_time}
                    )
                    result = original_run_query(query)
                    logger.info(
                        f"✅ SQL RESULT: {result[:200]}..."
                        if len(str(result)) > 200
                        else f"✅ SQL RESULT: {result}"
                    )
                    return result

                self.postgres_tools.run_district_query = logged_run_query

            # Process with the AI agent - let it handle HTML formatting via instructions
            logger.info("🤖 Starting AI Agent Processing...")
            response = self.agent.run(contextual_query)

            # Capture agent reasoning if available
            if hasattr(response, "messages") and self.verbose:
                for message in response.messages:
                    if hasattr(message, "content"):
                        execution_log["agent_reasoning"].append(
                            {
                                "role": getattr(message, "role", "unknown"),
                                "content": message.content[:500] + "..."
                                if len(str(message.content)) > 500
                                else str(message.content),
                                "timestamp": time.time() - start_time,
                            }
                        )

            # Simple cleanup like in text processing agent
            processed_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            logger.debug(f"Raw AI Response: {processed_content[:300]}...")

            # Basic cleanup similar to api.py pattern
            if processed_content.startswith("```html\n"):
                processed_content = processed_content[8:]
                logger.debug("Removed ```html\n prefix")
            if processed_content.endswith("\n```"):
                processed_content = processed_content[:-4]
                logger.debug("Removed \n``` suffix")

            execution_log["execution_time"] = time.time() - start_time

            logger.info(f"✅ QUERY COMPLETED in {execution_log['execution_time']:.2f}s")
            logger.info(f"📊 SQL Queries Executed: {len(execution_log['sql_queries'])}")

            if self.verbose:
                logger.debug(
                    f"📋 Full Execution Log: {json.dumps(execution_log, indent=2)}"
                )

            return {
                "html_response": processed_content,
                "execution_log": execution_log if self.verbose else None,
            }

        except Exception as e:
            execution_log["error"] = str(e)
            execution_log["execution_time"] = time.time() - start_time

            logger.error(f"❌ ERROR processing query: {e}")
            logger.error(
                f"📋 Error Execution Log: {json.dumps(execution_log, indent=2)}"
            )

            return {
                "html_response": self._format_error_response(str(e)),
                "execution_log": execution_log if self.verbose else None,
            }

    def _format_error_response(self, error_message: str) -> str:
        """Format error messages in HTML."""
        return f"""
        <div class="alert alert-danger">
            <h4>⚠️ Error Processing Request</h4>
            <p>An error occurred while processing your request:</p>
            <code>{error_message}</code>
            <p>Please try rephrasing your question or contact support if the issue persists.</p>
        </div>
        """

    def get_district_dashboard(self) -> dict:
        """Generate a comprehensive district dashboard."""
        dashboard_query = """
        MANDATORY: You MUST use the database tools to generate this dashboard with REAL data.

        Follow this exact workflow:
        1. FIRST: Call get_software_usage_summary() to get overall district metrics
        2. SECOND: Call get_top_software_by_usage(10) to get the most used software
        3. THIRD: Call get_usage_trends(30) to get recent usage trends
        4. FOURTH: Call get_district_software_count() to get total software count

        Generate a comprehensive dashboard for our district showing:
        1. Overall software usage summary with key metrics FROM THE DATABASE
        2. Top 10 most used software applications FROM THE DATABASE
        3. Recent usage trends (last 30 days) FROM THE DATABASE
        4. Quick insights and recommendations based on REAL DATA

        DO NOT use any mock, fake, or example data. Only use data returned by the database tools.
        Present this as an executive dashboard with clear visualizations using proper HTML structure.
        """
        return self.process_query(dashboard_query)

    def analyze_software_roi(self) -> dict:
        """Analyze software return on investment."""
        roi_query = """
        Analyze the ROI of our educational software by:
        1. Identifying high-usage vs low-usage applications
        2. Calculating cost per student/session where possible
        3. Finding underutilized expensive software
        4. Recommending optimization opportunities

        Focus on actionable cost-saving and efficiency recommendations.
        """
        return self.process_query(roi_query)

    def get_security_insights(self) -> dict:
        """Get security and compliance insights."""
        security_query = """
        Provide security and compliance insights including:
        1. Any unauthorized software usage patterns
        2. Software usage outside normal hours
        3. Unusual access patterns that might indicate security issues
        4. Compliance status summary

        Present as a security dashboard with clear risk indicators.
        """
        return self.process_query(security_query)


def create_educational_agent(
    district_id: str, postgres_config: dict, verbose: bool = False
) -> EducationalDataAgent:
    """
    Factory function to create a district-aware educational data agent.

    Args:
        district_id: The district identifier for data access control
        postgres_config: Database connection configuration
        verbose: Enable verbose logging and detailed execution tracking

    Returns:
        Configured EducationalDataAgent instance
    """
    return EducationalDataAgent(
        district_id=district_id, postgres_config=postgres_config, verbose=verbose
    )
