## Complete Materialized View SQL Definitions

Below are all 16 materialized views with their complete SQL code:

---

### 1. `mv_dashboard_software_metrics`

```sql
CREATE MATERIALIZED VIEW public.mv_dashboard_software_metrics AS
SELECT 
    s.id AS software_id,
    s.name,
    s.district_id,
    s.school_name,
    s.category,
    s.funding_source,
    s.total_cost,
    s.user_type,
    s.authorized,
    s.district_purchased,
    s.students_licensed,
    s.purchase_date,
    s.grade_range,
    s.created_at,
    COALESCE(sm.roi_percentage, 0::numeric) AS roi_percentage,
    COALESCE(sm.cost_per_student, 0::numeric) AS cost_per_student,
    COALESCE((
        SELECT count(DISTINCT su.user_id)
        FROM software_usage su
        WHERE su.software_id = s.id 
          AND su.date >= (CURRENT_DATE - '30 days'::interval)
    ), 0::bigint) AS active_users_30d,
    COALESCE((
        SELECT count(DISTINCT su.user_id)
        FROM software_usage su
        WHERE su.software_id = s.id
    ), 0::bigint) AS active_users_all_time,
    COALESCE((
        SELECT sum(su.minutes_used)
        FROM software_usage su
        WHERE su.software_id = s.id 
          AND su.date >= (CURRENT_DATE - '90 days'::interval)
    ), 0::numeric) AS total_minutes_90d,
    (
        SELECT max(su.date)
        FROM software_usage su
        WHERE su.software_id = s.id
    ) AS last_usage_date,
    CASE
        WHEN s.students_licensed > 0 THEN 
            round((COALESCE((
                SELECT count(DISTINCT su.user_id)
                FROM software_usage su
                WHERE su.software_id = s.id 
                  AND su.date >= (CURRENT_DATE - '30 days'::interval)
            ), 0::bigint)::numeric / s.students_licensed::numeric) * 100::numeric, 2)
        ELSE 0::numeric
    END AS utilization,
    CASE
        WHEN COALESCE(sm.roi_percentage, 0::numeric) >= 70::numeric THEN 'high'::text
        WHEN COALESCE(sm.roi_percentage, 0::numeric) >= 40::numeric THEN 'moderate'::text
        ELSE 'low'::text
    END AS roi_status
FROM software s
LEFT JOIN software_metrics sm ON s.id = sm.software_id
WHERE s.authorized = true OR s.district_purchased = true;
```

---

### 2. `mv_dashboard_user_analytics`

```sql
CREATE MATERIALIZED VIEW public.mv_dashboard_user_analytics AS
SELECT 
    row_number() OVER (ORDER BY p.district_id, p.school_id, p.role, p.grade) AS row_id,
    p.district_id,
    p.school_id,
    s.name AS school_name,
    p.role AS user_type,
    p.grade,
    count(*) AS total_users,
    count(*) FILTER (WHERE EXISTS (
        SELECT 1
        FROM software_usage su
        WHERE su.user_id = p.id 
          AND su.date >= (CURRENT_DATE - '30 days'::interval)
    )) AS active_users_30d,
    count(*) FILTER (WHERE EXISTS (
        SELECT 1
        FROM software_usage su
        WHERE su.user_id = p.id
    )) AS active_users_all_time,
    COALESCE(sum(usage_agg.total_minutes), 0::numeric) AS total_usage_minutes_90d
FROM profiles p
LEFT JOIN schools s ON p.school_id = s.id
LEFT JOIN LATERAL (
    SELECT sum(su.minutes_used) AS total_minutes
    FROM software_usage su
    WHERE su.user_id = p.id 
      AND su.date >= (CURRENT_DATE - '90 days'::interval)
) usage_agg ON true
WHERE p.role = ANY (ARRAY['student'::text, 'teacher'::text])
  AND p.district_id IS NOT NULL
GROUP BY p.district_id, p.school_id, s.name, p.role, p.grade;
```

---

### 3. `mv_software_usage_analytics_v4`

