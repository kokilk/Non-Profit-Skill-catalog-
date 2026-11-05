# Shortlist, schedule and tracking

Read this at step 6 (shortlist) and step 9 (tracking).

## Contents
1. Shortlisting
2. The working-back schedule
3. Tracking

## 1. Shortlisting

The user picks 3 to 5 grants from the ranked list (or from "needs checking", once its questions are answered). For each:

```
python3 scripts/pipeline.py add grant-pipeline-{slug}.json G-03
```

`add` refuses unverified leads, closed grants and anything already shortlisted. Show the schedule it prints and ask whether the day counts suit the org.

## 2. The working-back schedule

From the funder's deadline, counting back: **submit by** = deadline − buffer days; **internal review** starts review days before that; **drafting** starts drafting days before review. The defaults (10 drafting, 5 review, 2 buffer) are placeholders. Ask the org what's realistic, store the answer in `pipeline.settings`, or override per grant (`--drafting-days 15`). The output always says which numbers it used.

If drafting would have had to start already, the output says **NOT FEASIBLE**. Offer a shorter plan, or the next cycle. Never quietly squeeze the schedule.

Rolling grants have no schedule: set a follow-up date instead.

## 3. Tracking

- `update` moves a grant through: shortlisted → loi_drafting → loi_review → submitted_by_org → awarded / declined / withdrawn. Each change is logged.
- `status` shows days left and the tier: **passed**, **due soon** (14 days or fewer by default), **comfortable**. It exits 1 when something needs action.
- `export-csv --out tracker.csv` writes a tracker the user can open in a spreadsheet or upload to a shared drive (after confirming).
- Use `submitted_by_org` only when the user says they submitted. You never submit.
