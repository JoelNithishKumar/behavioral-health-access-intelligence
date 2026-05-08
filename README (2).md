# Behavioral Health Access Intelligence Platform

An AI-assisted healthcare operations analytics platform for monitoring behavioral health referral lag, appointment access, no-show risk, ZIP-code access friction, clinic capacity, and data quality using synthetic EHR-style data.

> **No PHI. No real patient data. No clinical advice. Synthetic data only.**

---

## Project Overview

The **Behavioral Health Access Intelligence Platform** is a healthcare operations analytics project designed to simulate how a health system analytics team could monitor behavioral health access bottlenecks across the referral-to-appointment journey.

Behavioral health access is a major operational challenge for healthcare systems. Patients may be referred for behavioral health services, but delays can occur between referral creation, review, scheduling, first appointment completion, and follow-up care.

This project turns synthetic healthcare operations data into a structured analytics product that helps teams answer questions such as:

- Which clinics have the highest referral-to-appointment lag?
- Which clinics improved or worsened over the last reporting period?
- How many referrals are still open after 21 days?
- Where are patients dropping off in the referral funnel?
- Which ZIP codes have the highest access friction?
- Which appointment types have the highest no-show rate?
- Are telehealth visits associated with lower no-show rates?
- Which clinics or providers may have capacity constraints?
- Which patient segments are least likely to complete a first appointment?
- What operational actions should leadership prioritize this week?

The project combines **SQL analytics, Python ETL, data quality validation, dashboarding, predictive modeling, and responsible AI summarization** into one portfolio-grade healthcare analytics application.

---

## Real-World Problem This Project Solves

In many healthcare operations settings, referral and access data can be spread across multiple systems such as EHRs, scheduling platforms, referral management systems, encounter records, and reporting tools.

This creates several operational challenges:

1. **Referral delays are hard to monitor consistently**
   - Teams may not know which clinics have the longest referral-to-appointment lag.
   - Aging open referrals may go unnoticed without structured reporting.

2. **No-shows and cancellations reduce access efficiency**
   - High no-show rates can waste appointment capacity.
   - Operations teams need to identify patterns by visit mode, appointment type, ZIP code, clinic, and patient segment.

3. **Referral funnel leakage is difficult to diagnose**
   - Patients may drop off between referral creation, review, scheduling, appointment completion, and follow-up.
   - Leaders need a clear funnel view to understand where the process is breaking down.

4. **Access friction varies by community**
   - Transportation barriers, insurance type, language preference, and telehealth usage can affect access.
   - ZIP-code-level analysis helps operations teams identify communities that may need targeted outreach or scheduling support.

5. **Data quality issues reduce trust in reporting**
   - Missing IDs, invalid appointment statuses, impossible dates, and orphaned records can distort analytics.
   - A data quality monitor helps identify whether metrics are reliable.

6. **Executive reporting is often manual**
   - Analysts may spend hours pulling SQL queries, exporting spreadsheets, building charts, and writing weekly summaries.
   - This platform automates much of that workflow.

---

## Estimated Time Savings

This project is built with synthetic data, so the time savings below are **estimated based on a simulated healthcare operations reporting workflow**. They are not production-validated claims.

| Workflow | Manual Process Estimate | Platform-Assisted Estimate | Potential Time Saved |
|---|---:|---:|---:|
| Weekly access performance summary | 3–5 hours | 5–10 minutes | 2.5–4.8 hours/week |
| Clinic referral lag analysis | 1–2 hours | <5 minutes | 1–2 hours/week |
| Open referral aging review | 1–2 hours | <5 minutes | 1–2 hours/week |
| No-show pattern analysis | 2–4 hours | 10–15 minutes | 1.75–3.75 hours/week |
| ZIP/access friction analysis | 2–3 hours | 10 minutes | 1.8–2.8 hours/week |
| Data quality checks | 2–3 hours | Automated | 2–3 hours/week |
| Executive summary drafting | 1–2 hours | 5–10 minutes | 0.8–1.8 hours/week |

### Estimated Total Savings

For a small analytics or operations team, this type of platform could potentially save:

```text
8–15 hours per week
30–60 hours per month
```

The biggest savings come from automating repetitive SQL pulls, manual spreadsheet review, data quality checks, dashboard updates, and executive summary drafting.

---

## Key Features

### 1. Executive Overview

The executive dashboard provides high-level visibility into behavioral health access performance.

Key metrics include:

