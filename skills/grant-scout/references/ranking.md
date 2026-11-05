# Reading and explaining the ranking

Read this at step 5, when you run `rank.py` and explain its output.

## Contents
1. The five buckets
2. Explaining a score
3. Unknowns and questions
4. Weights

## 1. The five buckets

| Bucket | Meaning | How to present it |
|---|---|---|
| **Ranked** | Every hard gate passes | Score with its components, deadline, source URL and checked date |
| **Needs checking** | No hard gate fails, but at least one is unknown (or the status is unknown, or SAM.gov registration is pending) | List the exact questions `rank.py` gives. Batch them in one message |
| **Not eligible, because…** | A hard gate fails | The requirement and where the page says it. Shown, not hidden: the user may know something the profile doesn't |
| **Closed** | The page says closed, or the deadline has passed | Offer a follow-up date for the next cycle |
| **Unverified leads** | The record fails `validate.py` | "Lead, not checked." Never call these open or eligible |

## 2. Explaining a score

Never give a bare number. Say what it rests on:

> **Maple Fund Invitational: 100** (issue match 1.0, award fit 1.0, deadline 1.0; preferences not scored: the page lists none).

Components: `issue_match` (share of the grant's issue areas the org works in), `award_fit` (1 inside the range, 0.5 overlapping, 0 outside), `preferences_met`, and `deadline_feasibility` (days left against the org's days needed; rolling = 1). Unknown components are left out, and the output lists them. A score built on two components is weaker than one built on four: say so.

The score orders the eligible grants. It doesn't predict funding. Don't describe a high score as a "strong chance".

## 3. Unknowns and questions

Unknown is an answer, not a failure. For each grant in "needs checking", show the questions `rank.py` produced, ask the user, add their answers as profile facts with sources, and re-run. If the question is about the funder ("Is the program open?"), the answer has to come from the funder's page or the funder, not from the user's guess.

## 4. Weights

Show the weights line from the output every time. They live in `assets/rank-weights.json`. If the org wants different weights, use a copy (`--weights`) and record the change and the reason in `change_log`. Never adjust weights to push a particular grant up.
