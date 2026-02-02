"""
Materialized View Optimized Educational Agent

This agent uses materialized views as the primary data source for all queries,
resulting in 10-100x faster response times compared to querying raw tables.

Supports both regular responses and SSE streaming with markdown format.
"""

import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from openai import OpenAI

from mv_knowledge_registry import (
    MATERIALIZED_VIEW_REGISTRY,
    QueryIntent,
    detect_query_intents,
    get_best_materialized_view,
    get_mv_aware_instructions,
)
from mv_query_router import MVQueryRouter, create_mv_router

logger = logging.getLogger(__name__)


class MVOptimizedAgent:
    """
    Educational agent optimized for materialized view usage.

    This agent:
    1. Analyzes user queries to detect intent
    2. Routes queries to the most appropriate materialized view
    3. Executes optimized SQL against pre-computed MVs
    4. Uses AI to generate human-friendly HTML responses
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
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if self.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info(f"Initializing MVOptimizedAgent for district: {district_id}")

        # Initialize MV Query Router
        self.mv_router = create_mv_router(postgres_config, district_id)

        # Initialize OpenAI client for streaming
        self.openai_client = OpenAI(api_key=self.openai_api_key)

        # Create the AI agent for response generation (non-streaming fallback)
        self.analysis_agent = Agent(
            name="MV-Optimized Educational Analytics Agent",
            model=OpenAIChat(
                id="gpt-4o-mini",
                api_key=self.openai_api_key
            ),
            instructions=self._get_agent_instructions(),
            markdown=True,
        )

        logger.info(f"MVOptimizedAgent initialized successfully for district: {district_id}")

    def _get_agent_instructions(self) -> List[str]:
        """Get comprehensive instructions for the agent (HTML format)."""
        return [
            "You are an educational software analytics specialist.",
            "You will receive REAL data from optimized materialized view queries.",
            "Your job is to create clear, actionable HTML analysis.",
            "",
            "CRITICAL - DATA DISPLAY RULES:",
            "- When user asks for 'all', 'list', 'show all', 'every', or 'complete list' - display ALL records in the data, not just top 5-10",
            "- NEVER summarize or truncate data when user explicitly asks for all/list/complete data",
            "- Include EVERY record from the provided data in your table",
            "- If there are 50 records, show all 50. If there are 100 records, show all 100.",
            "",
            "RESPONSE GUIDELINES:",
            "- Create clean HTML (no CSS, JavaScript, or styling)",
            "- Use semantic HTML elements: tables, divs, headers, lists",
            "- Present data in tables when showing multiple records",
            "- Highlight key insights and trends",
            "- Provide actionable recommendations based on the data",
            "- Use user-friendly language (avoid technical jargon)",
            "- Never include UUIDs or district IDs in visible content",
            "- Focus on what matters to educators and administrators",
            "",
            "HTML STRUCTURE:",
            "- Use <h3> or <h4> for section headers",
            "- Use <table class='table table-striped'> for data tables",
            "- Use <div class='alert alert-info'> for insights",
            "- Use <div class='alert alert-warning'> for concerns",
            "- Use <div class='alert alert-success'> for positive findings",
            "",
            "ROI STATUS INTERPRETATION:",
            "- 'high' = Good investment, well utilized",
            "- 'moderate' = Acceptable, room for improvement",
            "- 'low' = Underutilized, consider action",
            "",
            "OS/DATA SOURCE LABELS:",
            "- 'Chrome OS' = Chromebook devices",
            "- 'Windows' = Windows PCs/laptops",
            "- 'iOS' = iPad/iPhone devices",
            "- 'Other' = Other platforms",
            "- 'Unknown' = No usage data or unidentified platform",
            "- When referring to OS data, also use the term 'data source' or 'platform'",
            "",
            "INSIGHT TYPES TO PROVIDE:",
            "- Usage patterns and trends",
            "- Cost effectiveness analysis",
            "- Recommendations for improvement",
            "- Comparison with benchmarks where applicable",
            "- Actionable next steps",
        ]

    def _get_markdown_instructions(self) -> str:
        """Get instructions for markdown format (streaming responses)."""
        return """You are an educational software analytics specialist.
