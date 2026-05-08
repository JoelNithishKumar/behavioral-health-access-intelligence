CREATE OR REPLACE VIEW vw_referral_lag_summary AS
SELECT
    c.clinic_id,
    c.clinic_name,
    DATE_TRUNC('month', r.referral_created_date) AS referral_month,
    COUNT(DISTINCT r.referral_id) AS total_referrals,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, r.referral_reviewed_date)) AS median_referral_to_review_days,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_scheduled_date)) AS median_referral_to_scheduled_days,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days,
    SUM(CASE WHEN r.referral_status = 'open' THEN 1 ELSE 0 END) AS open_referrals,
    SUM(CASE WHEN r.referral_status = 'open' AND DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) > 21 THEN 1 ELSE 0 END) AS open_referrals_over_21_days
FROM fact_referral r
LEFT JOIN fact_appointment a ON r.referral_id = a.referral_id
LEFT JOIN dim_clinic c ON a.clinic_id = c.clinic_id
GROUP BY c.clinic_id, c.clinic_name, DATE_TRUNC('month', r.referral_created_date);

CREATE OR REPLACE VIEW vw_appointment_completion_summary AS
SELECT
    c.clinic_id,
    c.clinic_name,
    a.appointment_type,
    a.visit_mode,
    DATE_TRUNC('month', a.appointment_date) AS appointment_month,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) AS completed_appointments,
    SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_appointments,
    SUM(CASE WHEN a.appointment_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_appointments,
    SUM(CASE WHEN a.appointment_status = 'rescheduled' THEN 1 ELSE 0 END) AS rescheduled_appointments,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS completion_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS no_show_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'canceled' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS cancellation_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'rescheduled' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS reschedule_rate_pct
FROM fact_appointment a
JOIN dim_clinic c ON a.clinic_id = c.clinic_id
GROUP BY c.clinic_id, c.clinic_name, a.appointment_type, a.visit_mode, DATE_TRUNC('month', a.appointment_date);

CREATE OR REPLACE VIEW vw_no_show_summary AS
SELECT
    c.clinic_id,
    c.clinic_name,
    p.age_group,
    p.insurance_type,
    p.transportation_risk_flag,
    z.zip_code,
    a.appointment_type,
    a.visit_mode,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_count,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS no_show_rate_pct,
    AVG(p.prior_no_show_count) AS avg_prior_no_show_count,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days
FROM fact_appointment a
JOIN fact_referral r ON a.referral_id = r.referral_id
JOIN dim_patient p ON a.patient_id = p.patient_id
JOIN dim_clinic c ON a.clinic_id = c.clinic_id
JOIN dim_zip_code z ON p.zip_code = z.zip_code
GROUP BY c.clinic_id, c.clinic_name, p.age_group, p.insurance_type, p.transportation_risk_flag, z.zip_code, a.appointment_type, a.visit_mode;

CREATE OR REPLACE VIEW vw_open_referral_aging AS
SELECT
    r.referral_id,
    r.patient_id,
    r.referral_priority,
    r.referral_created_date,
    r.referral_status,
    DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) AS open_days,
    CASE
        WHEN DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) BETWEEN 0 AND 7 THEN '0-7 days'
        WHEN DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) BETWEEN 8 AND 14 THEN '8-14 days'
        WHEN DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) BETWEEN 15 AND 21 THEN '15-21 days'
        WHEN DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) BETWEEN 22 AND 30 THEN '22-30 days'
        ELSE '30+ days'
    END AS aging_bucket
FROM fact_referral r
WHERE r.referral_status = 'open';

CREATE OR REPLACE VIEW vw_behavioral_health_funnel AS
SELECT 'Referral Created' AS stage, 1 AS stage_order, COUNT(DISTINCT referral_id) AS stage_count FROM fact_referral
UNION ALL
SELECT 'Referral Reviewed', 2, COUNT(DISTINCT referral_id) FROM fact_referral WHERE referral_reviewed_date IS NOT NULL
UNION ALL
SELECT 'Appointment Scheduled', 3, COUNT(DISTINCT referral_id) FROM fact_appointment
UNION ALL
SELECT 'Appointment Completed', 4, COUNT(DISTINCT referral_id) FROM fact_appointment WHERE appointment_status = 'completed'
UNION ALL
SELECT 'Follow-Up Completed', 5, COUNT(DISTINCT e.encounter_id)
FROM fact_encounter e
JOIN fact_followup f ON e.encounter_id = f.encounter_id
WHERE f.followup_status = 'completed';

