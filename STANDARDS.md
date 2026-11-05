# Standards checklist

The acceptance criteria from build spec §3, as a checklist. Each stage ticks what it delivered, with evidence. A tick is only added for something that was actually built and checked in that stage.

**Key:** ✅ met this stage (evidence in the notes) · ❌ applies but not met (see notes) · ⬜ applies, comes in a later stage · ➖ does not apply to this stage's work

**Stages:** S0 skeleton · S1 pii-guard · S2 grant-scout · S3 impact-report-builder · S4 board-minutes-tracker · S5 donor-thank-you-writer · S6 pack docs and packaging · S7 eval runs and break-it

---

## 3.1 Skill file anatomy

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 | S6 | S7 |
|---|---|---|---|---|---|---|---|---|---|
| S1 | `SKILL.md` frontmatter has `name`, `description`, `compatibility` | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | | |
| S2 | First 500 chars of `description` carry the full pitch, a "use for … even one piece" and a "Not for …" clause | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | | |
| S3 | `SKILL.md` is a router under 500 lines (rules, step table, scripts, connectors, boundaries, reference index) | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | | |
| S4 | Each reference says when to read it, has a table of contents if over 300 lines, and covers one topic | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | | |
| S5 | Imperative instructions that give reasons; no walls of capitalized MUSTs | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |

## 3.2 Working rules every skill contains

| ID | Rule | S0 | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|---|---|
| W1 | Draft, preview, confirm, act, verify | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W2 | Use only what you were given; missing facts reported as missing | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W3 | One decision at a time; show before you ask | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W4 | Short replies with a progress strip and one `Next:` line | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W5 | Scripts do counting, dates, math, pattern matching | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W6 | State lives in one user-kept file (`{skill}-{slug}.json`) | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W7 | Never fabricate; gaps become `[NEEDS FROM ORG: …]` / `[CONFIRM: …]` | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W8 | Boundaries and handoffs are explicit | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |
| W9 | Exceptions are not argued: rule, reason, approver, stop | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 3.3 Script standard

Applies to every Python file in the pack, including `samples/generate.py`.

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|---|---|
| SC1 | Python 3.9+, standard library only, runnable as `python3 x.py --help` with no installs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC2 | Subcommands (where there is more than one action) with clear `--help`, worked examples in the module docstring | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC3 | `--format json\|md` option; human-readable by default | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |
| SC4 | Exit codes `0` ok, `1` findings or warnings, `2` bad input or error; documented in `--help` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC5 | Refuse to guess: bad input stops with a clear message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC6 | No network calls | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC7 | No raw sensitive values printed by default (masked) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SC8 | Scripts that write state refuse if the file changed since it was read | ➖ | ✅ | ✅ | ➖ | ✅ | ➖ |

## 3.4 Test standard

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 | S7 |
|---|---|---|---|---|---|---|---|---|
| T1 | Every script has `unittest` tests in `tests/` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| T2 | At least 30 tests pack-wide | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| T3 | Every documented subcommand has a happy-path and a failure-path test | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| T4 | A synthetic corpus in `samples/` drives the tests | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| T5 | `python3 -m unittest discover tests` passes with no network and no installs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |
| T6 | Test names say what they check | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |

## 3.5 Eval standard

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 | S7 |
|---|---|---|---|---|---|---|---|---|
| E1 | Case-folder format: `prompt.md`, `case.yaml`, `graders/NN-*.md`, `files/` + `place-files.sh` | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| E2 | ≥ 8 cases per skill (≥ 3 happy, ≥ 3 boundary/refusal, ≥ 2 trap); grant-scout ≥ 10 | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| E3 | Graders are objective, one verifiable statement each | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| E4 | Each case run with and without the skill; raw counts, N and runs reported | ➖ | | | | | | ⬜ |
| E5 | Failing evals go in README "Known limits" | ➖ | | | | | | ⬜ |

## 3.6 Privacy and data standard

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|---|
| P1 | Every skill classifies data with the shared tiers and behaves per tier | ✅ (tiers doc) | ✅ | ✅ | ✅ | ✅ | ✅ | |
| P2 | Personal data is stored only in a local, user-controlled state file; never Red data | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| P3 | Named sensitive data never posted, quoted or echoed unnecessarily | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| P4 | README states "uploading a file to a chat sends it to the model" | ✅ | | | | | | ✅ |
| P5 | All sample data is synthetic (no real people, orgs or credentials) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |

