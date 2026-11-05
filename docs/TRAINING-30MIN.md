# 30-minute training

For staff and volunteers who will use the pack. Everything runs on `samples/` (synthetic data only). Nobody brings real files to the session.

## Contents
1. Agenda
2. Facilitator notes
3. Hands-on exercises
4. One-page handout
5. Quiz (five questions)
6. Feedback form

## 1. Agenda

| Minutes | Block | What happens |
|---|---|---|
| 0–5 | Why, and the data tiers | Green / Amber / Red with one example each; "uploading sends data to the model" |
| 5–10 | Demo: pii-guard | Facilitator scans `samples/data/donors.csv`, shows the masked summary, redacts, verifies |
| 10–20 | Hands-on | Pairs do one exercise (§3); grant-scout recommended |
| 20–25 | Where it goes wrong | Show 3 refusals: invented grant, Red case notes, "send it for me" |
| 25–30 | Who owns what next | Name the owner, backup and data policy owner; how to report a problem; feedback form |

## 2. Facilitator notes

- Before the session: install the skills in a test account; have the sample files ready to upload.
- Say plainly what the pack is not: not legal or tax advice, never sends or submits anything, and every result is a draft someone checks.
- When something goes wrong in the demo, that's useful: show how the skill flags it.

## 3. Hands-on exercises (pick one per pair)

| Skill | Exercise | Done when |
|---|---|---|
| grant-scout (recommended) | Upload `samples/grants/grant-pipeline-riverbend.json`. Ask "which grants can we apply to?" | You can say why G-04 is not eligible and what question G-12 needs answered |
| impact-report-builder | Upload `samples/impact/cohort.csv` and `metrics-config.json`. Ask for a one-paragraph summary | Every number in it passed `verify`; you can say why Family Literacy isn't shown |
| board-minutes-tracker | Paste `samples/minutes/notes-oct.txt`. Ask for draft minutes | You've answered the `[CONFIRM]` questions and lint passes |
| donor-thank-you-writer | Upload `samples/data/donors.csv` and `samples/letters/`. Ask for the G-0001 letter | Lint passes and the letter uses only supplied facts |

## 4. One-page handout

**The pack in one page**
- **Five helpers:** pii-guard (privacy check first), grant-scout, impact-report-builder, board-minutes-tracker, donor-thank-you-writer.
- **Green** = public or totals: fine. **Amber** = names, amounts, minutes: OK with care, run pii-guard first for lists of people. **Red** = client case notes, health, immigration, shelter, children's details, card numbers: **don't**.
- **Uploading a file sends it to the model.** Check people-lists *before* uploading.
- **Everything is a draft.** You check it, you approve it, you send or submit it.
- **Markers:** `[NEEDS FROM ORG]` = we must supply it; `[CONFIRM]` = check this; `[VERIFY]` = check an outside fact. Anything with a marker isn't final.
- **Keep your state file** (the `.json` it gives you) and attach it next time.
- **Problems?** Tell `[NEEDS FROM ORG: owner]`.

## 5. Quiz (five questions)

1. A spreadsheet lists clients with their housing situation and health notes. Which tier? *(Red: don't process; ask for counts instead.)*
2. When does pii-guard actually prevent exposure? *(When it runs on your own computer before upload.)*
3. grant-scout lists a grant as an "unverified lead". What does that mean? *(Nobody has confirmed it on the funder's own page; it isn't presented as open or eligible.)*
4. The impact draft says "85% completed" and `verify` fails. What do you do? *(Copy the number from metrics.json, 80.0% (16 of 20); don't add it to the allowed list.)*
5. Who sends the thank-you letters? *(You do. The skill never sends.)*

## 6. Feedback form

1. What worked?
2. What confused you?
3. What would you use this week?

Record answers (without names) in `ADOPTION-METRICS.md` under "Training feedback".
