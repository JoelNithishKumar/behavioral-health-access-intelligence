import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config import SYNTHETIC_DIR

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

N_PATIENTS = 5000
N_REFERRALS = 7500
N_PROVIDERS = 25
N_CLINICS = 8
N_DEPARTMENTS = 10

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 4, 30)


def random_date(start: datetime = START_DATE, end: datetime = END_DATE) -> datetime:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def clamp(value, low, high):
    return max(low, min(high, value))


def make_departments() -> pd.DataFrame:
    names = [
        "Behavioral Health",
        "Primary Care",
        "Psychiatry",
        "Psychology",
        "Social Work",
        "Internal Medicine",
        "Pediatrics",
        "Women’s Health",
        "Emergency Medicine",
        "Care Navigation",
    ]
    return pd.DataFrame({
        "department_id": [f"DEPT{i:03d}" for i in range(1, N_DEPARTMENTS + 1)],
        "department_name": names,
        "service_line": ["Behavioral Health" if n in ["Behavioral Health", "Psychiatry", "Psychology", "Social Work"] else "Medical" for n in names],
    })


def make_clinics() -> pd.DataFrame:
    groups = ["North", "North", "Central", "Central", "West", "West", "South", "South"]
    names = [
        "North Behavioral Health Center",
        "Lakeview Integrated Care",
        "Central Psychiatry Clinic",
        "Downtown Access Clinic",
        "Westside Behavioral Health",
        "Austin Community Clinic",
        "South Behavioral Health Center",
        "Hyde Park Integrated Care",
    ]
    return pd.DataFrame({
        "clinic_id": [f"CLINIC{i:03d}" for i in range(1, N_CLINICS + 1)],
        "clinic_name": names,
        "clinic_group": groups,
        "city": ["Chicago"] * N_CLINICS,
        "weekly_intake_slot_capacity": [80, 65, 95, 75, 60, 55, 70, 85],
    })


def make_zip_codes() -> pd.DataFrame:
    zip_codes = ["60601", "60602", "60603", "60604", "60605", "60606", "60607", "60608", "60609", "60610", 
                 "60611", "60612", "60613", "60614", "60615", "60616", "60617", "60618", "60619", "60620"]
    records = []
    for z in zip_codes:
        base = random.random()
        records.append({
            "zip_code": z,
            "area_name": f"Chicago ZIP {z}",
            "transportation_risk_rate": round(clamp(np.random.beta(2, 5) + base * 0.10, 0.03, 0.65), 3),
            "underinsured_rate": round(clamp(np.random.beta(2, 6) + base * 0.08, 0.02, 0.55), 3),
            "limited_english_rate": round(clamp(np.random.beta(2, 8) + base * 0.05, 0.01, 0.40), 3),
            "telehealth_adoption_rate": round(clamp(np.random.beta(5, 3) - base * 0.08, 0.20, 0.95), 3),
        })
    return pd.DataFrame(records)


def make_patients(zip_df: pd.DataFrame) -> pd.DataFrame:
    age_groups = ["0-17", "18-25", "26-40", "41-64", "65+"]
    insurance_types = ["Commercial", "Medicaid", "Medicare", "Self-Pay", "Uninsured"]
    languages = ["English", "Spanish", "Polish", "Mandarin", "Arabic", "Other"]
    genders = ["Female", "Male", "Nonbinary", "Unknown"]
    race_ethnicities = ["Asian", "Black", "Hispanic/Latino", "White", "Multiracial", "Other", "Unknown"]

    records = []
    for i in range(1, N_PATIENTS + 1):
        zip_row = zip_df.sample(1).iloc[0]
        insurance = np.random.choice(insurance_types, p=[0.48, 0.24, 0.14, 0.08, 0.06])
        lang = np.random.choice(languages, p=[0.74, 0.15, 0.03, 0.03, 0.02, 0.03])
        transportation_flag = np.random.rand() < zip_row["transportation_risk_rate"]
        prior_no_show = np.random.poisson(0.6 + 1.2 * int(transportation_flag) + 0.6 * int(insurance in ["Medicaid", "Self-Pay", "Uninsured"]))
        records.append({
            "patient_id": f"PAT{i:06d}",
            "age_group": np.random.choice(age_groups, p=[0.12, 0.18, 0.30, 0.28, 0.12]),
            "gender": np.random.choice(genders, p=[0.53, 0.43, 0.02, 0.02]),
            "race_ethnicity": np.random.choice(race_ethnicities, p=[0.08, 0.24, 0.23, 0.32, 0.04, 0.04, 0.05]),
            "preferred_language": lang,
            "insurance_type": insurance,
            "zip_code": zip_row["zip_code"],
            "transportation_risk_flag": bool(transportation_flag),
            "prior_no_show_count": int(clamp(prior_no_show, 0, 8)),
            "chronic_condition_flag": bool(np.random.rand() < 0.28),
            "behavioral_health_screening_score": int(clamp(round(np.random.normal(9, 5)), 0, 27)),
            "created_at": random_date(datetime(2024, 1, 1), datetime(2025, 12, 31)).date(),
        })
    return pd.DataFrame(records)


