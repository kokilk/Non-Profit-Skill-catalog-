# Pack-level evals

> **Status: Stage 5.** 46 cases: pii-guard 9, grant-scout 11, impact-report-builder 8, board-minutes-tracker 10, donor-thank-you-writer 8. **None have been run yet.** All cases run with baselines at Stage 7.

## Case format (build spec §3.5, in the current `claude plugin eval` format)
```
evals/<skill>/<case-name>/
├── prompt.md                   frontmatter: description, tags: [happy|boundary|trap, <skill>], limits, tools
├── case.yaml                   schema_version "1.1", name, context.scaffold_script: place-files.sh
├── graders/NN-few-words.md     one check each: regex, llm (one PASS/FAIL statement), tool_used, file_exists
├── files/                      synthetic inputs, if any
└── place-files.sh              copies files/ into the empty workspace (run only with --scaffold)
```
Cases live in one root `evals/` because `claude plugin eval` reads a single eval directory. Grouping by skill folder is supported.

## Running (Stage 7)

```bash
claude plugin eval . --scaffold
```

This needs Claude Code v2.1.269 or later. Each case runs 3 times with the plugin and 3 times without; both scores and the difference are reported. `--scaffold` is needed because the cases copy their input files in with a script.

## Minimum per skill
At least 8 cases: 3+ happy path, 3+ boundary or refusal, 2+ traps where a careless model would fabricate or leak. grant-scout needs at least 10.

## How results are reported
- Every case is run **with and without** the skill.
- Report the model, date, number of cases, number of runs and raw counts ("17 of 20 expectations"), not percentages from small samples.
- Failing cases go into the README "Known limits" table.
- Results go in `evals/results/` (generated, one file per run).

## Runner
The format was checked against the docs on 2026-11-05. **No case has been run yet.** Still unconfirmed: how `place-files.sh` finds its case folder (it uses `BASH_SOURCE`).
