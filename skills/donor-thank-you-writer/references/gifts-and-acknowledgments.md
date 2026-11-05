# Gifts, acknowledgments and segments

Read this at steps 4–5, when checking the gift list, deciding acknowledgment content, and segmenting donors.

## 1. Gift checks

`letters.py check` needs at least `gift_id, donor_id, first_name, last_name, gift_date (YYYY-MM-DD), amount`. Optional: `email`, `street`, `gift_type` (recurring), `tribute`, `anonymous`, `goods_services_value`. Walk through what it flags:

- **Refunds and zero amounts:** no letter.
- **Possible duplicates** (same donor, date, amount): ask before writing two letters.
- **No name:** don't invent one. **No email or address:** no way to send; ask.
- **Anonymous, tribute, recurring:** see `letter-craft.md` §3–4.

## 2. Acknowledgment basics (US reference points: verify)

The config holds two values the skill treats as **reference points to verify with the org's accountant**, marked `[VERIFY]`. They haven't been checked against current IRS guidance in this version:

- A **written acknowledgment** is generally needed for a single contribution of **$250 or more**, for the donor to claim a deduction. For those gifts the letter includes the org's legal name, the amount, the date, and either "No goods or services were provided in exchange for this contribution" or a description and good-faith estimate of what was provided.
- A gift where the donor receives goods or services (a gala dinner, say) above a set amount (commonly cited as **more than $75**) needs a disclosure statement with the value of what was received.

When `goods_services_value` isn't in the list, `check` asks you to confirm, for each gift at or above the threshold, whether anything was given. Never assume "no goods or services" for an event or gala gift. Other countries differ. This skill doesn't give tax advice or decide deductibility.

## 3. Segments

Ask the org two questions and record the answers (and who decided) in `thank-you-config.json`: the **major-gift amount**, and after **how many months without a gift** a donor counts as lapsed. `segment` refuses until both are set.

History comes only from the gift file you're given. A donor whose earlier gifts aren't in it shows as first-time, so ask whether the file covers the donor's whole history before writing "your first gift".
