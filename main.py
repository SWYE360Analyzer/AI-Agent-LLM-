"""
Alternative main.py using Tool Intercepting Agent

This version guarantees that database tools are called by using
the ToolCallInterceptingAgent instead of relying on the phi framework.
"""

import logging
import os
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# Import all agent types
from educational_agent import EducationalDataAgent, create_educational_agent
from intelligent_tool_agent import IntelligentToolAgent, create_intelligent_agent
from phi_educational_agent import PhiEducationalAgent, create_phi_educational_agent
from tool_intercepting_agent import (
    ToolCallInterceptingAgent,
    create_tool_intercepting_agent,
)
from mv_optimized_agent import MVOptimizedAgent, create_mv_optimized_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Educational Software Analytics API - Fixed Version",
    description="District-aware AI agent with guaranteed database tool calling",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware with restricted origins for security
allowed_origins = [
    "https://classsight.ai",
    "https://www.classsight.ai",
    "https://swye360.ai",
    "https://www.swye360.ai",
    "https://preview--roi-bright-future.lovable.app",
]

logger.info(f"🔒 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add middleware to log request origins for CORS debugging
@app.middleware("http")
async def log_request_origin(request, call_next):
    """Log incoming request origins and enforce strict origin whitelist."""
    origin = request.headers.get("origin", None)
    referer = request.headers.get("referer", "No Referer")
    host = request.headers.get("host", "No Host")

    logger.info(
        f"📨 Incoming Request - "
        f"Origin: {origin if origin else 'No Origin Header'} | "
        f"Referer: {referer} | "
        f"Host: {host} | "
        f"Path: {request.url.path}"
    )

    # Whitelist paths that don't require origin validation (e.g., health checks from monitoring)
    # Remove paths from this list if you want to block everything without exception
    whitelisted_paths = [
        "/docs",  # API documentation
        "/redoc",  # API documentation
        "/openapi.json",  # OpenAPI schema
    ]

    # Check if Origin header is present
    if origin is None:
        # Block requests without Origin header unless path is whitelisted
        if request.url.path not in whitelisted_paths:
            logger.error(
                f"🚫 BLOCKED - No Origin header present for path: {request.url.path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "You are not authorized to access this API.",
                },
            )
        else:
            logger.info(
                f"ℹ️  No Origin header - allowing whitelisted path: {request.url.path}"
            )
    elif origin not in allowed_origins:
        # Block requests with unauthorized Origin header
        logger.error(f"🚫 BLOCKED - Origin NOT in allowed list: {origin}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": "You are not authorized to access this API.",
            },
        )
    else:
        # Allow requests with valid Origin header
        logger.info(f"✅ Origin ALLOWED: {origin}")

    response = await call_next(request)
    return response


# Request/Response Models
class AnalyticsRequest(BaseModel):
    """Request model for analytics queries."""

    message: str = Field(
        ..., description="Natural language query about educational software analytics"
    )
    district_id: str = Field(
        ..., description="District identifier for data access control"
    )
    verbose: bool = Field(
        False, description="Enable verbose logging and detailed execution tracking"
    )
    use_mv_optimized_agent: bool = Field(
        True,
        description="Use MV-optimized agent (RECOMMENDED - 10-100x faster using materialized views)",
    )
    use_intercepting_agent: bool = Field(
        False, description="Use tool-intercepting agent for guaranteed database calls"
    )
    use_intelligent_agent: bool = Field(
        False,
        description="Use intelligent agent with smart tool selection based on query",
    )
    use_phi_agent: bool = Field(
        False,
        description="Use phi's native PostgreSQL tools for dynamic query generation",
    )


class AnalyticsResponse(BaseModel):
    """Response model for analytics queries."""

    success: bool = Field(description="Whether the request was successful")
    html_response: str = Field(
        description="HTML-formatted response with analytics insights"
    )
    district_id: str = Field(description="District identifier that was used")
    execution_log: Optional[dict] = Field(
        None, description="Detailed execution log including SQL queries and tool calls"
    )
    agent_type: str = Field(description="Type of agent used (original/intercepting)")
    error: Optional[str] = Field(None, description="Error message if request failed")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    district_agent_ready: bool
    database_connected: bool
    intercepting_agent_available: bool