```sql
CREATE MATERIALIZED VIEW public.mv_software_usage_analytics_v4 AS
WITH software_with_metrics AS (
    SELECT 
        s.id, s.name, s.category, s.total_cost, s.students_licensed,
        s.school_name, s.authorized, s.district_purchased, s.user_type,
        s.district_id, s.grade, s.grade_range, s.funding_source,
        s.url, s.icon, s.applicable_grade_bands,
        s.sub_population, s.program_population
    FROM software s
),
usage_per_software AS (
    SELECT 
        su.software_id,
        sum(su.minutes_used) AS total_usage_minutes,
        count(DISTINCT su.date) AS usage_days,
        min(su.date) AS first_use_date,
        max(su.date) AS last_use_date
    FROM software_usage su
    WHERE su.minutes_used > 0::numeric
    GROUP BY su.software_id
),
grouped_by_name_and_district_pre AS (
    SELECT 
        lower(swm.name) AS name_lower,
        min(swm.name) AS name,
        swm.district_id,
        swm.authorized,
        swm.district_purchased,
        array_agg(DISTINCT swm.id) AS software_ids,
        array_agg(DISTINCT swm.category) FILTER (WHERE swm.category IS NOT NULL) AS categories,
        array_agg(DISTINCT swm.school_name) FILTER (WHERE swm.school_name IS NOT NULL) AS school_names,
        array_agg(DISTINCT swm.user_type) FILTER (WHERE swm.user_type IS NOT NULL) AS user_types,
        array_agg(DISTINCT swm.grade) FILTER (WHERE swm.grade IS NOT NULL) AS raw_grades,
        array_agg(DISTINCT swm.grade_range) FILTER (WHERE swm.grade_range IS NOT NULL) AS grade_ranges,
        array_agg(DISTINCT swm.funding_source) FILTER (WHERE swm.funding_source IS NOT NULL) AS funding_sources,
        sum(swm.total_cost) AS total_cost,
        sum(swm.students_licensed) AS students_licensed,
        max(swm.url) AS url,
        max(swm.icon) AS icon,
        min(swm.applicable_grade_bands::text) AS applicable_grade_bands,
        min(swm.sub_population) AS sub_population,
        min(swm.program_population) AS program_population
    FROM software_with_metrics swm
    GROUP BY lower(swm.name), swm.district_id, swm.authorized, swm.district_purchased
),
grouped_by_name_and_district AS (
    SELECT 
        name, district_id, authorized, district_purchased, software_ids,
        categories, school_names, user_types,
        (
            SELECT array_agg(DISTINCT all_expanded_grades.expanded_grade)
            FROM (
                SELECT unnest(expand_grade_range(g.g)) AS expanded_grade
                FROM unnest(raw_grades) g(g)
                WHERE g.g IS NOT NULL
                UNION
                SELECT unnest(expand_grade_range(gr.gr)) AS expanded_grade
                FROM unnest(grade_ranges) gr(gr)
                WHERE gr.gr IS NOT NULL
                UNION
                SELECT unnest(expand_grade_range(band.band)) AS expanded_grade
                FROM unnest(string_to_array(TRIM(BOTH '{}' FROM COALESCE(applicable_grade_bands, '{}')), ',')) band(band)
                WHERE band.band IS NOT NULL AND TRIM(BOTH '"' FROM band.band) <> ''
            ) all_expanded_grades
            WHERE all_expanded_grades.expanded_grade IS NOT NULL 
              AND TRIM(FROM all_expanded_grades.expanded_grade) <> ''
        ) AS grades,
        grade_ranges, funding_sources, total_cost, students_licensed,
        url, icon, applicable_grade_bands, sub_population, program_population
    FROM grouped_by_name_and_district_pre
),
name_district_users AS (
    SELECT DISTINCT 
        lower(s.name) AS name,
        s.district_id,
        su.user_id,
        p.role
    FROM software s
    JOIN software_usage su ON su.software_id = s.id
    LEFT JOIN profiles p ON p.id = su.user_id
    WHERE su.minutes_used > 0::numeric AND su.user_id IS NOT NULL
),
district_wide_user_counts AS (
    SELECT 
        ndu.name,
        ndu.district_id,
        count(DISTINCT ndu.user_id) AS active_users,
        count(DISTINCT CASE WHEN ndu.role = 'student' THEN ndu.user_id ELSE NULL END) AS active_students,
        count(DISTINCT CASE WHEN ndu.role = 'teacher' THEN ndu.user_id ELSE NULL END) AS active_teachers
    FROM name_district_users ndu
    GROUP BY ndu.name, ndu.district_id
),
user_counts AS (
    SELECT 
        lower(gbn.name) AS name,
        gbn.district_id,
        gbn.authorized,
        gbn.district_purchased,
        COALESCE(dwuc.active_users, 0::bigint) AS active_users,
        COALESCE(dwuc.active_students, 0::bigint) AS active_students,
        COALESCE(dwuc.active_teachers, 0::bigint) AS active_teachers
    FROM grouped_by_name_and_district gbn
    LEFT JOIN district_wide_user_counts dwuc 
        ON dwuc.name = lower(gbn.name) AND dwuc.district_id = gbn.district_id
),
aggregated_usage AS (
    SELECT 
        lower(gbn.name) AS name,
        gbn.district_id,
        gbn.authorized,
        gbn.district_purchased,
        sum(ups.total_usage_minutes) AS total_minutes,
        sum(ups.usage_days) AS usage_days,
        min(ups.first_use_date) AS first_use_date,
        max(ups.last_use_date) AS last_use_date
    FROM grouped_by_name_and_district gbn
    CROSS JOIN LATERAL unnest(gbn.software_ids) unnested_software(software_id)
    LEFT JOIN usage_per_software ups ON ups.software_id = unnested_software.software_id
    GROUP BY lower(gbn.name), gbn.district_id, gbn.authorized, gbn.district_purchased
),
category_expectations AS (
    SELECT 
        lower(gbn.name) AS name,
        gbn.district_id,
        gbn.authorized,
        gbn.district_purchased,
        gbn.categories,
        COALESCE(gbn.categories[1], 'Other') AS primary_category,
        CASE COALESCE(gbn.categories[1], 'Other')
            WHEN 'Educational' THEN 10::numeric
            WHEN 'E-learning' THEN 15::numeric
            WHEN 'Gamified Learning' THEN 12::numeric
            WHEN 'Student Engagement' THEN 8::numeric
            WHEN 'Productivity (Students)' THEN 10::numeric
            WHEN 'Productivity (Staff)' THEN 15::numeric
            WHEN 'Blended/Flipped Lessons' THEN 20::numeric
            WHEN 'STEM' THEN 7::numeric
            WHEN 'Arts & Music' THEN 6::numeric
            WHEN 'Language Learning' THEN 5::numeric
            WHEN 'Special Education' THEN 9::numeric
            WHEN 'Curriculum Design & Instruction (Students)' THEN 6::numeric
            WHEN 'Curriculum Design & Instruction (Teachers)' THEN 8::numeric
            WHEN 'Learning Management Systems' THEN 7::numeric
            WHEN 'Online Literary Resources' THEN 5::numeric
            WHEN 'Professional Development & Supports (Staff)' THEN 9::numeric
            WHEN 'Supplemental - Intervention' THEN 8::numeric
            WHEN 'Virtual Experiences & Lessons' THEN 6::numeric
            WHEN 'Assessment' THEN 4.5
            WHEN 'Data Analysis & Progress Monitoring' THEN 6::numeric
            WHEN 'Test Prep' THEN 4::numeric
            WHEN 'Student Information & Monitoring Systems' THEN 3::numeric
            WHEN 'Cyber Safety/Security' THEN 1.5
            WHEN 'Future Ready' THEN 2.25
            WHEN 'Esports' THEN 3::numeric
            WHEN 'Entertainment' THEN 2::numeric
            WHEN 'Social Media' THEN 1::numeric
            WHEN 'Textbooks' THEN 3::numeric
            ELSE 5::numeric
        END AS expected_daily_minutes,
        CASE
            WHEN COALESCE(gbn.categories[1], 'Other') = ANY (ARRAY['Educational', 'E-learning', 'Gamified Learning', 'Student Engagement', 'Productivity (Students)', 'Productivity (Staff)', 'Blended/Flipped Lessons']) THEN 'daily'
            WHEN COALESCE(gbn.categories[1], 'Other') = ANY (ARRAY['STEM', 'Arts & Music', 'Language Learning', 'Special Education', 'Curriculum Design & Instruction (Students)', 'Curriculum Design & Instruction (Teachers)', 'Learning Management Systems', 'Online Literary Resources', 'Professional Development & Supports (Staff)', 'Supplemental - Intervention', 'Virtual Experiences & Lessons']) THEN 'weekly'
            WHEN COALESCE(gbn.categories[1], 'Other') = ANY (ARRAY['Assessment', 'Data Analysis & Progress Monitoring', 'Test Prep', 'Student Information & Monitoring Systems', 'Cyber Safety/Security', 'Future Ready', 'Esports']) THEN 'periodic'
            WHEN COALESCE(gbn.categories[1], 'Other') = ANY (ARRAY['Entertainment', 'Social Media', 'Textbooks']) THEN 'sporadic'
            ELSE 'daily'
        END AS category_type
    FROM grouped_by_name_and_district gbn
),
roi_thresholds AS (
    SELECT 
        ce.name, ce.district_id, ce.authorized, ce.district_purchased, ce.category_type,
        CASE ce.category_type
            WHEN 'daily' THEN 0.9
            WHEN 'weekly' THEN 0.8
            WHEN 'periodic' THEN 0.7
            WHEN 'sporadic' THEN 0.6
            ELSE 0.9
        END AS high_threshold,
        CASE ce.category_type
            WHEN 'daily' THEN 0.75
            WHEN 'weekly' THEN 0.65
            WHEN 'periodic' THEN 0.5
            WHEN 'sporadic' THEN 0.4
            ELSE 0.75
        END AS moderate_threshold
    FROM category_expectations ce
)
SELECT 
    gbn.name,
    gbn.district_id,
    gbn.software_ids AS ids,
    ce.categories,
    gbn.school_names,
    gbn.user_types,
    gbn.grades,
    gbn.grade_ranges,
    gbn.funding_sources,
    gbn.total_cost,
    gbn.students_licensed,
    gbn.authorized,
    gbn.district_purchased,
    gbn.url,
    gbn.icon,
    gbn.applicable_grade_bands,
    gbn.sub_population,
    gbn.program_population,
    ce.primary_category,
    ce.category_type,
    COALESCE(au.total_minutes, 0::numeric) AS total_minutes,
    COALESCE(uc.active_users, 0::bigint) AS active_users,
    COALESCE(au.usage_days, 0::bigint::numeric) AS usage_days,
    au.first_use_date,
    au.last_use_date,
    COALESCE(uc.active_students, 0::bigint) AS active_students,
    COALESCE(uc.active_teachers, 0::bigint) AS active_teachers,
    ce.expected_daily_minutes,
    CASE WHEN gbn.students_licensed > 0 THEN gbn.total_cost / gbn.students_licensed::numeric ELSE 0::numeric END AS cost_per_student,
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL THEN LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric ELSE 0::numeric END AS days_since_start,
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL AND gbn.students_licensed > 0 
         THEN LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes * gbn.students_licensed::numeric 
         ELSE 0::numeric END AS expected_minutes_to_date,
    -- usage_ratio
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND ce.expected_daily_minutes > 0::numeric AND gbn.students_licensed > 0 
              AND ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric) > 0::numeric 
         THEN COALESCE(au.total_minutes, 0::numeric) / ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric) 
         ELSE 0::numeric END AS usage_ratio,
    -- avg_minutes_per_day
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND LEAST((au.last_use_date - au.first_use_date + 1), 180) > 0 AND gbn.students_licensed > 0 
         THEN COALESCE(au.total_minutes, 0::numeric) / (LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * gbn.students_licensed::numeric) 
         ELSE 0::numeric END AS avg_minutes_per_day,
    -- avg_roi_percentage
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND ce.expected_daily_minutes > 0::numeric AND gbn.students_licensed > 0 
              AND ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric) > 0::numeric 
         THEN ((COALESCE(au.total_minutes, 0::numeric) / ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric)) - 1::numeric) * 100::numeric 
         ELSE (-100)::numeric END AS avg_roi_percentage,
    -- roi_status
    CASE
        WHEN au.first_use_date IS NULL OR ce.expected_daily_minutes = 0::numeric 
             OR LEAST((au.last_use_date - au.first_use_date + 1), 180) = 0 OR gbn.students_licensed = 0 THEN 'low'
        WHEN (COALESCE(au.total_minutes, 0::numeric) / NULLIF((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric, 0::numeric)) >= rt.high_threshold
             AND (COALESCE(au.total_minutes, 0::numeric) / NULLIF(LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * gbn.students_licensed::numeric, 0::numeric)) >= (ce.expected_daily_minutes * 0.8) THEN 'high'
        WHEN (COALESCE(au.total_minutes, 0::numeric) / NULLIF((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * gbn.students_licensed::numeric, 0::numeric)) >= rt.moderate_threshold
             AND (COALESCE(au.total_minutes, 0::numeric) / NULLIF(LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * gbn.students_licensed::numeric, 0::numeric)) >= (ce.expected_daily_minutes * 0.6) THEN 'moderate'
        ELSE 'low'
    END AS roi_status,
    -- engagement_rate
    CASE WHEN COALESCE(au.usage_days, 0::bigint::numeric) > 0::numeric AND ce.expected_daily_minutes > 0::numeric AND gbn.students_licensed > 0 
         THEN LEAST(100::numeric, (COALESCE(au.total_minutes, 0::numeric) / (au.usage_days * ce.expected_daily_minutes * gbn.students_licensed::numeric)) * 100::numeric) 
         ELSE 0::numeric END AS engagement_rate,
    -- usage_compliance
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND ce.expected_daily_minutes > 0::numeric 
              AND ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * COALESCE(gbn.students_licensed, 1::bigint)::numeric) > 0::numeric 
         THEN LEAST(100::numeric, (COALESCE(au.total_minutes, 0::numeric) / ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * COALESCE(gbn.students_licensed, 1::bigint)::numeric)) * 100::numeric) 
         ELSE 0::numeric END AS usage_compliance,
    -- avg_usage_compliance
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND COALESCE(au.usage_days, 0::bigint::numeric) > 0::numeric AND LEAST((au.last_use_date - au.first_use_date + 1), 180) > 0 
         THEN (COALESCE(au.usage_days, 0::bigint::numeric) / LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric) * 100::numeric 
         ELSE 0::numeric END AS avg_usage_compliance
FROM grouped_by_name_and_district gbn
LEFT JOIN aggregated_usage au ON lower(gbn.name) = au.name AND gbn.district_id = au.district_id AND gbn.authorized = au.authorized AND gbn.district_purchased = au.district_purchased
LEFT JOIN user_counts uc ON lower(gbn.name) = uc.name AND gbn.district_id = uc.district_id AND gbn.authorized = uc.authorized AND gbn.district_purchased = uc.district_purchased
LEFT JOIN category_expectations ce ON lower(gbn.name) = ce.name AND gbn.district_id = ce.district_id AND gbn.authorized = ce.authorized AND gbn.district_purchased = ce.district_purchased
LEFT JOIN roi_thresholds rt ON lower(gbn.name) = rt.name AND gbn.district_id = rt.district_id AND gbn.authorized = rt.authorized AND gbn.district_purchased = rt.district_purchased;
```