- Total behavioral health referrals
- Median referral-to-appointment lag
- Appointment completion rate
- No-show rate
- Open referrals older than selected threshold
- Average access friction score
- Prior-period KPI comparison
- Weekly, monthly, yearly, or custom trend views

Users can switch the executive summary period between:

- Weekly
- Monthly
- Yearly
- Custom dates

For custom date ranges, users can group trends by:

- Daily
- Weekly
- Monthly
- Yearly

---

### 2. Referral Funnel

The referral funnel tracks the behavioral health access journey:

```text
Referral Created
→ Referral Reviewed
→ Appointment Scheduled
→ Appointment Completed
→ Follow-Up Completed
```

This helps identify where patients are dropping off in the process.

Example funnel questions:

- How many referrals were created?
- How many were reviewed?
- How many were scheduled?
- How many resulted in completed appointments?
- How many completed follow-up care?

---

### 3. Clinic Performance Analytics

The clinic performance page compares clinics across operational access metrics.

Metrics include:

- Referral volume
- Median referral-to-appointment lag
- Appointment completion rate
- No-show rate
- Open referrals over threshold
- Capacity utilization proxy
- Clinic Attention Index

The **Clinic Attention Index** ranks clinics based on a weighted combination of:

- Referral lag
- No-show rate
- Open referral aging
- Capacity utilization

Users can adjust the weights interactively.

---

### 4. ZIP-Code Access Friction Analysis

The platform calculates an **Access Friction Score** to identify ZIP codes that may face greater operational access barriers.

The score uses factors such as:

- Median referral lag
- No-show rate
- Transportation risk proxy
- Underinsured/uninsured proxy
- Limited English preference proxy
- Open referral aging
- Low telehealth usage

This is not a clinical risk score. It is an operational prioritization metric.

---

### 5. No-Show Risk Model

The project includes a supervised machine learning model that estimates appointment no-show probability for operational outreach prioritization.

Features include:

- Days from referral to appointment
- Days from scheduling to appointment
- Prior no-show count
- Appointment type
- Visit mode
- Insurance type
- Age group
- Transportation risk flag
- ZIP access friction score
- Clinic ID
- Referral priority

Model evaluation includes:

- Accuracy
- Precision
- Recall
- F1 score
- ROC-AUC
- Confusion matrix

> The model is for operational outreach prioritization only. It does not diagnose, treat, determine eligibility, or make clinical decisions.

---

### 6. Data Quality Monitor

The platform includes a data quality layer that validates whether analytics outputs can be trusted.

Example checks include:

- `patient_id` cannot be null
- `referral_id` cannot be null
- `appointment_id` cannot be null
- Referral created date must be before reviewed date
- Referral created date must be before appointment date
- Appointment date cannot be in an impossible past or future
- Appointment status must be valid
- Visit mode must be valid
- Completed appointments should have encounters
- No-show appointments should not have completed encounters
- Closed referrals should have either completion or closure reason
- ZIP code should be valid
- Provider ID should exist in provider dimension
- Clinic ID should exist in clinic dimension
- Source and target row counts should match

The dashboard displays:

- Overall data quality score
- Critical issue count
- Warning issue count
- Failed checks by table
- Most common data quality failures

---

### 7. AI Copilot

The AI copilot generates executive-facing operational summaries from structured analytics metrics.

The AI can summarize:

- Referral lag trends
- Clinic bottlenecks
- No-show patterns
- Open referral aging
- ZIP-code access friction
- Data quality caveats
- Recommended operational actions

The AI does **not** read unrestricted raw patient data. It receives structured metrics from predefined SQL views.

Example output sections:

1. Executive summary
2. Key changes
3. Clinics needing attention
4. Possible operational drivers
5. Recommended operational actions
6. Data quality caveats

---

### 8. Ask the Data

The platform includes a controlled natural language analytics interface.

Users can ask questions such as:

- Which clinics have the highest median referral-to-appointment lag?
- Which clinics improved access over the last 30 days?
- How many referrals are open after 21 days?
- Where are patients dropping off in the referral funnel?
- Which ZIP codes have the highest access friction score?
- Are telehealth appointments associated with lower no-show rates?
- Which providers or clinics have capacity constraints?
- What operational actions should leadership prioritize this week?

This feature does not allow unrestricted SQL generation. Instead, questions are routed to predefined analytics functions and approved SQL views.

---

### 9. Settings & Scenario Lab

The project includes interactive settings and scenario analysis.

Users can change:

