# Data tiers: Green, Amber, Red

Every skill in this pack sorts the data it is given into one of three tiers before doing anything with it, and behaves differently per tier. Each skill restates this briefly; this file is the single source.

**Why three tiers:** the people using this pack are not privacy experts. A rule they can remember beats a policy they will never read.

## Contents
- The tiers
- What to do per tier
- When in doubt
- Uploading sends data to the model
- Who decides

## The tiers

| Tier | Examples | Rule |
|---|---|---|
| **Green** | Public information, aggregate numbers, the org's own mission text, published grant information | Use freely. |
| **Amber** | Donor names and contact details, gift amounts, board minutes, staff names, internal finances, draft strategy | Use with the org's consent on their Claude plan terms. Run `pii-guard scan` first where individuals are named in bulk. Keep named data out of anything shared. |
| **Red** | Client-level case notes, health or mental health information, immigration status, domestic violence or shelter locations, minors' identifying details, financial account numbers, criminal history | The default is **do not process with the skill**. Offer to work on a de-identified or aggregate version instead. Do not draft a workaround. Point to the org's data policy owner. |

## What to do per tier

- **Green:** go ahead. Still cite where public facts came from.
- **Amber:** confirm the org is comfortable using this data with its Claude plan (see `skills/pii-guard/references/plan-terms-checklist.md`). Where many individuals are named, run `pii-guard` first. Never put named Amber data into anything meant to be shared beyond the people who already have it.
- **Red:** stop. Say which item made it Red, offer the aggregate or de-identified route, and name the person who can approve an exception (the org's data policy owner). Do not argue the case or draft a justification. A skill is a helper, not an approver.

## When in doubt

Treat it as the higher tier. A mixed file takes the tier of its most sensitive part: a donor list with one column of health notes is Red until that column is removed.

## Uploading sends data to the model

**Uploading a file to a chat sends it to the model.** A redaction step only protects data if it runs *before* upload (locally, with `pii-guard`'s script on your own machine) or if the sensitive file is never uploaded at all. Running a check after upload catches mistakes and stops further processing, but it cannot undo the exposure.

## Who decides

Whether Amber data may be used with an AI tool is the organization's decision, based on its own Claude plan's data-handling terms. This pack does not give legal advice. Fill in the name of the person who decides:

| Role | Name |
|---|---|
| Data policy owner | `[NEEDS FROM ORG: name]` |
| Backup | `[NEEDS FROM ORG: name]` |