You will receive REAL data from optimized materialized view queries.
Your job is to create clear, actionable analysis in MARKDOWN format.

CRITICAL - DATA DISPLAY RULES:
- When user asks for 'all', 'list', 'show all', 'every', or 'complete list' - display ALL records, not just top 5-10
- NEVER summarize or truncate data when user explicitly asks for all/list/complete data
- Include EVERY record from the provided data in your table
- If there are 50 records, show all 50. If there are 100 records, show all 100.

RESPONSE FORMAT (MARKDOWN):
- Use ## for main section headers
- Use ### for sub-section headers
- Use markdown tables with | column | headers |
- Use **bold** for emphasis on key metrics
- Use bullet points (- item) for lists
- Use > blockquotes for insights/recommendations
- Use emojis sparingly for visual appeal (📊 📈 ✅ ⚠️ 💡)

MARKDOWN STRUCTURE EXAMPLE:
## 📊 Software Analytics Summary

### Key Metrics
| Metric | Value |
|--------|-------|
| Total Software | 25 |
| Total Cost | $50,000 |

### 💡 Key Insights
> Your top-performing software is achieving 85% ROI

### ⚠️ Areas of Concern
- Software X has low utilization (15%)

### ✅ Recommendations
1. Review underutilized software
2. Consider consolidation opportunities

ROI STATUS INTERPRETATION:
- 'high' = Good investment, well utilized
- 'moderate' = Acceptable, room for improvement
- 'low' = Underutilized, consider action

OS/DATA SOURCE LABELS:
- 'Chrome OS' = Chromebook devices
- 'Windows' = Windows PCs/laptops
- 'iOS' = iPad/iPhone devices
- 'Other' = Other platforms
- 'Unknown' = No usage data or unidentified platform
- When referring to OS data, you may also use the term "data source" or "platform"

