# Runbook

Everything a new owner needs to install, update, test and look after the pack. Every command here runs from the pack folder with Python 3.9 or later and nothing else installed.

## Contents
1. Install
2. Update and roll back
3. Uninstall
4. State files: where they live, who owns them
5. Run the unit tests
6. Run the evals
7. Known failure modes and first fixes
8. Who to call

## 1. Install

1. Build the packages: `python3 tools/package_skills.py` (writes `dist/<skill>.zip` and an identical `.skill`).
2. Turn on **Settings → Capabilities → Code execution and file creation**, then go to **Customize → Skills → + → Create skill → Upload a skill** and upload each `.zip`. Step by step, with Cowork: `docs/GUIDE.md` §4–5.
3. Start a new chat and say what you need ("help me find grants", "draft our board minutes"). Claude picks the skill from its description. If it doesn't, name it: "use grant-scout".

Install **pii-guard** whenever you install any other skill: the others send people to it.

## 2. Update and roll back

- **Update:** rebuild the package for the changed skill, upload it again in Claude (it replaces the old one), and note the version in the changelog.
- **Roll back:** keep the previous `.skill` files (for example in `dist/previous/`), and upload the old one again.

## 3. Uninstall

Remove the skill in Claude's skills settings. Then remind users to delete state files they no longer need (§4).

## 4. State files: where they live, who owns them

Each skill keeps one JSON file the **user** keeps: `pii-guard-{slug}.json`, `grant-pipeline-{slug}.json`, `impact-report-{slug}.json`, `action-tracker-{slug}.json`, `thank-you-{slug}.json`. In Claude chat they come as downloads; the user saves them and attaches them next time. They hold Amber data (names, amounts), never Red. pii-guard's **mapping file** holds original values: it stays on the user's own computer and is never uploaded.

## 5. Run the unit tests

```bash
python3 -m unittest discover tests
```

Expected (as of 2026-11-05): every test passes on Python 3.10 or later; on 3.9 one test (the stdlib-only import check) is skipped. Also check the synthetic samples are current:

```bash
python3 samples/generate.py --check
```

## 6. Run the evals

**By hand, in Claude chat or Cowork:** work through `docs/EVAL-RUN-SHEET.md` (regenerate it with `python3 tools/make_eval_sheet.py` after changing any eval). **With Claude Code** (optional): `claude plugin eval . --scaffold` (v2.1.269 or later); see `evals/README.md`. Each case runs with and without the pack. Record the model, the date, the case and run counts, and raw pass counts.

## 7. Known failure modes and first fixes

| Symptom | First fix |
|---|---|
| A skill doesn't trigger | Name it in the request; check it's installed and code execution is on |
| "file not found" from a script | The user's file wasn't uploaded, or the name differs; ask for it |
| "not UTF-8" / "expected a .csv" | Re-save as CSV UTF-8 from the spreadsheet |
| pii-guard refuses to redact | Red data present: that's the rule working (`DATA-TIERS.md`) |
| grant-scout shows a grant as an unverified lead | The funder page wasn't opened or lacks a deadline; open it, or keep it as a lead |
| impact `verify` fails | A number was typed by hand; copy it from `metrics.json` |
| minutes lint reports a missing field | The notes didn't say; it's a `[CONFIRM]` for the secretary |
| letters `segment` refuses | Set the major-gift amount and lapsed months in the config with the org |

## 8. Who to call

| Role | Name | Contact |
|---|---|---|
| Owner | `[NEEDS FROM ORG]` | |
| Backup | `[NEEDS FROM ORG]` | |
| IT contact | `[NEEDS FROM ORG]` | |
| Board data-policy contact | `[NEEDS FROM ORG]` | |