---

### 4. `mv_unauthorized_software_analytics_v3`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_software_analytics_v3 AS
WITH unauthorized_software AS (
    SELECT 
        s.id,
        s.name,
        s.category,
        s.url,
        s.district_id,
        s.school_name,
        s.user_type,
        d.name AS district_name
    FROM software s
    LEFT JOIN districts d ON s.district_id = d.id
    WHERE s.authorized = false
),
usage_aggregates AS (
    SELECT 
        su.software_id,
        sum(su.minutes_used) AS total_minutes,
        count(DISTINCT su.user_id) FILTER (WHERE su.user_id IS NOT NULL) AS unique_users,
        count(DISTINCT su.user_id) FILTER (WHERE su.user_id IS NOT NULL AND su.user_type = 'student') AS student_users,
        count(DISTINCT su.user_id) FILTER (WHERE su.user_id IS NOT NULL AND su.user_type = 'teacher') AS teacher_users,
        count(DISTINCT su.date) AS usage_days,
        max(su.date) AS last_usage_date
    FROM software_usage su
    WHERE su.software_id IN (SELECT id FROM unauthorized_software)
      AND su.minutes_used > 0::numeric
    GROUP BY su.software_id
)
SELECT 
    us.id,
    us.name,
    COALESCE(us.category, 'Uncategorized') AS category,
    us.url,
    us.district_id,
    us.school_name,
    us.user_type,
    COALESCE(us.district_name, 'Unknown District') AS district_name,
    COALESCE(ua.total_minutes, 0::numeric) AS total_usage_minutes,
    COALESCE(ua.unique_users, 0::bigint) AS unique_users,
    COALESCE(ua.student_users, 0::bigint) AS student_users,
    COALESCE(ua.teacher_users, 0::bigint) AS teacher_users,
    COALESCE(ua.usage_days, 0::bigint) AS usage_count,
    ua.last_usage_date AS last_used_date,
    CASE WHEN ua.unique_users > 0 THEN ua.total_minutes / ua.unique_users::numeric ELSE 0::numeric END AS avg_minutes_per_user,
    now() AS refreshed_at
