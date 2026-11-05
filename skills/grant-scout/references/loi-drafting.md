# Drafting a letter of inquiry

Read this at steps 7 and 8, before drafting any LOI and when you review one with the user.

## Contents
1. Structure
2. Tracing every claim
3. What never goes in
4. Review and the fact-trace table
5. Tone

## 1. Structure

Follow the funder's stated length and format if the page gives one. If not, keep it to one page:

1. **Need:** the problem, in the community the org serves, using only numbers the org supplied
2. **Org and capacity:** who the org is, how long it has done this, its size
3. **Project and approach:** what the money would do
4. **Expected outcomes:** "we aim to…" for plans; measured results only if the org gave them
5. **The ask:** amount (from `ask_amount`), period, and what it covers
6. **Closing:** contact line from the org, an invitation to talk

Echo the funder's priorities in plain language. Don't copy the funder's wording.

## 2. Tracing every claim

Every factual statement carries a fact ID while drafting, `[F-07]`. Remove the tags only in the final copy the user approves, and keep the fact-trace table with the draft.

- No fact ID means no claim. Write `[NEEDS FROM ORG: number of students served last year]` instead.
- Facts about the funder come only from its page, tagged with the grant ID: `[G-03]`.
- Anything from outside the org and the funder's page that needs a human check: `[VERIFY: …]`.

## 3. What never goes in

- Invented statistics, outcomes or quotes.
- Superlatives ("leading", "unique", "only") unless the org supplied evidence as a fact.
- Outcomes the org hasn't measured, stated as results. Use "we aim to".
- Client names, stories or case details (Red data). Aggregate numbers only.
- Promises about the funder's decision, or what the funder "wants" beyond its page.

## 4. Review and the fact-trace table

Show the draft with this table beneath it:

| # | Claim in the letter | Fact ID | Source of the fact |
|---|---|---|---|
| 1 | "Founded in 2014" | F-06 | Executive director, 2026-11-05 |
| 2 | "We serve about 300 students a year" | F-10 | 2025 annual report (org-supplied) |
| 3 | "Your fund prioritizes early literacy" | G-02 | Funder page, "Priorities" (checked 2026-11-01) |

Then ask one question: approve, or what to change. While any marker remains, the top line reads **DRAFT: n items needed before this can be sent**. Store the draft and its table in `lois[]` in the state file. The org submits; you don't.

## 5. Tone

Warm, specific, short sentences, no jargon. Write as the org ("we"), to a person if the page names one. One page is a ceiling, not a target.
