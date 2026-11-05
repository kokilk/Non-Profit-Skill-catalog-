# Org profile intake

Read this at step 1, and whenever a profile fact is missing, disputed or changes.

## Contents
1. What to collect first
2. How each fact is stored
3. Asking well
4. When a fact changes

## 1. What to collect first

Collect the **hard-gate facts** first, because they decide eligibility. Fit facts can follow.

| Priority | Field (as `rank.py` reads it) | Why |
|---|---|---|
| Hard gate | `tax_status` (501(c)(3), fiscally sponsored, other), `fiscal_sponsor`, `applicant_type` | The most common eligibility rule |
| Hard gate | `geography` (list: states, counties, cities served) | Most foundations fund locally |
| Hard gate | `annual_budget` (number) | Budget caps and floors |
| Hard gate | `sam_uei_status` (registered, not_registered, in_progress) | Federal grants generally require SAM.gov registration with a UEI `[VERIFY: current SAM.gov requirement and processing time]` |
| Hard gate | `audited_financials` (true/false), `can_provide_match` (true/false) | Common for larger awards |
| Fit | `issue_areas` (list), `project_to_fund`, `ask_amount` (`{"min", "max"}`), `project_timeline` | Scoring and the LOI |
| Fit | `days_needed_per_application`, `grant_writing_capacity` | Deadline feasibility and the schedule |
| LOI | `legal_name`, `mission` (the org's own words), `programs`, `populations_served` (aggregate only), `year_founded`, `staff_count`, `volunteer_count`, `board_size`, `prior_funders` | Facts the LOI can cite |
| Optional, Amber | `ein` | Some applications ask for it. Never put it in anything shared |

Field names and shapes are in `assets/profile-template.json`. Use those names exactly: a fact under a different name is invisible to `rank.py`.

## 2. How each fact is stored

```json
{"id": "F-07", "field": "annual_budget", "value": 420000, "source": "Executive director, chat 2026-11-05"}
```

- **One fact per field.** `rank.py` refuses a profile with two facts for one field, rather than guess which is current.
- **`source` says who said it and when**, or which document it came from.
- **Leave a fact out rather than guess.** A missing fact becomes an `unknown` with a question, which is the honest result.
- **`populations_served` is aggregate** ("about 300 K–5 students a year"), never individuals.

## 3. Asking well

- Batch the hard-gate questions in one message, numbered, and offer "not sure" as an answer.
- Show the parsed profile as a table (ID, field, value, source) before saving, and ask for one confirmation.
- Use the org's words for `mission`. Don't polish them; the LOI can do that, with the user's approval.
- If the user doesn't know their SAM.gov status, record `unknown` (leave the fact out) and say federal grants will show as "needs checking".

## 4. When a fact changes

Edit only that fact, keep its ID, update `source`, and add a `change_log` entry ("F-07 annual_budget 420000 → 455000, per treasurer"). Re-run `rank.py`: a changed hard-gate fact can move grants between buckets. If an LOI already cites the fact, flag the LOI for re-review.
