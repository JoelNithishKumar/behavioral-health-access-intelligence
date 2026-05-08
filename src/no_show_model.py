import json
from pathlib import Path

import duckdb
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import DB_PATH, MODELS_DIR, SYNTHETIC_DIR

FEATURE_QUERY = """
SELECT
    a.appointment_id,
    CASE WHEN a.appointment_status = 'no_show' THEN 1 ELSE 0 END AS no_show_target,
    DATE_DIFF('day', r.referral_created_date, a.appointment_date) AS days_from_referral_to_appointment,
    DATE_DIFF('day', a.appointment_scheduled_date, a.appointment_date) AS days_from_scheduled_to_appointment,
    p.prior_no_show_count,
    a.appointment_type,
    a.visit_mode,
    p.insurance_type,
    p.age_group,
    p.transportation_risk_flag,
    z.access_friction_score AS zip_access_friction_score,
    a.clinic_id,
    r.referral_priority
FROM fact_appointment a
JOIN fact_referral r ON a.referral_id = r.referral_id
JOIN dim_patient p ON a.patient_id = p.patient_id
LEFT JOIN vw_zip_access_friction z ON p.zip_code = z.zip_code
WHERE a.appointment_status IN ('completed', 'no_show', 'canceled', 'rescheduled')
"""


def train_model() -> None:
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(FEATURE_QUERY).fetchdf()
    conn.close()

    if df.empty:
        raise ValueError("No appointment data found. Run the data generator and warehouse loader first.")

    y = df["no_show_target"]
    X = df.drop(columns=["appointment_id", "no_show_target"])

    numeric_features = [
        "days_from_referral_to_appointment",
        "days_from_scheduled_to_appointment",
        "prior_no_show_count",
        "zip_access_friction_score",
    ]
    categorical_features = [
        "appointment_type",
        "visit_mode",
        "insurance_type",
        "age_group",
        "transportation_risk_flag",
        "clinic_id",
        "referral_priority",
    ]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    model = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "model_note": "For operational outreach prioritization only. Not for diagnosis, treatment, eligibility, or clinical decision-making.",
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "no_show_model.pkl")
    (MODELS_DIR / "no_show_metrics.json").write_text(json.dumps(metrics, indent=2))

    all_probs = model.predict_proba(X)[:, 1]
    prediction_df = df[["appointment_id"]].copy()
    prediction_df["predicted_no_show_probability"] = all_probs
    prediction_df["risk_bucket"] = pd.cut(
        prediction_df["predicted_no_show_probability"],
        bins=[-0.01, 0.30, 0.60, 1.01],
        labels=["low", "medium", "high"],
    )
    prediction_df.to_csv(SYNTHETIC_DIR / "no_show_predictions.csv", index=False)

    print("No-show model trained.")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    train_model()
