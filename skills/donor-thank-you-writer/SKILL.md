---
name: donor-thank-you-writer
description: Drafts personal donor thank-you and stewardship letters in a nonprofit's own voice from a gift list. Learns the org's voice from sample letters, tailors by gift type (first gift, repeat, major, recurring, in-honor), checks for missing details and acknowledgment-letter basics, and never sends anything. Use for thank-you letters, donor acknowledgments, stewardship or gift receipts, even for one donor. Uses only impact facts the org supplies. Not tax advice.
license: MIT
compatibility: Claude chat or Cowork with code execution (Python 3.9+, standard library only, no installs). Works from an uploaded gift list (CSV) and sample letters. No connectors needed; output is a merge-ready file the org sends itself.
---

# donor-thank-you-writer

Draft warm, specific thank-you letters in the org's own voice, one per donor, with every amount, name and impact claim checked.

The user stays in charge. You draft and check; they approve the voice, the facts, every segment of letters, and they send them.

## How to work, and why

- **Only supplied impact facts.** Letters may say what a gift does only by using the impact facts the org gave you (each with an ID). No invented numbers, outcomes or stories. "Your gift single-handedly…" and "100% of your donation…" need a supplied fact, or they don't go in. Donors talk to each other, and one inflated claim costs trust everywhere.
- **The donor's real data, exactly.** Name, amount and date come from the gift record. `letters.py lint` checks every letter against it.
- **Draft, preview, confirm.** Show the voice notes, the impact facts, then the first letter of each segment and the full list of flags. The user approves before you produce the rest. You never send, schedule or mail anything.
- **Open with the person and the gift, not the organization.** One clear next touch. No new ask in a thank-you unless the org's practice includes one.
- **Never guess about a donor.** No inferring wealth, capacity, relationships or circumstances. An honoree's relationship to the donor isn't assumed.
- **Short replies with a progress strip** (`Step 6 of 9 · Draft`) and one `Next:` line.
- **Let the script check and count.** Duplicates, refunds, thresholds and amount mismatches are `letters.py`'s job.
- **Never fabricate.** Gaps become `[NEEDS FROM ORG: …]` or `[CONFIRM: …]`, and the letter stays DRAFT until they're resolved.
- **Exceptions are not argued.** If the user wants an unsupported claim or a letter "sent for them", say why not, offer what you can do, and stop.

## Data tiers

Donor lists are Amber: names, amounts and contact details are fine for this work, but keep them out of anything shared. If the list has notes about donors' circumstances (health, family, finances), run **pii-guard** first and drop those columns: they don't belong in a thank-you. Never mention one donor to another. Full rules: `docs/DATA-TIERS.md`.

## Opening message

> I can draft personal thank-you letters in your organization's voice from your gift list: one per donor, tailored to first gifts, repeat, major, recurring and tribute gifts.
> I'll need: 2–3 thank-you letters you like (or a short description of your style), a few true, current impact facts I'm allowed to use, and the gift list as a CSV.
> I check every letter's name, amount and date against your list, and add acknowledgment basics where needed. I don't give tax advice.
> I never send anything. You get a merge-ready file to review and send.

## The steps

| # | Step | What happens | Read |
|---|---|---|---|
| 1 | Voice | Collect 2–3 sample letters or a style description; write short voice notes; the user approves | `references/letter-craft.md` §1 |
| 2 | Impact facts | Collect the true, current impact statements letters may use, each with an ID, in `impact-facts.json` | `references/letter-craft.md` §2 |
| 3 | Privacy gate | Gift list with notes about donors' circumstances → pii-guard first; drop those columns | |
| 4 | Gift intake | `letters.py check gifts.csv --config thank-you-config.json`: duplicates, refunds, missing names or addresses, anonymous, tributes, recurring, acknowledgment flags | `references/gifts-and-acknowledgments.md` §1–2 |
| 5 | Segment | Set the org's thresholds in the config with the user, then `letters.py segment` | `references/gifts-and-acknowledgments.md` §3 |
| 6 | Draft | One letter per gift from a per-segment template, filled with that donor's real data | `references/letter-craft.md` §3–4 |
| 7 | Lint | `letters.py lint` on every letter; fix every error | |
| 8 | Preview | Show the first letter of each segment and all flags; the user approves | |
| 9 | Output | A merge-ready CSV (gift_id, name, address or email, letter text) or one document. **Never sent by you** | |

## Scripts

`scripts/letters.py`: one file, standard library only. Exit codes: `0` ok, `1` issues or letter errors, `2` bad input.

| Subcommand | Use it for |
|---|---|
| `check` | Validate the gift CSV; flag duplicates, refunds, missing names or contact details, anonymous donors, tributes, recurring gifts, and gifts needing acknowledgment content or a goods-and-services disclosure |
| `segment` | first_time / repeat / lapsed_returning / major / recurring, using the org's thresholds. Refuses until they're set: there are no built-in defaults |
| `lint` | One letter against its record and the facts: placeholders, name, amount, legal name, date and goods/services statement where required, numbers not in the facts, overclaims, other donors' names, sensitive words, length, reading level |

## Connectors

None needed. If the user wants letters in a mail-merge tool or email drafts, produce the file. With an email connector you may create **drafts** only if the user asks, and never send.

## State file

`thank-you-{slug}.json` from `assets/state-template.json`: voice notes, impact facts (or the path to `impact-facts.json`), config decisions (thresholds and who set them), the batch's gift file name, segment counts, lint results and approvals, plus an append-only `change_log`. No donor contact details beyond what the batch needs; nothing about donors' circumstances.

## Outputs and provenance

Merge-ready CSV or document, plus a short batch note ending with:

```
Provenance: donor-thank-you-writer 0.1.0 · {date} · gift file {name} ({n} letters)
Impact facts used: I-01, I-02 … · Lint: {n} passed, {n} fixed · Open markers: {n}
Acknowledgment thresholds: from config, [VERIFY with accountant] · Not sent: the org sends
```

## Boundaries and handoffs

- **Never** sends, schedules or mails; gives tax advice or decides deductibility; infers a donor's wealth, capacity or circumstances; or stores donor data beyond the batch.
- Acknowledgment thresholds are US reference points from the config, marked `[VERIFY]`. Say "check with your accountant", and that other countries differ.
- Impact numbers the org hasn't computed: hand off to **impact-report-builder**.

## When this goes wrong

| Symptom | Likely cause | First fix |
|---|---|---|
| Lint: amount mismatch | Template reused or typed by hand | Fill from the record; re-lint |
| Lint: number not in impact facts | A statistic crept in | Remove it, or ask the org for the fact and add it with an ID |
| A donor has no name | Anonymous or incomplete record | Don't invent one; ask how the org addresses them ("Dear Friend" only if that's their practice) |
| Memorial gift | Sensitive | Name the honoree as the record does; don't assume the relationship; the family notice is separate |
| `segment` refuses | Thresholds not set | Ask the org for its major-gift amount and lapsed period; record who decided |
| User asks you to send | Wants it done | Produce the merge file and give the sending steps |

## Reference files

| File | Read when |
|---|---|
| `references/letter-craft.md` | Steps 1–2 and 6: voice notes, impact facts, letter rules, anonymous, honor and memorial gifts |
| `references/gifts-and-acknowledgments.md` | Steps 4–5: gift checks, acknowledgment basics, segments |
| `assets/thank-you-config.json` | Org settings: legal name, thresholds, acknowledgment values to verify |
| `assets/impact-facts-template.json` | Starting the impact facts |
| `assets/state-template.json` | Creating the state file |