## 3.7 Documentation standard

| ID | Standard | S0 | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|---|
| D1 | Each skill documents purpose, inputs, steps, outputs, boundaries, "when this goes wrong" | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| D2 | README: owner and status table | ✅ (stub) | | | | | | ✅ |
| D3 | README: design decisions with reasons | ✅ (started) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D4 | README: assumptions-to-verify table (what was checked and how) | ✅ (started) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D5 | README: known limits | ✅ (stub) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| D6 | README: changelog | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 3.8 Packaging standard

| ID | Standard | S0 | S6 |
|---|---|---|---|
| K1 | Each skill packages with skill-creator `package_skill` into `.skill`; `evals/` excluded | ➖ | ✅ |
| K2 | Scripts small and readable | ✅ | ✅ |
| K3 | Each skill versioned (`0.1.0` first), bumped on behavior change, logged in changelog | ➖ | ✅ |

## 3.9 Evidence ladder

| Skill | Level reached | Date | Evidence |
|---|---|---|---|
| pii-guard | L2 Unit-tested on synthetic data | 2026-11-05 | 50 unit tests; selftest numbers in the README. Evals written, not run |
| grant-scout | L2 Unit-tested on synthetic data | 2026-11-05 | 47 tests including a synthetic golden set (0 misses). Evals written, not run |
| impact-report-builder | L2 Unit-tested on synthetic data | 2026-11-05 | 15 tests; metrics match the hand-computed key; 10 of 10 injected wrong numbers caught. Evals written, not run |
| board-minutes-tracker | L2 Unit-tested on synthetic data | 2026-11-05 | 17 tests; lint catches 11 of 11 seeded errors. Evals written, not run |
| donor-thank-you-writer | L2 Unit-tested on synthetic data | 2026-11-05 | 11 tests; letter lint catches 11 of 11 seeded errors. Evals written, not run |

---

## Stage log

### Stage 0 (2026-11-05)
- **SC1–SC7, T1, T3–T6:** apply to `samples/generate.py` and its tests. Evidence: `tests/test_samples_generator.py`, `tests/test_repo_hygiene.py`. The test suite was run on Python 3.9.6 and 3.14.2.
- **SC2:** the generator does one thing (write the corpus), so it has flags rather than subcommands: `--check` and `--format`.
- **SC7:** the generator prints only file names, counts and hashes, never sample values.
- **T2:** 39 tests (29 generator, 10 pack hygiene). Python 3.14.2: 39 pass. Python 3.9.6: 38 pass, 1 skipped (the stdlib-only import check needs `sys.stdlib_module_names`, which arrived in 3.10). Re-ticked at every stage.
- **Guards proven to fail:** a planted `import urllib.request` failed the network-import test, and a hand-edited `donors.csv` made `generate.py --check` exit 1. Both were reverted.
- **P1:** `docs/DATA-TIERS.md` written. The per-skill behavior comes in each skill's own stage.

### Stage 1 (2026-11-05): pii-guard
- **S1–S5:** checked by `tests/test_skill_structure.py`: frontmatter keys and limits (mirrors skill-creator's validator, which couldn't run without PyYAML), a 441-character description with "Use before… even if…" and "Not legal advice", a 136-line router, every reference indexed and saying when to read it, no capitalized MUSTs.
- **W1–W9:** in `SKILL.md` "How to work, and why", the steps table and Boundaries. Opening message (§4.5), provenance block (§4.4) and `[NEEDS FROM ORG]` markers (§4.3) included. W6: `assets/state-template.json` with the shared fields; the state file never holds raw values.
- **SC1–SC8:** `scan.py` is stdlib only and one file, with subcommands, `--help` with examples, `--format json|md`, exit codes 0/1/2, no network, and masked output by default (`--reveal` is opt-in and warns). SC8: the mapping file refuses to write if it changed since it was read (sha256), and a test covers it.
- **T1–T6:** 50 tests in `tests/test_pii_guard_scan.py`, with a happy and a failure path for every subcommand. The pack total is 102 tests. Python 3.14.2: 102 pass. Python 3.9.6: 101 pass, 1 skipped (as in Stage 0).
- **E1–E3:** 9 cases (3 happy, 4 boundary, 2 trap). The format is checked by tests. E4 and E5 (runs, baseline) are Stage 7.
- **P1–P3, P5:** tiers in SKILL.md and `references/data-tiers.md`. No raw values in default output (tested). Fixtures are synthetic. SSNs removed pack-wide (owner decision).
- **D1:** purpose, inputs, steps, outputs, boundaries and "When this goes wrong" are all in `SKILL.md`. **D3–D6:** README updated.
- **Detector accuracy (Stage 1 gate):** template corpus 1,660 of 1,660 labels found, 0 false positives (a consistency check only). Hand-written holdout: 20 of 24 found, 0 false positives; context 6 of 7. The misses are listed in the README Known limits.

