# Behavioral Health Access Intelligence Platform

An analytics-first healthcare operations project that uses synthetic EHR-style data to monitor behavioral health referral lag, appointment access, no-show risk, ZIP-code access friction, provider capacity, and data quality.

> Safety boundary: This project uses only synthetic data. It does not use PHI. The AI copilot summarizes operational analytics metrics only and does not diagnose, treat, or provide medical advice.

## What this demonstrates

- SQL analytics views and healthcare-style data mart design
- Python ETL and synthetic data generation
- DuckDB warehouse for local analytics development
- Streamlit executive dashboard
- Data quality validation layer
- No-show prediction model for operational outreach prioritization
- Responsible AI copilot layer grounded in structured metrics

## Quickstart

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/generate_synthetic_data.py
python src/load_warehouse.py
python src/no_show_model.py
streamlit run app/streamlit_app.py
```

## Project layout

```text
app/                  Streamlit dashboard
src/                  ETL, data quality, ML, AI copilot logic
sql/                  SQL views and metric queries
data/synthetic/       Generated CSV data
data/warehouse/       DuckDB analytics database
models/               Saved ML model artifacts
docs/                 Documentation
```

## Core SQL views

- `vw_referral_lag_summary`
- `vw_appointment_completion_summary`
- `vw_no_show_summary`
- `vw_clinic_access_performance`
- `vw_zip_access_friction`
- `vw_open_referral_aging`
- `vw_behavioral_health_funnel`
- `vw_provider_capacity_summary`
- `vw_data_quality_scorecard`
