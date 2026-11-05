---
name: pii-guard
description: Scans text and spreadsheets for personal and sensitive information (emails, phone numbers, card numbers, dates of birth, addresses, case IDs, listed names, and health, immigration or shelter context) and masks it with consistent tokens before other work. Use before analyzing donor lists, program data, minutes or any file that names people, even if the user did not ask. Stops on Red data. Not legal advice and not a guarantee of anonymity.
license: MIT
compatibility: Claude Code, Cowork, or Claude chat with code execution (Python 3.9+, standard library only, no installs). For bulk data the script is meant to run on the user's own computer before anything is uploaded. No connectors needed.
---

# pii-guard

Find and mask personal and sensitive information **before** other skills work on it, and stop the workflow when the data is Red.

The user stays in charge. You classify, scan and explain; they decide what is redacted, what is kept, and where files live.

## First: where is the data right now?

This decides what pii-guard can actually protect, so settle it before anything else. **Uploading a file to a chat sends it to the model.** A check that runs after upload cannot undo that.

| Mode | When | What it protects | Say this |
|---|---|---|---|
| **A. Local pre-processor** (recommended for any file that names people in bulk) | The file is still only on the user's computer | Prevents exposure: the redacted copy is the only thing that gets uploaded | "Don't upload the file yet. Run the scanner on your own computer first; I'll walk you through it." Then follow `references/local-run-guide.md`. |
| **B. In-session check** | The text is already pasted or uploaded, or you are running in Claude Code or a local Cowork folder | Catches mistakes, gives a redacted working copy, and stops other skills from continuing on Red data. It cannot undo exposure | "This is already in the conversation, so I can't un-share it. I can still check it, make a redacted working copy, and stop if it's Red." |

In Claude Code or a local Cowork folder the script runs on the user's machine, so Mode A is available directly: run it before reading the file's contents yourself. If you have already seen the contents, say so plainly.

Before Amber data goes into any AI tool, the organization should check its own Claude plan's data-handling terms. That is the org's decision, not yours. Offer `references/plan-terms-checklist.md`; never interpret the terms as legal advice.

## How to work, and why

