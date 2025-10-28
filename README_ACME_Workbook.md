# ACME Systems Engineering – Team & Workload Workbook

This Excel workbook is generated from the SAFe 6 organization structure in `save6/SAFe6OrganizationStructure.md`.
It helps oversee the project, track stakeholders, and plan resource workload.

## Files
- `ACME_Project_Team_Workload.xlsx` – The generated workbook
- `tools/generate_acme_workbook.py` – Generator script (Python + openpyxl)

## How to regenerate
```bash
# From repo root
. .venv/bin/activate  # if not already active
python tools/generate_acme_workbook.py
```

### CLI parameters
You can regenerate the workbook without editing the script by passing flags:

```bash
# Examples
python tools/generate_acme_workbook.py --sprints 6 --length 10 --capacity-hours 50

# Fine-grained capacity
python tools/generate_acme_workbook.py \
  --sprints 8 \
  --length 14 \
  --working-days 9 \
  --hours-per-day 7.0

# Custom input/output paths
python tools/generate_acme_workbook.py \
  --markdown save6/SAFe6OrganizationStructure.md \
  --out ACME_Project_Team_Workload.xlsx
```

## Sheets overview
- Project_Info: Project metadata. Update freely.
- Sprints: 8, two-week sprints starting next Monday. Adjust dates if needed.
- Stakeholders: Auto-filled with Portfolio/Large Solution/ART leaders. Add influence, engagement plan, and contacts.
- Organization: Full hierarchy of levels (Portfolio, Large Solution, ART), ARTs, Teams, Roles, and Names.
- Teams: Count of roles per team to help with quick sizing.
- Activities: Backlog template (ID, Title, Team, ART, Assignee, Sprint, Estimate, Status, Priority, Dependency). Includes a few sample rows.
- RACI: Template matrix for common ceremonies and reviews.
- Risks_Issues: Log template for risks and issues with impact, probability, mitigation.
- Resource_Workload: Main planning sheet for per-resource capacity and allocations per sprint.
  - Cap Hrs/Sprint defaults to 65 (10 days x 6.5h). Adjust per person.
  - Columns S1 %..S8 %: enter planned allocation (e.g., 0.5 for 50%).
  - S1 Hrs..S8 Hrs: auto-computed hours.
  - Total Hrs, Avg Util %, Over/Under Hrs: auto-computed.
- Dashboard: Lightweight KPIs computed from Resource_Workload.
 - Summary_ART: Pivot-style aggregation by ART (headcount, total capacity per sprint, S1..S8 hours, totals, utilization, over/under).
 - Summary_Team: Pivot-style aggregation by ART + Team + Unit with the same metrics as above.

### Actuals import and roll-up (optional)
If you have a CSV of tasks with actual (or estimated) hours and assignees, you can include it when generating:

```bash
python tools/generate_acme_workbook.py --tasks-csv path/to/tasks.csv
```

CSV headers supported (case-insensitive):
- Required: `Assignee`, `Sprint` (e.g., "Sprint 3" or `3`), `Hours` (or `Actual (h)` or `ActualHrs` or `Estimate (h)`)
- Optional: `ID`, `Title`, `Team`, `ART`, `Status`

New sheets created:
- Actual_Tasks: the raw tasks normalized
- Actuals_Rollup: per-assignee, per-sprint hour totals (+ overall total)
- Summary_Actuals_ART: per-ART aggregation of actual hours by sprint and total
- Summary_Actuals_Team: per-(ART, Team, Unit) aggregation

### Variance and dashboard visual
When a tasks CSV is supplied, the generator also creates:
- Summary_Variance_ART: per-sprint variance (Actual - Planned) by ART, plus planned/actual totals, variance hours, and variance %.
- Dashboard visual: a clustered column chart comparing Planned vs Actual by ART, with a compact table of totals.

If no tasks CSV is provided, the variance sheet and chart are omitted.

Note: Assignee names are matched to `Resource_Workload` resources to infer ART/Team/Unit for rollup summaries. If a name doesn't match, ART/Team/Unit will be blank but the hours still roll up.

## Name assignment policy
When a role has no explicit name in the source markdown, the generator assigns a themed random name based on the team/unit:
- Marvel teams (Avengers, Guardians, X‑Men, Fantastic Four, S.H.I.E.L.D.): Marvel-themed names
- DC teams (Justice League, Teen Titans, Watchmen): DC-themed names
- Portfolio (Olympus Gods): Olympian names
- Large Solution (James Bond): MI6-themed names

## Customization tips
- Edit `save6/SAFe6OrganizationStructure.md` to change structure; re-run the generator.
- To add/remove team specialties (which drive auto-generated team members), edit the "- **Team**:" lines in the markdown.
- Adjust sprint count/length by editing the script (`Sprints` sheet creation part).
- You can safely add extra columns/sheets; the generator only overwrites sheets by re-creating the file.

### Planning parameters
At the top of `tools/generate_acme_workbook.py`, you can change:

- `SPRINT_COUNT` (default: 8)
- `SPRINT_CALENDAR_LENGTH_DAYS` (default: 14)
- `WORKING_DAYS_PER_SPRINT` (default: 10)
- `HOURS_PER_WORK_DAY` (default: 6.5)

The default per-person capacity is computed as `WORKING_DAYS_PER_SPRINT * HOURS_PER_WORK_DAY` and prefilled in `Resource_Workload`.
All formulas (hours per sprint, totals, utilization, and the Summary sheets) adjust automatically to the sprint count.

## Troubleshooting
- If Excel shows formulas as text, ensure the cells are not formatted as Text.
- If you add many resources, you may want to widen columns or freeze panes differently.
- The Dashboard intentionally avoids PivotTables for broad compatibility. You can add your own.