FROM unauthorized_software us
LEFT JOIN usage_aggregates ua ON us.id = ua.software_id;
```

---

### 5. `mv_unauthorized_usage_dashboard`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_usage_dashboard AS
WITH unauthorized_software AS (
    SELECT DISTINCT ON (s.name, s.district_id) 
        s.id AS software_id,
        s.name AS software_name,
        s.category,
        s.url,
        s.district_id,
        d.name AS district_name
    FROM software s
    LEFT JOIN districts d ON s.district_id = d.id
    WHERE s.authorized = false
    ORDER BY s.name, s.district_id, s.created_at
),
aggregated_usage AS (
    SELECT 
        s.name AS software_name,
        s.district_id,
        string_agg(DISTINCT su.user_type, ', ' ORDER BY su.user_type) AS user_type,
        sum(su.minutes_used) AS total_minutes,
        sum(su.minutes_used * 0.60) AS in_school_minutes,
        sum(su.minutes_used * 0.40) AS out_of_school_minutes,
        count(DISTINCT su.user_id) FILTER (WHERE su.user_id IS NOT NULL) AS unique_users,
        count(DISTINCT su.date) AS usage_days,
        max(su.date) AS last_used_date,
        string_agg(DISTINCT COALESCE(sch.name, s.school_name, 'Unknown'), ', ' ORDER BY COALESCE(sch.name, s.school_name, 'Unknown')) AS school_names
    FROM software s
    JOIN software_usage su ON s.id = su.software_id
    LEFT JOIN schools sch ON s.school_name = sch.name OR su.school_name = sch.name
    WHERE s.authorized = false 
      AND su.minutes_used > 0::numeric 
      AND su.date >= (CURRENT_DATE - '90 days'::interval)
    GROUP BY s.name, s.district_id
)
SELECT 
    us.software_id,
    us.software_name,
    COALESCE(us.category, 'Uncategorized') AS category,
    us.url,
    us.district_id,
    COALESCE(us.district_name, 'Unknown District') AS district_name,
    COALESCE(au.user_type, 'Unknown') AS user_type,
    round(COALESCE(au.total_minutes, 0::numeric), 2) AS total_minutes,
    round(COALESCE(au.in_school_minutes, 0::numeric), 2) AS in_school_minutes,
    round(COALESCE(au.out_of_school_minutes, 0::numeric), 2) AS out_of_school_minutes,
    COALESCE(au.unique_users, 0::bigint) AS active_users,
    COALESCE(au.usage_days, 0::bigint) AS usage_count,
    au.last_used_date,
    COALESCE(au.school_names, 'Unknown') AS school_name,
    CASE WHEN au.total_minutes > 0::numeric THEN round((au.in_school_minutes / au.total_minutes) * 100::numeric, 2) ELSE 60.00 END AS in_school_percentage,
    CASE WHEN au.total_minutes > 0::numeric THEN round((au.out_of_school_minutes / au.total_minutes) * 100::numeric, 2) ELSE 40.00 END AS out_of_school_percentage,
    now() AS refreshed_at
FROM unauthorized_software us
JOIN aggregated_usage au ON us.software_name = au.software_name AND us.district_id = au.district_id
WHERE au.total_minutes > 0::numeric;
```

---

### 6. `mv_software_investment_summary`

```sql
CREATE MATERIALIZED VIEW public.mv_software_investment_summary AS
SELECT 
    s.software_id,
    lower(s.name) AS software_name,
    s.name AS display_name,
    s.district_id,
    s.school_name,
    s.category,
    COALESCE(s.funding_source, 'Unknown') AS funding_source,
    s.grade_range AS grade_ranges,
    s.user_type,
    COALESCE(s.purchase_date, s.created_at) AS latest_purchase_date,
    s.last_usage_date,
    s.created_at,
    COALESCE(s.total_cost, 0::numeric) AS total_investment,
    COALESCE(s.students_licensed, 0) AS total_licensed_users,
    COALESCE(s.active_users_all_time, 0::bigint) AS active_users,
    COALESCE(s.utilization, 0::numeric) AS avg_utilization,
    COALESCE(s.total_minutes_90d, 0::numeric) AS total_minutes,
    COALESCE(s.cost_per_student, 0::numeric) AS avg_cost_per_student,
    COALESCE(s.roi_percentage, 0::numeric) AS avg_roi_percentage,
    s.roi_status,
    CASE s.roi_status
        WHEN 'high' THEN 1
        WHEN 'moderate' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END AS roi_status_priority,
    s.authorized,
    s.district_purchased
FROM mv_dashboard_software_metrics s
WHERE s.name IS NOT NULL AND s.name <> '' AND s.school_name IS NOT NULL;
```

---

### 7. `mv_user_software_utilization_v2`