def make_providers(clinic_df: pd.DataFrame, dept_df: pd.DataFrame) -> pd.DataFrame:
    bh_depts = dept_df[dept_df["service_line"] == "Behavioral Health"]["department_id"].tolist()
    records = []
    for i in range(1, N_PROVIDERS + 1):
        clinic = clinic_df.sample(1).iloc[0]
        dept_id = random.choice(bh_depts)
        records.append({
            "provider_id": f"PROV{i:03d}",
            "provider_name": f"Provider {i:03d}",
            "clinic_id": clinic["clinic_id"],
            "department_id": dept_id,
            "provider_type": np.random.choice(["Psychiatrist", "Psychologist", "Therapist", "Social Worker"], p=[0.18, 0.20, 0.42, 0.20]),
            "weekly_capacity_slots": int(np.random.randint(20, 36)),
            "active_flag": True,
        })
    return pd.DataFrame(records)


def make_referrals(patient_df: pd.DataFrame, dept_df: pd.DataFrame) -> pd.DataFrame:
    source_depts = dept_df[dept_df["department_name"].isin(["Primary Care", "Internal Medicine", "Pediatrics", "Women’s Health", "Emergency Medicine"])]
    target_depts = dept_df[dept_df["service_line"] == "Behavioral Health"]
    reasons = ["Anxiety", "Depression", "Substance Use", "Care Navigation", "Medication Evaluation", "Therapy Intake", "Crisis Follow-up"]
    records = []
    for i in range(1, N_REFERRALS + 1):
        patient = patient_df.sample(1).iloc[0]
        created = random_date()
        priority = np.random.choice(["routine", "urgent", "high"], p=[0.72, 0.20, 0.08])
        review_lag = int(clamp(np.random.gamma(2.0, 2.0) - (2 if priority == "urgent" else 0), 0, 21))
        reviewed = created + timedelta(days=review_lag)
        open_prob = 0.16 if priority == "routine" else 0.10
        status = np.random.choice(["open", "closed"], p=[open_prob, 1-open_prob])
        closed_date = None
        closure_reason = None
        if status == "closed":
            closed_date = reviewed + timedelta(days=int(clamp(np.random.gamma(3, 5), 1, 90)))
            closure_reason = np.random.choice(["appointment_completed", "patient_declined", "unable_to_contact", "referred_elsewhere", "administrative_closure"], p=[0.70, 0.08, 0.10, 0.07, 0.05])
        records.append({
            "referral_id": f"REF{i:06d}",
            "patient_id": patient["patient_id"],
            "referring_department_id": source_depts.sample(1).iloc[0]["department_id"],
            "referred_to_department_id": target_depts.sample(1).iloc[0]["department_id"],
            "referral_reason": np.random.choice(reasons, p=[0.24, 0.24, 0.12, 0.10, 0.10, 0.16, 0.04]),
            "referral_priority": priority,
            "referral_created_date": created.date(),
            "referral_reviewed_date": reviewed.date(),
            "referral_status": status,
            "referral_closed_date": closed_date.date() if closed_date else None,
            "closure_reason": closure_reason,
        })
    return pd.DataFrame(records)


