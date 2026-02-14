"""
Materialized View Query Router

This module provides intelligent query routing to the most appropriate
materialized view based on user query analysis.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from mv_knowledge_registry import (
    MATERIALIZED_VIEW_REGISTRY,
    QueryIntent,
    detect_query_intents,
    get_best_materialized_view,
    get_recommended_views_for_query,
    generate_mv_query_suggestion,
)

logger = logging.getLogger(__name__)


class MVQueryRouter:
    """
    Intelligent query router that selects and executes queries against
    the most appropriate materialized view.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        district_id: str,
        schema: str = "public",
        school_id: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.district_id = district_id
        self.schema = schema
        self.school_id = school_id
        self._connection: Optional[psycopg2.extensions.connection] = None

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get database connection with read-only settings."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,
            )
            self._connection.set_session(readonly=True, autocommit=True)
        return self._connection

    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as list of dicts with error recovery."""
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                conn = self._get_connection()

                # Check if connection is in a bad state and reconnect if needed
                if conn.closed:
                    logger.warning("Connection was closed, reconnecting...")
                    self._connection = None
                    conn = self._get_connection()

                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return [dict(row) for row in cursor.fetchall()]

            except psycopg2.OperationalError as e:
                # Connection lost - try to reconnect
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                self._connection = None
                last_error = e

            except psycopg2.InterfaceError as e:
                # Connection issue - reconnect
                logger.warning(f"Interface error (attempt {attempt + 1}): {e}")
                self._connection = None
                last_error = e

            except psycopg2.InternalError as e:
                # Transaction aborted or similar - reconnect
                logger.warning(f"Internal error (attempt {attempt + 1}): {e}")
                self._connection = None
                last_error = e

            except Exception as e:
                logger.error(f"Query execution error: {e}")
                last_error = e
                # For other errors, don't retry
                break

        logger.error(f"Query failed after {max_retries} attempts: {last_error}")
        raise last_error

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _build_school_filter(self, column: str = "school_id") -> Tuple[str, List]:
        """Build conditional school filter clause for views with school_id column."""
        if self.school_id:
            return f" AND {column} = %s", [self.school_id]
        return "", []

    def _build_school_name_filter(self) -> Tuple[str, List]:
        """Build school filter using school_name lookup from school_id."""
        if self.school_id:
            return " AND school_name = (SELECT name FROM schools WHERE id = %s AND district_id = %s)", [self.school_id, self.district_id]
        return "", []

    @staticmethod
    def _enrich_with_investment_fields(rows: List[Dict]) -> List[Dict]:
        """
        Compute investment_return and unrealized_value for each row,
        then remove avg_roi_percentage from the output.

        investment_return  = (total_cost * usage_compliance) / 100
        unrealized_value   = total_cost - investment_return
        """
        for row in rows:
            total_cost = float(row.get("total_cost") or 0)
            usage_compliance = float(row.get("usage_compliance") or 0)
            investment_return = round((total_cost * usage_compliance) / 100, 2)
            unrealized_value = round(total_cost - investment_return, 2)
            row["investment_return"] = investment_return
            row["unrealized_value"] = unrealized_value
            row.pop("avg_roi_percentage", None)
            row.pop("roi_percentage", None)
        return rows

    # =========================================================================
    # PRIMARY MV QUERY METHODS - These should be used by the agent
    # =========================================================================

    def get_software_analytics(
        self,
        limit: int = 100,
        order_by: str = "total_minutes",
        roi_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive software analytics.
        Uses mv_software_usage_by_school_v2 when school_id is provided,
        otherwise uses mv_software_usage_analytics_v4 for district-wide data.
        """
        start_time = time.time()

        if self.school_id:
            # Use school-level MV when school_id is provided
            school_filter, school_params = self._build_school_filter("school_id")

            query = f"""
            SELECT
                software_name as name,
                category as primary_category,
                total_cost,
                total_minutes,
                active_users,
                active_students,
                active_teachers,
                students_licensed,
                school_name,
                usage_days,
                first_use_date,
                last_use_date,
                cost_per_student,
                avg_roi_percentage,
                roi_status,
                engagement_rate,
                usage_compliance,
                authorized,
                district_purchased
            FROM mv_software_usage_by_school_v2
            WHERE district_id = %s{school_filter}
            """

            params = [self.district_id] + school_params

            if roi_status:
                query += " AND roi_status = %s"
                params.append(roi_status)

            query += f" ORDER BY {order_by} DESC LIMIT %s"
            params.append(limit)

            results = self._execute_query(query, tuple(params))
            self._enrich_with_investment_fields(results)
            execution_time = time.time() - start_time

            return {
                "data": results,
                "mv_used": "mv_software_usage_by_school_v2",
                "execution_time": execution_time,
                "count": len(results),
                "school_id": self.school_id
            }
        else:
            # Use district-level MV when no school_id
            query = """
            SELECT
                name,
                primary_category,
                total_cost,
                total_minutes,
                active_users,
                active_students,
                active_teachers,
                students_licensed,
                school_names,
                usage_days,
                first_use_date,
                last_use_date,
                cost_per_student,
                avg_roi_percentage,
                roi_status,
                engagement_rate,
                usage_compliance,
                authorized,
                district_purchased
            FROM mv_software_usage_analytics_v4
            WHERE district_id = %s
            """

            params = [self.district_id]

            if roi_status:
                query += " AND roi_status = %s"
                params.append(roi_status)

            query += f" ORDER BY {order_by} DESC LIMIT %s"
            params.append(limit)

            results = self._execute_query(query, tuple(params))
            self._enrich_with_investment_fields(results)
            execution_time = time.time() - start_time

            return {
                "data": results,
                "mv_used": "mv_software_usage_analytics_v4",
                "execution_time": execution_time,
                "count": len(results)
            }

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get dashboard-ready software metrics.
        Uses mv_software_usage_by_school_v2 when school_id is provided,
        otherwise uses mv_software_usage_analytics_v4 for district-wide data.
        """
        start_time = time.time()
        school_filter, school_params = self._build_school_filter("school_id")

        if self.school_id:
            # Use school-level MV when school_id is provided
            summary_query = f"""
            SELECT
                sw.total_software,
                sw.high_roi_count,
                sw.moderate_roi_count,
                sw.low_roi_count,
                sw.total_investment,
                sw.total_licensed,
                COALESCE(au.total_active_users, 0) as total_active_users,
                sw.total_minutes,
                sw.avg_usage_compliance
            FROM (
                SELECT
                    COUNT(DISTINCT software_name) as total_software,
                    COUNT(DISTINCT software_name) FILTER (WHERE roi_status = 'high') as high_roi_count,
                    COUNT(DISTINCT software_name) FILTER (WHERE roi_status = 'moderate') as moderate_roi_count,
                    COUNT(DISTINCT software_name) FILTER (WHERE roi_status = 'low') as low_roi_count,
                    COALESCE(SUM(total_cost), 0) as total_investment,
                    COALESCE(SUM(students_licensed), 0) as total_licensed,
                    COALESCE(SUM(total_minutes), 0) as total_minutes,
                    COALESCE(AVG(usage_compliance), 0) as avg_usage_compliance
                FROM mv_software_usage_by_school_v2
                WHERE district_id = %s{school_filter}
            ) sw
            CROSS JOIN (
                SELECT COUNT(*) as total_active_users
                FROM mv_active_users_summary
                WHERE district_id = %s AND total_usage_minutes > 0{school_filter}
            ) au
            """

            params = [self.district_id] + school_params + [self.district_id] + school_params
            summary = self._execute_query(summary_query, tuple(params))

            # Top software by usage from school-level MV
            top_query = f"""
            SELECT
                software_name as name,
                category as primary_category,
                total_cost,
                active_users,
                total_minutes,
                usage_compliance,
                roi_status
            FROM mv_software_usage_by_school_v2
            WHERE district_id = %s{school_filter}
            ORDER BY total_minutes DESC
            LIMIT 100
            """

            params = [self.district_id] + school_params
            top_software = self._execute_query(top_query, tuple(params))
            mv_used = "mv_software_usage_by_school_v2"
        else:
            # Use district-level MV when no school_id
            summary_query = f"""
            SELECT
                sw.total_software,
                sw.high_roi_count,
                sw.moderate_roi_count,
                sw.low_roi_count,
                sw.total_investment,
                sw.total_licensed,
                COALESCE(au.total_active_users, 0) as total_active_users,
                sw.total_minutes,
                sw.avg_usage_compliance
            FROM (
                SELECT
                    COUNT(*) as total_software,
                    COUNT(*) FILTER (WHERE roi_status = 'high') as high_roi_count,
                    COUNT(*) FILTER (WHERE roi_status = 'moderate') as moderate_roi_count,
                    COUNT(*) FILTER (WHERE roi_status = 'low') as low_roi_count,
                    COALESCE(SUM(total_cost), 0) as total_investment,
                    COALESCE(SUM(students_licensed), 0) as total_licensed,
                    COALESCE(SUM(total_minutes), 0) as total_minutes,
                    COALESCE(AVG(usage_compliance), 0) as avg_usage_compliance
                FROM mv_software_usage_analytics_v4
                WHERE district_id = %s
            ) sw
            CROSS JOIN (
                SELECT COUNT(*) as total_active_users
                FROM mv_active_users_summary
                WHERE district_id = %s AND total_usage_minutes > 0
            ) au
            """

            params = [self.district_id, self.district_id]
            summary = self._execute_query(summary_query, tuple(params))

            # Top software by usage from district-level MV
            top_query = """
            SELECT
                name,
                primary_category,
                total_cost,
                active_users,
                total_minutes,
                usage_compliance,
                roi_status
            FROM mv_software_usage_analytics_v4
            WHERE district_id = %s
            ORDER BY total_minutes DESC
            LIMIT 100
            """

            top_software = self._execute_query(top_query, (self.district_id,))
            mv_used = "mv_software_usage_analytics_v4"

        self._enrich_with_investment_fields(top_software)
        execution_time = time.time() - start_time

        return {
            "summary": summary[0] if summary else {},
            "top_software": top_software,
            "mv_used": mv_used,
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_user_analytics(self) -> Dict[str, Any]:
        """
        Get user analytics from mv_dashboard_user_analytics.
        Best for user counts by role and grade.
        """
        start_time = time.time()
        school_filter, school_params = self._build_school_filter("school_id")

        # Summary by role
        role_query = f"""
        SELECT
            user_type,
            SUM(total_users) as total_users,
            SUM(active_users_30d) as active_users_30d,
            SUM(active_users_all_time) as active_users_all_time,
            SUM(total_usage_minutes_90d) as total_usage_minutes_90d
        FROM mv_dashboard_user_analytics
        WHERE district_id = %s{school_filter}
        GROUP BY user_type
        """

        params = [self.district_id] + school_params
        by_role = self._execute_query(role_query, tuple(params))

        # By grade (students only, aggregated across schools)
        grade_query = f"""
        SELECT
            grade,
            SUM(total_users) as total_users,
            SUM(active_users_all_time) as active_users_all_time,
            SUM(active_users_30d) as active_users_30d,
            SUM(total_usage_minutes_90d) as total_usage_minutes_90d
        FROM mv_dashboard_user_analytics
        WHERE district_id = %s AND user_type = 'student' AND grade IS NOT NULL{school_filter}
        GROUP BY grade
        ORDER BY grade
        """

        params = [self.district_id] + school_params
        by_grade = self._execute_query(grade_query, tuple(params))

        # By school (one row per school, all user types combined)
        school_query = f"""
        SELECT
            school_name,
            SUM(total_users) as total_users,
            SUM(active_users_all_time) as active_users_all_time,
            SUM(active_users_30d) as active_users_30d,
            SUM(CASE WHEN user_type = 'student' THEN total_users ELSE 0 END) as total_students,
            SUM(CASE WHEN user_type = 'student' THEN active_users_all_time ELSE 0 END) as active_students_all_time,
            SUM(CASE WHEN user_type = 'teacher' THEN total_users ELSE 0 END) as total_teachers,
            SUM(CASE WHEN user_type = 'teacher' THEN active_users_all_time ELSE 0 END) as active_teachers_all_time
        FROM mv_dashboard_user_analytics
        WHERE district_id = %s AND school_name IS NOT NULL{school_filter}
        GROUP BY school_name
        ORDER BY school_name
        """

        params = [self.district_id] + school_params
        by_school = self._execute_query(school_query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "by_role": by_role,
            "by_grade": by_grade,
            "by_school": by_school,
            "mv_used": "mv_dashboard_user_analytics",
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_investment_analysis(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get investment analysis from mv_software_investment_summary.
        Best for financial reports and budget analysis.
        """
        start_time = time.time()
        school_name_filter, school_name_params = self._build_school_name_filter()

        query = f"""
        SELECT
            software_name,
            display_name,
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
            latest_purchase_date
        FROM mv_software_investment_summary
        WHERE district_id = %s AND total_investment > 0{school_name_filter}
        ORDER BY total_investment DESC
        LIMIT %s
        """

        params = [self.district_id] + school_name_params + [limit]
        results = self._execute_query(query, tuple(params))

        # Summary
        summary_query = f"""
        SELECT
            SUM(total_investment) as total_investment,
            COUNT(*) as software_count,
            COUNT(*) FILTER (WHERE roi_status = 'high') as high_roi_count,
            COUNT(*) FILTER (WHERE roi_status = 'low') as low_roi_count,
            AVG(avg_roi_percentage) as avg_roi
        FROM mv_software_investment_summary
        WHERE district_id = %s AND total_investment > 0{school_name_filter}
        """

        params = [self.district_id] + school_name_params
        summary = self._execute_query(summary_query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "software": results,
            "summary": summary[0] if summary else {},
            "mv_used": "mv_software_investment_summary",
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_unauthorized_software(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get unauthorized software analytics from mv_unauthorized_software_analytics_v4.
        Best for security and compliance dashboards.
        """
        start_time = time.time()
        school_name_filter, school_name_params = self._build_school_name_filter()

        query = f"""
        SELECT
            name,
            category,
            url,
            school_name,
            district_name,
            total_usage_minutes,
            student_usage_minutes,
            teacher_usage_minutes,
            unique_users,
            student_users,
            teacher_users,
            usage_count,
            last_used_date,
            avg_minutes_per_user,
            avg_minutes_per_student,
            avg_minutes_per_teacher
        FROM mv_unauthorized_software_analytics_v4
        WHERE district_id = %s{school_name_filter}
        ORDER BY total_usage_minutes DESC
        LIMIT %s
        """

        params = [self.district_id] + school_name_params + [limit]
        results = self._execute_query(query, tuple(params))

        # Summary
        summary_query = f"""
        SELECT
            COUNT(DISTINCT name) as total_unauthorized,
            SUM(total_usage_minutes) as total_minutes,
            SUM(student_usage_minutes) as total_student_minutes,
            SUM(teacher_usage_minutes) as total_teacher_minutes,
            SUM(unique_users) as total_users,
            SUM(student_users) as total_students,
            SUM(teacher_users) as total_teachers
        FROM mv_unauthorized_software_analytics_v4
        WHERE district_id = %s{school_name_filter}
        """

        params = [self.district_id] + school_name_params
        summary = self._execute_query(summary_query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "software": results,
            "summary": summary[0] if summary else {},
            "mv_used": "mv_unauthorized_software_analytics_v4",
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_top_users(self, limit: int = 100, role: Optional[str] = None) -> Dict[str, Any]:
        """
        Get top users by usage from mv_user_software_utilization_v2.
        Best for individual user reports.
        """
        start_time = time.time()
        school_filter, school_params = self._build_school_filter("school_id")

        query = f"""
        SELECT
            first_name,
            last_name,
            user_email,
            user_role,
            grade,
            school_name,
            software_name,
            software_category,
            total_minutes,
            sessions_count,
            avg_weekly_minutes,
            first_active,
            last_active
        FROM mv_user_software_utilization_v2
        WHERE district_id = %s{school_filter}
        """

        params = [self.district_id] + school_params

        if role:
            query += " AND user_role = %s"
            params.append(role)

        query += " ORDER BY total_minutes DESC LIMIT %s"
        params.append(limit)

        results = self._execute_query(query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "users": results,
            "mv_used": "mv_user_software_utilization_v2",
            "execution_time": execution_time,
            "count": len(results),
            "school_id": self.school_id
        }

    def get_school_analysis(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get software usage by school from mv_software_usage_by_school_v2.
        Best for school-level comparisons.
        """
        start_time = time.time()
        school_filter, school_params = self._build_school_filter("school_id")

        query = f"""
        SELECT
            school_name,
            software_name,
            category,
            total_cost,
            students_licensed,
            active_users,
            active_students,
            active_teachers,
            total_minutes,
            avg_roi_percentage,
            roi_status,
            usage_compliance
        FROM mv_software_usage_by_school_v2
        WHERE district_id = %s{school_filter}
        ORDER BY total_minutes DESC
        LIMIT %s
        """

        params = [self.district_id] + school_params + [limit]
        results = self._execute_query(query, tuple(params))

        # School summary
        summary_query = f"""
        SELECT
            school_name,
            COUNT(DISTINCT software_name) as software_count,
            SUM(total_cost) as total_investment,
            SUM(active_users) as total_active_users,
            SUM(total_minutes) as total_minutes,
            AVG(avg_roi_percentage) as avg_roi
        FROM mv_software_usage_by_school_v2
        WHERE district_id = %s{school_filter}
        GROUP BY school_name
        ORDER BY total_minutes DESC
        """

        params = [self.district_id] + school_params
        school_summary = self._execute_query(summary_query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "details": results,
            "school_summary": school_summary,
            "mv_used": "mv_software_usage_by_school_v2",
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_usage_rankings(
        self,
        grade_band: Optional[str] = None,
        user_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get software usage rankings from mv_software_usage_rankings_v4.
        Best for top software lists with percentage calculations.
        """
        start_time = time.time()
        school_name_filter, school_name_params = self._build_school_name_filter()

        query = f"""
        SELECT
            name,
            category,
            grade_band,
            user_type,
            school_name,
            funding_source,
            total_cost,
            total_minutes,
            usage_percentage
        FROM mv_software_usage_rankings_v4
        WHERE district_id = %s{school_name_filter}
        """

        params = [self.district_id] + school_name_params

        if grade_band:
            query += " AND grade_band = %s"
            params.append(grade_band)

        if user_type:
            query += " AND user_type = %s"
            params.append(user_type)

        query += " ORDER BY total_minutes DESC LIMIT %s"
        params.append(limit)

        results = self._execute_query(query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "rankings": results,
            "mv_used": "mv_software_usage_rankings_v4",
            "execution_time": execution_time,
            "count": len(results),
            "school_id": self.school_id
        }

    def get_active_users_summary(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get active users summary from mv_active_users_summary.
        Best for user activity reports with grade bands, role breakdowns, and OS/platform analysis.
        Now includes ALL roles and OS/data source information.
        """
        start_time = time.time()
        school_filter, school_params = self._build_school_filter("school_id")

        # Summary by grade band and role (only users with actual usage)
        summary_query = f"""
        SELECT
            grade_band,
            role,
            COUNT(*) as user_count,
            SUM(total_usage_minutes) as total_minutes,
            AVG(total_usage_minutes) as avg_minutes_per_user
        FROM mv_active_users_summary
        WHERE district_id = %s AND total_usage_minutes > 0{school_filter}
        GROUP BY grade_band, role
        ORDER BY grade_band, role
        """

        params = [self.district_id] + school_params
        summary = self._execute_query(summary_query, tuple(params))

        # Summary by role (all roles, including users with 0 usage)
        role_summary_query = f"""
        SELECT
            role,
            COUNT(*) as total_users,
            COUNT(*) FILTER (WHERE total_usage_minutes > 0) as active_users,
            SUM(total_usage_minutes) as total_minutes,
            SUM(chrome_os_minutes) as chrome_os_minutes,
            SUM(windows_minutes) as windows_minutes,
            SUM(ios_minutes) as ios_minutes,
            SUM(other_os_minutes) as other_os_minutes
        FROM mv_active_users_summary
        WHERE district_id = %s{school_filter}
        GROUP BY role
        ORDER BY total_users DESC
        """

        params = [self.district_id] + school_params
        by_role = self._execute_query(role_summary_query, tuple(params))

        # Summary by OS/data source (only users with actual usage)
        os_summary_query = f"""
        SELECT
            primary_os as data_source,
            COUNT(*) as user_count,
            SUM(total_usage_minutes) as total_minutes,
            SUM(chrome_os_minutes) as chrome_os_minutes,
            SUM(windows_minutes) as windows_minutes,
            SUM(ios_minutes) as ios_minutes,
            SUM(other_os_minutes) as other_os_minutes
        FROM mv_active_users_summary
        WHERE district_id = %s AND total_usage_minutes > 0{school_filter}
        GROUP BY primary_os
        ORDER BY user_count DESC
        """

        params = [self.district_id] + school_params
        by_os = self._execute_query(os_summary_query, tuple(params))

        # Top active users (only users with actual usage, includes OS info)
        top_users_query = f"""
        SELECT
            full_name,
            role,
            grade,
            school_name,
            total_usage_minutes,
            total_sessions,
            primary_os,
            chrome_os_minutes,
            windows_minutes,
            ios_minutes,
            last_active_date
        FROM mv_active_users_summary
        WHERE district_id = %s AND total_usage_minutes > 0{school_filter}
        ORDER BY total_usage_minutes DESC
        LIMIT %s
        """

        params = [self.district_id] + school_params + [limit]
        top_users = self._execute_query(top_users_query, tuple(params))
        execution_time = time.time() - start_time

        return {
            "by_grade_band": summary,
            "by_role": by_role,
            "by_os": by_os,
            "top_users": top_users,
            "mv_used": "mv_active_users_summary",
            "execution_time": execution_time,
            "school_id": self.school_id
        }

    def get_peer_benchmarking_summary(self) -> Dict[str, Any]:
        """
        Get peer district benchmarking data from peer_district_metrics and peer_comparisons.
        Best for comparing the district against similar peer districts.
        """
        start_time = time.time()

        # District's own metrics from peer_district_metrics
        metrics_query = """
        SELECT
            metric_name, metric_value, percentile, peer_average,
            unit, category, ranking, matching_tier, peer_count
        FROM peer_district_metrics
        WHERE district_id = %s
        ORDER BY category, metric_name
        """

        metrics = self._execute_query(metrics_query, (self.district_id,))

        # Peer comparisons
        comparisons_query = """
        SELECT
            metric, your_value, peer_average, percentile,
            ranking, total_districts, unit, interpretation,
            matching_tier, peer_count
        FROM peer_comparisons
        WHERE district_id = %s
        ORDER BY percentile DESC
        """

        comparisons = self._execute_query(comparisons_query, (self.district_id,))
        execution_time = time.time() - start_time

        return {
            "metrics": metrics,
            "comparisons": comparisons,
            "mv_used": "peer_district_metrics + peer_comparisons",
            "execution_time": execution_time,
            "metrics_count": len(metrics),
            "comparisons_count": len(comparisons)
        }

    def get_peer_comparisons(self) -> Dict[str, Any]:
        """
        Get peer comparison data from peer_comparisons.
        Best for detailed metric-by-metric comparison against peer group.
        """
        start_time = time.time()

        query = """
        SELECT
            metric, your_value, peer_average, percentile,
            ranking, total_districts, unit, interpretation
        FROM peer_comparisons
        WHERE district_id = %s
        ORDER BY percentile DESC
        """

        results = self._execute_query(query, (self.district_id,))
        execution_time = time.time() - start_time

        return {
            "comparisons": results,
            "mv_used": "peer_comparisons",
            "execution_time": execution_time,
            "count": len(results)
        }

    # =========================================================================
    # INTELLIGENT QUERY ROUTING
    # =========================================================================

    def route_query(self, user_query: str) -> Dict[str, Any]:
        """
        Intelligently route a user query to the appropriate MV and return results.
        This is the main entry point for natural language queries.
        """
        start_time = time.time()

        # Detect intents
        intents = detect_query_intents(user_query)
        logger.info(f"Detected intents: {[i.value for i in intents]}")

        # Get recommended views
        recommended_views = get_recommended_views_for_query(user_query)
        logger.info(f"Recommended views: {[v.name for v in recommended_views]}")

        # Route to appropriate method based on primary intent
        primary_intent = intents[0] if intents else QueryIntent.DASHBOARD_OVERVIEW

        result = {
            "intents": [i.value for i in intents],
            "recommended_views": [v.name for v in recommended_views],
            "primary_intent": primary_intent.value,
        }

        # Call appropriate method based on intent
        if primary_intent == QueryIntent.UNAUTHORIZED_SOFTWARE:
            data = self.get_unauthorized_software()
        elif primary_intent == QueryIntent.SOFTWARE_INVESTMENT:
            data = self.get_investment_analysis()
        elif primary_intent == QueryIntent.USER_ANALYTICS:
            data = self.get_user_analytics()
        elif primary_intent == QueryIntent.STUDENT_ANALYSIS:
            data = self.get_top_users(role="student")
        elif primary_intent == QueryIntent.TEACHER_ANALYSIS:
            data = self.get_top_users(role="teacher")
        elif primary_intent == QueryIntent.SCHOOL_ANALYSIS:
            data = self.get_school_analysis()
        elif primary_intent == QueryIntent.USAGE_RANKINGS:
            data = self.get_usage_rankings()
        elif primary_intent == QueryIntent.ACTIVE_USERS:
            data = self.get_active_users_summary()
        elif primary_intent == QueryIntent.COST_ANALYSIS:
            data = self.get_investment_analysis()
        elif primary_intent == QueryIntent.PEER_BENCHMARKING:
            data = self.get_peer_benchmarking_summary()
        elif primary_intent == QueryIntent.SOFTWARE_ROI:
            data = self.get_software_analytics(order_by="avg_roi_percentage")
        elif primary_intent == QueryIntent.DASHBOARD_OVERVIEW:
            data = self.get_dashboard_metrics()
        else:
            data = self.get_software_analytics()

        result["data"] = data
        result["total_execution_time"] = time.time() - start_time

        return result

    def get_comprehensive_dashboard_data(self) -> Dict[str, Any]:
        """
        Get all data needed for a comprehensive dashboard in a single call.
        This method queries multiple MVs efficiently.
        """
        start_time = time.time()

        return {
            "dashboard_metrics": self.get_dashboard_metrics(),
            "user_analytics": self.get_user_analytics(),
            "investment_summary": self.get_investment_analysis(limit=10),
            "top_software": self.get_software_analytics(limit=10),
            "unauthorized_summary": self.get_unauthorized_software(limit=5),
            "total_execution_time": time.time() - start_time
        }


def create_mv_router(
    postgres_config: dict,
    district_id: str,
    school_id: Optional[str] = None
) -> MVQueryRouter:
    """Factory function to create an MV Query Router."""
    return MVQueryRouter(
        host=postgres_config.get("host"),
        port=postgres_config.get("port", 5432),
        database=postgres_config.get("database"),
        user=postgres_config.get("user"),
        password=postgres_config.get("password"),
        district_id=district_id,
        schema=postgres_config.get("schema", "public"),
        school_id=school_id,
    )
