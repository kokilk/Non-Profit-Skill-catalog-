# Searching and recording grants

Read this at steps 2–4: agreeing the search plan, deciding where to look, opening funder pages, and writing grant records.

## Contents
1. The search plan
2. Where to look
3. Opening the funder's page
4. Writing the record
5. Saying what was not covered

## 1. The search plan

Agree on these before searching, and store them in `search_plan`:

- **Focus:** federal, state, local, foundation, corporate (one or several)
- **Geography** and **issue areas** (from the profile)
- **Ask range** and **deadline window** (for example, deadlines in the next 2 to 6 months)

A narrow plan with honest coverage beats a wide one that skims.

## 2. Where to look

These sources are the starting points. Their current details have not been re-checked for this version of the skill: confirm each as you use it, and mark anything you couldn't confirm `[VERIFY: …]`.

| Kind | Where | Notes |
|---|---|---|
| Federal | Grants.gov listings | Federal applications generally need SAM.gov registration with a UEI `[VERIFY]`; make it an eligibility item with its lead time |
| Foundations | The foundation's own site and published guidelines | Guidelines on the funder's site are the source of truth |
| Foundations (giving history) | Form 990 and 990-PF filings, for example through ProPublica's Nonprofit Explorer | Shows what a funder actually gave and in what sizes. Use it for fit, not eligibility |
| Local | Community foundations, city and county grant pages | Often the best fit for small orgs |
| State | State agency grant portals | Varies by state |
| Corporate | Company community-investment pages | Often regional and invitation-based |
| Paid directories | Foundation directories at a public library | Mention as an option; never assume access |

## 3. Opening the funder's page

For every candidate:

1. Open the funder's **own** page for the program, not a blog post or a list of grants.
2. Note what the page says about status (open, rolling, closed), the deadline, the award range, who can apply, and any requirements (registration, audit, match, invitation only).
3. Note **where on the page** each item is (section heading), for `deadline_source` and `source_quote_location`.
4. Record today's date as `checked_on`.

If the page doesn't open, or doesn't state the deadline or eligibility, don't fill the gap from a search snippet or memory. Record what the page does say; the record stays an unverified lead or `status: unknown`.

## 4. Writing the record

Use `assets/grant-record-template.json`.

- **Paraphrase closely; don't copy long passages.** Keep the requirement's meaning exact.
- **`kind: hard`** for requirements ("must", "only", "eligible applicants are"); **`kind: preference`** for priorities ("we prioritize", "preference for").
- **Add a `check`** when a criterion maps onto a profile field (`tax_status`, `geography`, `annual_budget` …). Ops: `in`, `not_in`, `equals`, `is_true`, `is_false`, `lte`, `gte`, `overlaps`. If it doesn't map, leave `check` out: `rank.py` turns it into an `unknown` with a question.
- **`requires`**: set `sam_uei`, `audit`, `match_funds`, `prior_relationship` (invitation only) when the page says so.
- Run `python3 scripts/validate.py {state} --update`. Fix what it lists, or leave the grant as a lead.

## 5. Saying what was not covered

Every results message lists the sources you actually searched and the ones you didn't ("Searched: Grants.gov, 3 community foundations in Franklin County. Not searched: corporate giving, state portals, paid directories"). Store both lists in `search_plan`. If a search for "a grant for X" finds nothing you could verify, say exactly that. Don't offer a plausible-sounding program instead.