# Database configuration
def get_postgres_config() -> dict:
    """Get PostgreSQL configuration from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "schema": os.getenv("POSTGRES_SCHEMA", "public"),
    }


# Agent cache for all types
original_agent_cache = {}
intercepting_agent_cache = {}
intelligent_agent_cache = {}
phi_agent_cache = {}
mv_optimized_agent_cache = {}


def get_original_agent(district_id: str, verbose: bool = False) -> EducationalDataAgent:
    """Get or create original educational data agent."""
    cache_key = f"{district_id}_{verbose}"

    if cache_key not in original_agent_cache:
        try:
            postgres_config = get_postgres_config()
            agent = create_educational_agent(
                district_id, postgres_config, verbose=verbose
            )
            original_agent_cache[cache_key] = agent
            logger.info(f"Created original agent for district: {district_id}")
        except Exception as e:
            logger.error(f"Failed to create original agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    return original_agent_cache[cache_key]


def get_intercepting_agent(
    district_id: str, verbose: bool = False
) -> ToolCallInterceptingAgent:
    """Get or create tool-intercepting agent."""
    cache_key = f"{district_id}_{verbose}"

    if cache_key not in intercepting_agent_cache:
        try:
            postgres_config = get_postgres_config()
            agent = create_tool_intercepting_agent(
                district_id, postgres_config, verbose=verbose
            )
            intercepting_agent_cache[cache_key] = agent
            logger.info(f"Created intercepting agent for district: {district_id}")
        except Exception as e:
            logger.error(f"Failed to create intercepting agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    return intercepting_agent_cache[cache_key]


def get_intelligent_agent(
    district_id: str, verbose: bool = False
) -> IntelligentToolAgent:
    """Get or create intelligent tool selection agent."""
    cache_key = f"{district_id}_{verbose}"

    if cache_key not in intelligent_agent_cache:
        try:
            postgres_config = get_postgres_config()
            agent = create_intelligent_agent(
                district_id, postgres_config, verbose=verbose
            )
            intelligent_agent_cache[cache_key] = agent
            logger.info(f"Created intelligent agent for district: {district_id}")
        except Exception as e:
            logger.error(f"Failed to create intelligent agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    return intelligent_agent_cache[cache_key]


def get_phi_agent(district_id: str, verbose: bool = False) -> PhiEducationalAgent:
    """Get or create phi-based educational agent."""
    cache_key = f"{district_id}_{verbose}"

    if cache_key not in phi_agent_cache:
        try:
            postgres_config = get_postgres_config()
            agent = create_phi_educational_agent(
                district_id, postgres_config, verbose=verbose
            )
            phi_agent_cache[cache_key] = agent
            logger.info(f"Created phi agent for district: {district_id}")
        except Exception as e:
            logger.error(f"Failed to create phi agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    return phi_agent_cache[cache_key]


def get_mv_optimized_agent(district_id: str, verbose: bool = False) -> MVOptimizedAgent:
    """Get or create MV-optimized educational agent (RECOMMENDED)."""
    cache_key = f"{district_id}_{verbose}"

    if cache_key not in mv_optimized_agent_cache:
        try:
            postgres_config = get_postgres_config()
            agent = create_mv_optimized_agent(
                district_id, postgres_config, verbose=verbose
            )
            mv_optimized_agent_cache[cache_key] = agent
            logger.info(f"Created MV-optimized agent for district: {district_id}")
        except Exception as e:
            logger.error(f"Failed to create MV-optimized agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    return mv_optimized_agent_cache[cache_key]


# API Endpoints
@app.post("/api/ask", response_model=AnalyticsResponse)
async def ask_analytics_question(request: AnalyticsRequest):
    """
    Process natural language questions about educational software analytics.
    Now with guaranteed database tool calling!
    """
    try:
        logger.info(
            f"Received request for district {request.district_id}, "
            f"verbose: {request.verbose}, mv_optimized: {request.use_mv_optimized_agent}, "
            f"intercepting: {request.use_intercepting_agent}, "
            f"intelligent: {request.use_intelligent_agent}, phi: {request.use_phi_agent}"
        )

        # Validate required fields
        if not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )
        if not request.district_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="District ID is required",
            )

        # Choose agent type with MV-optimized agent as the default (RECOMMENDED)
        if request.use_mv_optimized_agent:
            agent = get_mv_optimized_agent(request.district_id, verbose=request.verbose)
            agent_type = "mv_optimized"
            logger.info(
                "🚀 Using MV-Optimized Agent (10-100x faster using materialized views)"
            )
        elif request.use_phi_agent:
            agent = get_phi_agent(request.district_id, verbose=request.verbose)
            agent_type = "phi_native"
            logger.info(
                "🔥 Using Phi Native Agent (dynamic SQL generation from natural language)"
            )
        elif request.use_intelligent_agent:
            agent = get_intelligent_agent(request.district_id, verbose=request.verbose)
            agent_type = "intelligent"
            logger.info(
                "🧠 Using Intelligent Agent (smart tool selection based on query)"
            )
        elif request.use_intercepting_agent:
            agent = get_intercepting_agent(request.district_id, verbose=request.verbose)
            agent_type = "intercepting"
            logger.info("🔧 Using Tool Intercepting Agent (guaranteed database calls)")
        else:
            agent = get_original_agent(request.district_id, verbose=request.verbose)
            agent_type = "original"
            logger.info("🤖 Using Original Agent (phi framework tool calling)")

        # Process the query
        result = agent.process_query(request.message)
        html_response = result["html_response"]
        execution_log = result.get("execution_log")

        # Simple cleanup
        if html_response.startswith("```html\n"):
            html_response = html_response[8:]
        if html_response.endswith("\n```"):
            html_response = html_response[:-4]

        # Log execution summary
        if execution_log:
            if agent_type == "mv_optimized":
                mv_count = len(execution_log.get("mv_queries", []))
                exec_time = execution_log.get("execution_time", 0)
                primary_intent = execution_log.get("primary_intent", "unknown")
                best_mv = execution_log.get("best_mv", "unknown")
                logger.info(
                    f"📊 Execution Summary ({agent_type}): {mv_count} MV queries, "
                    f"{exec_time:.2f}s, intent: {primary_intent}, best_mv: {best_mv}"
                )
            elif agent_type == "phi_native":
                logger.info(
                    f"📊 Execution Summary ({agent_type}): Dynamic SQL generation completed"
                )
            else:
                sql_count = len(execution_log.get("sql_queries", []))
                exec_time = execution_log.get("execution_time", 0)
                intent = execution_log.get("query_intent", {}).get("type", "unknown")
                logger.info(
                    f"📊 Execution Summary ({agent_type}): {sql_count} database calls, {exec_time:.2f}s, intent: {intent}"
                )

        return AnalyticsResponse(
            success=True,
            html_response=html_response,
            district_id=request.district_id,
            execution_log=execution_log,
            agent_type=agent_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return AnalyticsResponse(
            success=False,
            html_response=f"<div class='alert alert-danger'>Error: {str(e)}</div>",
            district_id=request.district_id,
            execution_log=None,
            agent_type="error",
            error=str(e),
        )


@app.get("/api/dashboard/{district_id}", response_model=AnalyticsResponse)
async def get_district_dashboard(
    district_id: str, verbose: bool = False, use_intercepting: bool = True
):
    """Get comprehensive analytics dashboard - now with guaranteed database calls!"""
    try:
        if use_intercepting:
            agent = get_intercepting_agent(district_id, verbose=verbose)
            agent_type = "intercepting"
        else:
            agent = get_original_agent(district_id, verbose=verbose)
            agent_type = "original"

        result = agent.get_district_dashboard()
        html_response = result["html_response"]
        execution_log = result.get("execution_log")

        # Simple cleanup
        if html_response.startswith("```html\n"):
            html_response = html_response[8:]
        if html_response.endswith("\n```"):
            html_response = html_response[:-4]

        return AnalyticsResponse(
            success=True,
            html_response=html_response,
            district_id=district_id,
            execution_log=execution_log,
            agent_type=agent_type,
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return AnalyticsResponse(
            success=False,
            html_response=f"<div class='alert alert-danger'>Dashboard Error: {str(e)}</div>",
            district_id=district_id,
            execution_log=None,
            agent_type="error",
            error=str(e),
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with intercepting agent status."""
    try:
        postgres_config = get_postgres_config()
        database_connected = all(
            [
                postgres_config.get("host"),
                postgres_config.get("database"),
                postgres_config.get("user"),
                postgres_config.get("password"),
            ]
        )

        # Test intercepting agent creation
        intercepting_available = True
        try:
            test_agent = create_tool_intercepting_agent(
                "test", postgres_config, verbose=False
            )
        except:
            intercepting_available = False

        return HealthResponse(
            status="healthy",
            district_agent_ready=True,
            database_connected=database_connected,
            intercepting_agent_available=intercepting_available,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            district_agent_ready=False,
            database_connected=False,
            intercepting_agent_available=False,
        )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with updated documentation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Educational Analytics API - Fixed Version</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            .fix { background: #d4edda; padding: 15px; margin: 10px 0; border-left: 4px solid #28a745; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }
            .method { color: #27ae60; font-weight: bold; }
            code { background: #e9ecef; padding: 2px 4px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1 class="header">🎓 Educational Analytics API - Fixed Version</h1>

        <div class="fix">
            <h2>✅ PERMANENT FIX IMPLEMENTED</h2>
            <p><strong>Problem:</strong> AI agent was generating JavaScript instead of calling database tools (0 SQL queries executed)</p>
            <p><strong>Solution:</strong> Tool Intercepting Agent that guarantees database tool calling</p>
            <ul>
                <li>✅ Forces database tool calls before HTML generation</li>
                <li>✅ Guarantees real data instead of mock data</li>
                <li>✅ Provides detailed execution logging</li>
                <li>✅ Maintains backward compatibility</li>
            </ul>
        </div>

        <h2>🔗 API Endpoints</h2>

        <div class="endpoint">
            <h3><span class="method">POST</span> /api/ask</h3>
            <p>Ask questions with guaranteed database tool calling</p>
            <p><strong>Payload:</strong></p>
            <code>{
  "message": "Tell me the top software investments",
  "district_id": "district123",
  "verbose": true,
  "use_intercepting_agent": true
}</code>
            <p><strong>New Features:</strong></p>
            <ul>
                <li><code>use_intercepting_agent</code>: true = guaranteed database calls, false = original agent</li>
                <li><code>agent_type</code> in response shows which agent was used</li>
            </ul>
        </div>

        <div class="endpoint">
            <h3><span class="method">GET</span> /api/dashboard/{district_id}?use_intercepting=true</h3>
            <p>Dashboard with guaranteed database tool calling</p>
        </div>

        <h2>🔧 Agent Comparison</h2>
        <table border="1" style="width:100%; border-collapse: collapse;">
            <tr>
                <th>Feature</th>
                <th>Original Agent</th>
                <th>Intercepting Agent</th>
            </tr>
            <tr>
                <td>Database Tool Calling</td>
                <td>❌ Unreliable (phi framework dependent)</td>
                <td>✅ Guaranteed (manual implementation)</td>
            </tr>
            <tr>
                <td>SQL Queries Executed</td>
                <td>❌ Often 0</td>
                <td>✅ Always > 0</td>
            </tr>
            <tr>
                <td>Real vs Mock Data</td>
                <td>❌ Often generates mock data</td>
                <td>✅ Always uses real database data</td>
            </tr>
            <tr>
                <td>JavaScript Generation</td>
                <td>❌ Sometimes generates JS code</td>
                <td>✅ Pure HTML only</td>
            </tr>
        </table>

        <h2>🧪 Test Examples</h2>
        <h3>Original Agent (problematic):</h3>
        <code>curl -X POST "/api/ask" -d '{"message": "Executive summary", "use_intercepting_agent": false}'</code>
        <p>Result: 0 SQL queries, mock data</p>

        <h3>Intercepting Agent (fixed):</h3>
        <code>curl -X POST "/api/ask" -d '{"message": "Executive summary", "use_intercepting_agent": true}'</code>
        <p>Result: 4+ SQL queries, real data</p>

        <h2>📊 What You'll Now See in Logs</h2>
        <pre>
🔧 STEP 1: Calling database tools...
   📊 Calling get_software_usage_summary()...
   ✅ get_software_usage_summary completed in 0.045s
   📊 Calling get_top_software_by_usage()...
   ✅ get_top_software_by_usage completed in 0.032s
📊 Database Tools Called: 4
        </pre>
    </body>
    </html>
    """


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))  # Different port to avoid conflicts
    debug = os.getenv("DEBUG", "False").lower() == "true"

    logger.info(f"Starting FIXED Educational Analytics API on {host}:{port}")
    logger.info("🔧 Tool Intercepting Agent available for guaranteed database calls!")

    uvicorn.run("main:app", host=host, port=port, reload=debug, log_level="info")