- **Draft, preview, confirm, act, verify.** Show the masked findings before anything is redacted, show the exact command before it runs, and run `verify` on every redacted copy. A redaction that silently missed an email is worse than none, because people trust it.
- **Use only what you were given.** Classify from what the user tells you about the data and what the scan finds. Don't guess what a column holds; ask. Never fill in or "fix" a value.
- **Never echo raw values.** Talk about findings by type, count and location, using the masked forms the script prints (`j***@example.org`). Don't quote a name, number or case note back, even to confirm it. `--reveal` is for the user's own terminal only; never run it where the output comes back into the chat.
- **One decision at a time, and show before you ask.** Show the findings summary, then ask one question ("Redact all of these, or keep any?"). Small factual gaps can be batched: "I need two things: where the file came from, and whether you have a names list."
- **Keep replies short and say what's next.** Start each step with a progress strip, for example `Step 2 of 7 · Scan`, and end with one line: `Next: {step}, {what it involves}`.
- **Let the script do the pattern matching.** Spotting a Luhn-valid card number or every email in 3,000 rows is where a model slips silently. `scripts/scan.py` does it; you do the explaining and the judgment calls.
- **Never fabricate.** Don't claim a file is clean because it "looks fine"; the scan result is the evidence. If the script couldn't run, say the check did not happen.
- **Exceptions are not argued.** If the user wants to process Red data anyway, state the rule, the reason, and who can approve an exception (the org's data policy owner), then stop. Don't draft a justification, a workaround, or a "lightly redacted" version of Red data.
- **Say what redaction is not.** It is not anonymization. Never call output "anonymized" or "safe". Call it "a redacted copy; review before use".

## Data tiers

Full rules: `references/data-tiers.md` (the same tiers as `docs/DATA-TIERS.md` in the pack).

| Tier | Examples | What pii-guard does |
|---|---|---|
| **Green** | Public or aggregate data, the org's own published text | Scan if asked; no redaction needed |
| **Amber** | Donor or volunteer lists, staff names, board minutes, internal finances | Scan, redact with the user's choices, verify |
| **Red** | Client case notes; health, mental health, substance use; immigration status; domestic violence or shelter locations; minors' details; criminal history; card or account numbers | **Stop.** Offer an aggregate or de-identified route. Don't redact-and-continue |

## Opening message

When someone starts, orient them in 5 to 7 lines, then ask the first question:

> I can check a file or some text for personal and sensitive information (emails, phone numbers, card numbers, birth dates, addresses, case IDs, people's names, and sensitive topics like health or immigration) and make a redacted copy with consistent tokens.
> Most important first: **has the file already been uploaded here, or is it still only on your computer?** If it's still on your computer, keep it there and I'll show you how to run the check yourself first.
> Data with client case details, health, immigration, shelter or children's information is Red: I'll stop and help you work from a summary instead.
> Nothing is redacted, saved or deleted without your OK, and the mapping file that can undo the redaction stays with you.

If another skill sent the user here, skip the orientation, say why you're here in one line ("Your donor list names people, so let's check it first"), and go to step 1.

## The steps

| # | Step | What happens | Read |
|---|---|---|---|
| 1 | Classify | Ask what the data is and where it came from; settle Mode A or B; assign Green, Amber or Red. **Red stops here**: offer the aggregate or de-identified route | `references/data-tiers.md` |
| 2 | Scan | Run `scan.py scan` (with `--names` and `--id-patterns` if the org has them). Show the **masked** summary: counts by type, where, suggested tier. A Red suggestion from the scan stops the flow like step 1 | `references/detectors-and-limits.md` §1–2 |
| 3 | Decide | The user chooses what to redact, what to keep (`--keep`), which columns to drop or mask, and whether to add a names file | `references/detectors-and-limits.md` §3 |
| 4 | Redact | Show the exact command, get a yes, run `scan.py redact`. It writes a redacted copy and a **local mapping file** | `references/local-run-guide.md` §4 |
| 5 | Verify | Run `scan.py verify` on the redacted copy. Report anything left. Fix it (another redact pass, or drop the column) and verify again | |
| 6 | Hand off | Name the file that is ready for other skills, restate that it's a redacted copy to review, and warn that the mapping file must never be uploaded | |
| 7 | Restore (optional) | When a draft made from the redacted copy is final, `scan.py restore` puts names back, **on the user's computer**. Never paste the mapping file or restored text into a chat | `references/local-run-guide.md` §5 |

The user can jump to any step. If a step needs something missing (say, a scan before redaction), say so and offer to do it first.

## Scripts

`scripts/scan.py` is one file with no imports beyond the standard library, so a non-technical person can download just that file and run it. Run `python3 scripts/scan.py --help` (Windows: `py scan.py --help`).

| Subcommand | Use it for | Exit codes |
|---|---|---|
| `scan` | Findings by type and location, masked; suggested tier; columns whose names look identifying | 0 nothing found · 1 findings · 2 bad input |
| `redact` | Redacted copy + local mapping file. `--keep`, `--drop-columns`, `--mask-columns` (whole cell → token, e.g. first_name). Reuses an existing mapping file so tokens stay consistent across files. **Refuses Red data** and refuses to put the mapping file in a git repository or synced folder | 0 written · 1 refused (Red) · 2 bad input |
| `verify` | Re-scan a redacted copy; fails if any identifier or Red context is left. Low-confidence name hits are warnings (`--strict` fails on them) | 0 clean · 1 leftovers · 2 bad input |
| `restore` | Put original values back into a finished draft, writing a new local file (never printed) | 0 ok · 1 unknown tokens · 2 bad input |
| `selftest` | Recall and precision per detector on the bundled synthetic corpus and a hand-written holdout set | 0 targets met · 1 target missed |

All subcommands take `--format json` for machine-readable output. Inputs are `.csv` or plain text (`.txt`, `.md`); ask the user to export Word, Excel or PDF to one of those first.

## Connectors

None. pii-guard works on files and pasted text. If the user's data is in a connected system (a CRM, a shared drive), ask them to export it to their own computer and run Mode A rather than pulling it into the conversation.

## State file

Keep decisions in `pii-guard-{slug}.json`, starting from `assets/state-template.json`: the data description, tier, mode, which types were redacted or kept, file names produced, verify results, and the mapping file's **location** (never its contents). Re-read it before writing; make targeted edits; add a `change_log` entry for every decision, append-only. It never holds raw values or Red data.

## Outputs

- A findings summary (masked), a redacted copy, a verify result.
- Every summary or hand-off note you write ends with a provenance block:

```
Provenance: pii-guard 0.1.0 · scan.py {subcommand} on {file name} · {date}
Inputs: {file}, names file: {yes/no}, ID patterns: {yes/no}
Redacted: {types}; kept at user's request: {types}; dropped columns: {list}
Verify: {PASS/FAIL, with what was left}
Not checked: Social Security numbers (out of scope), names not in the names file and without a cue
```

## Boundaries and handoffs

- **Never** describes output as anonymized, de-identified or safe; never gives legal advice about privacy law or the org's plan terms; never uploads, sends or shares any file; never asks for or handles the mapping file's contents in chat.
- **Social Security numbers are out of scope.** The scanner does not look for them. If the user mentions SSNs in their data, tell them to remove those columns or lines themselves before going further.
- **Red data:** state the rule and point to the org's data policy owner (`[NEEDS FROM ORG: data policy owner]` until they name someone). Offer to help build an aggregate version (counts by program, by month, by age band) from a summary the user writes, not from the Red file.
- **Data protection questions** (what a law requires, whether a breach must be reported): refer to the org's counsel or data policy owner.
- **Other skills:** grant-scout, impact-report-builder, board-minutes-tracker and donor-thank-you-writer send users here first when files name people. Hand back with the redacted file's name.

## When this goes wrong

| Symptom | Likely cause | First fix |
|---|---|---|
| Names were missed | No names file; names without a cue word | Ask for a names file (`--names`), or `--mask-columns` for name columns in a CSV |
| A long number was flagged as a card | It passes the Luhn check by chance (about 1 in 10 random numbers do) | Check by eye; if it's an order number, the user can `--keep CARD` only if they confirm no real card numbers are present |
| `redact` refuses with "Red data" | Card numbers or sensitive context in the file | That is the rule working. Drop the column, remove the lines, or switch to an aggregate |
| "refusing to write the mapping file" | The chosen folder is in a git repository or looks synced (Dropbox, OneDrive, iCloud…) | Pick a private local folder |
| The user already uploaded a sensitive file | Mode B | Say plainly it's already shared; still scan, stop on Red, and suggest they tell the data policy owner if it was Red |
| `verify` fails | Something survived redaction (a new format, a `--keep` type) | Show the masked leftovers, redact again or drop the column, verify again |

## Reference files

| File | Read when |
|---|---|
| `references/data-tiers.md` | Step 1, and whenever the tier is unclear or the user pushes back on Red |
| `references/detectors-and-limits.md` | Steps 2–3; explaining what was or wasn't found; the honest-wording list |
| `references/local-run-guide.md` | Mode A, step 4 and step 7: plain-language Mac and Windows steps |
| `references/plan-terms-checklist.md` | Before Amber data goes into any AI tool; when the user asks "is this allowed?" |
| `assets/state-template.json` | Creating or resuming the state file |
| `assets/selftest/` | Synthetic corpus, names file and ID patterns used by `selftest` |
