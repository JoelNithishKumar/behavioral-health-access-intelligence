import json
import sys
from datetime import timedelta
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from config import DB_PATH, MODELS_DIR, SYNTHETIC_DIR
from copilot import generate_access_summary

st.set_page_config(
    page_title="Behavioral Health Access Intelligence",
    page_icon="🏥",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {font-size: 2.1rem; font-weight: 750; margin-bottom: 0rem;}
    .subtitle {font-size: 1rem; color: #5f6368; margin-bottom: 1.2rem;}
    .section-note {background: #f7f9fc; border: 1px solid #e3e8ef; padding: 0.9rem; border-radius: 0.8rem; margin-bottom: 1rem;}
    .risk-note {background: #fff8e6; border: 1px solid #f2d184; padding: 0.9rem; border-radius: 0.8rem; margin-bottom: 1rem;}
    .success-note {background: #edf8f2; border: 1px solid #b8dfc8; padding: 0.9rem; border-radius: 0.8rem; margin-bottom: 1rem;}
    .question-box {background: #f9fbff; border: 1px solid #dfe7f3; padding: 1rem; border-radius: 0.9rem; margin-top: 0.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Database helpers
# -----------------------------

def query(sql: str) -> pd.DataFrame:
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(sql).fetchdf()
    conn.close()
    return df


def get_scalar(sql: str, default=0):
    try:
        df = query(sql)
        if df.empty:
            return default
        value = df.iloc[0, 0]
        if pd.isna(value):
            return default
        return value
    except Exception:
        return default


def sql_quote(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def in_clause(column: str, selected: list, all_values: list) -> str:
    """Return a SQL predicate without a leading AND.

    Empty selections intentionally return 1=0 so the dashboard shows no rows
    instead of accidentally removing the filter.
    """
    if selected is None or len(selected) == 0:
        return "1=0"
    if len(selected) == len(all_values):
        return ""
    quoted = ", ".join(sql_quote(v) for v in selected)
    return f"{column} IN ({quoted})"


def build_where(date_col: str = "a.appointment_date", include_date: bool = True) -> str:
    clauses = []
    if include_date:
        clauses.append(f"{date_col} BETWEEN DATE '{start_date}' AND DATE '{end_date}'")

    clauses.extend([
        in_clause("c.clinic_name", selected_clinics, clinic_options),
        in_clause("a.visit_mode", selected_visit_modes, visit_mode_options),
        in_clause("a.appointment_type", selected_appt_types, appointment_type_options),
        in_clause("p.insurance_type", selected_insurance_types, insurance_type_options),
    ])

    clauses = [clause for clause in clauses if clause]
    return " AND ".join(clauses) if clauses else "1=1"


def period_where(start, end) -> str:
    clauses = [f"a.appointment_date BETWEEN DATE '{start}' AND DATE '{end}'"]
    clauses.extend([
        in_clause("c.clinic_name", selected_clinics, clinic_options),
        in_clause("a.visit_mode", selected_visit_modes, visit_mode_options),
        in_clause("a.appointment_type", selected_appt_types, appointment_type_options),
        in_clause("p.insurance_type", selected_insurance_types, insurance_type_options),
    ])

    clauses = [clause for clause in clauses if clause]
    return " AND ".join(clauses) if clauses else "1=1"


def metric_delta(current, previous, suffix="", invert_good=False):
    try:
        current = float(current)
        previous = float(previous)
    except Exception:
        return None
    if previous == 0:
        return None
    delta = current - previous
    return f"{delta:+.1f}{suffix}"


def pct(numerator, denominator):
    if denominator in [0, None] or pd.isna(denominator):
        return 0
    return round(100 * numerator / denominator, 2)


# -----------------------------
# Metrics and analytic functions
# -----------------------------

def kpi_query(where_clause: str) -> dict:
    sql = f"""
    SELECT
        COUNT(DISTINCT r.referral_id) AS total_referrals,
        COUNT(DISTINCT a.appointment_id) AS total_appointments,
        SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) AS completed_appointments,
        SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_appointments,
        ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS median_lag_days,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
        COUNT(DISTINCT CASE WHEN r.referral_status = 'open' AND DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) > {aging_threshold_days} THEN r.referral_id END) AS open_referrals_over_threshold,
        ROUND(AVG(z.access_friction_score), 2) AS avg_access_friction
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    LEFT JOIN vw_zip_access_friction z ON p.zip_code = z.zip_code
    WHERE {where_clause}
    """
    df = query(sql)
    if df.empty:
        return {
            "total_referrals": 0,
            "total_appointments": 0,
            "completed_appointments": 0,
            "no_show_appointments": 0,
            "median_lag_days": 0,
            "completion_rate_pct": 0,
            "no_show_rate_pct": 0,
            "open_referrals_over_threshold": 0,
            "avg_access_friction": 0,
        }
    row = df.iloc[0].fillna(0)
    return row.to_dict()


def filtered_clinic_performance(where_clause: str) -> pd.DataFrame:
    return query(f"""
    WITH base AS (
        SELECT
            c.clinic_id,
            c.clinic_name,
            c.clinic_group,
            COUNT(DISTINCT r.referral_id) AS referral_volume,
            COUNT(DISTINCT a.appointment_id) AS appointment_volume,
            ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS median_referral_to_appointment_days,
            ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
            COUNT(DISTINCT CASE WHEN r.referral_status = 'open' AND DATE_DIFF('day', r.referral_created_date, CURRENT_DATE) > {aging_threshold_days} THEN r.referral_id END) AS open_referrals_over_threshold,
            ROUND(COUNT(DISTINCT a.appointment_id) / NULLIF(MAX(c.weekly_intake_slot_capacity) * 4.0, 0) * 100, 2) AS monthly_capacity_utilization_pct
        FROM fact_appointment a
        JOIN fact_referral r ON a.referral_id = r.referral_id
        JOIN dim_patient p ON a.patient_id = p.patient_id
        JOIN dim_clinic c ON a.clinic_id = c.clinic_id
        WHERE {where_clause}
        GROUP BY c.clinic_id, c.clinic_name, c.clinic_group
    ), normalized AS (
        SELECT
            *,
            median_referral_to_appointment_days / NULLIF(MAX(median_referral_to_appointment_days) OVER (), 0) AS norm_lag,
            no_show_rate_pct / NULLIF(MAX(no_show_rate_pct) OVER (), 0) AS norm_no_show,
            open_referrals_over_threshold * 1.0 / NULLIF(MAX(open_referrals_over_threshold) OVER (), 0) AS norm_open_aging,
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
        open_referrals_over_threshold,
        monthly_capacity_utilization_pct,
        ROUND(100 * (
            {clinic_lag_weight} * COALESCE(norm_lag, 0)
            + {clinic_no_show_weight} * COALESCE(norm_no_show, 0)
            + {clinic_open_aging_weight} * COALESCE(norm_open_aging, 0)
            + {clinic_capacity_weight} * COALESCE(norm_capacity, 0)
        ), 2) AS clinic_attention_index
    FROM normalized
    ORDER BY clinic_attention_index DESC
    """)


def filtered_access_trends(where_clause: str, trend_grain: str = "week") -> pd.DataFrame:
    """Return access trend metrics grouped by day, week, month, or year.

    trend_grain is controlled by dashboard UI and sanitized before being inserted
    into DATE_TRUNC, so users cannot inject arbitrary SQL.
    """
    allowed_grains = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }
    safe_grain = allowed_grains.get(trend_grain, "week")

    return query(f"""
    SELECT
        DATE_TRUNC('{safe_grain}', a.appointment_date) AS period_start,
        COUNT(DISTINCT r.referral_id) AS referral_volume,
        COUNT(DISTINCT a.appointment_id) AS appointment_volume,
        ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS median_lag_days,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    WHERE {where_clause}
    GROUP BY DATE_TRUNC('{safe_grain}', a.appointment_date)
    ORDER BY period_start
    """)


def trend_grain_label(trend_grain: str) -> str:
    return {
        "day": "Daily",
        "week": "Weekly",
        "month": "Monthly",
        "year": "Yearly",
    }.get(trend_grain, "Weekly")


def zip_access_friction_custom() -> pd.DataFrame:
    """Calculate custom access friction score from adjustable dashboard weights."""
    df = query("SELECT * FROM vw_zip_access_friction")
    if df.empty:
        return df

    df = df.copy()
    for col in ["median_referral_to_appointment_days", "no_show_rate_pct", "open_over_21_rate_pct", "telehealth_usage_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    def normalize(series):
        max_value = series.max()
        if max_value == 0 or pd.isna(max_value):
            return series * 0
        return series / max_value

    df["norm_lag"] = normalize(df["median_referral_to_appointment_days"])
    df["norm_no_show"] = normalize(df["no_show_rate_pct"])
    df["norm_open_aging"] = normalize(df["open_over_21_rate_pct"])
    df["low_telehealth_penalty"] = 1 - normalize(df["telehealth_usage_pct"])

    df["custom_access_friction_score"] = (100 * (
        zip_lag_weight * df["norm_lag"].fillna(0)
        + zip_no_show_weight * df["norm_no_show"].fillna(0)
        + zip_transportation_weight * df["transportation_risk_rate"].fillna(0)
        + zip_underinsured_weight * df["underinsured_rate"].fillna(0)
        + zip_language_weight * df["limited_english_rate"].fillna(0)
        + zip_open_aging_weight * df["norm_open_aging"].fillna(0)
        + zip_telehealth_weight * df["low_telehealth_penalty"].fillna(0)
    )).round(2)

    return df.sort_values("custom_access_friction_score", ascending=False)


def appointment_type_no_show(where_clause: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        a.appointment_type,
        COUNT(a.appointment_id) AS appointment_count,
        SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_count,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    WHERE {where_clause}
    GROUP BY a.appointment_type
    ORDER BY no_show_rate_pct DESC, appointment_count DESC
    """)


def visit_mode_no_show(where_clause: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        a.visit_mode,
        COUNT(a.appointment_id) AS appointment_count,
        SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) AS no_show_count,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    WHERE {where_clause}
    GROUP BY a.visit_mode
    ORDER BY no_show_rate_pct DESC
    """)


def patient_segment_completion(where_clause: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        p.age_group,
        p.insurance_type,
        p.preferred_language,
        p.transportation_risk_flag,
        a.visit_mode,
        COUNT(a.appointment_id) AS appointment_count,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS completion_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct,
        ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS median_referral_to_appointment_days
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    WHERE {where_clause}
    GROUP BY p.age_group, p.insurance_type, p.preferred_language, p.transportation_risk_flag, a.visit_mode
    HAVING COUNT(a.appointment_id) >= {minimum_segment_volume}
    ORDER BY completion_rate_pct ASC, appointment_count DESC
    """)


def provider_capacity(where_clause: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        pr.provider_id,
        pr.provider_name,
        pr.provider_type,
        c.clinic_name,
        COUNT(a.appointment_id) AS appointment_count,
        ROUND(COUNT(a.appointment_id) / NULLIF(MAX(pr.weekly_capacity_slots) * 4.0, 0) * 100, 2) AS monthly_provider_utilization_pct,
        ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS median_referral_to_appointment_days,
        ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS no_show_rate_pct
    FROM fact_appointment a
    JOIN fact_referral r ON a.referral_id = r.referral_id
    JOIN dim_patient p ON a.patient_id = p.patient_id
    JOIN dim_clinic c ON a.clinic_id = c.clinic_id
    JOIN dim_provider pr ON a.provider_id = pr.provider_id
    WHERE {where_clause}
    GROUP BY pr.provider_id, pr.provider_name, pr.provider_type, c.clinic_name
    ORDER BY monthly_provider_utilization_pct DESC, median_referral_to_appointment_days DESC
    """)


def clinic_improvement_last_30() -> pd.DataFrame:
    current_end = max_date
    current_start = max_date - timedelta(days=29)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=29)
    current_where = period_where(current_start, current_end)
    previous_where = period_where(previous_start, previous_end)

    current = query(f"""
        SELECT c.clinic_name,
               ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS current_median_lag,
               ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS current_completion_rate,
               COUNT(a.appointment_id) AS current_appointment_count
        FROM fact_appointment a
        JOIN fact_referral r ON a.referral_id = r.referral_id
        JOIN dim_patient p ON a.patient_id = p.patient_id
        JOIN dim_clinic c ON a.clinic_id = c.clinic_id
        WHERE {current_where}
        GROUP BY c.clinic_name
    """)
    previous = query(f"""
        SELECT c.clinic_name,
               ROUND(MEDIAN(DATE_DIFF('day', r.referral_created_date, a.appointment_date)), 1) AS previous_median_lag,
               ROUND(100.0 * SUM(CASE WHEN a.appointment_status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.appointment_id), 0), 2) AS previous_completion_rate,
               COUNT(a.appointment_id) AS previous_appointment_count
        FROM fact_appointment a
        JOIN fact_referral r ON a.referral_id = r.referral_id
        JOIN dim_patient p ON a.patient_id = p.patient_id
        JOIN dim_clinic c ON a.clinic_id = c.clinic_id
        WHERE {previous_where}
        GROUP BY c.clinic_name
    """)
    if current.empty or previous.empty:
        return pd.DataFrame()
    merged = current.merge(previous, on="clinic_name", how="inner")
    merged["lag_improvement_days"] = (merged["previous_median_lag"] - merged["current_median_lag"]).round(1)
    merged["completion_rate_change_pct_points"] = (merged["current_completion_rate"] - merged["previous_completion_rate"]).round(1)
    return merged.sort_values(["lag_improvement_days", "completion_rate_change_pct_points"], ascending=False)


def operational_action_queue_dynamic(clinic_df: pd.DataFrame, zip_df: pd.DataFrame) -> pd.DataFrame:
    actions = []
    if not clinic_df.empty:
        for _, row in clinic_df.iterrows():
            triggers = []
            if row["median_referral_to_appointment_days"] >= high_lag_threshold_days:
                triggers.append(f"median lag {row['median_referral_to_appointment_days']:.1f} days")
            if row["no_show_rate_pct"] >= high_no_show_threshold_pct:
                triggers.append(f"no-show rate {row['no_show_rate_pct']:.1f}%")
            if row["open_referrals_over_threshold"] > 0:
                triggers.append(f"{int(row['open_referrals_over_threshold'])} open referrals older than {aging_threshold_days} days")
            if row["monthly_capacity_utilization_pct"] >= high_capacity_threshold_pct:
                triggers.append(f"capacity utilization {row['monthly_capacity_utilization_pct']:.1f}%")
            if triggers:
                actions.append({
                    "entity_type": "Clinic",
                    "entity_name": row["clinic_name"],
                    "priority_score": round(float(row["clinic_attention_index"]), 2),
                    "recommended_action": "Review intake slots, aging referrals, reminder workflows, and scheduling backlog.",
                    "triggering_metrics": "; ".join(triggers),
                })
    if not zip_df.empty:
        for _, row in zip_df.head(10).iterrows():
            triggers = []
            if row["custom_access_friction_score"] >= high_access_friction_threshold:
                triggers.append(f"access friction {row['custom_access_friction_score']:.1f}")
            if row["no_show_rate_pct"] >= high_no_show_threshold_pct:
                triggers.append(f"no-show rate {row['no_show_rate_pct']:.1f}%")
            if row["open_over_21_rate_pct"] >= 20:
                triggers.append(f"open aging rate {row['open_over_21_rate_pct']:.1f}%")
            if triggers:
                actions.append({
                    "entity_type": "ZIP Code",
                    "entity_name": str(row["zip_code"]),
                    "priority_score": round(float(row["custom_access_friction_score"]), 2),
                    "recommended_action": "Review access barriers, reminder workflows, and telehealth scheduling options.",
                    "triggering_metrics": "; ".join(triggers),
                })
    return pd.DataFrame(actions).sort_values("priority_score", ascending=False) if actions else pd.DataFrame()


def run_controlled_question(question: str, where_clause: str, clinic_df: pd.DataFrame, zip_df: pd.DataFrame):
    """Controlled natural-language analytics router. No unrestricted SQL generation."""
    q = question.lower().strip()

    if not q:
        return "Ask a question or choose one from the examples.", pd.DataFrame(), None

    if "clinic" in q and ("highest" in q or "longest" in q) and ("lag" in q or "delay" in q):
        df = clinic_df.sort_values("median_referral_to_appointment_days", ascending=False).head(10)
        top = df.iloc[0] if not df.empty else None
        answer = "No matching clinic data found for the current filters."
        if top is not None:
            answer = (
                f"{top['clinic_name']} has the highest median referral-to-appointment lag "
                f"at {top['median_referral_to_appointment_days']:.1f} days in the selected filter context."
            )
        return answer, df, "bar_lag"

    if "improved" in q or "improving" in q or "last 30" in q:
        df = clinic_improvement_last_30().head(10)
        if df.empty:
            return "I do not have enough data to compare the latest 30 days with the prior 30 days for the selected filters.", df, None
        top = df.iloc[0]
        answer = (
            f"{top['clinic_name']} improved the most over the latest 30-day comparison, "
            f"with median lag improving by {top['lag_improvement_days']:.1f} days and completion rate changing by "
            f"{top['completion_rate_change_pct_points']:.1f} percentage points."
        )
        return answer, df, "bar_improvement"

    if "open" in q and ("21" in q or "older" in q or "aging" in q or "after" in q):
        count_value = int(current_metrics.get("open_referrals_over_threshold", 0))
        answer = (
            f"There are {count_value:,} appointment-linked behavioral health referrals still open after "
            f"{aging_threshold_days} days in the selected filter context. You can change this threshold in the sidebar."
        )
        df = clinic_df[["clinic_name", "open_referrals_over_threshold", "clinic_attention_index"]].sort_values("open_referrals_over_threshold", ascending=False)
        return answer, df, "bar_open"

    if "drop" in q or "funnel" in q or "leak" in q:
        df = query("SELECT * FROM vw_behavioral_health_funnel ORDER BY stage_order")
        if df.empty:
            return "No funnel data is available.", df, None
        df = df.copy()
        df["prior_stage_count"] = df["stage_count"].shift(1)
        df["dropoff_from_prior_stage"] = (df["prior_stage_count"] - df["stage_count"]).fillna(0).astype(int)
        largest = df.sort_values("dropoff_from_prior_stage", ascending=False).iloc[0]
        answer = (
            f"The largest funnel drop-off occurs at '{largest['stage']}', with an estimated "
            f"drop-off of {int(largest['dropoff_from_prior_stage']):,} from the prior stage."
        )
        return answer, df, "funnel"

    if "zip" in q or "friction" in q or "access barrier" in q:
        df = zip_df.head(10)
        if df.empty:
            return "No ZIP access friction data is available.", df, None
        top = df.iloc[0]
        answer = (
            f"ZIP {top['zip_code']} has the highest custom access friction score "
            f"at {top['custom_access_friction_score']:.1f}. The score reflects the weights currently selected in the sidebar."
        )
        return answer, df, "bar_zip"

    if "appointment type" in q and ("no-show" in q or "no show" in q):
        df = appointment_type_no_show(where_clause)
        if df.empty:
            return "No appointment-type no-show data is available for the current filters.", df, None
        top = df.iloc[0]
        answer = (
            f"{top['appointment_type']} has the highest no-show rate at {top['no_show_rate_pct']:.1f}% "
            f"across {int(top['appointment_count']):,} appointments in the selected context."
        )
        return answer, df, "bar_appt_type"

    if "telehealth" in q or "visit mode" in q:
        df = visit_mode_no_show(where_clause)
        if df.empty or len(df) < 2:
            return "I do not have enough visit-mode data to compare telehealth and in-person no-show rates.", df, None
        tele = df[df["visit_mode"] == "telehealth"]
        in_person = df[df["visit_mode"] == "in_person"]
        if tele.empty or in_person.empty:
            answer = "The current filters do not include both telehealth and in-person appointments. Adjust visit-mode filters to compare them."
        else:
            tele_rate = float(tele.iloc[0]["no_show_rate_pct"])
            in_rate = float(in_person.iloc[0]["no_show_rate_pct"])
            direction = "lower" if tele_rate < in_rate else "higher"
            answer = f"Telehealth no-show rate is {tele_rate:.1f}%, which is {direction} than in-person no-show rate of {in_rate:.1f}% in the selected context."
        return answer, df, "bar_visit_mode"

    if "provider" in q or "capacity" in q or "constraint" in q:
        df = provider_capacity(where_clause).head(15)
        if df.empty:
            return "No provider capacity data is available for the current filters.", df, None
        top = df.iloc[0]
        answer = (
            f"{top['provider_name']} at {top['clinic_name']} has the highest provider utilization proxy "
            f"at {top['monthly_provider_utilization_pct']:.1f}% for the selected period."
        )
        return answer, df, "bar_provider_capacity"

    if "segment" in q or "least likely" in q or "completion gap" in q:
        df = patient_segment_completion(where_clause).head(15)
        if df.empty:
            return "No segment data meets the minimum volume threshold for the current filters.", df, None
        top = df.iloc[0]
        answer = (
            f"The lowest-completion segment is age group {top['age_group']}, {top['insurance_type']} insurance, "
            f"preferred language {top['preferred_language']}, visit mode {top['visit_mode']}, with a "
            f"completion rate of {top['completion_rate_pct']:.1f}%."
        )
        return answer, df, "bar_segment"

    if "action" in q or "prioritize" in q or "leadership" in q:
        df = operational_action_queue_dynamic(clinic_df, zip_df).head(15)
        if df.empty:
            return "No operational actions crossed the current thresholds. Try lowering thresholds in the sidebar.", df, None
        top = df.iloc[0]
        answer = (
            f"The top recommended priority is {top['entity_type']} {top['entity_name']} with priority score "
            f"{top['priority_score']:.1f}. Recommended action: {top['recommended_action']}"
        )
        return answer, df, "bar_action"

    return (
        "I can answer this dashboard question only through controlled analytics routes. Try one of the suggested questions, or use keywords like clinic lag, ZIP friction, no-show, telehealth, funnel, capacity, segment, or actions.",
        pd.DataFrame(),
        None,
    )


# -----------------------------
# Header and prerequisite check
# -----------------------------

st.markdown('<div class="main-title">Behavioral Health Access Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Synthetic healthcare operations analytics for referral lag, appointment access, no-show risk, access friction, and data quality. No PHI. No clinical advice.</div>', unsafe_allow_html=True)

if not DB_PATH.exists():
    st.warning("Warehouse database not found. Run these commands first:")
    st.code("python src/generate_synthetic_data.py\npython src/load_warehouse.py\npython src/no_show_model.py", language="powershell")
    st.stop()


# -----------------------------
# Sidebar controls
# -----------------------------

min_max = query("SELECT MIN(appointment_date) AS min_date, MAX(appointment_date) AS max_date FROM fact_appointment")
min_date = pd.to_datetime(min_max.iloc[0]["min_date"]).date()
max_date = pd.to_datetime(min_max.iloc[0]["max_date"]).date()
default_start = max(min_date, max_date - timedelta(days=120))

clinic_options = query("SELECT clinic_name FROM dim_clinic ORDER BY clinic_name")["clinic_name"].tolist()
visit_mode_options = query("SELECT DISTINCT visit_mode FROM fact_appointment ORDER BY visit_mode")["visit_mode"].tolist()
appointment_type_options = query("SELECT DISTINCT appointment_type FROM fact_appointment ORDER BY appointment_type")["appointment_type"].tolist()
insurance_type_options = query("SELECT DISTINCT insurance_type FROM dim_patient ORDER BY insurance_type")["insurance_type"].tolist()

with st.sidebar:
    st.header("Dashboard Filters")

    st.subheader("Time Period")
    period_mode = st.selectbox(
        "Executive summary period",
        ["Weekly", "Monthly", "Yearly", "Custom dates"],
        index=0,
        help=(
            "Weekly = last 12 weeks grouped by week. "
            "Monthly = last 12 months grouped by month. "
            "Yearly = full available dataset grouped by year. "
            "Custom dates lets you choose any date range."
        ),
    )

    custom_trend_grain = None
    if period_mode == "Weekly":
        start_date = max(min_date, max_date - timedelta(weeks=12))
        end_date = max_date
        trend_grain = "week"
    elif period_mode == "Monthly":
        start_date = max(min_date, max_date - timedelta(days=365))
        end_date = max_date
        trend_grain = "month"
    elif period_mode == "Yearly":
        start_date = min_date
        end_date = max_date
        trend_grain = "year"
    else:
        date_range = st.date_input(
            "Custom appointment date range",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = default_start, max_date

        custom_grain_label = st.selectbox(
            "Custom trend grouping",
            ["Daily", "Weekly", "Monthly", "Yearly"],
            index=1,
            help="Choose how the trend chart should group your selected custom date range.",
        )
        trend_grain = {
            "Daily": "day",
            "Weekly": "week",
            "Monthly": "month",
            "Yearly": "year",
        }[custom_grain_label]

    st.caption(f"Active window: {start_date} to {end_date} · Trend grouping: {trend_grain_label(trend_grain)}")

    selected_clinics = st.multiselect("Clinics", clinic_options, default=clinic_options)
    selected_visit_modes = st.multiselect("Visit mode", visit_mode_options, default=visit_mode_options)
    selected_appt_types = st.multiselect("Appointment type", appointment_type_options, default=appointment_type_options)
    selected_insurance_types = st.multiselect("Insurance type", insurance_type_options, default=insurance_type_options)

    st.markdown("---")
    st.header("Interactive Settings")
    aging_threshold_days = st.slider("Open referral aging threshold", 7, 60, 21, help="Used for open referral aging KPIs and action alerts.")
    high_lag_threshold_days = st.slider("High median lag threshold", 7, 60, 24, help="Used to trigger operational action recommendations.")
    high_no_show_threshold_pct = st.slider("High no-show threshold (%)", 5, 50, 18, help="Used to trigger no-show-focused action recommendations.")
    high_capacity_threshold_pct = st.slider("High capacity utilization threshold (%)", 50, 140, 90, help="Used to flag possible capacity constraints.")
    high_access_friction_threshold = st.slider("High access friction threshold", 25, 100, 60, help="Used to flag ZIP codes needing access review.")
    minimum_segment_volume = st.slider("Minimum segment volume", 5, 100, 20, help="Filters small patient segments in Ask the Data.")

    with st.expander("Clinic Attention Index Weights"):
        clinic_lag_raw = st.slider("Clinic lag weight", 0, 100, 35)
        clinic_no_show_raw = st.slider("Clinic no-show weight", 0, 100, 25)
        clinic_open_raw = st.slider("Clinic open-aging weight", 0, 100, 20)
        clinic_capacity_raw = st.slider("Clinic capacity weight", 0, 100, 20)
        total = max(clinic_lag_raw + clinic_no_show_raw + clinic_open_raw + clinic_capacity_raw, 1)
        clinic_lag_weight = clinic_lag_raw / total
        clinic_no_show_weight = clinic_no_show_raw / total
        clinic_open_aging_weight = clinic_open_raw / total
        clinic_capacity_weight = clinic_capacity_raw / total
        st.caption(f"Normalized total: {clinic_lag_weight + clinic_no_show_weight + clinic_open_aging_weight + clinic_capacity_weight:.2f}")

    with st.expander("ZIP Access Friction Weights"):
        zip_lag_raw = st.slider("ZIP lag weight", 0, 100, 25)
        zip_no_show_raw = st.slider("ZIP no-show weight", 0, 100, 20)
        zip_transportation_raw = st.slider("Transportation risk weight", 0, 100, 15)
        zip_underinsured_raw = st.slider("Underinsured proxy weight", 0, 100, 15)
        zip_language_raw = st.slider("Limited English proxy weight", 0, 100, 10)
        zip_open_raw = st.slider("Open-aging weight", 0, 100, 10)
        zip_telehealth_raw = st.slider("Low telehealth usage weight", 0, 100, 5)
        total_zip = max(zip_lag_raw + zip_no_show_raw + zip_transportation_raw + zip_underinsured_raw + zip_language_raw + zip_open_raw + zip_telehealth_raw, 1)
        zip_lag_weight = zip_lag_raw / total_zip
        zip_no_show_weight = zip_no_show_raw / total_zip
        zip_transportation_weight = zip_transportation_raw / total_zip
        zip_underinsured_weight = zip_underinsured_raw / total_zip
        zip_language_weight = zip_language_raw / total_zip
        zip_open_aging_weight = zip_open_raw / total_zip
        zip_telehealth_weight = zip_telehealth_raw / total_zip
        st.caption(f"Normalized total: {zip_lag_weight + zip_no_show_weight + zip_transportation_weight + zip_underinsured_weight + zip_language_weight + zip_open_aging_weight + zip_telehealth_weight:.2f}")

    show_query_logic = st.checkbox("Show controlled query logic in Ask the Data", value=False)
    st.markdown("---")
    st.caption("Filters apply to appointment-linked operational metrics. Settings update KPIs, alerts, and custom prioritization scores.")

where = build_where()
current_metrics = kpi_query(where)

# Prior-period benchmark for KPI deltas
window_days = max((end_date - start_date).days + 1, 1)
prev_end = start_date - timedelta(days=1)
prev_start = prev_end - timedelta(days=window_days - 1)
previous_metrics = kpi_query(period_where(prev_start, prev_end))

clinic_df = filtered_clinic_performance(where)
zip_df = zip_access_friction_custom()
action_df_dynamic = operational_action_queue_dynamic(clinic_df, zip_df)

st.markdown(
    """
    <div class="success-note">
    <b>Stage 5 interactive upgrade:</b> This version adds weekly, monthly, yearly, and custom date controls for the executive summary and trend chart, while preserving controlled Q&A, adjustable thresholds, custom prioritization weights, and scenario analysis.
    </div>
    """,
    unsafe_allow_html=True,
)


tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Executive Overview",
    "Referral Funnel",
    "Clinic Performance",
    "ZIP Access Friction",
    "No-Show Risk",
    "Data Quality",
    "AI Copilot",
    "Ask the Data",
    "Settings & Scenario Lab",
])


with tab1:
    st.subheader("Executive Overview")
    st.caption(
        f"{period_mode} view · Analysis window: {start_date} to {end_date}. "
        f"KPI deltas compare against {prev_start} to {prev_end}."
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "Total referrals",
        f"{current_metrics['total_referrals']:,.0f}",
        metric_delta(current_metrics["total_referrals"], previous_metrics["total_referrals"]),
    )
    c2.metric(
        "Median lag",
        f"{current_metrics['median_lag_days']:.1f} days",
        metric_delta(current_metrics["median_lag_days"], previous_metrics["median_lag_days"], "d"),
    )
    c3.metric(
        "Completion rate",
        f"{current_metrics['completion_rate_pct']:.1f}%",
        metric_delta(current_metrics["completion_rate_pct"], previous_metrics["completion_rate_pct"], "%"),
    )
    c4.metric(
        "No-show rate",
        f"{current_metrics['no_show_rate_pct']:.1f}%",
        metric_delta(current_metrics["no_show_rate_pct"], previous_metrics["no_show_rate_pct"], "%"),
    )
    c5.metric(
        f"Open >{aging_threshold_days} days",
        f"{current_metrics['open_referrals_over_threshold']:,.0f}",
        metric_delta(current_metrics["open_referrals_over_threshold"], previous_metrics["open_referrals_over_threshold"]),
    )
    c6.metric(
        "Avg friction",
        f"{current_metrics['avg_access_friction']:.1f}",
        metric_delta(current_metrics["avg_access_friction"], previous_metrics["avg_access_friction"]),
    )

    st.markdown("### Access Trends")
    st.caption(
        f"Currently grouped as {trend_grain_label(trend_grain).lower()} periods. "
        "Change the period control in the sidebar to switch between weekly, monthly, yearly, or custom dates."
    )

    trends = filtered_access_trends(where, trend_grain)
    if not trends.empty:
        fig = px.line(
            trends,
            x="period_start",
            y=["median_lag_days", "no_show_rate_pct", "completion_rate_pct"],
            markers=True,
            title=f"{trend_grain_label(trend_grain)} Access Trends: Lag, No-Show Rate, and Completion Rate",
        )
        fig.update_xaxes(title_text=f"{trend_grain_label(trend_grain)} period")
        fig.update_yaxes(title_text="Metric value")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data is available for the selected filters and time period.")

    left, right = st.columns([1.1, 1])
    with left:
        st.plotly_chart(
            px.bar(
                clinic_df.head(8),
                x="clinic_name",
                y="clinic_attention_index",
                hover_data=["median_referral_to_appointment_days", "no_show_rate_pct", "open_referrals_over_threshold", "monthly_capacity_utilization_pct"],
                title="Custom Clinic Attention Index",
            ),
            use_container_width=True,
        )
    with right:
        st.dataframe(
            clinic_df[[
                "clinic_name",
                "clinic_group",
                "clinic_attention_index",
                "median_referral_to_appointment_days",
                "completion_rate_pct",
                "no_show_rate_pct",
                "open_referrals_over_threshold",
            ]].head(8),
            use_container_width=True,
        )

with tab2:
    st.subheader("Referral Funnel")
    funnel = query("SELECT * FROM vw_behavioral_health_funnel ORDER BY stage_order")
    max_count = funnel["stage_count"].max() if not funnel.empty else 1
    funnel["conversion_from_created_pct"] = (100 * funnel["stage_count"] / max_count).round(2)
    funnel["dropoff_from_prior_stage"] = funnel["stage_count"].shift(1) - funnel["stage_count"]
    funnel["dropoff_from_prior_stage"] = funnel["dropoff_from_prior_stage"].fillna(0).astype(int)
    st.plotly_chart(px.funnel(funnel, x="stage_count", y="stage", title="Behavioral Health Referral Funnel"), use_container_width=True)
    st.dataframe(funnel, use_container_width=True)

with tab3:
    st.subheader("Clinic Performance")
    st.plotly_chart(
        px.scatter(
            clinic_df,
            x="monthly_capacity_utilization_pct",
            y="median_referral_to_appointment_days",
            size="referral_volume",
            color="clinic_group",
            hover_name="clinic_name",
            title="Capacity Utilization vs Referral Lag",
        ),
        use_container_width=True,
    )
    st.dataframe(clinic_df, use_container_width=True)

    st.markdown("#### Dynamic Operational Action Queue")
    if action_df_dynamic.empty:
        st.info("No clinics or ZIP codes crossed the current thresholds. Lower thresholds in the sidebar to make the action queue more sensitive.")
    else:
        st.dataframe(action_df_dynamic, use_container_width=True)

with tab4:
    st.subheader("ZIP Code Access Friction")
    st.caption("This page uses the custom ZIP access friction weights from the sidebar.")
    st.plotly_chart(px.bar(zip_df.head(10), x="zip_code", y="custom_access_friction_score", title="Top ZIP Codes by Custom Access Friction Score"), use_container_width=True)
    st.dataframe(zip_df[[
        "zip_code", "area_name", "referral_volume", "median_referral_to_appointment_days", "no_show_rate_pct",
        "transportation_risk_rate", "underinsured_rate", "limited_english_rate", "telehealth_usage_pct",
        "open_over_21_rate_pct", "access_friction_score", "custom_access_friction_score"
    ]], use_container_width=True)

with tab5:
    st.subheader("No-Show Risk Model")
    st.markdown(
        """
        <div class="risk-note">
        <b>Responsible use boundary:</b> This model is for operational outreach prioritization only. It is not for diagnosis, treatment, eligibility, or clinical decision-making.
        </div>
        """,
        unsafe_allow_html=True,
    )
    metrics_path = MODELS_DIR / "no_show_metrics.json"
    preds_path = SYNTHETIC_DIR / "no_show_predictions.csv"
    if metrics_path.exists() and preds_path.exists():
        metrics = json.loads(metrics_path.read_text())
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Accuracy", metrics["accuracy"])
        c2.metric("Precision", metrics["precision"])
        c3.metric("Recall", metrics["recall"])
        c4.metric("F1", metrics["f1"])
        c5.metric("ROC-AUC", metrics["roc_auc"])
        preds = pd.read_csv(preds_path)
        st.plotly_chart(px.histogram(preds, x="predicted_no_show_probability", color="risk_bucket", title="Predicted No-Show Probability Distribution"), use_container_width=True)
        bucket_summary = preds.groupby("risk_bucket", observed=False).size().reset_index(name="appointment_count")
        st.dataframe(bucket_summary, use_container_width=True)
        st.dataframe(preds.sort_values("predicted_no_show_probability", ascending=False).head(50), use_container_width=True)
    else:
        st.warning("Model outputs not found. Run: python src/no_show_model.py")

with tab6:
    st.subheader("Data Quality Monitor")
    dq = query("SELECT * FROM fact_data_quality_issue ORDER BY severity, rule_id")
    pass_rate = round(100 * (dq["status"] == "pass").sum() / len(dq), 2) if len(dq) else 0
    critical_failures = len(dq[(dq["severity"] == "critical") & (dq["status"] == "fail")])
    warning_failures = len(dq[(dq["severity"] == "warning") & (dq["status"] == "fail")])
    c1, c2, c3 = st.columns(3)
    c1.metric("Data quality score", f"{pass_rate}%")
    c2.metric("Critical failures", critical_failures)
    c3.metric("Warning failures", warning_failures)
    st.plotly_chart(px.bar(dq, x="rule_id", y="failed_row_count", color="severity", title="Failed Rows by Data Quality Rule"), use_container_width=True)
    st.dataframe(dq, use_container_width=True)

with tab7:
    st.subheader("AI Copilot")
    st.markdown(
        """
        The copilot receives only structured, aggregated metric context from SQL views and dashboard filters. It should not inspect raw patient-level records or generate clinical advice.
        """
    )

    worst = clinic_df.iloc[0]["clinic_name"] if not clinic_df.empty else "insufficient clinic data"
    dq_score = get_scalar("SELECT ROUND(100.0 * SUM(CASE WHEN status='pass' THEN 1 ELSE 0 END) / COUNT(*), 2) FROM fact_data_quality_issue")

    metrics = {
        "analysis_window": {"start_date": str(start_date), "end_date": str(end_date)},
        "settings": {
            "open_referral_aging_threshold_days": aging_threshold_days,
            "high_median_lag_threshold_days": high_lag_threshold_days,
            "high_no_show_threshold_pct": high_no_show_threshold_pct,
            "high_capacity_threshold_pct": high_capacity_threshold_pct,
            "high_access_friction_threshold": high_access_friction_threshold,
        },
        "total_referrals": int(current_metrics["total_referrals"]),
        "median_referral_to_appointment_days": float(current_metrics["median_lag_days"]),
        "completion_rate_pct": float(current_metrics["completion_rate_pct"]),
        "no_show_rate_pct": float(current_metrics["no_show_rate_pct"]),
        "open_referrals_over_threshold": int(current_metrics["open_referrals_over_threshold"]),
        "average_access_friction_score": float(current_metrics["avg_access_friction"]),
        "clinic_needing_attention": worst,
        "data_quality_score_pct": float(dq_score),
        "top_operational_actions": action_df_dynamic.head(5).to_dict(orient="records") if not action_df_dynamic.empty else [],
    }

    with st.expander("Structured metric context sent to copilot"):
        st.json(metrics)

    if st.button("Generate Executive Access Summary", type="primary"):
        st.markdown(generate_access_summary(metrics))

with tab8:
    st.subheader("Ask the Data")
    st.markdown(
        """
        <div class="question-box">
        This is a controlled analytics Q&A layer. It does not generate unrestricted SQL. User questions are routed to predefined metric functions and SQL views.
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggested_questions = [
        "Which clinics have the highest median referral-to-appointment lag?",
        "Which clinics have improved access over the last 30 days?",
        f"How many behavioral health referrals are still open after {aging_threshold_days} days?",
        "Where are patients dropping off in the referral funnel?",
        "Which ZIP codes have the highest access friction score?",
        "Which appointment types have the highest no-show rate?",
        "Are telehealth appointments associated with lower no-show rates?",
        "Which providers or clinics have capacity constraints?",
        "Which patient segments are least likely to complete a first appointment?",
        "What operational actions should leadership prioritize this week?",
    ]
    selected_question = st.selectbox("Choose a sample question", suggested_questions)
    custom_question = st.text_input("Or type your own dashboard question", placeholder="Example: Which ZIP codes have the highest access friction?")
    final_question = custom_question.strip() if custom_question.strip() else selected_question

    if st.button("Ask", type="primary"):
        answer, answer_df, chart_type = run_controlled_question(final_question, where, clinic_df, zip_df)
        st.markdown("#### Answer")
        st.write(answer)

        if show_query_logic:
            st.info("This answer was produced through a controlled analytics route, not unrestricted LLM-generated SQL. Routes include clinic lag, latest 30-day improvement, open referral aging, funnel drop-off, ZIP friction, appointment-type no-show, visit-mode no-show, provider capacity, patient segment completion, and operational actions.")

        if answer_df is not None and not answer_df.empty:
            if chart_type == "bar_lag":
                st.plotly_chart(px.bar(answer_df, x="clinic_name", y="median_referral_to_appointment_days", title="Clinics by Median Referral-to-Appointment Lag"), use_container_width=True)
            elif chart_type == "bar_improvement":
                st.plotly_chart(px.bar(answer_df, x="clinic_name", y="lag_improvement_days", title="Clinic Improvement: Latest 30 Days vs Prior 30 Days"), use_container_width=True)
            elif chart_type == "bar_open":
                st.plotly_chart(px.bar(answer_df, x="clinic_name", y="open_referrals_over_threshold", title=f"Open Referrals Older Than {aging_threshold_days} Days"), use_container_width=True)
            elif chart_type == "funnel":
                st.plotly_chart(px.funnel(answer_df, x="stage_count", y="stage", title="Referral Funnel"), use_container_width=True)
            elif chart_type == "bar_zip":
                st.plotly_chart(px.bar(answer_df, x="zip_code", y="custom_access_friction_score", title="ZIP Codes by Custom Access Friction"), use_container_width=True)
            elif chart_type == "bar_appt_type":
                st.plotly_chart(px.bar(answer_df, x="appointment_type", y="no_show_rate_pct", title="No-Show Rate by Appointment Type"), use_container_width=True)
            elif chart_type == "bar_visit_mode":
                st.plotly_chart(px.bar(answer_df, x="visit_mode", y="no_show_rate_pct", title="No-Show Rate by Visit Mode"), use_container_width=True)
            elif chart_type == "bar_provider_capacity":
                st.plotly_chart(px.bar(answer_df, x="provider_name", y="monthly_provider_utilization_pct", color="clinic_name", title="Provider Capacity Utilization Proxy"), use_container_width=True)
            elif chart_type == "bar_segment":
                answer_df["segment"] = answer_df["age_group"].astype(str) + " | " + answer_df["insurance_type"].astype(str) + " | " + answer_df["visit_mode"].astype(str)
                st.plotly_chart(px.bar(answer_df, x="segment", y="completion_rate_pct", title="Lowest Completion Segments"), use_container_width=True)
            elif chart_type == "bar_action":
                st.plotly_chart(px.bar(answer_df, x="entity_name", y="priority_score", color="entity_type", title="Operational Actions by Priority Score"), use_container_width=True)
            st.dataframe(answer_df, use_container_width=True)

with tab9:
    st.subheader("Settings & Scenario Lab")
    st.markdown(
        """
        Use this page to show recruiters that the dashboard is not static. Users can change assumptions and immediately see how operational priorities change.
        """
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aging threshold", f">{aging_threshold_days} days")
    c2.metric("High lag threshold", f">={high_lag_threshold_days} days")
    c3.metric("High no-show threshold", f">={high_no_show_threshold_pct}%")
    c4.metric("High capacity threshold", f">={high_capacity_threshold_pct}%")

    st.markdown("#### Scenario 1: Outreach Impact Simulator")
    st.caption("Estimate how many no-show appointments could be recovered if reminder/outreach workflows reduced no-shows. This is an operational planning estimate, not a clinical prediction.")
    outreach_reduction_pct = st.slider("Assumed no-show reduction from outreach (%)", 0, 50, 10)
    no_show_count = int(current_metrics.get("no_show_appointments", 0))
    recovered_appointments = round(no_show_count * outreach_reduction_pct / 100)
    new_no_show_count = max(no_show_count - recovered_appointments, 0)
    new_completion_count = int(current_metrics.get("completed_appointments", 0)) + recovered_appointments
    total_appointments = int(current_metrics.get("total_appointments", 0))

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Current no-shows", f"{no_show_count:,}")
    s2.metric("Potential recovered visits", f"{recovered_appointments:,}")
    s3.metric("Scenario no-show rate", f"{pct(new_no_show_count, total_appointments):.1f}%")
    s4.metric("Scenario completion rate", f"{pct(new_completion_count, total_appointments):.1f}%")

    st.markdown("#### Scenario 2: Intake Capacity Simulator")
    additional_slots_per_clinic_week = st.slider("Additional intake slots per selected clinic per week", 0, 30, 5)
    selected_clinic_count = len(selected_clinics)
    added_monthly_slots = additional_slots_per_clinic_week * selected_clinic_count * 4
    backlog = int(current_metrics.get("open_referrals_over_threshold", 0))
    potential_backlog_coverage = min(backlog, added_monthly_slots)

    c1, c2, c3 = st.columns(3)
    c1.metric("Added monthly slots", f"{added_monthly_slots:,}")
    c2.metric(f"Open referrals >{aging_threshold_days} days", f"{backlog:,}")
    c3.metric("Potential backlog coverage", f"{potential_backlog_coverage:,}")

    st.markdown("#### Current Dynamic Action Queue")
    if action_df_dynamic.empty:
        st.info("No actions currently cross your selected thresholds.")
    else:
        st.dataframe(action_df_dynamic, use_container_width=True)

    st.markdown("#### Current Custom Weights")
    weights_df = pd.DataFrame([
        {"score": "Clinic Attention", "component": "Lag", "weight": clinic_lag_weight},
        {"score": "Clinic Attention", "component": "No-show", "weight": clinic_no_show_weight},
        {"score": "Clinic Attention", "component": "Open aging", "weight": clinic_open_aging_weight},
        {"score": "Clinic Attention", "component": "Capacity", "weight": clinic_capacity_weight},
        {"score": "ZIP Friction", "component": "Lag", "weight": zip_lag_weight},
        {"score": "ZIP Friction", "component": "No-show", "weight": zip_no_show_weight},
        {"score": "ZIP Friction", "component": "Transportation", "weight": zip_transportation_weight},
        {"score": "ZIP Friction", "component": "Underinsured", "weight": zip_underinsured_weight},
        {"score": "ZIP Friction", "component": "Limited English", "weight": zip_language_weight},
        {"score": "ZIP Friction", "component": "Open aging", "weight": zip_open_aging_weight},
        {"score": "ZIP Friction", "component": "Low telehealth", "weight": zip_telehealth_weight},
    ])
    weights_df["weight_pct"] = (100 * weights_df["weight"]).round(1)
    st.dataframe(weights_df, use_container_width=True)
