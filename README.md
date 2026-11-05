# Nonprofit Skill Pack

**Five Claude skills for the everyday work of small nonprofits:** checking files for private information, finding grants, writing impact reports, drafting board minutes, and writing donor thank-you letters. They come with privacy and accuracy checks built in.

Every skill **drafts**. You decide, approve and send. None of them sends an email, submits an application or posts anything.

> **Status (5 November 2026):** all five skills are built, unit-tested on synthetic data and packaged (**evidence level L2**, explained under [Owner and status](#owner-and-status)). The 46 behavior tests (evals) are written but **have not been run yet**, and the skills haven't been piloted with a real organization. This README never claims more than that.

## Contents

- [What is this?](#what-is-this)
- [Who it's for](#who-its-for)
- [What each skill does](#what-each-skill-does)
- [Quick start: use it in Claude chat or Cowork](#quick-start-use-it-in-claude-chat-or-cowork)
- [The skills in detail, with examples](#the-skills-in-detail-with-examples)
  - [pii-guard](#1-pii-guard-the-privacy-check)
  - [grant-scout](#2-grant-scout-find-check-and-track-grants)
  - [impact-report-builder](#3-impact-report-builder-funder-reports-with-checked-numbers)
  - [board-minutes-tracker](#4-board-minutes-tracker-minutes-and-action-items)
  - [donor-thank-you-writer](#5-donor-thank-you-writer-personal-thank-you-letters)
- [Data tiers: the privacy rules](#data-tiers-the-privacy-rules)
- [For developers: run, test and package](#for-developers-run-test-and-package)
- [Folder structure](#folder-structure)
- [Owner and status](#owner-and-status)
- [Project details](#project-details) (design decisions, known limits, assumptions, maintenance, changelog)
- [License](#license): MIT

---

## What is this?

A **skill** is a small package that teaches Claude to do one job the same careful way every time. It's a set of instructions plus, here, a small Python script that does the parts where people (and AI) slip: counting, dates, matching numbers, spotting email addresses. Once a skill is installed and switched on, Claude uses it automatically when your request matches. You don't need to type a command.

Small nonprofits try AI tools and hit the same three problems:

1. **Generic output** that doesn't sound like them or fit what funders expect.
2. **Privacy risk:** client names, case notes or donor details pasted in without thinking.
3. **No consistency:** everyone asks differently, and know-how leaves when a person does.

This pack answers each one: skills that follow the org's own facts and voice, a privacy check built into every workflow, and the same steps every time, documented so a non-technical person can own the pack.

**Four rules run through every skill:**

| Rule | What it means in practice |
|---|---|
| **Never invent** | No made-up grants, deadlines, statistics, votes or impact claims. A gap becomes a visible marker like `[NEEDS FROM ORG: number of students served]`, and anything with a marker is labeled **DRAFT** |
| **Scripts do the math** | Counting, dates, percentages and pattern matching are done by a script, not estimated by the model |
| **Show before acting** | You see every draft, ranking and finding before anything is saved or shared |
| **Privacy first** | Data is sorted Green / Amber / Red before use. Red data (client case notes, health, immigration…) isn't processed |

## Who it's for

Small nonprofits (roughly 2 to 10 staff, plus volunteers and a board), and the volunteer or staff member who looks after their tools. You need a Claude account with code execution turned on. No coding is needed to *use* the skills.

## What each skill does

| Skill | Use it when you want to… | You get |
|---|---|---|
| **pii-guard** | check a file or text for personal or sensitive information before using it | A masked summary of what was found, a redacted copy, and a private mapping file. Stops on Red data |
| **grant-scout** | find grants that fit, check eligibility, track deadlines, draft a letter of inquiry | A ranked list (each score with its reasons), the questions that settle unclear eligibility, a deadline schedule, an LOI tracing every claim to your facts |
| **impact-report-builder** | turn a program spreadsheet into a funder report | A check of your data, calculated results (small groups hidden), and a draft where every number has been verified |
| **board-minutes-tracker** | turn meeting notes into minutes and follow-ups | Draft minutes in standard form, a list of things to confirm, an action tracker, reminder drafts |
| **donor-thank-you-writer** | write personal thank-you letters from a gift list | A gift-list check, one letter per donor checked for name, amount, date and acknowledgment wording, and a merge-ready file |

**How they fit together:** the four working skills send you to **pii-guard** first whenever a file names people. Each skill still installs and works on its own.

```
  your file ──► pii-guard ──► redacted copy ──► grant-scout / impact-report-builder /
                   │                             board-minutes-tracker / donor-thank-you-writer
                   └─ Red data? stop, and work from totals instead
```

---

## Quick start: use it in Claude chat or Cowork

The full step-by-step guide, with screenshots-in-words and troubleshooting, is **[docs/GUIDE.md](docs/GUIDE.md)**. The short version:

**1. Get the five `.zip` files**

```
pii-guard.zip   grant-scout.zip   impact-report-builder.zip   board-minutes-tracker.zip   donor-thank-you-writer.zip
```

Download them from this repository's **Releases** page, or build them yourself (Python 3.9+, nothing to install):

```bash
python3 tools/package_skills.py
```

That writes them to `dist/`. **Don't unzip them.**

**2. Turn on code execution in Claude**

- **Free, Pro, Max, Ultra:** **Settings → Capabilities →** turn on **"Code execution and file creation"** (or "Create and edit files").
- **Team, Enterprise:** an admin enables **"Cloud code execution and file creation"** and **"Skills"** under **Organization settings → Plugins & skills → Policy**.

**3. Upload the skills**

**Customize → Skills → + → Create skill → Upload a skill**, then choose a `.zip`. Do `pii-guard.zip` first, then the other four. Make sure each one's switch is on.

**4. Use them**

Start a new chat and say what you need in plain words:

> *Help me find grants for our after-school reading program in Franklin County, Ohio.*

Claude picks the right skill, introduces itself in a few lines, and asks its first question. If it doesn't pick one up, name it: *"Use grant-scout for this."*

**In Cowork:** click **Customize** in the left sidebar and check the skills are listed and on. Then choose your working folder, so Claude can read and save files there directly. With pii-guard, ask it to check a file *before* reading it: *"Before you read donors.csv, run pii-guard on it."*

*The menu names come from Claude's help pages as of 5 November 2026 ([Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)). Uploading to Claude hasn't been tested with this pack yet: see [Known limits](#known-limits).*

---

## The skills in detail, with examples

Every skill follows the same pattern:

- It opens with a short introduction.
- It asks **one decision at a time**.
- Each reply starts with a progress line (`Step 3 of 9 · Profile`) and ends with `Next: …`.
- It keeps your progress in a **state file** (a `.json` download). Save it, and attach it next time to pick up where you left off.

The example outputs below are **real output from the skills' scripts**, run on the pack's synthetic sample data. All names and organizations in them are invented.

### 1. pii-guard: the privacy check

**What it does.** Finds personal and sensitive information in a CSV or text file, shows you a **masked** summary, and makes a redacted copy where each detail becomes a consistent token. For example, the same email always becomes `[EMAIL_1]`, so analysis still works. A separate **mapping file** can put the real values back later, on your own computer.

**What it detects:**
- email addresses and phone numbers
- card numbers (checked with the card-number checksum)
- dates of birth (only next to "DOB", "born" and similar words)
- street addresses
- IP addresses and web links with long IDs
- your own case or member ID formats
- names from a list you provide
- names after words like "Ms." or "client" (lower confidence)
- **sensitive context** (health, mental health, immigration, domestic violence or shelter, minors, criminal justice, substance use), which it flags rather than redacts

**The one thing to know:** **uploading a file to a chat sends it to the model.** pii-guard fully protects a file only if it runs **before** the file is shared, on your computer or in Cowork. Checking a file that's already in the chat still catches mistakes and stops the work on Red data, but it can't un-share anything.

**Bring:** the file (CSV or text). Optionally, a names list (one full name per line) and your ID formats.

**Example prompts:**
- *"Check donors.csv for personal information before I use it."*
- *"I want to analyze our volunteer list in another chat. Make me a redacted copy."*
- *"Is there anything private in this text before I share it with the board?"*

**What you'll see** (scanning the synthetic 60-gift donor list):

```text
pii-guard scan: samples/data/donors.csv (csv)
Suggested tier: AMBER (identifies individuals). Confirm with the user.
Findings (masked values):
  EMAIL          59  email (59)   e.g. n***@example.org, m***@example.com, p***@example.com   [high confidence]
  PHONE          60  phone (60)   e.g. ***87, ***03, ***81   [high confidence]
  ADDRESS        60  street (60)   e.g. [street address]   [medium confidence]
Columns whose names suggest identifying data: first_name, last_name, email, phone, street, zip
```

**When the data is Red, it stops** instead of "lightly redacting":

```text
Redaction refused: this file contains Red data. Redacting it would not make it
safe to use, so nothing was written. Remove or drop the Red parts first
(e.g. --drop-columns), or work from an aggregate version. Exceptions are the
data policy owner's decision.
Found:
  - CARD in the text
  - criminal_justice context in the text
```

**It will not:** process Red data; describe any output as "anonymized" or "safe" (it says "a redacted copy; review before use"); give legal advice; or ask for your mapping file in the chat.

**Measured accuracy** (`scan.py selftest`): on the hand-written holdout set it found **20 of 24** identifiers, with 0 false alarms. On the generated corpus it found all of them, but that corpus was written alongside the detectors, so it's a consistency check, not a quality claim. Social Security numbers are deliberately **not** detected (out of scope for this pack).

### 2. grant-scout: find, check and track grants

**What it does:** works through 9 steps:
1. Builds a profile of your organization. Each fact gets an ID like `F-07` and a note of who said it.
2. Agrees a search plan with you.
3. Finds candidate grants.
4. **Opens each funder's own page**, records its URL and the date it was checked, and runs a check on every record.
5. Ranks them openly.
6. Builds a deadline schedule for your shortlist.
7. Drafts a letter of inquiry.
8. Reviews it with you: every claim in the letter traces back to one of your facts.
9. Tracks follow-ups.

**Its central rule:** a grant is called **open** or **eligible** only if it has a source URL, a checked date, and a deadline and eligibility rules taken from the funder's own page. Anything else is an **unverified lead**, and it says so.

**Bring:** your tax status, where you work, annual budget, what you want funded and roughly how much, and whether you're registered in SAM.gov (needed for federal grants).

**Example prompts:**
- *"Help me find grants for our literacy program in Franklin County, Ohio."*
- *"Here's a funder page I found: can we apply?"*
- *"Draft a letter of inquiry for the Ohio Youth Reading Fund."*
- *"What grant deadlines are coming up for us?"*

**What the ranking looks like** (synthetic golden-set data). Every score shows what it's made of, and nothing is hidden:

```text
grant-scout rank (2026-11-05). Weights: issue_match 0.4, award_fit 0.25, preferences_met 0.15, deadline_feasibility 0.2.

Ranked (all hard gates pass):
- G-06 Maple Fund (synthetic) / Maple Fund Invitational: score 100 (issue_match 1.0, award_fit 1.0, deadline_feasibility 1.0; not scored: preferences_met); deadline 2027-03-01; source https://maple-fund.example.org/... (checked 2026-11-01)
- G-01 Federal Literacy Office (synthetic) / Community Literacy Grants: score 85 (issue_match 1.0, award_fit 0.5, deadline_feasibility 1.0; ...); deadline 2027-02-15
- G-02 Buckeye Reading Trust (synthetic) / Ohio Youth Reading Fund: score 62 (issue_match 1.0, award_fit 0.5, preferences_met 0.0, deadline_feasibility 0.5); deadline 2026-12-01

Needs checking (no hard gate fails, but some are unknown):
- G-12 Federal Rural Programs (synthetic) / Rural Food Systems
    ? Profile has no answer for "service_area_type". Needed for: "Projects must serve a rural area"

Not eligible, because:
- G-04 Hometown Grocers (synthetic) / Hometown Grocers Giving: Applicant must serve OR, WA (Who can apply); Audited financial statements required
- G-11 Small Orgs Capacity Fund (synthetic) / Capacity Grants: Annual budget of $250,000 or less (Eligibility)
```

**And a deadline schedule** counted back from the funder's deadline:

```text
Shortlisted G-01 (Federal Literacy Office (synthetic) / Community Literacy Grants).
Schedule: start drafting 2027-01-29 -> internal review 2027-02-08 -> submit by 2027-02-13 (deadline 2027-02-15). Using 10 drafting, 5 review and 2 buffer days.
```

**It will not:** invent a grant or a deadline; call a closed grant open; add impact numbers you didn't give it; submit or email anything; give tax or legal advice; or write a full proposal (letters of inquiry only, for now).

### 3. impact-report-builder: funder reports with checked numbers

**What it does:**
1. Checks your program data: duplicates, blanks, mixed or ambiguous dates (is 03/02/2026 March or February?), and columns that identify people.
2. Proposes each clean-up step for your approval.
3. Helps you define each metric in plain words.
4. Calculates the results with a script, hiding any group under 5 people (and one more group when needed, so the total can't give the hidden one away).
5. Drafts the report.
6. **Checks every number in the draft against the calculated results.**

**Bring:** your data as CSV (in Excel: **File → Save As → CSV UTF-8**), plus who the report is for, the reporting period, and the results the funder asked about.

**Example prompts:**
- *"Build a spring impact report for our funder from program-data.csv."*
- *"How many people did we serve this year, and how many completed?"*
- *"Did participants' scores improve?"*

**Calculated results** (synthetic cohort: 21 rows, one duplicate):

```text
Metrics (20 rows). Groups smaller than 5 are suppressed (min_cell is an org policy choice). Dropped 1 exact duplicate row(s) before computing.
- people_served: 20 (n=20)  (Different people enrolled in spring 2026)
- completion_rate: 80.0% (16 of 20)  (Share of enrolled people who completed)
    Family Literacy: suppressed, fewer than 5
    Job Readiness: suppressed, complementary (so the total can't reveal the hidden group)
    Tutoring: 83.3% (10 of 12)
- score_change: change 10.63 (pre 44.69 -> post 55.31; 16 matched, 4 dropped)
```

**Then it catches a draft that gets the numbers wrong.** Here the draft said "We served 21 people. 85% (17 of 20) completed.":

```text
verify: 4 numbers checked: FAIL
  line 1: 21: not in metrics.json or the allowed list
  line 1: 85%: not in metrics.json or the allowed list
  line 1: 17: not in metrics.json or the allowed list
  line 1: 85% (17 of 20): percentage, numerator and denominator don't match any computed rate
```

**It will not:** invent outcomes; claim the program *caused* a before/after change (it says "associated with"); write a made-up story or quote; or use client case notes.

### 4. board-minutes-tracker: minutes and action items

**What it does:** turns notes or a transcript into **draft** minutes in standard form:
- attendance and quorum
- each motion with who moved it, who seconded it, the vote and the outcome
- conflicts of interest
- executive session, recorded by time and topic only
- action items

It flags anything unclear as `[CONFIRM: …]` instead of guessing, and checks the draft. Then it keeps an **action tracker**, where every task has a named person and a real date, and drafts reminder messages for you to send.

**Bring:** the notes or transcript, who attended, and your quorum rule (from your bylaws, if they define one).

**Example prompts:**
- *"Turn these board meeting notes into draft minutes."* (then paste the notes)
- *"Add the action items to our tracker."*
- *"It's the 20th. Draft reminders for anyone with overdue actions."*

**The checker catches what notes get wrong.** Here a seconder is missing and the vote doesn't add up:

```text
minutes lint: FAIL
  error: Motion M-2: Approve the FY2027 budget: missing 'Seconded by'
  error: Motion M-2: Approve the FY2027 budget: vote 7 yes + 2 no = 9, but 8 present. Record abstentions, recusals or members who left, or [CONFIRM] the tally
  warning: 3 unresolved [CONFIRM] item(s): settle them before approval
```

**…and won't let "the board" own a task:**

```text
error: owner 'the board' is a group: ask which person will do it
```

**It will not:** invent a vote, a seconder or an attendee; mark minutes approved (your board does that, usually at its next meeting); record what was said in executive session; put health or personnel details in the minutes; send reminders; or give legal advice. If notes came from a recording, it reminds you to confirm everyone agreed to being recorded, without stating the law.

### 5. donor-thank-you-writer: personal thank-you letters

**What it does:**
1. Learns your voice from 2–3 letters you like.
2. Collects a short list of **true, current impact facts**: the only impact claims letters may use.
3. Checks your gift list: duplicates, refunds, missing names or addresses, anonymous donors, gifts in honor or in memory of someone, recurring gifts.
4. Groups donors using **your** thresholds: first-time, repeat, lapsed, major, recurring.
5. Drafts one letter per donor.
6. **Checks every letter** for the right name, amount and date, the acknowledgment wording gifts of $250 or more need, numbers not backed by your facts, overclaims, and mentions of other donors.
7. Gives you a merge-ready file to send yourself.

**Bring:** 2–3 sample letters (or a style description), a few impact facts (for example *"Our tutors met with 312 students this year"*), and your gift list as CSV (gift ID, donor ID, first and last name, gift date, amount).

**Example prompts:**
- *"Draft thank-you letters for this month's gifts in gifts.csv."*
- *"Write a thank-you for Priya's $2,500 gift."*
- *"Check this letter before I send it."*

**The checker catches a wrong amount and an invented number:**

```text
letter lint G-0001: FAIL (80 words, reading grade ~6.6)
  error: amount in letter ($500.00) doesn't match the gift ($250.00)
  error: number(s) not in the impact facts: 150. Use only supplied facts
```

**It will not:** send, schedule or mail anything; give tax advice or decide deductibility; guess anything about a donor (wealth, family, circumstances); invent a name for an anonymous donor; or use an impact claim you didn't supply. The US acknowledgment thresholds ($250 written acknowledgment; more than $75 for the goods-or-services disclosure) are reference points in the config, **marked to verify with your accountant**.

---

## Data tiers: the privacy rules

All five skills sort data before using it. Full rules: [docs/DATA-TIERS.md](docs/DATA-TIERS.md).

| Tier | Examples | Rule |
|---|---|---|
| 🟢 **Green** | Public information, totals, your mission text, published grant information | Use freely |
| 🟡 **Amber** | Donor names and amounts, staff names, board minutes, internal finances | Use with care, under your organization's Claude plan terms. Run pii-guard first for lists of people. Keep names out of anything shared |
| 🔴 **Red** | Client case notes, health or mental health, immigration status, shelter locations, children's identifying details, card or account numbers, criminal history | **Don't process with the skills.** Work from a summary with counts only. Exceptions are your data policy owner's decision, not the skill's |

**Uploading a file to a chat sends it to the model.** A redaction step only protects data if it runs before the file is uploaded (locally, or in Cowork before Claude reads the file), or if the sensitive file is never uploaded.

**Files you keep:**
- Each skill's **state file** (`grant-pipeline-….json` and similar): save it and attach it next time.
- pii-guard's **mapping file**: keep it on your own computer and **never upload it**, because it turns tokens back into real details.

---

## For developers: run, test and package

Everything is **Python 3.9+, standard library only**: no installs and no network calls. All sample data is synthetic.

**Run the tests**

```bash
python3 -m unittest discover tests
```

210 tests as of 5 November 2026, covering:
- unit tests for every script
- answer keys and seeded-error tests (the grant golden set, impact metrics, minutes lint, letter lint)
- pack hygiene (standard library only, no network imports, valid Python 3.9)
- skill structure (frontmatter, references, eval format)
- an install test from the packages alone

They pass on Python 3.9.6 and 3.14.2. On 3.9 one test is skipped, because it needs `sys.stdlib_module_names`, which arrived in 3.10.

**Run a skill's script yourself.** Each script has `--help` with examples and exit codes: `0` ok, `1` something to look at, `2` bad input. For example:

```bash
python3 skills/pii-guard/scripts/scan.py scan samples/data/donors.csv
python3 skills/grant-scout/scripts/rank.py samples/grants/grant-pipeline-riverbend.json --today 2026-11-05
python3 skills/impact-report-builder/scripts/impact.py metrics samples/impact/cohort.csv --config samples/impact/metrics-config.json
python3 skills/board-minutes-tracker/scripts/minutes.py lint samples/minutes/minutes-good.md
python3 skills/donor-thank-you-writer/scripts/letters.py check samples/data/donors.csv --config samples/letters/thank-you-config.json
```

**Package the skills**

```bash
python3 tools/package_skills.py            # writes dist/<skill>.zip (and an identical .skill)
```

**Regenerate the synthetic samples and the eval run sheet**

```bash
python3 samples/generate.py --check        # exits 1 if sample files were edited by hand
python3 tools/make_eval_sheet.py           # rebuilds docs/EVAL-RUN-SHEET.md from evals/
```

**Run the evals.** The 46 cases live in `evals/<skill>/<case>/`. You can run them:
- **by hand in Claude chat**, with [docs/EVAL-RUN-SHEET.md](docs/EVAL-RUN-SHEET.md) (163 checks, each run with the skill on and off)
- **with Claude Code:** `claude plugin eval . --scaffold` (see [evals/README.md](evals/README.md))

**Claude Code users** can also load the whole folder as a plugin: the manifest is at `.claude-plugin/plugin.json`.

**More docs:**

| Doc | For |
|---|---|
| [docs/GUIDE.md](docs/GUIDE.md) | People using the skills: install, chat, Cowork, each skill step by step |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | The person who looks after the pack: install, update, roll back, failure modes, who to call |
| [docs/GOVERNANCE.md](docs/GOVERNANCE.md) | Who may change what, release checklist, incident process |
| [docs/TRAINING-30MIN.md](docs/TRAINING-30MIN.md) | Running a 30-minute training session (agenda, exercises, handout, quiz) |
| [docs/BREAK-IT-CHECKLIST.md](docs/BREAK-IT-CHECKLIST.md) | 18 adversarial prompts a new owner runs to try to break the skills |
| [docs/ADOPTION-METRICS.md](docs/ADOPTION-METRICS.md) | Measuring time saved without overclaiming |
| [STANDARDS.md](STANDARDS.md) | The quality standard, ticked per build stage |

---

## Folder structure

```
nonprofit-skill-pack/
├── README.md                    this file
├── STANDARDS.md                 the quality standard as a checklist, ticked per build stage
├── .claude-plugin/plugin.json   pack manifest (for Claude Code)
├── skills/                      the five skills
│   └── <skill>/
│       ├── SKILL.md             what Claude reads: rules, steps, scripts, boundaries
│       ├── references/          detail loaded only when a step needs it
│       ├── scripts/             Python 3.9+, standard library only
│       └── assets/              templates, configs, state-file starter
├── docs/                        guide, runbook, governance, training, break-it, data tiers, metrics, eval run sheet
├── samples/                     synthetic data only: generator, PII corpus, grants golden set, impact cohort, minutes, letters
├── tests/                       standard-library unittest suite
├── tools/                       package_skills.py, make_eval_sheet.py
├── evals/                       46 behavior test cases, grouped by skill
└── dist/                        built .zip packages (generated)
```

---

## Owner and status

| Skill | Owner | Version | Evidence level | Date |
|---|---|---|---|---|
| pii-guard | Kokil | 0.1.0 | **L2** Unit-tested on synthetic data (evals written, not run) | 2026-11-05 |
| grant-scout | Kokil | 0.1.0 | **L2** Unit-tested on synthetic data, plus a synthetic golden set (evals written, not run) | 2026-11-05 |
| impact-report-builder | Kokil | 0.1.0 | **L2** Unit-tested on synthetic data with a hand-computed answer key (evals written, not run) | 2026-11-05 |
| board-minutes-tracker | Kokil | 0.1.0 | **L2** Unit-tested on synthetic data; lint catches 11 of 11 seeded errors (evals written, not run) | 2026-11-05 |
| donor-thank-you-writer | Kokil | 0.1.0 | **L2** Unit-tested on synthetic data; letter lint catches 11 of 11 seeded errors (evals written, not run) | 2026-11-05 |

**Evidence levels.** These are the only words this project uses to describe how far a skill has been proven:

| Level | Meaning | Reached? |
|---|---|---|
| L0 Designed | Spec only | ✅ |
| L1 Built | Code exists | ✅ |
| L2 Tested | Unit tests pass on synthetic data | ✅ all five |
| L3 Evaluated | Eval suite run with and without the skill | ⬜ not yet |
| L4 Piloted | A real organization used it on real work, with measured results | ⬜ not yet |

---

## Project details

The sections below are for maintainers and reviewers: why things are built the way they are, what's known not to work, and what still needs checking.

### Design decisions

| Decision | Why |
|---|---|
| Plugin manifest at `.claude-plugin/plugin.json`, not at the pack root | Current Claude Code docs (checked 2026-11-05) say the manifest lives in `.claude-plugin/`, with `skills/` at the plugin root. Approved 2026-11-05. |
| Bad-input exit code is `2`, not `1` | Spec §3.3 separates "findings the user must see" (1) from "bad input" (2), so a calling script can tell them apart. Approved 2026-11-05. |
| Tests use stdlib `unittest`, not pytest | Spec §3.4: tests must run with no installs. |
| Sample data comes from a deterministic generator, and the committed files are checked against it | Tests and evals need stable inputs. `--check` catches hand edits. |
| pii-guard has two modes, and the docs say which one protects | In a chat, an uploaded file is already visible to the model. Only a local run before upload prevents exposure (spec §5.2). |
| pii-guard `redact` refuses Red data outright; there is no override flag | Card numbers or sensitive context mean the data shouldn't be processed at all. An override flag would be the workaround spec W9 forbids. Dropping the column is the supported route. |
| `--mask-columns` added to `redact` (not named in the spec) | Spec §5.5 asks for column-aware CSV handling. Names in separate first_name and last_name columns can't be caught by pattern or names-file matching, so whole-cell tokens are the only reliable way to mask them. |
| A hand-written holdout set sits beside the generated corpus | The generated corpus and the detectors share an author and a format list, so 100% on it proves little. The holdout's misses are kept and reported. |
| The mapping file is owner-only (0600) and refused inside git repos and obvious synced folders | It reverses the redaction (spec §5.5). |
| Eval cases live in one root `evals/`, grouped by skill (`evals/pii-guard/…`) | `claude plugin eval` reads one eval directory (`experimental.evals` uses only the first path), and a root `evals/` is never inside a packaged skill. Approved 2026-11-05. |
| Eval graders use the Claude Code grader types (`regex`, `llm`, `tool_used`, `file_exists`) | Spec §3.5's "one verifiable statement each" maps onto them. Fixture copying uses `case.yaml` → `place-files.sh` as a `scaffold_script`. |
| pii-guard has 9 eval cases, not 8 | §3.5 asks for at least 3 boundary cases, but §5.8 lists only 2. The added case, `already-pasted-data`, tests the §5.2 point that data in the chat can't be un-shared. |
| grant-scout's golden set is synthetic (12 invented programs × 3 invented orgs), not real grants as spec §6.12 asked | Owner decision 2026-11-05: no real organizations anywhere. The logic is tested fully offline; accuracy on real funder pages is **not** tested. |
| grant-scout keeps profile, grants, pipeline and LOIs in one state file (`grant-pipeline-{slug}.json`) that all three scripts read | Spec W6: one state file. `rank.py` and `pipeline.py` reuse `validate.py`'s checks, so the "no source, no verified" rule lives in one place within the skill |
| "Capacity fit" is folded into deadline feasibility (the org's days needed per application) and a `preferences_met` component, instead of a separate score | The org's grant-writing capacity mostly decides whether a deadline is doable. A separate capacity number would have needed data nobody has |
| `unknown` is a first-class result with a generated question; a criterion without a machine check is always unknown | Spec §6.8: never guess |
| grant-scout evals run offline from synthetic funder pages in each case's files | Live web search would make results depend on the day's search results and on real funders |
| grant-scout has 11 eval cases, not 10 | §3.5 needs at least 3 boundary cases; §6.11 lists 2. Added `client-story-in-loi` (a child's foster-care story is Red data) |
| From Stage 3 on, builds are kept simple for use inside Claude: one script per skill where possible, two or three references | Owner direction 2026-11-05. Easier to upload and run in a chat; fewer files to maintain |
| impact-report-builder has one script, `impact.py` (profile, metrics, verify), instead of the spec's three | Same direction. The three subcommands keep the spec's separation |
| Numbers are rounded half up, not with Python's default half-to-even | 10.625 should read 10.63, the way people round |
| Ambiguous dates (03/02/2026) are flagged, not parsed | Spec §3.3: refuse to guess |
| board-minutes-tracker has one script, `minutes.py` (lint + action tracker), instead of the spec's `actions.py` and `minutes_lint.py` | Simplification approved 2026-11-05 |
| The minutes lint works on the pack's own minutes form (`assets/minutes-template.md`: `Moved by:`, `Vote:` and similar lines) | A fixed form makes the checks reliable; the skill drafts into that form |
| board-minutes-tracker has 10 eval cases | §8.7 lists 1 happy case; §3.5 needs 3. Added `reminder-drafts` and `conflict-recorded` |
| donor-thank-you-writer has one script, `letters.py` (check, segment, lint), instead of the spec's `gifts.py` and `lint_letter.py`; `flags` is part of `check` | Simplification approved 2026-11-05 |
| Segment thresholds (major gift, lapsed months) ship unset; `segment` refuses until the org sets them | Spec §9.4: no defaults baked in without telling the user |
| Letter lint treats any number not in the impact facts (other than the gift's amount and date) as an error | The simplest check that stops invented statistics |
| The PII corpus is template-built with exact span labels and has negative records | Recall *and* precision can be measured against exact ground truth (spec §5.9). |
| The corpus has at least 100 labels per structured type | With 25 samples, one miss reads as 96%. A ≥ 99% recall bar needs about 100 or more samples to mean anything. |

### Known limits

| Limit | Source | Status |
|---|---|---|
| Uploading the `.zip` files into Claude hasn't been tried yet; the install test only runs the scripts from the unzipped packages | `tests/test_packaging.py` | Check on the first install |
| One Claude help article limits a skill description to 200 characters; ours are 421–459. If the upload rejects them, they'll be shortened | Claude help, "How to create custom skills" | Open: the first upload settles it |
| donor-thank-you-writer evals written (8 cases) but **not run** | Stage 7 | Planned |
| Letter lint can't judge whether a sentence makes an impact claim without a number ("your gift fed families"); the evals cover this | `letters.py` | Accepted |
| Segment history comes only from the gift file given; earlier gifts elsewhere make a repeat donor look first-time | `letters.py segment` | Stated in the skill |
| Reading level is a rough Flesch–Kincaid estimate using a syllable heuristic | `letters.py` | Warning only |
| board-minutes-tracker evals written (10 cases) but **not run** | Stage 7 | Planned |
| The minutes lint only understands the pack's minutes form; minutes in another layout will show false "missing" errors | `minutes.py` | Accepted |
| The executive-session check allows only lines starting with Entered, Left, Returned, Resumed, Topic or Members present; it can't judge whether a Topic line itself says too much | `minutes.py` | Accepted |
| impact-report-builder evals written (8 cases) but **not run** | Stage 7 | Planned |
| `verify` allows any year from 1900 to 2100 and ignores text inside markers. A wrong year would not be caught | `impact.py` | Accepted |
| `verify` matches a number if it equals any computed value at the draft's precision, so a right number in the wrong sentence passes. It checks that numbers exist, not that they're used in the right place | `impact.py` | Accepted; the evals check placement |
| Cleaning beyond dropping exact duplicates (merging spellings, fixing typos) is done by the user or in a corrected CSV they approve, not by a script | Kept simple | Accepted |
| grant-scout evals written (11 cases) but **not run** | Stage 7 | Planned |
| grant-scout golden set: 0 misses on the first run (36 grant × org pairs). The key and the script share an author, so this shows the script follows the stated rules; it doesn't show the rules match real funders | `tests/test_grant_scout_golden.py` | Accepted |
| grant-scout has never been run against a real funder page; Grants.gov, SAM.gov and ProPublica details in the references are marked `[VERIFY]` | Owner decision: synthetic only | Open |
| The LOI fact-trace is a drafting rule, checked by evals only; there is no LOI lint script | Spec §6.8 lists none | Accepted |
| pii-guard evals written (9 cases) but **not run**: no with/without numbers yet | Stage 7 | Planned |
| pii-guard holdout misses: 4 of 24 values and 1 of 7 context lines (a UK mobile with a 6-digit group, two names with no cue and not in the names list, "sober since") | `scan.py selftest`, 2026-11-05 | Kept as found, not tuned away |
| pii-guard generated corpus scores 100% on every detector, but it was written alongside the detectors, so this is a consistency check, not evidence of real-world recall | `references/detectors-and-limits.md` §4 | Accepted, stated in the skill |
| NAME_CUE is a heuristic: names with no cue word are missed unless the org supplies a names file | Spec §5.6 | By design, stated in the skill |
| pii-guard reads only CSV and plain text. Word, Excel and PDF must be exported first | Standard library only | Accepted |
| `scan.py` is 772 lines, under the 800 max but larger than a typical file | Spec §5.5 single-file build | Accepted, flagged for review |
| The stdlib-only import check needs Python 3.10+ (`sys.stdlib_module_names`). On 3.9 that one test is skipped; the network-import and 3.9-syntax checks still run | `tests/test_repo_hygiene.py` | Accepted |
| No SSN detection. Social Security numbers are out of scope for the whole pack (owner decision, 2026-11-05). An SSN in a file is **not** caught by pii-guard; staff must remove it themselves | Owner decision | Accepted |

### Assumptions to verify

| Item | Where used | Status | How checked |
|---|---|---|---|
| Plugin manifest path and fields | `.claude-plugin/plugin.json` | **Checked 2026-11-05** | Claude Code plugins reference (code.claude.com/docs/en/plugins-reference): manifest at `.claude-plugin/plugin.json`, only `name` required, skills auto-discovered under `skills/<name>/SKILL.md` |
| `SKILL.md` frontmatter fields | All skills | **Checked 2026-11-05** | Claude Code skills docs: `compatibility` is a recognized field (≤ 500 chars); `SKILL.md` under 500 lines is a documented tip. skill-creator `quick_validate.py` allows only `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`; name ≤ 64 chars, description ≤ 1024 chars |
| `package_skill` excludes `evals/` | Stage 6 packaging | **Code read 2026-11-05; mirrored, not run** | `package_skill.py` has `ROOT_EXCLUDE_DIRS = {"evals"}`. Its `quick_validate.py` needs PyYAML, which isn't installed, so `tests/test_skill_structure.py` mirrors its rules in the standard library |
| Eval case format (`prompt.md` frontmatter, grader types, `case.yaml` `schema_version: "1.1"`, `scaffold_script`) | `evals/` | **Docs read 2026-11-05, not run** | code.claude.com/docs/en/plugin-evals. Needs Claude Code v2.1.269+ |
| `place-files.sh` finds its case folder via `BASH_SOURCE` (the docs don't say how the scaffold script is invoked) | `evals/*/*/place-files.sh` | **Assumption** | Check on the first eval run (Stage 7) |
| `claude plugin validate` passes | `.claude-plugin/plugin.json` | **Not run** | Needs the `claude` CLI; the manifest only uses documented fields (`name`, `version`, `description`, `keywords`) |
| Skill upload path in Claude | README, `docs/GUIDE.md` §4, `docs/RUNBOOK.md` §1 | **Checked against Claude's help pages 2026-11-05; not tried** | support.claude.com "Use skills in Claude": Customize → Skills → + → Create skill → Upload a skill (ZIP, skill folder at the root) |
| Skill description length on upload | All five SKILL.md files | **Open conflict** | The help article "How to create custom skills" says 200 characters max. skill-creator's validator and the Claude Code docs allow 1,024. Our descriptions are 421–459 characters (spec §3.1 asks for a 500-character pitch). The first real upload will settle it; if it's rejected, shorten them to 200 and rebuild |
| Grants.gov, SAM.gov/UEI, ProPublica Nonprofit Explorer | grant-scout | **Not checked** | Owner chose a synthetic golden set (2026-11-05), so no sites were visited. The skill marks these facts `[VERIFY]` in `profile-intake.md`, `search-and-sources.md` and rank.py's SAM.gov question |
| IRS $250 written acknowledgment; quid pro quo disclosure threshold | donor-thank-you-writer | **Not checked** (built offline) | Values are in `assets/thank-you-config.json` with a `[VERIFY]` source note; the skill tells users to confirm with their accountant and says other countries differ |
| Recording-consent wording only tells users to check | board-minutes-tracker | **Checked 2026-11-05** | SKILL.md step 1 and `minutes-form.md` §4 say "check… don't state what the law requires"; the eval `transcript-with-medical-detail` fails any reply that states a legal rule |
| Claude plan data-terms checklist is neutral | pii-guard | **Written neutral, 2026-11-05** | `plan-terms-checklist.md` asks questions only and states no plan terms; the org answers from its own agreement |
| Small-cell suppression threshold cited as practice | impact-report-builder | **Wording checked 2026-11-05; no external source cited** | The skill calls 5 "a common practice threshold, not a legal rule" and makes it the org's choice. No reference was looked up, to stay offline |
| `claude plugin eval` runs the case folders | Stage 7 | Not checked | Stage 7 |

### Packaging and installing

- `python3 tools/package_skills.py [skill …] [--out DIR]` validates each skill's frontmatter (the same rules as skill-creator's `quick_validate.py`, without needing PyYAML) and writes `dist/<skill>.skill`: a zip with the skill folder at its root, excluding `evals/`, caches and `.DS_Store`. Sizes as of 2026-11-05: 12–64 KB each (pii-guard is the largest because it bundles its self-test corpus).
- `tests/test_packaging.py` builds all five packages, unzips them into a fresh folder, and runs every script with `python3 -I` (isolated from this repo): every `--help`, the pii-guard self-test on its bundled corpus, grant-scout validate and rank, impact metrics with the packaged example config, the minutes lint, and the letters `segment` refusal. It passes on Python 3.9.6 and 3.14.2.
- **Not tested:** uploading to Claude itself, and whether Claude picks each skill from its description. Those need a Claude account and are planned with the evals (Stage 7).
- Claude Code users can also load the whole folder as a plugin (`.claude-plugin/plugin.json`).

### Maintenance

Run `python3 -m unittest discover tests` after any change, and follow `docs/GOVERNANCE.md` (review, versions, release checklist).

| When this changes | Do this |
|---|---|
| A funder's page, grant source or form | Nothing in the skill: grant-scout re-checks pages each time (`validate.py` warns after 30 days). If Grants.gov, SAM.gov or ProPublica change how they work, update `grant-scout/references/search-and-sources.md` and re-check its `[VERIFY]` items |
| IRS acknowledgment rules | Update `donor-thank-you-writer/assets/thank-you-config.json` (values and source date), repackage, bump the version |
| The org's thresholds (small-cell minimum, major gift, lapsed months) | Org settings in each config or state file; no skill change |
| How Claude installs skills, or code execution | Update the README install steps and `docs/RUNBOOK.md` §1; re-run the packaging test |
| A new Claude model | Re-run the evals and the break-it checklist before saying anything still works |
| Anything in the skills | Bump the version, update the changelog, repackage |

### Changelog

- **Guide and run sheet (2026-11-05):** `docs/GUIDE.md` (user guide for Claude chat and Cowork); `docs/EVAL-RUN-SHEET.md` (all 46 eval cases as a manual checklist, 163 checks), generated by `tools/make_eval_sheet.py`; packages now also written as `.zip` (the format Claude's upload asks for).
- **Stage 6 (2026-11-05):** pack docs written in full (governance, runbook, 30-minute training with handout, quiz and feedback form, an 18-prompt break-it checklist, adoption metrics); `tools/package_skills.py`; all five `.skill` packages built; install test from the packages alone (`tests/test_packaging.py`); a synthetic grant-scout state file for training (`samples/grants/grant-pipeline-riverbend.json`); manifest at 0.1.0.
- **donor-thank-you-writer 0.1.0 (2026-11-05), Stage 5:** `letters.py` (check, segment, lint); SKILL.md, 2 references, a config, an impact-facts template and a state template; a sample letter and facts in `samples/letters/`; 11 tests; 8 eval cases (not run). Found and fixed a lint bug (an empty EIN in the config split every number into digits). Pack test suite: 192 tests.
- **board-minutes-tracker 0.1.0 (2026-11-05), Stage 4:** `minutes.py` (lint, init, add, list, close, digest, export-csv); SKILL.md, 2 references, a minutes template and a state template; sample notes and minutes in `samples/minutes/`; 17 tests; 10 eval cases (not run). The seeded tests found a bug (an empty `Adjourned:` line read the next line as its value), which is fixed. Added a test that flags a setup script with no files to copy. Pack test suite: 181 tests.
- **impact-report-builder 0.1.0 (2026-11-05), Stage 3:** `impact.py` (profile, metrics, verify); SKILL.md, 2 references, an example config and a state template; a synthetic cohort with a hand-computed answer key in `samples/impact/`; 15 unit tests; 8 eval cases (not run). Fixed two double-escaped grader regexes and one grader that would have failed a correct refusal; added a test that blocks double escapes. Pack test suite: 164 tests.
- **grant-scout 0.1.0 (2026-11-05), Stage 2:** `validate.py`, `rank.py`, `pipeline.py`; SKILL.md, 5 references, 4 assets; synthetic golden set in `samples/grants/` (0 misses); 47 unit and golden tests; 11 eval cases (not run). Pack test suite: 149 tests.
- **pii-guard 0.1.0 (2026-11-05), Stage 1:** `scan.py` (scan, redact, verify, restore, selftest), SKILL.md, 4 references, state template, bundled self-test corpus and hand-written holdout, 50 unit tests, 9 eval cases (not run). Owner decisions: SSNs dropped from the pack entirely; no company references. Pack test suite: 102 tests.
- **0.0.0 (2026-11-05), Stage 0:** repo skeleton, manifest, shared doc outlines, `docs/DATA-TIERS.md`, `STANDARDS.md`, deterministic synthetic data generator, and the first unit tests.

---

## License

[MIT](LICENSE). Copyright (c) 2026 Kokil.

Any organization may use, copy, adapt and share these skills, free of charge, as long as the copyright notice stays with the copies. The skills come **as is, with no warranty**: they draft and check, but they aren't legal, tax or privacy advice, and a person reviews everything before it's used.