CREATE OR REPLACE VIEW vw_provider_capacity_summary AS
SELECT
    p.provider_id,
    p.provider_name,
    c.clinic_name,
    p.provider_type,
    p.weekly_capacity_slots,
    COUNT(a.appointment_id) AS appointment_volume,
    SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) AS completed_appointments,
    SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_appointments,
    ROUND(COUNT(a.appointment_id) / NULLIF(p.weekly_capacity_slots * 4.0, 0) * 100, 2) AS monthly_capacity_utilization_pct
FROM dim_provider p
JOIN dim_clinic c ON p.clinic_id = c.clinic_id
LEFT JOIN fact_appointment a ON p.provider_id = a.provider_id
GROUP BY p.provider_id, p.provider_name, c.clinic_name, p.provider_type, p.weekly_capacity_slots;

CREATE OR REPLACE VIEW vw_zip_access_friction AS
WITH zip_metrics AS (
    SELECT
        z.zip_code,
        z.area_name,
        z.transportation_risk_rate,
        z.underinsured_rate,
        z.limited_english_rate,
        z.telehealth_adoption_rate,
        COUNT(DISTINCT r.referral_id) AS referral_volume,
        MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN r.referral_status = 'open' AND DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) > 21 THEN 1 ELSE 0 END) / NULLIF(COUNT(DISTINCT r.referral_id), 0), 2) AS open_over_21_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN a.visit_mode = 'telehealth' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS telehealth_usage_pct
    FROM dim_zip_code z
    LEFT JOIN dim_patient p ON z.zip_code = p.zip_code
    LEFT JOIN fact_referral r ON p.patient_id = r.patient_id
    LEFT JOIN fact_appointment a ON r.referral_id = a.referral_id
    GROUP BY z.zip_code, z.area_name, z.transportation_risk_rate, z.underinsured_rate, z.limited_english_rate, z.telehealth_adoption_rate
), normalized AS (
    SELECT
        *,
        median_referral_to_appointment_days / NULLIF(MAX(median_referral_to_appointment_days) OVER (), 0) AS norm_lag,
        no_show_rate_pct / NULLIF(MAX(no_show_rate_pct) OVER (), 0) AS norm_no_show,
        open_over_21_rate_pct / NULLIF(MAX(open_over_21_rate_pct) OVER (), 0) AS norm_open_aging,
        1 - telehealth_usage_pct / NULLIF(MAX(telehealth_usage_pct) OVER (), 0) AS low_telehealth_penalty
    FROM zip_metrics
)
SELECT
    zip_code,
    area_name,
    referral_volume,
    median_referral_to_appointment_days,
    no_show_rate_pct,
    transportation_risk_rate,
    underinsured_rate,
    limited_english_rate,
    telehealth_usage_pct,
    open_over_21_rate_pct,
    ROUND(100 * (
        0.25 * COALESCE(norm_lag, 0)
        + 0.20 * COALESCE(norm_no_show, 0)
        + 0.15 * COALESCE(transportation_risk_rate, 0)
        + 0.15 * COALESCE(underinsured_rate, 0)
        + 0.10 * COALESCE(limited_english_rate, 0)
        + 0.10 * COALESCE(norm_open_aging, 0)
        + 0.05 * COALESCE(low_telehealth_penalty, 0)
    ), 2) AS access_friction_score
FROM normalized;

CREATE OR REPLACE VIEW vw_clinic_access_performance AS
SELECT
    c.clinic_id,
    c.clinic_name,
    c.clinic_group,
    COUNT(DISTINCT r.referral_id) AS referral_volume,
    COUNT(DISTINCT a.appointment_id) AS appointment_volume,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
    SUM(CASE WHEN r.referral_status = 'open' AND DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) > 21 THEN 1 ELSE 0 END) AS open_referrals_over_21_days,
    c.weekly_intake_slot_capacity,
    ROUND(COUNT(DISTINCT a.appointment_id) / NULLIF(c.weekly_intake_slot_capacity * 4.0, 0) * 100, 2) AS monthly_capacity_utilization_pct
FROM dim_clinic c
LEFT JOIN fact_appointment a ON c.clinic_id = a.clinic_id
LEFT JOIN fact_referral r ON a.referral_id = r.referral_id
GROUP BY c.clinic_id, c.clinic_name, c.clinic_group, c.weekly_intake_slot_capacity;

CREATE OR REPLACE VIEW vw_data_quality_scorecard AS
SELECT
    rule_id,
    rule_name,
    table_name,
    severity,
    failed_row_count,
    status,
    checked_at
FROM fact_data_quality_issue;

-- Stage 2 portfolio-grade views

CREATE OR REPLACE VIEW vw_weekly_access_trends AS
SELECT
    DATE_TRUNC('week', a.appointment_date) AS week_start,
    c.clinic_id,
    c.clinic_name,
    c.clinic_group,
    COUNT(DISTINCT r.referral_id) AS referral_volume,
    COUNT(DISTINCT a.appointment_id) AS appointment_volume,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.visit_mode = 'telehealth' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS telehealth_rate_pct
