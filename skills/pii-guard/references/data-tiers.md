# Data tiers: classifying before you scan

Read this at step 1, and whenever the tier is unclear or the user pushes back on a Red decision. The pack-wide version is `docs/DATA-TIERS.md`; this file adds what pii-guard does at each tier and what to say.

## Contents
1. The tiers
2. Questions to ask at step 1
3. Mixed files
4. When the data is Red: what to say
5. The aggregate route
6. When the user pushes back

## 1. The tiers

| Tier | Examples | Rule |
|---|---|---|
| **Green** | Public information, aggregate numbers, the org's own mission text, published grant information | Use freely. |
| **Amber** | Donor names and contact details, gift amounts, board minutes, staff names, internal finances, draft strategy | Use with the org's consent on their Claude plan terms. Run `pii-guard scan` first where individuals are named in bulk. Keep named data out of anything shared. |
| **Red** | Client-level case notes, health or mental health information, substance use, immigration status, domestic violence or shelter locations, minors' identifying details, financial account or card numbers, criminal history | Do not process with the skill. Offer a de-identified or aggregate version instead. Do not draft a workaround. Point to the org's data policy owner. |

**Why three tiers:** the people using this are not privacy experts. A rule they can remember beats a policy they will never read.

## 2. Questions to ask at step 1

Ask only what you don't already know, in one message:

1. What is it? (donor list, sign-in sheet, case notes, meeting notes, survey export…)
2. Where did it come from? (CRM export, a spreadsheet staff keep, a form)
3. Is it still only on your computer, or already uploaded here? (decides Mode A or B)
4. Does it describe clients or program participants as individuals, or only totals?

Then say the tier and the reason in one line: "This is Amber: it names donors and has their contact details."

## 3. Mixed files

A file takes the tier of its most sensitive part. A donor list with one "notes" column that mentions a donor's illness is Red until that column is gone. The fix is usually simple: drop the column (`--drop-columns notes`) and re-scan. Say which column and why, without quoting it.

The scanner's own verdict counts too: if `scan` suggests Red (a card number, or health, immigration, shelter, minors, criminal-justice or substance-use context), treat the file as Red even if the user described it as a donor list. Show the masked finding, not the text.

## 4. When the data is Red: what to say

Keep it short and kind; the user is usually trying to do something good.

> This file is Red: it has [client case details / health information / …] about individuals. I don't process Red data, even redacted, because people can often still be identified from what's left and the harm if that happens is serious.
> What I can do instead: help you build a summary with counts only (for example, people served by program and month), then work from that.
> If you need an exception, that's a decision for [the org's data policy owner].

Then stop. Don't redact it "just to see", don't summarize it, don't extract "only the numbers" from the Red file yourself.

## 5. The aggregate route

Help the user produce Green or Amber data from the Red source **themselves**, outside the chat:

- Suggest the counts they need: totals by program, month, age band, outcome category, never by person.
- Suggest suppressing small groups (fewer than 5 people is a common practice threshold; the org decides) so a count can't point to one person.
- Offer a blank CSV header they can fill in from their own system.
- Once they bring back the aggregate, classify it again. It's usually Green.

## 6. When the user pushes back

"It's fine, I have permission." "Just this once." "The names are fake anyway."

- State the rule, the reason (exposure can't be undone; redaction isn't anonymization), and the approver.
- Don't argue, negotiate, or draft the justification for them.
- If they say an exception was approved, ask them to record who approved it and when in their state file, and still offer the aggregate route first. The skill doesn't process Red data; an approved exception changes what the org may do, not what this skill does.