IMPORTANT:
- Be concise but comprehensive
- Focus on actionable insights
- Never include UUIDs or district IDs
- Use user-friendly language
- When showing OS/platform/data source data, display all available types even if count is 0"""

    def _call_mv_tools(self, user_query: str) -> Dict[str, Any]:
        """
        Call the appropriate MV methods based on query analysis.
        Returns all relevant data for the query.
        """
        start_time = time.time()

        # Detect query intent
        intents = detect_query_intents(user_query)
        primary_intent = intents[0] if intents else QueryIntent.DASHBOARD_OVERVIEW

        logger.info(f"🧠 Query Intent Analysis:")
        logger.info(f"   Primary Intent: {primary_intent.value}")
        logger.info(f"   All Intents: {[i.value for i in intents]}")

        # Get the best MV for this query
        best_mv = get_best_materialized_view(intents)
        logger.info(f"   Best MV: {best_mv.name}")

        # Collect data from relevant MVs
        tool_results = {}
        mv_queries = []

        # Get basic dashboard metrics for context (skip for self-contained intents)
        if primary_intent != QueryIntent.PEER_BENCHMARKING:
            try:
                logger.info("   📊 Calling get_dashboard_metrics()...")
                metrics_start = time.time()
                tool_results["dashboard_metrics"] = self.mv_router.get_dashboard_metrics()
                mv_queries.append({
                    "method": "get_dashboard_metrics",
                    "mv_used": "mv_dashboard_software_metrics",
                    "execution_time": time.time() - metrics_start
                })
                logger.info(f"   ✅ Dashboard metrics retrieved in {time.time() - metrics_start:.3f}s")
            except Exception as e:
                logger.error(f"   ❌ Dashboard metrics failed: {e}")
                tool_results["dashboard_metrics"] = {"error": str(e)}

        # Route to specific data based on intent
        if primary_intent == QueryIntent.UNAUTHORIZED_SOFTWARE:
            try:
                logger.info("   📊 Calling get_unauthorized_software()...")
                start = time.time()
                tool_results["unauthorized"] = self.mv_router.get_unauthorized_software()
                mv_queries.append({
                    "method": "get_unauthorized_software",
                    "mv_used": "mv_unauthorized_software_analytics_v3",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["unauthorized"] = {"error": str(e)}

        elif primary_intent in [QueryIntent.SOFTWARE_INVESTMENT, QueryIntent.COST_ANALYSIS]:
            try:
                logger.info("   📊 Calling get_investment_analysis()...")
                start = time.time()
                tool_results["investment"] = self.mv_router.get_investment_analysis()
                mv_queries.append({
                    "method": "get_investment_analysis",
                    "mv_used": "mv_software_investment_summary",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["investment"] = {"error": str(e)}

        elif primary_intent == QueryIntent.USER_ANALYTICS:
            try:
                logger.info("   📊 Calling get_user_analytics()...")
                start = time.time()
                tool_results["users"] = self.mv_router.get_user_analytics()
                mv_queries.append({
                    "method": "get_user_analytics",
                    "mv_used": "mv_dashboard_user_analytics",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["users"] = {"error": str(e)}

            # Also fetch active users summary (all roles + OS data) when
            # ACTIVE_USERS is a secondary intent, or when the query mentions
            # roles/active users — mv_dashboard_user_analytics only has
            # student/teacher, but mv_active_users_summary has ALL roles.
            if QueryIntent.ACTIVE_USERS in intents:
                try:
                    logger.info("   📊 Also calling get_active_users_summary() (all roles + OS)...")
                    start = time.time()
                    tool_results["active_users"] = self.mv_router.get_active_users_summary()
                    mv_queries.append({
                        "method": "get_active_users_summary",
                        "mv_used": "mv_active_users_summary",
                        "execution_time": time.time() - start
                    })
                except Exception as e:
                    tool_results["active_users"] = {"error": str(e)}

        elif primary_intent == QueryIntent.ACTIVE_USERS:
            try:
                logger.info("   📊 Calling get_active_users_summary()...")
                start = time.time()
                tool_results["active_users"] = self.mv_router.get_active_users_summary()
                mv_queries.append({
                    "method": "get_active_users_summary",
                    "mv_used": "mv_active_users_summary",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["active_users"] = {"error": str(e)}

        elif primary_intent == QueryIntent.STUDENT_ANALYSIS:
            try:
                logger.info("   📊 Calling get_top_users(role='student')...")
                start = time.time()
                tool_results["students"] = self.mv_router.get_top_users(role="student")
                mv_queries.append({
                    "method": "get_top_users",
                    "mv_used": "mv_user_software_utilization_v2",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["students"] = {"error": str(e)}

        elif primary_intent == QueryIntent.TEACHER_ANALYSIS:
            try:
                logger.info("   📊 Calling get_top_users(role='teacher')...")
                start = time.time()
                tool_results["teachers"] = self.mv_router.get_top_users(role="teacher")
                mv_queries.append({
                    "method": "get_top_users",
                    "mv_used": "mv_user_software_utilization_v2",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["teachers"] = {"error": str(e)}

        elif primary_intent == QueryIntent.SCHOOL_ANALYSIS:
            try:
                logger.info("   📊 Calling get_school_analysis()...")
                start = time.time()
                tool_results["schools"] = self.mv_router.get_school_analysis()
                mv_queries.append({
                    "method": "get_school_analysis",
                    "mv_used": "mv_software_usage_by_school_v2",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["schools"] = {"error": str(e)}

        elif primary_intent == QueryIntent.USAGE_RANKINGS:
            try:
                logger.info("   📊 Calling get_usage_rankings()...")
                start = time.time()
                tool_results["rankings"] = self.mv_router.get_usage_rankings()
                mv_queries.append({
                    "method": "get_usage_rankings",
                    "mv_used": "mv_software_usage_rankings_v4",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["rankings"] = {"error": str(e)}

        elif primary_intent == QueryIntent.SOFTWARE_ROI:
            try:
                logger.info("   📊 Calling get_software_analytics(order_by='avg_roi_percentage')...")
                start = time.time()
                tool_results["roi_analysis"] = self.mv_router.get_software_analytics(
                    order_by="avg_roi_percentage"
                )
                mv_queries.append({
                    "method": "get_software_analytics",
                    "mv_used": "mv_software_usage_analytics_v4",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["roi_analysis"] = {"error": str(e)}

        elif primary_intent == QueryIntent.PEER_BENCHMARKING:
            try:
                logger.info("   📊 Calling get_peer_benchmarking_summary()...")
                start = time.time()
                tool_results["peer_benchmarking"] = self.mv_router.get_peer_benchmarking_summary()
                mv_queries.append({
                    "method": "get_peer_benchmarking_summary",
                    "mv_used": "peer_district_metrics + peer_comparisons",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["peer_benchmarking"] = {"error": str(e)}

        else:
            # Default: get comprehensive software analytics
            try:
                logger.info("   📊 Calling get_software_analytics()...")
                start = time.time()
                tool_results["software"] = self.mv_router.get_software_analytics()
                mv_queries.append({
                    "method": "get_software_analytics",
                    "mv_used": "mv_software_usage_analytics_v4",
                    "execution_time": time.time() - start
                })
            except Exception as e:
                tool_results["software"] = {"error": str(e)}

        total_time = time.time() - start_time

        return {
            "tool_results": tool_results,
            "mv_queries": mv_queries,
            "intents": [i.value for i in intents],
            "primary_intent": primary_intent.value,
            "best_mv": best_mv.name,
            "total_time": total_time
        }

    def _format_data_for_agent(self, tool_data: Dict[str, Any]) -> str:
        """Format the tool results for the AI agent to process."""
        formatted = []

        formatted.append("=" * 60)
        formatted.append("REAL DATA FROM MATERIALIZED VIEWS")
        formatted.append("=" * 60)
        formatted.append(f"Query Intent: {tool_data['primary_intent']}")
        formatted.append(f"Primary MV Used: {tool_data['best_mv']}")
        formatted.append(f"Total Query Time: {tool_data['total_time']:.3f}s")
        formatted.append("")

        for key, value in tool_data["tool_results"].items():
            formatted.append(f"\n--- {key.upper().replace('_', ' ')} ---")
            if isinstance(value, dict) and "error" in value:
                formatted.append(f"Error: {value['error']}")
            elif isinstance(value, dict):
                # Handle nested structures
                for sub_key, sub_value in value.items():
                    if sub_key in ["execution_time", "mv_used"]:
                        continue
                    if isinstance(sub_value, list):
                        formatted.append(f"\n{sub_key}:")
                        for item in sub_value[:100]:  # Limit to 100 items
                            formatted.append(f"  {json.dumps(item, default=str)}")
                    else:
                        formatted.append(f"{sub_key}: {json.dumps(sub_value, default=str)}")
            else:
                formatted.append(str(value))

        return "\n".join(formatted)

    async def process_query_stream(self, user_query: str) -> AsyncGenerator[str, None]:
        """
        Process a user query with SSE streaming, returning markdown chunks.

        This method yields chunks of markdown as they are generated,
        providing much faster perceived response times.
        """
        execution_log = {
            "district_id": self.district_id,
            "user_query": user_query,
            "mv_queries": [],
            "intents": [],
            "execution_time": None,
            "error": None,
        }

        start_time = time.time()

        try:
            logger.info(f"=== MV OPTIMIZED STREAMING FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # STEP 1: Call MV tools based on query analysis
            logger.info("🔧 STEP 1: Calling materialized view tools...")
            tool_data = self._call_mv_tools(user_query)

            execution_log["mv_queries"] = tool_data["mv_queries"]
            execution_log["intents"] = tool_data["intents"]
            execution_log["primary_intent"] = tool_data["primary_intent"]
            execution_log["best_mv"] = tool_data["best_mv"]

            # Yield metadata event first
            metadata = {
                "type": "metadata",
                "primary_intent": tool_data["primary_intent"],
                "best_mv": tool_data["best_mv"],
                "mv_queries_count": len(tool_data["mv_queries"]),
                "data_fetch_time": tool_data["total_time"]
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            # STEP 2: Format data for AI agent
            logger.info("🎨 STEP 2: Streaming markdown analysis...")
            formatted_data = self._format_data_for_agent(tool_data)

            # Detect if user wants all/complete data
            query_lower = user_query.lower()
            wants_all_data = any(word in query_lower for word in ['all', 'list', 'every', 'complete', 'full', 'entire', 'show me'])

            data_display_instruction = ""
            if wants_all_data:
                data_display_instruction = """
