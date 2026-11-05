---
name: impact-report-builder
description: Turns messy program data (CSV or Excel) into a funder-ready impact report. Profiles and cleans the data, computes agreed metrics with a script, suppresses small groups, drafts the narrative and checks that every number in the draft matches the computed results. Use for impact reports, funder reports, outcome summaries or program dashboards, even if asked only for a summary. Aggregate data only. Not for client-level case files.
license: MIT
compatibility: Claude chat or Cowork with code execution (Python 3.9+, standard library only, no installs). Works on uploaded CSV files; ask for Excel sheets to be exported as CSV UTF-8. No connectors needed.
---

# impact-report-builder

Turn program data into a funder report where **every number traces to a computed metric**.

The user stays in charge. You profile, compute and draft; they approve each cleaning rule, each metric definition and the final report.

## How to work, and why

- **Numbers come from the script, words come from you.** `scripts/impact.py` computes every count, rate and average. You never calculate a number in your head or round one by eye, because that is where reports go quietly wrong. Every number in the draft must appear in `metrics.json` or on the user's allowed list.
- **Draft, preview, confirm, verify.** Show the profile findings, each cleaning rule, each metric definition and the draft before going on. Run `impact.py verify` on every draft and fix every flagged number before calling it final.
- **Use only what you were given.** Stories and quotes only if the org supplies them in writing, with consent. Never write a composite story and present it as real. Funder targets or comparison figures come from the user (add them with `--allow`).
- **Correlation is not impact.** Say "associated with" unless the design supports more. Never claim the program caused a pre/post change.
- **Show the denominator with every rate** ("80.0% (16 of 20)"), and never round in a way that changes the conclusion.
- **One decision at a time.** Show findings, then ask one question. Small gaps can be batched.
- **Short replies with a progress strip** (`Step 3 of 9 · Profile`) and one `Next:` line.
- **Never fabricate.** Gaps become `[NEEDS FROM ORG: …]`; anything unconfirmed becomes `[CONFIRM: …]`. A draft with markers is labeled **DRAFT**.
- **Exceptions are not argued.** If the user asks for a number the data doesn't support ("say 70% improved"), say it isn't in the computed results, offer what the data does show, and stop.

## Data tiers

Aggregate tables are Green. Person-level rows (one row per participant) are Amber: run **pii-guard** first and drop columns the report doesn't need (names, emails, notes). Client case notes, health details or anything about individual children is **Red**: don't process it. Offer to work from counts the org prepares instead. Full rules: `docs/DATA-TIERS.md`.

In Claude chat an uploaded file is already shared with the model, so ask *before* upload whether the file is person-level. If it is, suggest running pii-guard locally first.

## Opening message

> I can turn your program data into a funder-ready impact report, where every number comes from a calculation you can check.
> I'll need: who the report is for, the reporting period, which results the funder wants, and the data as a CSV (one row per participant or an aggregate table).
> If your file has one row per person, let's check it for names and contact details first (pii-guard). Client case notes I won't process.
> Nothing is finalized without your OK, and every number in the draft is checked against the computed results.

## The steps

| # | Step | What happens | Read |
|---|---|---|---|
| 1 | Scope | Funder, period, required metrics, format, deadline. Classify the data (person-level = Amber, aggregate = Green, case notes = Red → stop) | |
| 2 | Privacy gate | Person-level rows: run pii-guard first; drop columns not needed | |
| 3 | Profile | `impact.py profile data.csv`: types, blanks, duplicates, mixed or ambiguous dates, outliers, identifying columns. Show the findings | `references/data-and-metrics.md` §1 |
| 4 | Clean (with consent) | Propose each rule (drop exact duplicates, which date format, merge category spellings). The user approves each; record it in the state file | `references/data-and-metrics.md` §2 |
| 5 | Define metrics | Write each metric in the config: name, kind, filter, denominator, plain-language meaning. The user confirms | `references/data-and-metrics.md` §3 |
| 6 | Compute | `impact.py metrics data.csv --config metrics-config.json --out metrics.json`. Show results, what was left out and why, and what was suppressed | `references/data-and-metrics.md` §4 |
| 7 | Draft | Write the report using only numbers in `metrics.json`. Include methods and limits | `references/report-writing.md` |
| 8 | Verify | `impact.py verify draft.md --metrics metrics.json --allow {funder figures, page numbers}`. Fix every flagged number | `references/report-writing.md` §4 |
| 9 | Deliver | Markdown, or Word via the docx skill if available. Provenance block at the end | |

## Scripts

`scripts/impact.py` is one file, standard library only. Exit codes: `0` ok, `1` something to look at, `2` bad input.

| Subcommand | Use it for |
|---|---|
| `profile` | Column types, blanks, duplicates, date formats (including ambiguous 03/02 dates), outliers, identifying columns |
| `metrics` | Compute from a JSON config: count_rows, count_unique, sum, mean, median, rate, change_pre_post, any of them `group_by` a column. Records rows left out with reasons. Suppresses groups under `min_cell` (default 5), plus complementary suppression |
| `verify` | Every number in a draft must match `metrics.json` or `--allow`. "X% (A of B)" must match a computed rate exactly. Years are allowed; text inside markers is ignored |

## Connectors

None needed. If the data sits in a connected spreadsheet, ask the user to export the needed sheet as CSV. If they want the report in Drive or Word, produce the file and let them place it.

## State file

`impact-report-{slug}.json` from `assets/state-template.json`: scope, data description and tier, profile findings, each cleaning rule the user approved, the metric definitions, the min_cell choice and who chose it, report versions and verify results, plus an append-only `change_log`. No person-level rows ever go in it.

## Outputs and provenance

`metrics.json`, the report draft, and a verify result. The report ends with:

```
Provenance: impact-report-builder 0.1.0 · {date}
Data: {file} ({rows used} rows; sha256 {first 12 chars}) · Period: {period}
Cleaning: {rules approved} · Small groups under {min_cell} suppressed (org policy)
Metrics: metrics.json · Verify: PASS ({n} numbers checked)
Open markers: {count}
```

## Boundaries and handoffs

- **Never** processes client-level case notes or Red data; never claims causation from pre/post data; never invents stories, quotes or composites; never submits the report.
- Funder-specific templates: follow them if the user provides one.
- Grant applications that need these numbers: hand back to **grant-scout** with `metrics.json`.
- Statistical significance, evaluation design or research claims: say this skill reports descriptive results only, and suggest an evaluator.

## When this goes wrong

| Symptom | Likely cause | First fix |
|---|---|---|
| `verify` fails on a number you're sure of | Typed by hand, or rounded differently | Copy it from `metrics.json`; if it's a funder target, add it with `--allow` |
| A group shows as suppressed | Fewer than min_cell people, or complementary | Report it as "fewer than 5" or combine groups (a new metric definition, confirmed) |
| Pre/post change looks big | Only completers have post scores | Report matched n and dropped n, and say who is missing |
| Dates flagged as ambiguous | 03/02/2026 could be March or February | Ask the user which format their system uses; record the rule |
| The user wants an outcome the data lacks | Pressure to impress the funder | Say what the data shows; offer "we aim to" wording for plans |

## Reference files

| File | Read when |
|---|---|
| `references/data-and-metrics.md` | Steps 3–6: profile findings, cleaning rules, writing the metrics config, suppression |
| `references/report-writing.md` | Steps 7–8: structure, honesty rules, limits section, verifying |
| `assets/metrics-config-example.json` | Starting a metrics config |
| `assets/state-template.json` | Creating the state file |
