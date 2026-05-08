# Stage 5 Interactivity Notes

## New Feature: Executive Summary Time Period Controls

Stage 5 adds a time-period selector to the sidebar so users can switch the Executive Overview and Access Trends chart between:

- Weekly
- Monthly
- Yearly
- Custom dates

## How It Works

### Weekly

Uses the last 12 weeks of appointment-linked operational data and groups the trend chart by week.

### Monthly

Uses the last 12 months of appointment-linked operational data and groups the trend chart by month.

### Yearly

Uses the full available synthetic dataset and groups the trend chart by year.

### Custom Dates

Allows the user to choose any date range within the available dataset. The user can also choose the custom trend grouping:

- Daily
- Weekly
- Monthly
- Yearly

## Why This Matters

This makes the application more interactive and realistic for healthcare operations leaders. Users can compare short-term access issues, monthly operational trends, yearly performance patterns, or custom reporting windows.

## Safety and Analytics Boundary

The date-period controls only change aggregated operational metrics. They do not expose raw patient-level PHI and do not change the responsible AI boundary.
