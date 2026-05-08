from datetime import datetime

import duckdb
import pandas as pd


def _count(conn: duckdb.DuckDBPyConnection, query: str) -> int:
    return int(conn.execute(query).fetchone()[0])


def run_data_quality_checks(db_path: str) -> pd.DataFrame:
    conn = duckdb.connect(str(db_path))

    checks = [
        ("DQ001", "patient_id cannot be null", "dim_patient", "critical", "SELECT COUNT(*) FROM dim_patient WHERE patient_id IS NULL"),
        ("DQ002", "referral_id cannot be null", "fact_referral", "critical", "SELECT COUNT(*) FROM fact_referral WHERE referral_id IS NULL"),
        ("DQ003", "appointment_id cannot be null", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment WHERE appointment_id IS NULL"),
        ("DQ004", "referral_created_date must be before referral_reviewed_date", "fact_referral", "critical", "SELECT COUNT(*) FROM fact_referral WHERE referral_reviewed_date IS NOT NULL AND referral_created_date > referral_reviewed_date"),
        ("DQ005", "referral_created_date must be before appointment_date", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a JOIN fact_referral r ON a.referral_id = r.referral_id WHERE r.referral_created_date > a.appointment_date"),
        ("DQ006", "appointment_date cannot be in impossible past or future", "fact_appointment", "warning", "SELECT COUNT(*) FROM fact_appointment WHERE appointment_date < DATE '2020-01-01' OR appointment_date > CURRENT_DATE + INTERVAL 365 DAY"),
        ("DQ007", "appointment_status must be valid", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment WHERE appointment_status NOT IN ('scheduled', 'completed', 'canceled', 'no_show', 'rescheduled')"),
        ("DQ008", "visit_mode must be valid", "fact_appointment", "warning", "SELECT COUNT(*) FROM fact_appointment WHERE visit_mode NOT IN ('in_person', 'telehealth')"),
        ("DQ009", "completed appointments should have encounters", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a LEFT JOIN fact_encounter e ON a.appointment_id = e.appointment_id WHERE a.appointment_status = 'completed' AND e.encounter_id IS NULL"),
        ("DQ010", "no-show appointments should not have completed encounters", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a JOIN fact_encounter e ON a.appointment_id = e.appointment_id WHERE a.appointment_status = 'no_show'"),
        ("DQ011", "closed referrals should have completion or closure reason", "fact_referral", "warning", "SELECT COUNT(*) FROM fact_referral WHERE referral_status = 'closed' AND closure_reason IS NULL"),
        ("DQ012", "ZIP code should be valid", "dim_patient", "warning", "SELECT COUNT(*) FROM dim_patient p LEFT JOIN dim_zip_code z ON p.zip_code = z.zip_code WHERE z.zip_code IS NULL"),
        ("DQ013", "provider_id should exist in dim_provider", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a LEFT JOIN dim_provider p ON a.provider_id = p.provider_id WHERE p.provider_id IS NULL"),
        ("DQ014", "clinic_id should exist in dim_clinic", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a LEFT JOIN dim_clinic c ON a.clinic_id = c.clinic_id WHERE c.clinic_id IS NULL"),
        ("DQ015", "appointment referral_id should exist in fact_referral", "fact_appointment", "critical", "SELECT COUNT(*) FROM fact_appointment a LEFT JOIN fact_referral r ON a.referral_id = r.referral_id WHERE r.referral_id IS NULL"),
    ]

    rows = []
    now = datetime.now()
    for rule_id, rule_name, table_name, severity, query in checks:
        failed = _count(conn, query)
        rows.append({
            "rule_id": rule_id,
            "rule_name": rule_name,
            "table_name": table_name,
            "severity": severity,
            "failed_row_count": failed,
            "status": "pass" if failed == 0 else "fail",
            "checked_at": now,
        })

    df = pd.DataFrame(rows)
    conn.execute("DROP TABLE IF EXISTS fact_data_quality_issue")
    conn.register("dq_df", df)
    conn.execute("CREATE TABLE fact_data_quality_issue AS SELECT * FROM dq_df")
    conn.close()
    return df