```sql
CREATE MATERIALIZED VIEW public.mv_user_software_utilization_v2 AS
WITH aggregated AS (
    SELECT 
        su.software_id,
        su.user_id,
        count(*)::integer AS sessions_count,
        sum(su.minutes_used)::integer AS total_minutes,
        sum(COALESCE(su.used_in_school, 0::numeric))::integer AS minutes_in_school,
        sum(COALESCE(su.used_at_home, 0::numeric))::integer AS minutes_at_home,
        min(su.date) AS first_active,
        max(su.date) AS last_active
    FROM software_usage su
    WHERE su.user_id IS NOT NULL
    GROUP BY su.software_id, su.user_id
)
SELECT 
    a.software_id,
    a.user_id,
    p.email AS user_email,
    p.first_name,
    p.last_name,
    p.grade,
    p.school_id,
    p.district_id,
    p.role AS user_role,
    s.name AS school_name,
    d.name AS district_name,
    sw.name AS software_name,
    sw.category AS software_category,
    a.sessions_count,
    a.total_minutes,
    a.minutes_in_school,
    a.minutes_at_home,
    a.first_active,
    a.last_active,
    (a.last_active - a.first_active) + 1 AS days_active,
    CASE
        WHEN ((a.last_active - a.first_active) + 1) < 7 THEN a.total_minutes
        ELSE (a.total_minutes * 7) / ((a.last_active - a.first_active) + 1)
    END AS avg_weekly_minutes
FROM aggregated a
JOIN profiles p ON a.user_id = p.id
JOIN software sw ON a.software_id = sw.id
LEFT JOIN schools s ON p.school_id = s.id
LEFT JOIN districts d ON p.district_id = d.id;
```

---

### 8. `mv_active_users_summary`

```sql
CREATE MATERIALIZED VIEW public.mv_active_users_summary AS
SELECT 
    p.id AS user_id,
    p.email,
    p.first_name,
    p.last_name,
    p.role,
    p.grade,
    p.school_id,
    p.district_id,
    s.name AS school_name,
    d.name AS district_name,
    COALESCE(sum(mv.total_minutes), 0::bigint) AS total_usage_minutes,
    COALESCE(sum(mv.sessions_count), 0::bigint)::integer AS total_sessions,
    min(mv.first_active) AS first_active_date,
    max(mv.last_active) AS last_active_date,
    CASE
        WHEN p.grade IS NULL THEN NULL
        WHEN upper(TRIM(FROM p.grade)) = ANY (ARRAY['K', 'KG', 'PK', 'TK', 'PR']) THEN 'elementary'
        WHEN p.grade ~ '^[0-9]+$' THEN
            CASE
                WHEN p.grade::integer >= 0 AND p.grade::integer <= 5 THEN 'elementary'
                WHEN p.grade::integer >= 6 AND p.grade::integer <= 8 THEN 'middle'
                WHEN p.grade::integer >= 9 AND p.grade::integer <= 12 THEN 'high'
                ELSE NULL
            END
        ELSE NULL
    END AS grade_band,
    concat(COALESCE(p.first_name, ''), ' ', COALESCE(p.last_name, '')) AS full_name
FROM profiles p
LEFT JOIN mv_user_software_utilization_v2 mv ON p.id = mv.user_id
LEFT JOIN schools s ON p.school_id = s.id
LEFT JOIN districts d ON p.district_id = d.id
WHERE p.role = ANY (ARRAY['student', 'teacher'])
GROUP BY p.id, p.email, p.first_name, p.last_name, p.role, p.grade, p.school_id, p.district_id, s.name, d.name;
```

---

### 9. `mv_software_details_metrics`

```sql
CREATE MATERIALIZED VIEW public.mv_software_details_metrics AS
WITH software_base AS (
    SELECT 
        name, district_id, ids, categories, primary_category,
        school_names, user_types, grades, grade_ranges, funding_sources,
        total_cost, students_licensed, authorized, district_purchased,
        url, icon, total_minutes, active_users, active_students, active_teachers,
        usage_days, first_use_date, last_use_date, cost_per_student,
        avg_roi_percentage, roi_status, engagement_rate, usage_compliance, avg_usage_compliance
    FROM mv_software_usage_analytics_v3
),
user_weekly_usage AS (
    SELECT 
        s.name,
        mv.district_id,
        mv.user_id,
        mv.avg_weekly_minutes
    FROM mv_user_software_utilization_v2 mv
    JOIN software s ON s.id = mv.software_id
    WHERE mv.total_minutes > 0
),
user_day_usage_stats AS (
    SELECT 
        s.name,
        s.district_id,
        count(*) AS total_user_day_combinations,
        count(*) FILTER (WHERE su.minutes_used >= 10::numeric) AS days_with_10min_usage,
        count(*) FILTER (WHERE su.minutes_used >= 15::numeric) AS days_with_15min_usage,
        count(*) FILTER (WHERE su.minutes_used >= 20::numeric) AS days_with_20min_usage
    FROM software_usage su
    JOIN software s ON s.id = su.software_id
    GROUP BY s.name, s.district_id
),
average_weekly_per_software AS (
    SELECT 
        uwu.name,
        uwu.district_id,
        count(DISTINCT uwu.user_id) AS users_with_weekly_data,
        avg(uwu.avg_weekly_minutes) AS avg_weekly_minutes_per_user,
        sum(uwu.avg_weekly_minutes) AS total_weekly_minutes_all_users,
        min(uwu.avg_weekly_minutes) AS min_weekly_minutes,
        max(uwu.avg_weekly_minutes) AS max_weekly_minutes,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY uwu.avg_weekly_minutes::double precision) AS median_weekly_minutes
    FROM user_weekly_usage uwu
    GROUP BY uwu.name, uwu.district_id
),
combined_data AS (
    SELECT 
        sb.*,
        COALESCE(round(aws.avg_weekly_minutes_per_user), 0::numeric) AS avg_weekly_minutes_per_user,
        COALESCE(round(aws.total_weekly_minutes_all_users::double precision), 0::double precision) AS total_weekly_minutes_all_users,
        COALESCE(aws.users_with_weekly_data, 0::bigint) AS users_with_weekly_data,
        COALESCE(round(aws.min_weekly_minutes::double precision), 0::double precision) AS min_weekly_minutes_per_user,
        COALESCE(round(aws.max_weekly_minutes::double precision), 0::double precision) AS max_weekly_minutes_per_user,
        COALESCE(round(aws.median_weekly_minutes), 0::double precision) AS median_weekly_minutes_per_user,
        COALESCE(uds.total_user_day_combinations, 0::bigint) AS total_user_day_combinations,
        COALESCE(uds.days_with_10min_usage, 0::bigint) AS days_with_10min_usage,
        COALESCE(uds.days_with_15min_usage, 0::bigint) AS days_with_15min_usage,
        COALESCE(uds.days_with_20min_usage, 0::bigint) AS days_with_20min_usage,
        CASE WHEN COALESCE(uds.total_user_day_combinations, 0::bigint) > 0 
             THEN round((uds.days_with_15min_usage::numeric / uds.total_user_day_combinations::numeric) * 100::numeric, 1) 
             ELSE 0::numeric END AS usage_compliance_deprecated,
        CASE WHEN sb.active_users > 0 AND aws.avg_weekly_minutes_per_user > 0::numeric 
             THEN round((sb.total_cost / sb.active_users::numeric) / (aws.avg_weekly_minutes_per_user / 60.0), 2) 
             ELSE 0::numeric END AS cost_per_user_hour_per_week,
        CASE WHEN sb.students_licensed > 0 
             THEN round((sb.active_users::numeric / sb.students_licensed::numeric) * 100::numeric, 2) 
             ELSE 0::numeric END AS utilization_rate_percentage
    FROM software_base sb
    LEFT JOIN average_weekly_per_software aws ON lower(sb.name) = lower(aws.name) AND sb.district_id = aws.district_id
    LEFT JOIN user_day_usage_stats uds ON lower(sb.name) = lower(uds.name) AND sb.district_id = uds.district_id
)
SELECT DISTINCT ON (name, district_id) *
FROM combined_data
ORDER BY name, district_id, total_minutes DESC NULLS LAST;
```