IMPORTANT: The user is asking for ALL/COMPLETE data. You MUST:
- Display EVERY SINGLE record from the data provided below in your markdown table
- Do NOT summarize, truncate, or show only "top" items
- If there are 50 records, show all 50 in the table
- If there are 100 records, show all 100 in the table
- The user explicitly wants to see the complete list, not a summary
"""

            # Build the prompt for streaming
            system_prompt = self._get_markdown_instructions()
            user_prompt = f"""User Question: {user_query}
{data_display_instruction}
{formatted_data}

Based on this REAL data from the database, create a comprehensive MARKDOWN response that:
1. Directly answers the user's question
2. Shows ALL records in tables (do not truncate or summarize if user asked for all/list)
3. Highlights key insights from the data
4. Provides actionable recommendations
5. Uses clear markdown formatting (tables, headers, bullet points)

Remember to:
- Use proper markdown syntax
- Be concise but comprehensive
- Focus on insights that matter to educators
- SHOW ALL DATA RECORDS IN TABLES - never truncate when user asks for list/all"""

            # STEP 3: Stream response using OpenAI
            stream = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True,
                temperature=0.3,
                max_tokens=4096
            )

            # Yield content chunks
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'type': 'content', 'text': content})}\n\n"

            # Yield completion event
            execution_log["execution_time"] = time.time() - start_time
            completion_data = {
                "type": "done",
                "execution_time": execution_log["execution_time"],
                "mv_queries_count": len(execution_log["mv_queries"])
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

            logger.info(f"✅ MV STREAMING COMPLETED in {execution_log['execution_time']:.2f}s")

        except Exception as e:
            execution_log["error"] = str(e)
            execution_log["execution_time"] = time.time() - start_time
            logger.error(f"❌ MV STREAMING FAILED: {e}")

            error_data = {
                "type": "error",
                "error": str(e),
                "execution_time": execution_log["execution_time"]
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a user query using materialized views.

        This is the main entry point for the agent.
        """
        execution_log = {
            "district_id": self.district_id,
            "user_query": user_query,
            "mv_queries": [],
            "intents": [],
            "execution_time": None,
            "error": None,
        }

        start_time = time.time()

        try:
            logger.info(f"=== MV OPTIMIZED PROCESSING FOR DISTRICT {self.district_id} ===")
            logger.info(f"User Query: {user_query}")

            # STEP 1: Call MV tools based on query analysis
            logger.info("🔧 STEP 1: Calling materialized view tools...")
            tool_data = self._call_mv_tools(user_query)

            execution_log["mv_queries"] = tool_data["mv_queries"]
            execution_log["intents"] = tool_data["intents"]
            execution_log["primary_intent"] = tool_data["primary_intent"]
            execution_log["best_mv"] = tool_data["best_mv"]

            # STEP 2: Format data for AI agent
            logger.info("🎨 STEP 2: Generating HTML analysis...")
            formatted_data = self._format_data_for_agent(tool_data)

            # STEP 3: Generate HTML response using AI
            # Detect if user wants all/complete data
            query_lower = user_query.lower()
            wants_all_data = any(word in query_lower for word in ['all', 'list', 'every', 'complete', 'full', 'entire', 'show me'])

            data_display_instruction = ""
            if wants_all_data:
                data_display_instruction = """
IMPORTANT: The user is asking for ALL/COMPLETE data. You MUST:
- Display EVERY SINGLE record from the data provided below in your HTML table
- Do NOT summarize, truncate, or show only "top" items
- If there are 50 records, show all 50 in the table
- If there are 100 records, show all 100 in the table
- The user explicitly wants to see the complete list, not a summary
"""

            analysis_prompt = f"""
User Question: {user_query}
{data_display_instruction}
{formatted_data}

Based on this REAL data from the database, create a comprehensive HTML response that:
1. Directly answers the user's question
2. Shows ALL records in tables (do not truncate or summarize if user asked for all/list)
3. Highlights key insights from the data
4. Provides actionable recommendations
5. Uses clear visualizations (tables, lists)

Remember to:
- Use clean HTML without CSS or JavaScript
- Use user-friendly language
- Focus on insights that matter to educators
- Include both positive findings and areas for improvement
- SHOW ALL DATA RECORDS IN TABLES - never truncate when user asks for list/all
"""

            response = self.analysis_agent.run(analysis_prompt)
            html_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Clean up markdown artifacts
            if html_content.startswith("```html\n"):
                html_content = html_content[8:]
            if html_content.endswith("\n```"):
                html_content = html_content[:-4]

            execution_log["execution_time"] = time.time() - start_time

            logger.info(f"✅ MV OPTIMIZED PROCESSING COMPLETED in {execution_log['execution_time']:.2f}s")
            logger.info(f"📊 MV Queries Executed: {len(execution_log['mv_queries'])}")
            logger.info(f"🧠 Primary Intent: {execution_log['primary_intent']}")
            logger.info(f"📁 Best MV: {execution_log['best_mv']}")

            if self.verbose:
                logger.debug(f"📋 Full Execution Log: {json.dumps(execution_log, indent=2)}")

            return {
                "html_response": html_content,
                "execution_log": execution_log if self.verbose else None,
            }

        except Exception as e:
            execution_log["error"] = str(e)
            execution_log["execution_time"] = time.time() - start_time

            logger.error(f"❌ MV OPTIMIZED PROCESSING FAILED: {e}")

            return {
                "html_response": f"<div class='alert alert-danger'>Error: {str(e)}</div>",
                "execution_log": execution_log if self.verbose else None,
            }

    def get_district_dashboard(self) -> Dict[str, Any]:
        """Generate a comprehensive district dashboard using MVs."""
        return self.process_query(
            "Generate a comprehensive executive dashboard showing overall software usage metrics, "
            "investment summary, top software by ROI, and key insights for district decision making"
        )

    def analyze_software_roi(self) -> Dict[str, Any]:
        """Analyze software return on investment using MVs."""
        return self.process_query(
            "Analyze the ROI and cost-effectiveness of our educational software investments, "
            "showing which software provides the best value and identifying underutilized applications"
        )

    def get_security_insights(self) -> Dict[str, Any]:
        """Get security and compliance insights using MVs."""
        return self.process_query(
            "Provide security insights including unauthorized software usage patterns, "
            "which students and teachers are using unapproved apps, and compliance status"
        )

    def get_user_engagement_report(self) -> Dict[str, Any]:
        """Get user engagement report using MVs."""
        return self.process_query(
            "Generate a user engagement report showing student and teacher usage patterns, "
            "most active users, and engagement by grade level"
        )

    def get_school_comparison(self) -> Dict[str, Any]:
        """Compare software usage across schools using MVs."""
        return self.process_query(
            "Compare software usage and ROI across different schools in the district, "
            "identifying best practices and areas for improvement"
        )


def create_mv_optimized_agent(
    district_id: str,
    postgres_config: dict,
    verbose: bool = False
) -> MVOptimizedAgent:
    """Factory function to create an MV-optimized educational agent."""
    return MVOptimizedAgent(
        district_id=district_id,
        postgres_config=postgres_config,
        verbose=verbose
    )
