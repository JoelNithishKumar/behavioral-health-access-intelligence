# Stage 4 Interactivity Upgrade Notes

This upgrade adds recruiter-friendly interactivity before publishing the project on GitHub.

## New Features

### 1. Ask the Data

A controlled natural-language analytics panel where users can ask operational questions such as:

- Which clinics have the highest median referral-to-appointment lag?
- Which clinics improved over the last 30 days?
- How many referrals are open after the selected aging threshold?
- Where are patients dropping off in the referral funnel?
- Which ZIP codes have the highest access friction?
- Which appointment types have the highest no-show rate?
- Are telehealth appointments associated with lower no-show rates?
- Which providers or clinics have capacity constraints?
- Which patient segments are least likely to complete a first appointment?
- What actions should leadership prioritize this week?

The Q&A layer does not generate unrestricted SQL. Questions are routed to predefined analytics functions and approved SQL views.

### 2. Interactive Settings

The sidebar now lets users change:

- Open referral aging threshold
- High median lag threshold
- High no-show threshold
- High capacity utilization threshold
- High access friction threshold
- Minimum segment volume
- Clinic Attention Index weights
- ZIP Access Friction weights

These settings update KPIs, prioritization tables, action queues, and scenario outputs.

### 3. Settings & Scenario Lab

This tab includes:

- Current threshold summary
- No-show outreach impact simulator
- Intake capacity simulator
- Dynamic action queue
- Current custom weight table

### 4. Responsible Analytics Boundary

The interactive Q&A is intentionally controlled. It demonstrates analytics product thinking without allowing unrestricted SQL generation or unsafe clinical recommendations.

## Recommended GitHub Screenshots

Add these screenshots to the README:

1. Executive Overview
2. Ask the Data answer with chart
3. Settings & Scenario Lab
4. ZIP Access Friction custom score
5. Dynamic Operational Action Queue
6. AI Copilot structured context
