# Governance

Who may change the pack, how changes are checked, and what to do if something goes wrong. Written for a small nonprofit with one owner and one backup.

## Contents
1. Roles
2. Changing a skill
3. Versions
4. Release checklist
5. Adding your own skill
6. What may be shared outside the org
7. Incident process (sensitive data exposed)
8. Retiring a skill
9. Quarterly review

## 1. Roles

| Role | Who | Does |
|---|---|---|
| Owner | `[NEEDS FROM ORG]` | Approves changes and releases, keeps the runbook current |
| Reviewer | `[NEEDS FROM ORG]` (anyone other than the person making the change) | Reads the change, runs the tests, reads the eval results |
| Data policy owner | `[NEEDS FROM ORG]` | Decides Amber use and Red exceptions (`DATA-TIERS.md`) |

## 2. Changing a skill

1. Make the change on a copy, not on the installed skill.
2. A second person reads every changed line (the diff), runs `python3 -m unittest discover tests`, and reads the eval results for that skill.
3. Behavior changes need a test or an eval case that shows the new behavior.
4. Update the README (status table, known limits, changelog) in the same change.

## 3. Versions

Each skill has its own version, starting at `0.1.0`. Bump the last number for wording or bug fixes, the middle number for any behavior change (a new step, a new rule, a new script option). Record every bump in the README changelog.

## 4. Release checklist

- [ ] All unit tests pass (`python3 -m unittest discover tests`)
- [ ] The changed skill's evals were run with and without the skill, and the results are recorded (`evals/README.md`)
- [ ] README updated: status, evidence level (never higher than reached), known limits, changelog
- [ ] Packages rebuilt (`python3 tools/package_skills.py`) and installed in a test account first
- [ ] `[VERIFY]` items touched by the change were re-checked, with the date

## 5. Adding your own skill

Copy the shape of an existing skill: `SKILL.md` (frontmatter, how to work, steps, scripts, boundaries, "when this goes wrong", reference index), `references/`, `scripts/` (standard library only), `assets/state-template.json`, and at least 8 eval cases in `evals/<skill>/`. The structure tests in `tests/test_skill_structure.py` check it automatically.

## 6. What may be shared outside the org

The skills, docs, tests and synthetic samples. **Never** real data, state files, mapping files, letters or minutes. Everything in `samples/` is synthetic; keep it that way.

## 7. Incident process (sensitive data exposed)

If Red or Amber data went somewhere it shouldn't (uploaded unredacted, pasted into a shared doc, a mapping file shared):

1. **Stop:** pause using the skill for that data.
2. **Contain:** delete the shared copy where you can; revoke links; tell whoever received it not to use it.
3. **Tell the data owner** (the data policy owner) the same day, with what, where, when and who.
4. **Record it:** date, what happened, what was exposed (described in categories, not by copying it), actions taken.
5. **Fix the cause:** a rule, a skill change, or training. Add a break-it case so it's tested from now on.

Legal or reporting obligations are the data policy owner's and counsel's call. This document doesn't decide them.

## 8. Retiring a skill

Remove it from Claude, mark it retired in the README status table with the date and the reason, and keep its folder for reference. Remind users to delete its state files when they no longer need them.

## 9. Quarterly review

Every three months the owner checks:
- `[VERIFY]` items: grant sources (Grants.gov, SAM.gov, ProPublica), the IRS acknowledgment thresholds, the plan-terms checklist
- The adoption log (`ADOPTION-METRICS.md`): what's used, what isn't, problems
- Any Claude feature changes that affect skills (how skills are installed, code execution)