FROM fact_appointment a
JOIN fact_referral r ON a.referral_id = r.referral_id
JOIN dim_clinic c ON a.clinic_id = c.clinic_id
GROUP BY DATE_TRUNC('week', a.appointment_date), c.clinic_id, c.clinic_name, c.clinic_group;

CREATE OR REPLACE VIEW vw_clinic_attention_index AS
WITH base AS (
    SELECT
        clinic_id,
        clinic_name,
        clinic_group,
        referral_volume,
        appointment_volume,
        median_referral_to_appointment_days,
        completion_rate_pct,
        no_show_rate_pct,
        open_referrals_over_21_days,
        monthly_capacity_utilization_pct,
        ROUND(open_referrals_over_21_days * 1.0 / NULLIF(referral_volume, 0), 4) AS open_over_21_rate
    FROM vw_clinic_access_performance
), normalized AS (
    SELECT
        *,
        median_referral_to_appointment_days / NULLIF(MAX(median_referral_to_appointment_days) OVER (), 0) AS norm_lag,
        no_show_rate_pct / NULLIF(MAX(no_show_rate_pct) OVER (), 0) AS norm_no_show,
        open_over_21_rate / NULLIF(MAX(open_over_21_rate) OVER (), 0) AS norm_open_aging,
        monthly_capacity_utilization_pct / NULLIF(MAX(monthly_capacity_utilization_pct) OVER (), 0) AS norm_capacity
    FROM base
)
SELECT
    clinic_id,
    clinic_name,
    clinic_group,
    referral_volume,
    appointment_volume,
    median_referral_to_appointment_days,
    completion_rate_pct,
    no_show_rate_pct,
    open_referrals_over_21_days,
    open_over_21_rate,
    monthly_capacity_utilization_pct,
    ROUND(100 * (
        0.35 * COALESCE(norm_lag, 0)
        + 0.25 * COALESCE(norm_no_show, 0)
        + 0.20 * COALESCE(norm_open_aging, 0)
        + 0.20 * COALESCE(norm_capacity, 0)
    ), 2) AS clinic_attention_index,
    CASE
        WHEN COALESCE(median_referral_to_appointment_days, 0) >= 30 THEN 'Review intake slot capacity and prioritize older referrals'
        WHEN COALESCE(no_show_rate_pct, 0) >= 25 THEN 'Strengthen reminder outreach and confirmation workflows'
        WHEN COALESCE(open_referrals_over_21_days, 0) >= 25 THEN 'Create backlog worklist for referrals older than 21 days'
        WHEN COALESCE(monthly_capacity_utilization_pct, 0) >= 95 THEN 'Review provider capacity and scheduling templates'
        ELSE 'Monitor performance and maintain current workflow'
    END AS suggested_operational_action
FROM normalized;

CREATE OR REPLACE VIEW vw_patient_segment_completion_gap AS
SELECT
    p.age_group,
    p.insurance_type,
    p.preferred_language,
    p.transportation_risk_flag,
    a.visit_mode,
    COUNT(a.appointment_id) AS appointment_volume,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
    MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)) AS median_referral_to_appointment_days
FROM fact_appointment a
JOIN fact_referral r ON a.referral_id = r.referral_id
JOIN dim_patient p ON a.patient_id = p.patient_id
GROUP BY p.age_group, p.insurance_type, p.preferred_language, p.transportation_risk_flag, a.visit_mode;

CREATE OR REPLACE VIEW vw_operational_action_queue AS
SELECT
    'Clinic' AS entity_type,
    clinic_name AS entity_name,
    clinic_attention_index AS priority_score,
    suggested_operational_action AS recommended_action,
    'Referral lag, no-show rate, open referral aging, and capacity utilization' AS supporting_metric_context
FROM vw_clinic_attention_index
WHERE clinic_attention_index >= 60
UNION ALL
SELECT
    'ZIP Code' AS entity_type,
    zip_code AS entity_name,
    access_friction_score AS priority_score,
    CASE
        WHEN access_friction_score >= 65 THEN 'Review access barriers, reminder workflows, and telehealth availability'
        WHEN no_show_rate_pct >= 25 THEN 'Prioritize appointment confirmation and outreach workflows'
        WHEN open_over_21_rate_pct >= 20 THEN 'Review aging open referrals for this ZIP code'
        ELSE 'Monitor access friction trend'
    END AS recommended_action,
    'ZIP access friction score, no-show rate, transportation risk, and open referral aging' AS supporting_metric_context
FROM vw_zip_access_friction
WHERE access_friction_score >= 60;