### Stage 2 (2026-11-05): grant-scout
- **S1–S5:** `tests/test_skill_structure.py` passes for grant-scout: a 128-line router, 5 references (33–59 lines each, each saying when to read it), and a description with "Use for… even one piece" and "Not for full proposals".
- **W1–W9:** "How to work, and why" plus the source rule. W5: dates, scores and eligibility logic are in scripts. W6: `grant-pipeline-{slug}.json`. W7: `[NEEDS FROM ORG]` and `[VERIFY]` markers, and DRAFT labelling. W9: a failed hard gate is shown, not argued.
- **SC1–SC8:** three stdlib scripts with `--help` examples, `--format json|md` and exit codes 0/1/2. SC5: duplicate profile fields, unknown ops and bad dates stop with a message. SC7: no sensitive values are printed (the EIN is never output). SC8: state writes check a sha256 of the file, and a test covers it.
- **T1–T6:** 47 tests (16 validate, 15 rank, 13 pipeline, 3 golden). Every subcommand has a happy and a failure path. Pack total: 149. Python 3.14.2: 149 pass. Python 3.9.6: 148 pass, 1 skipped.
- **E1–E3:** 11 cases (4 happy, 3 boundary, 4 trap), offline fixtures, format checked by tests. One grader was rewritten after review: a "must not contain the child's name" regex would have failed a correct refusal.
- **Golden set (Stage 2 gate):** synthetic only, by owner decision. 36 grant × org pairs, hand-keyed before the first run: **0 misses**, covering bucket, rank order, score, deadline and source present. A mutation check (wrong score, wrong deadline, changed status) confirmed all 4 planted errors are caught.
- **Section 14:** Grants.gov, SAM.gov and ProPublica are not checked (synthetic-only decision). They are marked `[VERIFY]` in the skill.

### Stage 3 (2026-11-05): impact-report-builder (kept simple for use inside Claude)
- **S1–S5:** structure tests pass (a 106-line router, 2 references, each saying when to read it).
- **W1–W9:** in SKILL.md. W5: every number comes from `impact.py`. W7: markers, DRAFT label, no composites. W9: unsupported outcomes are refused, not argued.
- **SC1–SC7:** one stdlib script with three subcommands, `--format json|md`, exit codes 0/1/2, and refusals on bad columns, kinds, config and ambiguous dates. **SC8 n/a:** `impact.py` never writes the state file; it writes only `metrics.json` when asked.
- **T1–T6:** 15 tests, including the answer key and the injected errors. Pack total: 164. Python 3.14.2: 164 pass. Python 3.9.6: 163 pass, 1 skipped.
- **E1–E3:** 8 cases (3 happy, 3 boundary, 2 trap). Two double-escaped regexes and one flawed grader were fixed before any run; the structure test now blocks double escapes.
- **Stage 3 gate:** every metric matches the hand-computed key exactly (20 served; 80.0% (16 of 20); Tutoring 83.3% (10 of 12); matched 16, dropped 4; 44.69 → 55.31, change 10.63; mean 44.0; median 45; Tutoring 12). Family Literacy (n=3) suppressed, plus Job Readiness as complementary. **The verifier caught 10 of 10 injected wrong numbers.**

