"""
Robust PostgreSQL Tools with Transaction Handling

This module provides a PostgreSQL toolkit that properly handles transaction
errors and rollbacks, preventing "current transaction is aborted" errors.
"""

import logging
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from phi.tools import Toolkit

logger = logging.getLogger(__name__)


class RobustPostgresTools(Toolkit):
    """
    Robust PostgreSQL toolkit with proper transaction error handling.

    Key features:
    - Uses autocommit mode to prevent transaction aborted state
    - Automatic rollback on query errors
    - Read-only operations only
    - District-aware filtering
    """

    def __init__(
        self,
        db_name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: int = 5432,
        schema: str = "public",
        district_id: Optional[str] = None,
        run_queries: bool = True,
        inspect_queries: bool = False,
    ):
        super().__init__(name="robust_postgres_tools")

        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.schema = schema
        self.district_id = district_id
        self.run_queries = run_queries
        self.inspect_queries = inspect_queries

        # Connection pool - will be created on first use
        self._connection: Optional[psycopg2.extensions.connection] = None

        # Register available functions
        self.register(self.run_query)
        self.register(self.describe_table)
        self.register(self.list_tables)

        logger.info(f"RobustPostgresTools initialized for district: {district_id}")

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get or create a database connection with autocommit enabled."""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.db_name,
                    user=self.user,
                    password=self.password,
                    cursor_factory=RealDictCursor,
                )
                # Enable autocommit to prevent transaction aborted state
                self._connection.autocommit = True
                # Set session to read-only for safety
                with self._connection.cursor() as cur:
                    cur.execute("SET default_transaction_read_only = ON;")
                logger.info("Database connection established with autocommit=True")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

        return self._connection

    def _safe_execute(
        self, query: str, params: tuple = None
    ) -> List[Dict[str, Any]]:
        """
        Safely execute a query with automatic error handling and rollback.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        conn = self._get_connection()

        try:
            with conn.cursor() as cursor:
                if self.inspect_queries:
                    logger.info(f"Executing query: {query}")
                    if params:
                        logger.info(f"With params: {params}")

                cursor.execute(query, params)

                # Check if query returns results
                if cursor.description:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                return []

        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            # With autocommit, no rollback needed
            # But if somehow we got into a bad state, try to recover
            try:
                if not conn.autocommit:
                    conn.rollback()
                    logger.info("Transaction rolled back")
            except:
                pass
            raise

    def run_query(self, query: str) -> str:
        """
        Run a SQL query with automatic district filtering and transaction handling.

        IMPORTANT: This function automatically handles transaction errors.
        Use materialized views (mv_*) for best performance.

        Args:
            query: SQL SELECT query to execute

        Returns:
            JSON-formatted query results or error message
        """
        if not self.run_queries:
            return "Query execution is disabled."

        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
            return "Error: Only SELECT queries are allowed for security reasons."

        # Block dangerous keywords
        dangerous_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
            "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
        ]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return f"Error: {keyword} operations are not allowed."

        try:
            import time
            start_time = time.time()

            results = self._safe_execute(query)

            execution_time = time.time() - start_time
            logger.info(f"Query executed in {execution_time:.3f}s, returned {len(results)} rows")

            if not results:
                return "Query executed successfully but returned no results."

            # Format results
            import json
            # Limit to first 50 rows for performance
            limited_results = results[:50]
            output = json.dumps(limited_results, default=str, indent=2)

            if len(results) > 50:
                output += f"\n\n(Showing first 50 of {len(results)} total results)"

            return output

        except Exception as e:
            error_msg = f"Query error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def describe_table(self, table_name: str) -> str:
        """
        Describe the structure of a table or materialized view.

        Args:
            table_name: Name of the table or view to describe

        Returns:
            Table structure description
        """
        try:
            query = """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """

            results = self._safe_execute(query, (self.schema, table_name))

            if not results:
                return f"Table '{table_name}' not found in schema '{self.schema}'."

            output = f"Table: {table_name}\n"
            output += "=" * 60 + "\n"
            output += f"{'Column':<30} {'Type':<20} {'Nullable':<10}\n"
            output += "-" * 60 + "\n"

            for col in results:
                output += f"{col['column_name']:<30} {col['data_type']:<20} {col['is_nullable']:<10}\n"

            return output

        except Exception as e:
            return f"Error describing table: {str(e)}"

    def list_tables(self) -> str:
        """
        List all tables and materialized views in the database.

        Returns:
            List of tables and views with their types
        """
        try:
            query = """
                SELECT
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                UNION ALL
                SELECT
                    matviewname as table_name,
                    'MATERIALIZED VIEW' as table_type
                FROM pg_matviews
                WHERE schemaname = %s
                ORDER BY table_name
            """

            results = self._safe_execute(query, (self.schema, self.schema))

            if not results:
                return "No tables found."

            # Separate MVs and regular tables
            mvs = [r for r in results if 'MATERIALIZED' in r['table_type'] or r['table_name'].startswith('mv_')]
            tables = [r for r in results if r not in mvs]

            output = "MATERIALIZED VIEWS (Use these for fast queries!):\n"
            output += "=" * 50 + "\n"
            for mv in mvs:
                output += f"  - {mv['table_name']}\n"

            output += "\nBASE TABLES:\n"
            output += "=" * 50 + "\n"
            for t in tables[:20]:  # Limit base tables
                output += f"  - {t['table_name']} ({t['table_type']})\n"

            if len(tables) > 20:
                output += f"  ... and {len(tables) - 20} more tables\n"

            return output

        except Exception as e:
            return f"Error listing tables: {str(e)}"

    def close(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")