- Open referral aging threshold
- High median lag threshold
- High no-show threshold
- Capacity utilization threshold
- Access friction threshold
- Minimum patient segment volume
- Clinic Attention Index weights
- ZIP Access Friction Score weights

Scenario tools include:

- No-show outreach impact simulator
- Intake capacity simulator

Example scenario questions:

- If reminder outreach reduces no-shows by 10%, how many appointments could potentially be recovered?
- If each selected clinic adds 5 intake slots per week, how much aging referral backlog could be addressed?

---

## Project Screenshots

Add your screenshots to `artifacts/screenshots/` using the filenames below.

### Executive Overview

![Executive Overview](artifacts/screenshots/01_executive_overview.png)

### Referral Funnel

![Referral Funnel](artifacts/screenshots/02_referral_funnel.png)

### Clinic Performance

![Clinic Performance](artifacts/screenshots/03_clinic_performance.png)

### ZIP Access Friction

![ZIP Access Friction](artifacts/screenshots/04_zip_access_friction.png)

### No-Show Risk

![No-Show Risk](artifacts/screenshots/05_no_show_risk.png)

### Data Quality Monitor

![Data Quality Monitor](artifacts/screenshots/06_data_quality_monitor.png)

### AI Copilot

![AI Copilot](artifacts/screenshots/07_ai_copilot.png)

### Ask the Data

![Ask the Data](artifacts/screenshots/08_ask_the_data.png)

### Settings & Scenario Lab

![Settings Scenario Lab](artifacts/screenshots/09_settings_scenario_lab.png)

---

## Tech Stack

| Area | Tools |
|---|---|
| Programming | Python |
| Data Processing | Pandas, NumPy |
| Analytics Database | DuckDB |
| Query Layer | SQL |
| Dashboard | Streamlit |
| Visualization | Plotly |
| Machine Learning | scikit-learn |
| Model Persistence | joblib |
| AI Copilot | OpenAI API optional |
| Environment Management | python-dotenv |
| Documentation | Markdown |

---

## Architecture

```text
Synthetic Data Generator
        ↓
Synthetic CSV Data
        ↓
DuckDB Analytics Warehouse
        ↓
SQL Views / Data Mart
        ↓
Streamlit Dashboard
        ↓
AI Copilot + Ask the Data + Scenario Lab
```

### Detailed Flow

```text
1. Generate synthetic patients, referrals, appointments, encounters, follow-ups, clinics, providers, and ZIP indicators
2. Load data into DuckDB warehouse
3. Build SQL views for access metrics, clinic performance, no-show rates, referral aging, and data quality
4. Train no-show prediction model
5. Display insights in Streamlit dashboard
6. Allow users to ask controlled analytics questions
7. Generate responsible AI summaries from structured metrics
```

---

## Data Model

### Dimension Tables

```text
dim_patient
dim_provider
dim_clinic
dim_department
dim_zip_code
dim_date
```

### Fact Tables

```text
fact_referral
fact_appointment
fact_screening
fact_encounter
fact_followup
fact_data_quality_issue
```

### Analytics Views

```text
vw_referral_lag_summary
vw_appointment_completion_summary
vw_no_show_summary
vw_clinic_access_performance
vw_zip_access_friction
vw_open_referral_aging
vw_behavioral_health_funnel
vw_provider_capacity_summary
vw_data_quality_scorecard
vw_weekly_access_trends
vw_clinic_attention_index
vw_patient_segment_completion_gap
vw_operational_action_queue
```

---

## Business Questions Answered

This platform is designed to answer operational questions such as:

```text
Which clinics have the highest median referral-to-appointment lag?
Which clinics have improved access over the last 30 days?
How many behavioral health referrals are still open after 21 days?
Where are patients dropping off in the referral funnel?
Which ZIP codes have the highest access friction score?
Which appointment types have the highest no-show rate?
Are telehealth appointments associated with lower no-show rates?
Which providers or clinics have capacity constraints?
Which patient segments are least likely to complete a first appointment?
What operational actions should leadership prioritize this week?
```

---

## Responsible AI Boundary

This project is not a clinical decision-support system.

The AI copilot:

- Does not diagnose patients
- Does not recommend treatment
- Does not provide therapy
- Does not recommend medication
- Does not determine eligibility for care
- Does not make clinical decisions
- Does not use real PHI

The AI only summarizes structured operational metrics generated from SQL views.

The no-show model is used only for operational outreach prioritization.

---

## Synthetic Data Boundary

This project uses synthetic data only.

It does not contain:

