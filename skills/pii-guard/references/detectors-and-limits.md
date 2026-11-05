# Detectors and their limits

Read this at steps 2–3, and whenever you explain what the scan did or didn't find. Never say more about coverage than this file supports.

## Contents
1. What each detector does
2. Reading the scan summary
3. Helping the user decide
4. Measured accuracy (and what it doesn't tell you)
5. Redaction is not anonymization
6. Honest wording

## 1. What each detector does

| Type | Method | Confidence | Known gaps |
|---|---|---|---|
| EMAIL | Pattern | High | Obfuscated forms ("pat at example dot org") are missed |
| PHONE | US forms with separators (`(212) 555-0147`, `212.555.0147`, `+1 212 555 0147`) and `+`-prefixed international numbers | High | Numbers written without separators are skipped on purpose, so budget codes don't match. International groups longer than 5 digits are missed (see §4) |
| CARD | Runs of 13 to 19 digits that pass the Luhn check | High | About 1 in 10 random long numbers pass Luhn by chance, so an order number can be flagged. Any CARD hit makes the data Red |
| DOB | A date **next to** a cue: "DOB", "D.O.B.", "date of birth", "birthdate", "born", "born on" | High | Dates alone are never flagged. A birth date with no cue ("Age: 04/22/2001") is missed |
| ADDRESS | Street number + 1 to 3 capitalized words + street suffix, plus ", City, ST 12345" when present | Medium | PO boxes, rural routes, apartment-only lines and non-US formats are missed. ZIP codes on their own are not flagged |
| IP | IPv4 and IPv6, validated | High | |
| URL_ID | URLs with a path or query part of 12+ letters/digits containing a digit | High | Short IDs in URLs are missed |
| ID_NUMBER | Only the org's own patterns (`--id-patterns`, JSON) | As good as the patterns | Nothing is checked without a patterns file |
| NAME_LISTED | Exact, case-insensitive whole-name match against the org's names file (`--names`) | Highest for names | Nicknames, misspellings and first-name-only mentions are missed |
| NAME_CUE | A capitalized name after "Mr.", "Ms.", "Mrs.", "Mx.", "Dr.", "Miss", "client", "participant", "patient", "resident", "student", "tenant", "member", "donor", "volunteer" | **Low** | Any name without a cue word is missed; capitalized non-names after a cue can be flagged |
| SENSITIVE_CONTEXT | Keyword families: health, mental health, immigration, domestic violence and shelter, minors, criminal justice, substance use | Flag only | **Flags, does not redact.** Any hit makes the data Red. Keyword lists miss paraphrases ("sober since March") |

**Not detected at all:** Social Security numbers (out of scope for this pack), bank account and routing numbers without a card-like pattern, driver's licence and passport numbers (unless the org adds an ID pattern), photos, and anything in Word, Excel or PDF files that wasn't exported to CSV or text.

## 2. Reading the scan summary

The summary shows, per type: the count, where it was found (line numbers for text, column names for CSV), up to three **masked** examples, and the confidence. It also suggests a tier and lists CSV columns whose names look identifying (name, email, phone, address, zip, notes…). Pass on the summary; don't add values to it.

If the summary is empty, say "the scanner found nothing it recognizes", not "the file is clean". Then ask whether the file has people's names, because names are only caught with a names file or a cue word.

## 3. Helping the user decide

Ask one question at a time, starting with the most consequential:

1. **Red findings?** Stop (see `data-tiers.md` §4). If a column is the cause, offer `--drop-columns`.
2. **Columns that are pure identifiers** (first_name, last_name, email): offer `--mask-columns` for ones the analysis still needs to tell apart (each value becomes a consistent token), and `--drop-columns` for ones it doesn't need at all. Dropping beats masking: data that isn't there can't leak.
3. **Names in free text:** recommend a names file. It's the single biggest improvement to name coverage.
4. **Anything to keep?** (`--keep ADDRESS` if the task is about service areas, for example.) Record the choice and the reason in the state file.

## 4. Measured accuracy (and what it doesn't tell you)

Run `python3 scripts/scan.py selftest` to reproduce these numbers.

**Synthetic corpus** (1,478 template-built records; 1,660 labeled values; 200 negative records): every detector scored 100% recall and 100% precision as of 2026-11-05. **Treat that as a consistency check, not a quality claim.** The corpus and the detectors were written by the same builder from the same format list, so this number shows the detectors handle the formats they were designed for, and nothing more.

**Hand-written holdout** (35 records in formats the generator never produces), 2026-11-05: 20 of 24 labeled values found, with 0 false positives, and 6 of 7 sensitive-context lines flagged. The misses:

| Missed | Why |
|---|---|
| `+44 7700 900123` (UK mobile) | A 6-digit group; the international pattern allows up to 5 |
| Two names with no cue word and not in the names file | By design: only a names file catches these |
| "sober since March" (substance use) | The keyword list has "sobriety", not "sober" |

These misses are kept in the holdout on purpose so the number stays honest. Real documents are messier than either set: expect lower recall, especially for names and addresses.

## 5. Redaction is not anonymization

Say this whenever a redacted copy is handed off:

- **Small groups identify people.** "The one participant over 65 in the evening cohort" is identifiable without a name.
- **Combinations identify people.** Age band + ZIP + a rare condition can point to one person even with every name removed.
- **Free text leaks.** "Her brother runs the bakery on Main" names nobody and identifies someone.
- **The mapping file reverses everything.** Anyone with the redacted copy and the mapping file has the original.

## 6. Honest wording

| Say | Never say |
|---|---|
| "a redacted copy; review before use" | "anonymized", "de-identified", "safe", "clean", "compliant" |
| "the scanner found nothing it recognizes" | "there's no personal information in this file" |
| "names are best effort without a names file" | "all names were removed" |
| "verify passed: no recognized identifiers are left" | "verified safe to share" |
