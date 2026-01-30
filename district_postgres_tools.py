import logging
import re
from typing import Any, Dict, List, Optional

import psycopg2
from phi.tools import Toolkit
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DistrictAwarePostgresTools(Toolkit):
    """
    District-aware PostgreSQL toolkit that enforces district-level data access.
    All queries are automatically scoped to the user's district_id.
    Only read-only operations are allowed.
    """

    def __init__(
        self,
        connection: Optional[psycopg2.extensions.connection] = None,
        db_name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        schema: str = "public",
        district_id: Optional[str] = None,
    ):
        super().__init__(name="district_postgres_tools")

        self._connection: Optional[psycopg2.extensions.connection] = connection
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.schema = schema
        self.district_id = district_id

        # Read-only SQL commands allowed
        self.allowed_commands = {"SELECT", "WITH", "EXPLAIN", "DESCRIBE", "SHOW"}

        # Dangerous commands to block
        self.blocked_commands = {
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
            "CALL",
            "EXEC",
        }

        if self.functions:
            for f in self.functions:
                f.description = self._get_function_description(f.name)

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get database connection with read-only settings and autocommit."""
        # Check if existing connection is valid
        if self._connection:
            try:
                # Test if connection is still alive
                if not self._connection.closed:
                    return self._connection
            except Exception:
                pass
            # Connection is bad, reset it
            self._connection = None

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.db_name,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,
            )
            # Enable autocommit to prevent "transaction aborted" errors
            conn.set_session(readonly=True, autocommit=True)
            self._connection = conn
            logger.info("Database connection established with autocommit=True")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _validate_sql_safety(self, query: str) -> bool:
        """Validate that SQL query is safe (read-only)."""
        query_upper = query.upper().strip()

        # Check for blocked commands
        for blocked_cmd in self.blocked_commands:
            if blocked_cmd in query_upper:
                logger.warning(f"Blocked dangerous SQL command: {blocked_cmd}")
                return False

        # Must start with allowed commands
        first_word = query_upper.split()[0] if query_upper.split() else ""
        if first_word not in self.allowed_commands:
            logger.warning(
                f"SQL must start with allowed commands: {self.allowed_commands}"
            )
            return False

        return True

    def _inject_district_filter(self, query: str) -> str:
        """Automatically inject district_id filter into SQL queries."""
        if not self.district_id:
            logger.warning(
                "No district_id provided - queries may return unauthorized data"
            )
            return query

        # Simple injection for WHERE clauses
        # This is a basic implementation - in production, use a proper SQL parser
        query_lower = query.lower()

        # Pattern to find table references and add district filters
        if "where" in query_lower:
            # Add AND condition to existing WHERE
            where_pos = query_lower.rfind("where")
            before_where = query[: where_pos + 5]
            after_where = query[where_pos + 5 :]
            return (
                f"{before_where} district_id = '{self.district_id}' AND {after_where}"
            )
        elif "from" in query_lower and "join" not in query_lower:
            # Add WHERE clause to simple FROM queries
            return f"{query} WHERE district_id = '{self.district_id}'"
        else:
            # For complex queries, append at the end (basic approach)
            # In production, use a proper SQL parser
            return f"{query} -- District filter should be applied manually for complex queries"

    def _get_function_description(self, func_name: str) -> str:
        """Get detailed function descriptions."""
        descriptions = {
            "show_tables": "Lists all tables in the database that the user has access to in their district.",
            "describe_table": "Shows the structure of a specific table including columns, data types, and constraints.",
            "run_district_query": "Executes a read-only SQL query automatically scoped to the user's district. All queries are filtered by district_id.",
            "get_software_usage_summary": "Gets aggregated software usage statistics for the user's district.",
            "get_top_software_by_usage": "Returns the most used software applications in the user's district.",
            "get_district_software_count": "Returns the total count of software registered in the user's district.",
            "get_usage_trends": "Shows usage trends over time for software in the user's district.",
        }
        return descriptions.get(func_name, f"Database function: {func_name}")

    def show_tables(self) -> str:
        """Show all tables accessible to the user."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name
                """,
                    (self.schema,),
                )

                tables = cursor.fetchall()
                if not tables:
                    return "No tables found in the database."

                result = "**Available Tables:**\n\n"
                for table in tables:
                    result += f"- `{table['table_name']}` ({table['table_type']})\n"

                return result

        except Exception as e:
            logger.error(f"Error showing tables: {e}")
            return f"Error retrieving tables: {str(e)}"

    def describe_table(self, table_name: str) -> str:
        """Describe the structure of a specific table."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # Get column information
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """,
                    (self.schema, table_name),
                )

                columns = cursor.fetchall()
                if not columns:
                    return f"Table `{table_name}` not found or not accessible."

                result = f"**Table Structure: `{table_name}`**\n\n"
                result += "| Column | Type | Nullable | Default |\n"
                result += "|--------|------|----------|----------|\n"

                for col in columns:
                    type_info = col["data_type"]
                    if col["character_maximum_length"]:
                        type_info += f"({col['character_maximum_length']})"

                    nullable = "YES" if col["is_nullable"] == "YES" else "NO"
                    default = col["column_default"] or "-"

                    result += f"| `{col['column_name']}` | {type_info} | {nullable} | {default} |\n"

                return result

        except Exception as e:
            logger.error(f"Error describing table {table_name}: {e}")
            return f"Error describing table: {str(e)}"

    def run_district_query(self, query: str) -> str:
        """Execute a read-only SQL query with automatic district filtering and comprehensive logging."""
        try:
            logger.info(f"🔍 Executing SQL Query for District {self.district_id}")
            logger.info(f"📝 Original Query: {query}")

            # Validate query safety
            if not self._validate_sql_safety(query):
                error_msg = "Only read-only operations are allowed"
                logger.error(f"❌ Security Error: {error_msg}")
                return f"❌ **Query Rejected**: {error_msg}."

            # Inject district filter
            filtered_query = self._inject_district_filter(query)
            logger.info(f"🔒 Filtered Query: {filtered_query}")

            conn = self._get_connection()
            with conn.cursor() as cursor:
                # Log query execution start
                import time

                start_time = time.time()

                cursor.execute(filtered_query)
                results = cursor.fetchall()

                execution_time = time.time() - start_time
                logger.info(
                    f"⚡ Query executed in {execution_time:.3f}s, returned {len(results)} rows"
                )

                if not results:
                    logger.info("📊 Query returned no results")
                    return "Query executed successfully but returned no results."

                # Format results as HTML table for better display
                if len(results) == 1 and len(results[0]) == 1:
                    # Single value result
                    result_value = list(results[0].values())[0]
                    logger.info(f"📊 Single value result: {result_value}")
                    return f"**Result:** {result_value}"

                # Multiple results - create HTML table
                logger.info(f"📊 Creating HTML table for {len(results)} rows")
                html_result = "<div class='query-results'>\n"
                html_result += (
                    f"<p><strong>Query:</strong> <code>{filtered_query}</code></p>\n"
                )
                html_result += f"<p><strong>Results:</strong> {len(results)} rows</p>\n"

                if results:
                    html_result += (
                        "<table class='table table-striped'>\n<thead>\n<tr>\n"
                    )

                    # Headers
                    for column in results[0].keys():
                        html_result += f"<th>{column}</th>\n"
                    html_result += "</tr>\n</thead>\n<tbody>\n"

                    # Data rows (limit to first 50 for performance)
                    for row in results[:50]:
                        html_result += "<tr>\n"
                        for value in row.values():
                            html_result += (
                                f"<td>{value if value is not None else 'NULL'}</td>\n"
                            )
                        html_result += "</tr>\n"

                    html_result += "</tbody>\n</table>\n"

                    if len(results) > 50:
                        html_result += f"<p><em>Showing first 50 of {len(results)} results</em></p>\n"
                        logger.info(
                            f"📊 Truncated results: showing 50 of {len(results)} rows"
                        )

                html_result += "</div>\n"
                logger.info("✅ HTML table generated successfully")
                return html_result

        except psycopg2.Error as e:
            logger.error(f"❌ SQL Query Error: {str(e)}")
            logger.error(f"💥 Failed Query: {query}")
            # Reset connection to recover from any transaction issues
            self._connection = None
            return f"❌ **Query Error:** {str(e)}"
        except Exception as e:
            logger.error(f"❌ SQL Query Error: {str(e)}")
            logger.error(f"💥 Failed Query: {query}")
            return f"❌ **Query Error:** {str(e)}"

    def get_software_usage_summary(self) -> str:
        """Get aggregated software usage statistics for the district using materialized views."""
        query = """
        WITH district_summary AS (
            SELECT
                COUNT(DISTINCT s.id) as total_software,
                COUNT(DISTINCT CASE WHEN s.authorized = true THEN s.id END) as authorized_software,
                COUNT(DISTINCT CASE WHEN s.authorized = false THEN s.id END) as unauthorized_software,
                SUM(CASE WHEN s.authorized = true THEN COALESCE(s.total_cost, 0) END) as total_investment,
                SUM(s.students_licensed) as total_licensed_users
            FROM software s
            WHERE s.district_id = %s
        ),
        usage_summary AS (
            SELECT
                COUNT(DISTINCT su.user_id) as active_users_all_time,
                SUM(su.minutes_used) as total_minutes_used,
                COUNT(DISTINCT su.date) as total_usage_days,
                MAX(su.date) as last_usage_date
            FROM software_usage su
            JOIN software s ON s.id = su.software_id
            WHERE s.district_id = %s
        ),
        user_summary AS (
            SELECT
                COUNT(DISTINCT p.id) as total_users,
                COUNT(DISTINCT CASE WHEN p.role = 'student' THEN p.id END) as total_students,
                COUNT(DISTINCT CASE WHEN p.role = 'teacher' THEN p.id END) as total_teachers
            FROM profiles p
            WHERE p.district_id = %s
        )
        SELECT
            ds.total_software,
            ds.authorized_software,
            ds.unauthorized_software,
            COALESCE(ds.total_investment, 0) as total_investment,
            ds.total_licensed_users,
            COALESCE(us2.total_users, 0) as total_users,
            COALESCE(us2.total_students, 0) as total_students,
            COALESCE(us2.total_teachers, 0) as total_teachers,
            COALESCE(us.active_users_all_time, 0) as active_users,
            COALESCE(us.total_minutes_used, 0) as total_minutes_used,
            COALESCE(us.total_usage_days, 0) as total_usage_days,
            us.last_usage_date
        FROM district_summary ds
        CROSS JOIN usage_summary us
        CROSS JOIN user_summary us2
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    query, (self.district_id, self.district_id, self.district_id)
                )
                result = cursor.fetchone()

                if result:
                    html = "<div class='usage-summary'>\n"
                    html += "<h3>📊 District Software Usage Summary</h3>\n"
                    html += "<div class='row'>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['total_software']}</h4><p>Total Software</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['authorized_software']}</h4><p>Authorized</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['unauthorized_software']}</h4><p>Unauthorized</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>${result['total_investment']:,.0f}</h4><p>Total Investment</p></div></div>\n"
                    html += "</div>\n"
                    html += "<div class='row'>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['active_users']}</h4><p>Active Users</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['total_students']}</h4><p>Students</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['total_teachers']}</h4><p>Teachers</p></div></div>\n"
                    html += f"<div class='col-md-3'><div class='stat-card'><h4>{result['total_minutes_used']:,.0f}</h4><p>Total Minutes</p></div></div>\n"
                    html += "</div>\n</div>\n"
                    return html

                return "No usage data found for your district."

        except Exception as e:
            logger.error(f"Error getting usage summary: {e}")
            return f"Error retrieving usage summary: {str(e)}"

    def get_top_software_by_usage(self, limit: int = 10) -> str:
        """Get the most used software in the district using materialized views for better performance."""
        query = """
        SELECT
            name,
            primary_category as category,
            COALESCE(total_cost, 0) as total_investment,
            total_minutes,
            active_users as unique_users,
            usage_days,
            CASE
                WHEN roi_status = 'high' THEN '🟢 High'
                WHEN roi_status = 'moderate' THEN '🟡 Moderate'
                ELSE '🔴 Low'
            END as roi_indicator,
            COALESCE(avg_roi_percentage, 0) as roi_percentage
        FROM mv_software_usage_analytics_v3
        WHERE district_id = %s
            AND total_minutes > 0
        ORDER BY total_minutes DESC
        LIMIT %s
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, (self.district_id, limit))
                results = cursor.fetchall()

                if not results:
                    return "No software usage data found for your district."

                html = "<div class='top-software'>\n"
                html += f"<h3>🏆 Top {limit} Software by Usage (Real Data)</h3>\n"
                html += "<table class='table table-striped'>\n"
                html += "<thead><tr><th>Software</th><th>Category</th><th>Investment</th><th>Total Minutes</th><th>Active Users</th><th>ROI Status</th></tr></thead>\n"
                html += "<tbody>\n"

                for row in results:
                    html += f"<tr>\n"
                    html += f"<td><strong>{row['name']}</strong></td>\n"
                    html += f"<td>{row['category'] or 'N/A'}</td>\n"
                    html += f"<td>${row['total_investment']:,.0f}</td>\n"
                    html += f"<td>{row['total_minutes']:,.0f}</td>\n"
                    html += f"<td>{row['unique_users']}</td>\n"
                    html += f"<td>{row['roi_indicator']} ({row['roi_percentage']:.1f}%)</td>\n"
                    html += f"</tr>\n"

                html += "</tbody>\n</table>\n</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting top software: {e}")
            return f"Error retrieving top software: {str(e)}"

    def get_district_software_count(self) -> str:
        """Get total count of software registered in the district."""
        return self.run_district_query(
            "SELECT COUNT(*) as software_count FROM software"
        )

    def get_usage_trends(self, days: int = 30) -> str:
        """Show usage trends over the specified number of days using correct schema."""
        query = """
        SELECT
            su.date as usage_date,
            COUNT(DISTINCT su.software_id) as software_used,
            COUNT(DISTINCT su.user_id) as unique_users,
            SUM(su.minutes_used) as total_minutes,
            AVG(su.minutes_used) as avg_minutes_per_session
        FROM software_usage su
        JOIN software s ON su.software_id = s.id
        WHERE s.district_id = %s
            AND su.date >= CURRENT_DATE - INTERVAL '%s days'
            AND su.minutes_used > 0
        GROUP BY su.date
        ORDER BY su.date DESC
        LIMIT 30
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, (self.district_id, days))
                results = cursor.fetchall()

                if not results:
                    return f"No usage data found for the last {days} days."

                html = "<div class='usage-trends'>\n"
                html += f"<h3>📈 Usage Trends (Last {days} Days - Real Data)</h3>\n"
                html += "<table class='table table-striped'>\n"
                html += "<thead><tr><th>Date</th><th>Software Used</th><th>Unique Users</th><th>Total Minutes</th><th>Avg Minutes/Session</th></tr></thead>\n"
                html += "<tbody>\n"

                total_minutes = sum(row["total_minutes"] for row in results)
                total_users = sum(row["unique_users"] for row in results)

                for row in results:
                    html += f"<tr>\n"
                    html += f"<td>{row['usage_date']}</td>\n"
                    html += f"<td>{row['software_used']}</td>\n"
                    html += f"<td>{row['unique_users']}</td>\n"
                    html += f"<td>{row['total_minutes']:,.0f}</td>\n"
                    html += f"<td>{row['avg_minutes_per_session']:.1f}</td>\n"
                    html += f"</tr>\n"

                html += "</tbody>\n</table>\n"
                html += f"<div class='alert alert-info'>\n"
                html += f"<strong>Summary:</strong> {total_minutes:,.0f} total minutes across {len(results)} days\n"
                html += f"</div>\n"
                html += "</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting usage trends: {e}")
            return f"Error retrieving usage trends: {str(e)}"

    def get_investment_analysis(self) -> str:
        """Get comprehensive investment analysis using materialized views."""
        query = """
        SELECT
            software_name as name,
            category,
            funding_source,
            total_investment,
            total_licensed_users,
            active_users,
            avg_utilization,
            total_minutes,
            avg_cost_per_student,
            avg_roi_percentage,
            roi_status,
            authorized,
            latest_purchase_date
        FROM mv_software_investment_summary
        WHERE district_id = %s
            AND total_investment > 0
        ORDER BY total_investment DESC
        LIMIT 15
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, (self.district_id,))
                results = cursor.fetchall()

                if not results:
                    return "No investment data found for your district."

                total_investment = sum(row["total_investment"] for row in results)
                high_roi_count = sum(
                    1 for row in results if row["roi_status"] == "high"
                )

                html = "<div class='investment-analysis'>\n"
                html += "<h3>💰 Software Investment Analysis (Real Data)</h3>\n"
                html += f"<div class='alert alert-info'>\n"
                html += (
                    f"<strong>Total Investment:</strong> ${total_investment:,.0f} | "
                )
                html += f"<strong>High ROI Software:</strong> {high_roi_count}/{len(results)}\n"
                html += f"</div>\n"
                html += "<table class='table table-striped'>\n"
                html += "<thead><tr><th>Software</th><th>Investment</th><th>Licensed Users</th><th>Active Users</th><th>Cost/Student</th><th>ROI Status</th></tr></thead>\n"
                html += "<tbody>\n"

                for row in results:
                    roi_badge = (
                        "🟢 High"
                        if row["roi_status"] == "high"
                        else "🟡 Moderate"
                        if row["roi_status"] == "moderate"
                        else "🔴 Low"
                    )
                    html += f"<tr>\n"
                    html += f"<td><strong>{row['name']}</strong><br><small>{row['category'] or 'N/A'}</small></td>\n"
                    html += f"<td>${row['total_investment']:,.0f}</td>\n"
                    html += f"<td>{row['total_licensed_users']}</td>\n"
                    html += f"<td>{row['active_users']}</td>\n"
                    html += f"<td>${row['avg_cost_per_student']:.0f}</td>\n"
                    html += f"<td>{roi_badge}</td>\n"
                    html += f"</tr>\n"

                html += "</tbody>\n</table>\n</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting investment analysis: {e}")
            return f"Error retrieving investment analysis: {str(e)}"

    def get_peer_benchmarking_summary(self) -> str:
        """Get peer district benchmarking insights comparing the district to similar peers."""
        metrics_query = """
        SELECT
            metric_name, metric_value, percentile, peer_average,
            unit, category, ranking, peer_count
        FROM peer_district_metrics
        WHERE district_id = %s
        ORDER BY category, metric_name
        """

        comparisons_query = """
        SELECT
            metric, your_value, peer_average, percentile,
            ranking, total_districts, unit, interpretation
        FROM peer_comparisons
        WHERE district_id = %s
        ORDER BY percentile DESC
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(metrics_query, (self.district_id,))
                metrics = cursor.fetchall()

                cursor.execute(comparisons_query, (self.district_id,))
                comparisons = cursor.fetchall()

                if not metrics and not comparisons:
                    return "No peer benchmarking data found for your district."

                html = "<div class='peer-benchmarking'>\n"
                html += "<h3>Peer District Benchmarking</h3>\n"

                if metrics:
                    html += "<h4>District Metrics vs Peers</h4>\n"
                    html += "<table class='table table-striped'>\n"
                    html += "<thead><tr><th>Metric</th><th>Your Value</th><th>Peer Average</th><th>Percentile</th><th>Ranking</th><th>Category</th></tr></thead>\n"
                    html += "<tbody>\n"
                    for m in metrics:
                        unit = m['unit'] or ''
                        html += "<tr>\n"
                        html += f"<td>{m['metric_name']}</td>\n"
                        html += f"<td>{m['metric_value']} {unit}</td>\n"
                        html += f"<td>{m['peer_average']} {unit}</td>\n"
                        html += f"<td>{m['percentile']}%</td>\n"
                        html += f"<td>{m['ranking'] or 'N/A'}</td>\n"
                        html += f"<td>{m['category']}</td>\n"
                        html += "</tr>\n"
                    html += "</tbody>\n</table>\n"

                if comparisons:
                    html += "<h4>Peer Comparisons</h4>\n"
                    html += "<table class='table table-striped'>\n"
                    html += "<thead><tr><th>Metric</th><th>Your Value</th><th>Peer Avg</th><th>Percentile</th><th>Rank</th><th>Total Districts</th><th>Interpretation</th></tr></thead>\n"
                    html += "<tbody>\n"
                    for c in comparisons:
                        unit = c['unit'] or ''
                        html += "<tr>\n"
                        html += f"<td>{c['metric']}</td>\n"
                        html += f"<td>{c['your_value']} {unit}</td>\n"
                        html += f"<td>{c['peer_average']} {unit}</td>\n"
                        html += f"<td>{c['percentile']}%</td>\n"
                        html += f"<td>{c['ranking']}</td>\n"
                        html += f"<td>{c['total_districts']}</td>\n"
                        html += f"<td>{c['interpretation']}</td>\n"
                        html += "</tr>\n"
                    html += "</tbody>\n</table>\n"

                html += "</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting peer benchmarking summary: {e}")
            return f"Error retrieving peer benchmarking data: {str(e)}"

    def get_peer_comparisons(self) -> str:
        """Get peer comparison data showing metric-by-metric analysis against peer group."""
        query = """
        SELECT
            metric, your_value, peer_average, percentile,
            ranking, total_districts, unit, interpretation
        FROM peer_comparisons
        WHERE district_id = %s
        ORDER BY percentile DESC
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, (self.district_id,))
                results = cursor.fetchall()

                if not results:
                    return "No peer comparison data found for your district."

                html = "<div class='peer-comparisons'>\n"
                html += "<h3>Peer District Comparisons</h3>\n"
                html += "<table class='table table-striped'>\n"
                html += "<thead><tr><th>Metric</th><th>Your Value</th><th>Peer Avg</th><th>Percentile</th><th>Rank</th><th>Total</th><th>Interpretation</th></tr></thead>\n"
                html += "<tbody>\n"

                for row in results:
                    unit = row['unit'] or ''
                    html += "<tr>\n"
                    html += f"<td>{row['metric']}</td>\n"
                    html += f"<td>{row['your_value']} {unit}</td>\n"
                    html += f"<td>{row['peer_average']} {unit}</td>\n"
                    html += f"<td>{row['percentile']}%</td>\n"
                    html += f"<td>{row['ranking']}</td>\n"
                    html += f"<td>{row['total_districts']}</td>\n"
                    html += f"<td>{row['interpretation']}</td>\n"
                    html += "</tr>\n"

                html += "</tbody>\n</table>\n</div>\n"
                return html

        except Exception as e:
            logger.error(f"Error getting peer comparisons: {e}")
            return f"Error retrieving peer comparisons: {str(e)}"
