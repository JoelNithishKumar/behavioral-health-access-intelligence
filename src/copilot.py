import json
import os

try:
    from openai import OpenAI
except Exception:  # OpenAI is optional for the app's fallback mode.
    OpenAI = None

SYSTEM_PROMPT = """
You are an analytics copilot for a healthcare operations team.

You are not a clinician.
Do not diagnose, treat, or provide medical advice.
Only summarize operational analytics metrics.

Use only the structured data provided below.
Do not invent numbers.
If the data is insufficient, say so.
"""


def generate_rule_based_summary(metrics: dict) -> str:
    total_referrals = metrics.get("total_referrals", "unknown")
    median_lag = metrics.get("median_referral_to_appointment_days", "unknown")
    completion = metrics.get("completion_rate_pct", "unknown")
    no_show = metrics.get("no_show_rate_pct", "unknown")
    open_21 = metrics.get("open_referrals_over_21_days", "unknown")
    worst_clinic = metrics.get("clinic_needing_attention", "insufficient clinic data")
    dq_score = metrics.get("data_quality_score_pct", "unknown")

    return f"""### Executive Summary
Behavioral health access performance was reviewed using structured operational metrics only. The dashboard currently shows {total_referrals} total referrals, a median referral-to-appointment lag of {median_lag} days, an appointment completion rate of {completion}%, and a no-show rate of {no_show}%.

### Key Changes
Trend comparison requires a configured prior-period metric extract. Current-period open referrals over 21 days: {open_21}.

### Clinics Needing Attention
The clinic most needing operational review is: {worst_clinic}.

### Possible Operational Drivers
Potential operational drivers include referral backlog, intake slot availability, appointment wait time, no-show patterns, and ZIP-code access friction. These are operational hypotheses based on aggregated metrics, not clinical conclusions.

### Recommended Operational Actions
1. Review open referrals older than 21 days.
2. Check intake slot capacity for clinics with high referral lag.
3. Prioritize reminder outreach for high no-show-risk appointment segments.
4. Evaluate telehealth scheduling options for ZIP codes with high access friction.

### Data Quality Caveats
Current data quality score: {dq_score}%. Interpret metrics cautiously if critical data quality rules are failing.
"""


def generate_access_summary(metrics: dict) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return generate_rule_based_summary(metrics)

    client = OpenAI(api_key=api_key)
    user_prompt = f"""
Task:
Generate an executive summary of behavioral health access performance.

Metrics:
{json.dumps(metrics, indent=2)}

Required output:
1. Executive summary
2. Key changes
3. Clinics needing attention
4. Possible operational drivers
5. Recommended operational actions
6. Data quality caveats
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