def make_appointments(referral_df: pd.DataFrame, patient_df: pd.DataFrame, provider_df: pd.DataFrame, clinic_df: pd.DataFrame, zip_df: pd.DataFrame) -> pd.DataFrame:
    # Schedule roughly 80% of referrals.
    scheduled_referrals = referral_df.sample(frac=0.80, random_state=SEED).copy()
    records = []
    for idx, ref in scheduled_referrals.reset_index(drop=True).iterrows():
        patient = patient_df.loc[patient_df["patient_id"] == ref["patient_id"]].iloc[0]
        zip_row = zip_df.loc[zip_df["zip_code"] == patient["zip_code"]].iloc[0]
        clinic = clinic_df.sample(1).iloc[0]
        providers = provider_df[provider_df["clinic_id"] == clinic["clinic_id"]]
        provider = providers.sample(1).iloc[0] if len(providers) else provider_df.sample(1).iloc[0]

        reviewed = pd.to_datetime(ref["referral_reviewed_date"])
        priority = ref["referral_priority"]
        scheduled_lag = int(clamp(np.random.gamma(2, 3) - (2 if priority != "routine" else 0), 0, 30))
        appointment_wait = int(clamp(np.random.gamma(3, 6) + clinic["weekly_intake_slot_capacity"] / -20 + zip_row["transportation_risk_rate"] * 8, 2, 75))
        scheduled_date = reviewed + timedelta(days=scheduled_lag)
        appointment_date = scheduled_date + timedelta(days=appointment_wait)

        visit_mode = np.random.choice(["telehealth", "in_person"], p=[zip_row["telehealth_adoption_rate"], 1 - zip_row["telehealth_adoption_rate"]])
        no_show_logit = (
            -2.2
            + 0.35 * patient["prior_no_show_count"]
            + 0.55 * int(patient["transportation_risk_flag"])
            + 0.35 * int(patient["insurance_type"] in ["Medicaid", "Self-Pay", "Uninsured"])
            + 0.02 * appointment_wait
            - 0.35 * int(visit_mode == "telehealth")
        )
        no_show_prob = 1 / (1 + np.exp(-no_show_logit))
        cancel_prob = clamp(0.08 + 0.05 * int(appointment_wait > 30), 0.05, 0.22)
        reschedule_prob = clamp(0.07 + 0.04 * int(appointment_wait > 30), 0.04, 0.18)
        r = np.random.rand()
        if r < no_show_prob:
            status = "no_show"
        elif r < no_show_prob + cancel_prob:
            status = "canceled"
        elif r < no_show_prob + cancel_prob + reschedule_prob:
            status = "rescheduled"
        else:
            status = "completed"

        records.append({
            "appointment_id": f"APT{idx+1:06d}",
            "referral_id": ref["referral_id"],
            "patient_id": patient["patient_id"],
            "clinic_id": clinic["clinic_id"],
            "provider_id": provider["provider_id"],
            "appointment_scheduled_date": scheduled_date.date(),
            "appointment_date": appointment_date.date(),
            "appointment_status": status,
            "appointment_type": np.random.choice(["new_patient", "follow_up", "medication_management", "therapy_intake"], p=[0.45, 0.25, 0.15, 0.15]),
            "visit_mode": visit_mode,
            "cancellation_reason": np.random.choice(["patient_request", "provider_unavailable", "insurance_issue", "transportation", None], p=[0.35, 0.20, 0.15, 0.10, 0.20]) if status == "canceled" else None,
        })
    return pd.DataFrame(records)


def make_screenings(referral_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sample_refs = referral_df.sample(frac=0.70, random_state=SEED)
    for i, ref in enumerate(sample_refs.itertuples(index=False), start=1):
        created = pd.to_datetime(ref.referral_created_date)
        rows.append({
            "screening_id": f"SCR{i:06d}",
            "patient_id": ref.patient_id,
            "referral_id": ref.referral_id,
            "screening_date": (created - timedelta(days=random.randint(0, 14))).date(),
            "screening_score": int(clamp(round(np.random.normal(10, 5)), 0, 27)),
            "positive_screen_flag": bool(np.random.rand() < 0.58),
        })
    return pd.DataFrame(rows)


def make_encounters(appointment_df: pd.DataFrame) -> pd.DataFrame:
    completed = appointment_df[appointment_df["appointment_status"] == "completed"].copy()
    rows = []
    for i, appt in enumerate(completed.itertuples(index=False), start=1):
        rows.append({
            "encounter_id": f"ENC{i:06d}",
            "appointment_id": appt.appointment_id,
            "patient_id": appt.patient_id,
            "provider_id": appt.provider_id,
            "clinic_id": appt.clinic_id,
            "encounter_date": appt.appointment_date,
            "encounter_status": "completed",
        })
    return pd.DataFrame(rows)


def make_followups(encounter_df: pd.DataFrame) -> pd.DataFrame:
    sample_enc = encounter_df.sample(frac=0.72, random_state=SEED) if len(encounter_df) else encounter_df
    rows = []
    for i, enc in enumerate(sample_enc.itertuples(index=False), start=1):
        enc_date = pd.to_datetime(enc.encounter_date)
        rows.append({
            "followup_id": f"FUP{i:06d}",
            "encounter_id": enc.encounter_id,
            "patient_id": enc.patient_id,
            "followup_due_date": (enc_date + timedelta(days=random.choice([7, 14, 21, 30]))).date(),
            "followup_completed_date": (enc_date + timedelta(days=random.randint(5, 35))).date() if np.random.rand() < 0.78 else None,
            "followup_status": np.random.choice(["completed", "open", "overdue"], p=[0.70, 0.18, 0.12]),
        })
    return pd.DataFrame(rows)


def save(df: pd.DataFrame, name: str) -> None:
    path = SYNTHETIC_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"Saved {path} ({len(df):,} rows)")


def main() -> None:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    departments = make_departments()
    clinics = make_clinics()
    zips = make_zip_codes()
    patients = make_patients(zips)
    providers = make_providers(clinics, departments)
    referrals = make_referrals(patients, departments)
    appointments = make_appointments(referrals, patients, providers, clinics, zips)
    screenings = make_screenings(referrals)
    encounters = make_encounters(appointments)
    followups = make_followups(encounters)

    for name, df in {
        "dim_department": departments,
        "dim_clinic": clinics,
        "dim_zip_code": zips,
        "dim_patient": patients,
        "dim_provider": providers,
        "fact_referral": referrals,
        "fact_appointment": appointments,
        "fact_screening": screenings,
        "fact_encounter": encounters,
        "fact_followup": followups,
    }.items():
        save(df, name)

    print("Synthetic healthcare operations data generation complete.")


if __name__ == "__main__":
    main()
