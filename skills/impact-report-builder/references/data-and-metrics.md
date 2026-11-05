# Data, cleaning and metrics

Read this at steps 3–6: reading the profile, proposing cleaning rules, writing the metrics config and explaining suppression.

## 1. Reading the profile

`impact.py profile` lists every column (type, blanks, distinct values) and the issues. Walk the user through the issues in this order:

1. **Identifying columns** (name, email, phone, address, birth date, notes): drop them unless the report needs them. If the file wasn't checked yet, stop and run pii-guard.
2. **Exact duplicate rows and repeated IDs:** usually a double export or double entry.
3. **Dates in several formats, or ambiguous dates** (03/02/2026): ask which format the system uses. Never guess.
4. **Blanks:** say how many, and what they mean for each metric (blank post-scores shrink the matched group).
5. **Extreme values** (beyond 3× the interquartile range): ask whether they're real or typos. Never drop them silently.

## 2. Cleaning, with consent

Propose one rule at a time, in plain words, with its effect: "Drop the 1 exact duplicate row (P-05 appears twice). That changes the row count from 21 to 20." Record each approved rule in `cleaning_rules` with who approved it and when.

- Exact duplicates: `"drop_exact_duplicates": true` in the config.
- Anything else (merging "Tutoring" and "tutoring", fixing a typo'd score): the user fixes it in their own file, or you produce a corrected CSV they approve. Either way, the rule is recorded and the report's methods note mentions it.
- Never delete rows to make results look better.

## 3. Writing the metrics config

Start from `assets/metrics-config-example.json`. Each metric:

```json
{"name": "completion_rate", "kind": "rate", "numerator_where": {"completed": "yes"},
 "where": {"cohort": "2026-spring"}, "group_by": "program",
 "meaning": "Share of enrolled people who completed"}
```

| Kind | Needs | Reports |
|---|---|---|
| `count_rows` | | rows |
| `count_unique` | `column` | different values (people served) |
| `sum`, `mean`, `median` | `column` | value and n; non-numbers left out with a count |
| `rate` | `numerator_where` | percent with numerator and denominator (the denominator is every row in scope) |
| `change_pre_post` | `pre`, `post` (and `id_column`) | mean pre, mean post, change; matched n and dropped n |

`where` limits rows (equality, or a list of allowed values). `group_by` splits any metric by a column. Read every definition back to the user in plain language ("Completion rate: people marked completed, out of everyone enrolled in spring 2026, by program") and get a yes before computing.

## 4. Small groups and suppression

Groups with fewer than `min_cell` people are hidden. The default is 5, a common practice threshold, not a legal rule. It's the org's policy choice; record who chose it. When exactly one group is hidden, the next smallest is hidden too (**complementary suppression**). Otherwise the total minus the visible groups would reveal the hidden one.

Report suppressed groups as "fewer than 5 (not shown to protect privacy)". Never recover the number another way.