### Stage 4 (2026-11-05): board-minutes-tracker
- **S1–S5:** structure tests pass. The router is under 130 lines, with 2 references.
- **W1–W9:** in SKILL.md. Never invents a vote, seconder or attendee (`[CONFIRM]`); never marks minutes approved; reminders are drafts; the recording-consent reminder doesn't state the law.
- **SC1–SC8:** one stdlib script, with `--format json|md` and exit codes 0/1/2. SC5: relative dates and group owners ("the board") are refused with a clear message. SC8: the tracker refuses to write if it changed since it was read, and a test covers it.
- **T1–T6:** 17 tests. Pack total: 181. Python 3.14.2: 181 pass. Python 3.9.6: 180 pass, 1 skipped.
- **E1–E3:** 10 cases (3 happy, 4 boundary, 3 trap). Judgment checks use judged graders, not word filters. A case with a setup script but no files was caught and fixed, and a test now guards against it.
- **Stage 4 gate:** lint catches **11 of 11** seeded errors, each applied alone: missing quorum, adjournment, call to order, attendance, seconder or outcome; a tally mismatch (7 yes + 2 no with 8 present); a recusal without a conflict declaration; discussion in executive session; no DRAFT banner; approved with open [CONFIRM] items. The first run missed 2 because of a real parser bug (an empty field read the next line), which is now fixed.

### Stage 5 (2026-11-05): donor-thank-you-writer
- **S1–S5:** structure tests pass (a 103-line router, 2 references).
- **W1–W9:** in SKILL.md. Only supplied impact facts; never sends; no inferring donors' circumstances; anonymous, honor and memorial handling; an unsupported claim is refused, not argued.
- **SC1–SC7:** one stdlib script, `--format json|md`, exit codes 0/1/2. SC5: refuses to segment until the org sets thresholds; bad amounts or dates stop with a message. **SC8 n/a:** `letters.py` doesn't write the state file.
- **T1–T6:** 11 tests. Pack total: 192. Python 3.14.2: 192 pass. Python 3.9.6: 191 pass, 1 skipped.
- **E1–E3:** 8 cases (3 happy, 3 boundary, 2 trap); the `wrong-amount` fixture fails lint only on the planted amount.
- **Stage 5 gate:** letter lint catches **11 of 11** seeded errors, each applied alone and each for its intended reason: wrong amount, missing name, invented number, invented statistic, overclaim, another donor named, missing goods/services statement, missing legal name, missing date, leftover placeholder, leftover marker. Writing the good letter exposed one bug first (an empty EIN made every number look unsupported), which is fixed.
- **Section 14:** the IRS acknowledgment thresholds are **not verified** (built offline); they're marked `[VERIFY]` in the config.

### Stage 6 (2026-11-05): pack docs, packaging, install test
- **K1:** all five skills packaged into `.skill` files by `tools/package_skills.py`. That's a standard-library copy of skill-creator's `package_skill.py` (same zip layout and exclusions, same frontmatter checks), because the original needs PyYAML. The original packager itself **was not run**. `evals/` is outside the skill folders, so it's never packaged.
- **K2:** script sizes are 188–772 lines; pii-guard's `scan.py` is the largest (single-file by design).
- **K3:** every skill is at 0.1.0, recorded in its state template and the changelog. The manifest is 0.1.0.
- **Install test:** `tests/test_packaging.py` (8 tests) unzips all five packages into a fresh folder and runs every script in isolated mode: every `--help`, the pii-guard self-test, grant-scout validate and rank, impact metrics, the minutes lint, and the letters `segment` refusal. It passes on Python 3.9.6 and 3.14.2. **Not tested:** uploading to Claude itself.
- **D2–D6, P4:** the README has install steps, owner and status, design decisions, the data-tier notice, known limits, assumptions, folder structure, packaging, a maintenance table and the changelog.
- **Docs:** GOVERNANCE (roles, review, versions, release checklist, incident process, retirement, quarterly review), RUNBOOK (install, update, rollback, state files, tests, evals, failure modes, who to call), TRAINING-30MIN (agenda, notes, 4 exercises on synthetic data, handout, 5-question quiz, feedback form), BREAK-IT-CHECKLIST (18 prompts in 7 groups, not run yet), ADOPTION-METRICS (log fields, no-overclaim rules). `tests/test_docs.py` (7 tests) checks the required content and that every sample file the docs name exists.
- **Tests:** pack total 207. Python 3.14.2: 207 pass. Python 3.9.6: 206 pass, 1 skipped.