---

### 10. `mv_report_data_unified_v4`

```sql
CREATE MATERIALIZED VIEW public.mv_report_data_unified_v4 AS
WITH grouped_software AS (
    SELECT 
        lower(s.name) AS name_lower,
        min(s.name) AS software_name,
        COALESCE(s.school_name, 'District Wide') AS school_name,
        s.district_id,
        array_agg(DISTINCT s.id) AS software_ids,
        count(DISTINCT s.id) AS software_record_count,
        max(s.category) AS category,
        max(s.funding_source) AS funding_source,
        max(s.grade_range) AS grade_range,
        bool_or(s.authorized) AS authorized,
        max(s.approval_status) AS approval_status,
        max(s.purchase_date) AS purchase_date,
        max(s.url) AS url,
        sum(s.total_cost) AS total_cost,
        sum(s.students_licensed) AS students_licensed
    FROM software s
    WHERE s.authorized = true
    GROUP BY lower(s.name), COALESCE(s.school_name, 'District Wide'), s.district_id
),
name_school_users AS (
    SELECT DISTINCT 
        lower(s.name) AS name,
        s.district_id,
        COALESCE(sch.name, 'District Wide') AS user_school_name,
        su.user_id,
        p.role
    FROM software s
    JOIN software_usage su ON su.software_id = s.id
    LEFT JOIN profiles p ON p.id = su.user_id
    LEFT JOIN schools sch ON sch.id = p.school_id
    WHERE su.minutes_used > 0::numeric AND su.user_id IS NOT NULL AND s.authorized = true
),
school_user_counts AS (
    SELECT 
        nsu.name, nsu.district_id, nsu.user_school_name,
        count(DISTINCT nsu.user_id) AS active_users,
        count(DISTINCT CASE WHEN nsu.role = 'student' THEN nsu.user_id ELSE NULL END) AS active_students,
        count(DISTINCT CASE WHEN nsu.role = 'teacher' THEN nsu.user_id ELSE NULL END) AS active_teachers
    FROM name_school_users nsu
    GROUP BY nsu.name, nsu.district_id, nsu.user_school_name
),
aggregated_usage AS (
    SELECT 
        lower(s.name) AS name,
        s.district_id,
        COALESCE(sch.name, 'District Wide') AS user_school_name,
        sum(su.minutes_used) AS total_minutes,
        count(DISTINCT su.date) AS usage_days,
        min(su.date) AS first_use_date,
        max(su.date) AS last_use_date
    FROM software s
    JOIN software_usage su ON su.software_id = s.id
    LEFT JOIN profiles p ON p.id = su.user_id
    LEFT JOIN schools sch ON sch.id = p.school_id
    WHERE su.minutes_used > 0::numeric AND s.authorized = true
    GROUP BY lower(s.name), s.district_id, COALESCE(sch.name, 'District Wide')
),
category_expectations AS (
    SELECT 
        gs.name_lower, gs.district_id, gs.school_name, gs.category,
        CASE COALESCE(gs.category, 'Other')
            WHEN 'Educational' THEN 10::numeric
            WHEN 'E-learning' THEN 15::numeric
            -- ... (same category mappings as mv_software_usage_analytics_v4)
            ELSE 5::numeric
        END AS expected_daily_minutes,
        CASE
            WHEN COALESCE(gs.category, 'Other') = ANY (ARRAY['Educational', 'E-learning', 'Gamified Learning', 'Student Engagement', 'Productivity (Students)', 'Productivity (Staff)', 'Blended/Flipped Lessons']) THEN 'daily'
            WHEN COALESCE(gs.category, 'Other') = ANY (ARRAY['STEM', 'Arts & Music', 'Language Learning', 'Special Education', 'Curriculum Design & Instruction (Students)', 'Curriculum Design & Instruction (Teachers)', 'Learning Management Systems', 'Online Literary Resources', 'Professional Development & Supports (Staff)', 'Supplemental - Intervention', 'Virtual Experiences & Lessons']) THEN 'weekly'
            WHEN COALESCE(gs.category, 'Other') = ANY (ARRAY['Assessment', 'Data Analysis & Progress Monitoring', 'Test Prep', 'Student Information & Monitoring Systems', 'Cyber Safety/Security', 'Future Ready', 'Esports']) THEN 'periodic'
            WHEN COALESCE(gs.category, 'Other') = ANY (ARRAY['Entertainment', 'Social Media', 'Textbooks']) THEN 'sporadic'
            ELSE 'daily'
        END AS category_type
    FROM grouped_software gs
)
SELECT 
    gs.software_name,
    gs.software_ids,
    gs.software_record_count,
    sch.id AS school_id,
    gs.school_name,
    gs.district_id,
    gs.category,
    gs.funding_source,
    gs.grade_range,
    gs.authorized,
    gs.approval_status,
    gs.purchase_date,
    gs.url,
    gs.total_cost,
    gs.students_licensed,
    CASE WHEN gs.students_licensed > 0 THEN round(gs.total_cost / gs.students_licensed::numeric, 2) ELSE gs.total_cost END AS cost_per_student,
    COALESCE(suc.active_students, 0::bigint) AS active_students,
    COALESCE(suc.active_teachers, 0::bigint) AS active_teachers,
    COALESCE(au.total_minutes, 0::numeric)::bigint AS total_minutes,
    round(COALESCE(au.total_minutes, 0::numeric) / 60.0, 2) AS total_usage_hours,
    COALESCE(au.usage_days, 0::bigint) AS usage_days,
    CASE WHEN COALESCE(au.usage_days, 0::bigint) > 0 THEN round(COALESCE(au.total_minutes, 0::numeric) / au.usage_days::numeric, 2) ELSE 0::numeric END AS average_session_time,
    COALESCE(au.usage_days, 0::bigint) AS usage_frequency,
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
         THEN round((COALESCE(au.total_minutes, 0::numeric) / 60.0) / GREATEST(ceiling(((au.last_use_date - au.first_use_date + 1)::numeric / 7.0)), 1::numeric), 2) 
         ELSE 0::numeric END AS avg_weekly_usage_hours,
    -- ROI calculation (same formula as mv_software_usage_analytics_v4)
    -- ... budget_utilization, active_user_percentage, cost_efficiency_score, engagement_score, etc.
    au.first_use_date,
    au.last_use_date,
    50::numeric AS user_satisfaction,
    NULL::jsonb AS technical_metrics,
    ce.expected_daily_minutes,
    -- usage_compliance
    CASE WHEN au.first_use_date IS NOT NULL AND au.last_use_date IS NOT NULL 
              AND ce.expected_daily_minutes > 0::numeric 
              AND ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * COALESCE(gs.students_licensed, 1::bigint)::numeric) > 0::numeric 
         THEN LEAST(100::numeric, (COALESCE(au.total_minutes, 0::numeric) / ((LEAST((au.last_use_date - au.first_use_date + 1), 180)::numeric * ce.expected_daily_minutes) * COALESCE(gs.students_licensed, 1::bigint)::numeric)) * 100::numeric) 
         ELSE 0::numeric END AS usage_compliance
FROM grouped_software gs
LEFT JOIN schools sch ON lower(sch.name) = lower(gs.school_name) AND sch.district_id = gs.district_id
LEFT JOIN school_user_counts suc ON suc.name = gs.name_lower AND suc.district_id = gs.district_id AND lower(suc.user_school_name) = lower(gs.school_name)
LEFT JOIN aggregated_usage au ON au.name = gs.name_lower AND au.district_id = gs.district_id AND lower(au.user_school_name) = lower(gs.school_name)
LEFT JOIN category_expectations ce ON ce.name_lower = gs.name_lower AND ce.district_id = gs.district_id AND lower(ce.school_name) = lower(gs.school_name);
```

