# Writing and verifying the report

Read this at steps 7–8, before drafting and when you verify a draft.

## 1. Structure

Use the funder's template if the user gives one. Otherwise:

1. **Summary of results:** 3–5 sentences, the headline numbers with denominators
2. **Who we served:** aggregate only
3. **What we did:** activities, from the org's description
4. **Outcomes against goals:** goals come from the user (`--allow` for their target figures)
5. **Stories:** only written stories the org supplies, with consent. Otherwise leave this out
6. **Challenges and what we learned**
7. **What the data can't tell us** (the limits section, always included)
8. **Next steps**
9. **Methods note:** data source, period, cleaning rules, metric definitions, min_cell

## 2. Honesty rules

- **Associated with, not caused by.** Pre/post change without a comparison group can't show the program caused it.
- **Every rate shows its denominator.** "80.0% (16 of 20)", not "80%".
- **Matched n for pre/post.** "Among the 16 with both scores; 4 had no ending score."
- **No rounding that changes a conclusion.** 49.6% is not "half".
- **No composites.** Never merge several people into one "story" presented as real.
- **Plans use "we aim to".** Only measured results are stated as results.

## 3. The limits section

Always say what applies: data gaps (blanks, missing post-scores), who dropped out and why it matters, self-reported measures, small groups that were suppressed, and anything the period or data source leaves out.

## 4. Verifying

Save the draft and run:

```
python3 scripts/impact.py verify report-draft.md --metrics metrics.json --allow 150,3
```

`--allow` is for numbers that legitimately aren't computed: the funder's own target, page or section numbers, the grant amount. Ask the user for each one; don't add numbers to make the check pass. Years (1900–2100) and anything inside `[NEEDS FROM ORG: …]` or `[CONFIRM: …]` markers are ignored.

Fix every flagged number by copying it from `metrics.json`, or remove the claim. Re-run until it passes. Report the result in the provenance block ("Verify: PASS, 16 numbers checked").