- Real patient names
- Real medical record numbers
- Real addresses
- Real appointment records
- Real diagnoses
- Real clinical notes
- Protected health information

The purpose of the synthetic data is to simulate healthcare operations workflows for analytics development and portfolio demonstration.

---

## How to Run the Project Locally

### 1. Clone the repository

```powershell
git clone https://github.com/YOUR_USERNAME/behavioral-health-access-intelligence.git
cd behavioral-health-access-intelligence
```

### 2. Create a virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Generate synthetic data

```powershell
python src/generate_synthetic_data.py
```

### 5. Load the analytics warehouse

```powershell
python src/load_warehouse.py
```

### 6. Train the no-show model

```powershell
python src/no_show_model.py
```

### 7. Launch the Streamlit app

```powershell
streamlit run app/streamlit_app.py
```

---

## Environment Variables

Create a `.env` file if using the optional AI copilot with OpenAI.

```env
OPENAI_API_KEY=your_api_key_here
```

A sample file is provided:

```text
.env.example
```

The application can still run without an OpenAI API key using the non-generative dashboard and analytics features.

---

## Repository Structure

```text
behavioral-health-access-intelligence/
│
├── app/
│   └── streamlit_app.py
│
├── data/
│   ├── synthetic/
│   └── warehouse/
│
├── docs/
│   ├── data_dictionary.md
│   ├── metric_definitions.md
│   ├── responsible_ai_statement.md
│   ├── project_walkthrough.md
│   ├── screenshot_checklist.md
│   ├── stage4_interactivity_notes.md
│   └── stage5_time_period_controls.md
│
├── models/
│
├── sql/
│   ├── 01_create_schema.sql
│   ├── 02_create_views.sql
│   └── 03_metric_queries.sql
│
├── src/
│   ├── config.py
│   ├── generate_synthetic_data.py
│   ├── load_warehouse.py
│   ├── data_quality.py
│   ├── metrics.py
│   ├── no_show_model.py
│   ├── copilot.py
│   └── utils.py
│
├── artifacts/
│   └── screenshots/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

---

## Skills Demonstrated

This project demonstrates:

- Healthcare operations analytics
- SQL data modeling
- Analytics data mart design
- Python ETL development
- Data quality validation
- Streamlit dashboard development
- KPI design
- Referral funnel analysis
- No-show risk modeling
- ZIP-code access analysis
- Responsible AI design
- Executive summary automation
- Interactive product thinking
- Business-facing documentation

---

## Potential Real-World Use Cases

In a real healthcare setting, a production version of this platform could support:

- Behavioral health access monitoring
- Referral management analytics
- Clinic operations review
- Capacity planning
- No-show outreach prioritization
- Health equity and access analysis
- Data quality governance
- Weekly executive reporting
- Operational improvement planning

---

## Limitations

This is a portfolio project using synthetic data.

Current limitations:

- Not connected to a real EHR
- Not validated on real healthcare operations data
- Not HIPAA-audited
- No production authentication layer
- No live scheduling system integration
- No real clinical workflow integration
- No formal model governance process
- No human-subjects or clinical validation

The project is designed to demonstrate analytics engineering, dashboarding, predictive modeling, and responsible AI product thinking.

---

## Future Enhancements

Potential next steps:

- Add Power BI dashboard version
- Add SQL Server implementation
- Add role-based access control
- Add automated report export to PDF
- Add real-time refresh simulation
- Add appointment reminder workflow simulation
- Add provider-level capacity forecasting
- Add model monitoring dashboard
- Add bias/fairness analysis for no-show model
- Add audit log for AI copilot outputs
- Add Docker deployment
- Deploy Streamlit app publicly

---

## Resume Summary

Built an AI-assisted healthcare operations analytics platform using Python, SQL, DuckDB, Streamlit, and scikit-learn to monitor behavioral health referral lag, appointment access, no-show risk, ZIP-code access friction, provider capacity, and data quality.

Designed reusable SQL views and a synthetic healthcare analytics mart across patients, referrals, appointments, encounters, follow-ups, clinics, providers, and ZIP-code indicators to support executive dashboards and operational reporting.

Developed a no-show prediction model and responsible AI copilot that summarizes structured operational metrics from SQL views, enabling executive summaries, clinic bottleneck alerts, and operational action recommendations without using PHI or providing clinical advice.

---

## Author

**Joel Nithish Kumar Murugan**

AI Product & Operations Strategist  
Focused on healthcare analytics, responsible AI, workflow optimization, and data-driven operational decision-making.