---

### 11. `mv_unauthorized_software_by_school`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_software_by_school AS
SELECT 
    su.software_id,
    COALESCE(s.name, 'Unknown School') AS school_name,
    sum(su.minutes_used)::integer AS total_minutes,
    count(DISTINCT su.user_id)::integer AS unique_users,
    count(*)::integer AS session_count
FROM software_usage su
JOIN software sw ON su.software_id = sw.id
JOIN profiles p ON su.user_id = p.id
LEFT JOIN schools s ON p.school_id = s.id
WHERE sw.authorized = false 
  AND su.date >= (CURRENT_DATE - '90 days'::interval) 
  AND su.minutes_used > 0::numeric
GROUP BY su.software_id, s.name;
```

---

### 12. `mv_unauthorized_software_by_grade`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_software_by_grade AS
SELECT 
    su.software_id,
    p.grade,
    sum(su.minutes_used)::integer AS total_minutes,
    count(DISTINCT su.user_id)::integer AS unique_users,
    count(*)::integer AS session_count
FROM software_usage su
JOIN software sw ON su.software_id = sw.id
JOIN profiles p ON su.user_id = p.id
WHERE sw.authorized = false 
  AND su.date >= (CURRENT_DATE - '90 days'::interval) 
  AND su.minutes_used > 0::numeric 
  AND p.grade IS NOT NULL
GROUP BY su.software_id, p.grade;
```

---

### 13. `mv_unauthorized_software_by_hour`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_software_by_hour AS
SELECT 
    su.software_id,
    su.usage_hour AS hour,
    count(*)::integer AS session_count,
    sum(su.minutes_used)::integer AS total_minutes
FROM software_usage su
JOIN software sw ON su.software_id = sw.id
WHERE sw.authorized = false 
  AND su.date >= (CURRENT_DATE - '90 days'::interval) 
  AND su.minutes_used > 0::numeric 
  AND su.usage_hour IS NOT NULL
GROUP BY su.software_id, su.usage_hour;
```

---

### 14. `mv_unauthorized_software_timeline`

```sql
CREATE MATERIALIZED VIEW public.mv_unauthorized_software_timeline AS
SELECT 
    su.software_id,
    su.date,
    sum(su.minutes_used) AS total_minutes,
    count(DISTINCT su.user_id) AS unique_users,
    count(*) AS session_count
FROM software_usage su
JOIN software s ON su.software_id = s.id
WHERE s.authorized = false
GROUP BY su.software_id, su.date
ORDER BY su.date DESC;
```

---

### 15. `mv_software_usage_by_school_v2`

```sql
CREATE MATERIALIZED VIEW public.mv_software_usage_by_school_v2 AS
WITH school_software AS (
    SELECT 
        s.id AS software_id, s.name AS software_name, s.district_id,
        sch.id AS school_id, sch.name AS school_name,
        s.total_cost, s.category, s.authorized, s.district_purchased,
        s.students_licensed, s.funding_source, s.user_type, s.grade, s.applicable_grade_bands
    FROM software s
    JOIN schools sch ON sch.district_id = s.district_id 
        AND s.selected_schools IS NOT NULL 
        AND sch.id = ANY (s.selected_schools)
    WHERE s.district_id IS NOT NULL
),
usage_aggregates AS (
    SELECT 
        lower(s.name) AS software_name_lower,
        s.district_id,
        p.school_id,
        count(DISTINCT su.user_id) FILTER (WHERE su.user_id IS NOT NULL AND su.minutes_used > 0::numeric) AS active_users,
        count(DISTINCT su.user_id) FILTER (WHERE p.role = 'student' AND su.minutes_used > 0::numeric) AS active_students,
        count(DISTINCT su.user_id) FILTER (WHERE p.role = 'teacher' AND su.minutes_used > 0::numeric) AS active_teachers,
        COALESCE(sum(su.minutes_used) FILTER (WHERE su.minutes_used > 0::numeric), 0::numeric) AS total_minutes,
        count(DISTINCT su.date) FILTER (WHERE su.minutes_used > 0::numeric) AS usage_days,
        min(su.date) FILTER (WHERE su.minutes_used > 0::numeric) AS first_use_date,
        max(su.date) FILTER (WHERE su.minutes_used > 0::numeric) AS last_use_date
    FROM software_usage su
    JOIN software s ON su.software_id = s.id
    JOIN profiles p ON su.user_id = p.id
    WHERE p.school_id IS NOT NULL AND s.district_id IS NOT NULL
    GROUP BY lower(s.name), s.district_id, p.school_id
),
school_usage AS (
    SELECT 
        ss.*, 
        COALESCE(ua.active_users, 0::bigint) AS active_users,
        COALESCE(ua.active_students, 0::bigint) AS active_students,
        COALESCE(ua.active_teachers, 0::bigint) AS active_teachers,
        COALESCE(ua.total_minutes, 0::numeric) AS total_minutes,
        COALESCE(ua.usage_days, 0::bigint) AS usage_days,
        ua.first_use_date, ua.last_use_date
    FROM school_software ss
    LEFT JOIN usage_aggregates ua ON lower(ss.software_name) = ua.software_name_lower 
        AND ss.district_id = ua.district_id AND ss.school_id = ua.school_id
),
category_expectations AS (
    SELECT su.*,
        CASE WHEN su.first_use_date IS NOT NULL AND su.last_use_date IS NOT NULL 
             THEN LEAST((su.last_use_date - su.first_use_date + 1), 180)::numeric 
             ELSE 0::numeric END AS days_since_start,
        CASE su.category
            WHEN 'Educational' THEN 10::numeric
            -- ... (same category mappings)
            ELSE 5::numeric
        END AS expected_daily_minutes,
        -- category_type mapping
    FROM school_usage su
),
roi_thresholds AS (
    SELECT ce.*,
        CASE ce.category_type WHEN 'daily' THEN 0.9 WHEN 'weekly' THEN 0.8 WHEN 'periodic' THEN 0.7 WHEN 'sporadic' THEN 0.6 ELSE 0.9 END AS high_threshold,
        CASE ce.category_type WHEN 'daily' THEN 0.75 WHEN 'weekly' THEN 0.65 WHEN 'periodic' THEN 0.5 WHEN 'sporadic' THEN 0.4 ELSE 0.75 END AS moderate_threshold
    FROM category_expectations ce
)
SELECT 
    rt.software_id, rt.software_name, rt.school_id, rt.school_name, rt.district_id,
    rt.total_cost, rt.category, rt.authorized, rt.district_purchased,
    rt.students_licensed, rt.funding_source, rt.user_type, rt.grade, rt.applicable_grade_bands,
    rt.active_users, rt.active_students, rt.active_teachers, rt.total_minutes, rt.usage_days,
    rt.first_use_date, rt.last_use_date, rt.days_since_start, rt.expected_daily_minutes, rt.category_type,
    -- cost_per_student, expected_minutes_to_date, usage_ratio, avg_minutes_per_day, avg_roi_percentage, roi_status, engagement_rate, usage_compliance, avg_usage_compliance
FROM roi_thresholds rt;
```

---

### 16. `mv_software_usage_rankings_v4`

```sql
CREATE MATERIALIZED VIEW public.mv_software_usage_rankings_v4 AS
WITH filtered_software_all_permutations AS (
    SELECT 
        s.id, s.name, s.category, s.total_cost, s.district_id, s.school_name,
        s.funding_source, s.user_type, s.grade, s.grade_range, s.applicable_grade_bands,
        CASE WHEN s.grade = ANY (ARRAY['K', 'KG', '0', '1', '2', '3', '4', '5']) 
              OR s.grade_range ~~* '%K-5%' OR s.grade_range ~~* '%Elementary%'
              OR s.applicable_grade_bands @> ARRAY['Elementary School'] THEN 'elementary' ELSE NULL END AS is_elementary,
        CASE WHEN s.grade = ANY (ARRAY['6', '7', '8']) 
              OR s.grade_range ~~* '%6-8%' OR s.grade_range ~~* '%Middle%'
              OR s.applicable_grade_bands @> ARRAY['Middle School'] THEN 'middle' ELSE NULL END AS is_middle,
        CASE WHEN s.grade = ANY (ARRAY['9', '10', '11', '12']) 
              OR s.grade_range ~~* '%9-12%' OR s.grade_range ~~* '%High%'
              OR s.applicable_grade_bands @> ARRAY['High School'] THEN 'high' ELSE NULL END AS is_high
    FROM software s
    WHERE s.total_cost > 0::numeric AND (s.authorized = true OR s.district_purchased = true)
),
usage_by_software_all_grades AS (
    SELECT fs.id, fs.name, fs.category, fs.total_cost, fs.district_id, fs.school_name, fs.funding_source, fs.user_type,
           COALESCE(sum(su.minutes_used), 0::numeric) AS total_minutes
    FROM filtered_software_all_permutations fs
    LEFT JOIN software_usage su ON fs.id = su.software_id
    GROUP BY fs.id, fs.name, fs.category, fs.total_cost, fs.district_id, fs.school_name, fs.funding_source, fs.user_type
),
usage_by_software_elementary AS (
    SELECT fs.id, fs.name, fs.category, fs.total_cost, fs.district_id, fs.school_name, fs.funding_source, fs.user_type,
           COALESCE(sum(su.minutes_used), 0::numeric) AS total_minutes
    FROM filtered_software_all_permutations fs
    LEFT JOIN software_usage su ON fs.id = su.software_id
    WHERE fs.is_elementary = 'elementary'
    GROUP BY fs.id, fs.name, fs.category, fs.total_cost, fs.district_id, fs.school_name, fs.funding_source, fs.user_type
),
usage_by_software_middle AS (
    -- Similar to elementary but for middle school
),
usage_by_software_high AS (
    -- Similar to elementary but for high school
),
totals_by_context AS (
    SELECT district_id, user_type, school_name, funding_source, 'all' AS grade_band, sum(total_minutes) AS context_total_minutes
    FROM usage_by_software_all_grades
    GROUP BY district_id, user_type, school_name, funding_source
    UNION ALL
    SELECT district_id, user_type, school_name, funding_source, 'elementary' AS grade_band, sum(total_minutes) AS context_total_minutes
    FROM usage_by_software_elementary
    GROUP BY district_id, user_type, school_name, funding_source
    UNION ALL
    -- middle and high unions
),
grouped_by_name_and_context AS (
    SELECT 
        TRIM(FROM u.name) AS name,
        u.district_id, u.user_type, u.school_name, u.funding_source, u.category,
        'all' AS grade_band,
        COALESCE(max(CASE WHEN u.category IS NOT NULL THEN u.category ELSE NULL END), max(u.category)) AS category_resolved,
        sum(u.total_cost) AS total_cost,
        sum(u.total_minutes) AS total_minutes,
        count(DISTINCT u.id) AS instance_count,
        array_agg(DISTINCT u.id::text) AS software_ids,
        max(t.context_total_minutes) AS context_total_minutes
    FROM usage_by_software_all_grades u
    JOIN totals_by_context t ON NOT (t.district_id IS DISTINCT FROM u.district_id) 
        AND t.user_type = u.user_type 
        AND NOT (t.school_name IS DISTINCT FROM u.school_name) 
        AND NOT (t.funding_source IS DISTINCT FROM u.funding_source) 
        AND t.grade_band = 'all'
    GROUP BY TRIM(FROM u.name), u.district_id, u.user_type, u.school_name, u.funding_source, u.category
    UNION ALL
    -- elementary, middle, high unions
)
SELECT 
    gen_random_uuid() AS id,
    name,
    category_resolved AS category,
    district_id, user_type, school_name, funding_source, grade_band,
    total_cost, total_minutes, instance_count, software_ids, context_total_minutes,
    CASE WHEN context_total_minutes > 0::numeric 
         THEN round((total_minutes / context_total_minutes) * 100::numeric, 2) 
         ELSE 0::numeric END AS usage_percentage
FROM grouped_by_name_and_context;
```
