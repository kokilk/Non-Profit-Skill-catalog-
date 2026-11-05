# Synthetic samples

Everything in this folder is invented. No real people, organizations, accounts or credentials appear anywhere. The data drives the unit tests, the evals and the training session.

## Contents
- How to regenerate
- What's here
- Why each value can't be real
- Deliberate edge cases
- Stage-specific fixtures

## How to regenerate

```bash
python3 samples/generate.py            # write samples/data
python3 samples/generate.py --check    # exit 1 if the committed files are out of date
```

The output is deterministic: the same seed (default `20261105`) produces byte-identical files on Python 3.9 and later. `data/MANIFEST.json` records the seed, the generator version, and a sha256 and line count for every file. Don't edit files in `data/` by hand. Change the generator and regenerate instead, otherwise `--check` and the tests will fail.

## What's here

| File | Used by | What it is |
|---|---|---|
| `data/donors.csv` | donor-thank-you-writer, pii-guard | 60 gifts from a pool of 45 donors, with names, emails, phones and addresses |
| `data/participants.csv` | impact-report-builder | 120 program participants: program, cohort, age band, pre/post scores, completion. No names |
| `data/pii/corpus.jsonl` | pii-guard `selftest` (a copy ships in `skills/pii-guard/assets/selftest/`) | 1,478 short text records, each with labeled spans (`type`, `start`, `end`, `value`) and `context_families` |
| `data/pii/names-list.txt` | pii-guard NAME_LISTED | The kind of names file an org would supply |
| `data/pii/id-patterns.json` | pii-guard ID_NUMBER | The kind of case-number and member-ID patterns an org would configure |

### Corpus labels

Records are built from templates, so every identifier in the text is labeled exactly, with nothing missed and nothing extra. That makes it possible to measure both recall and precision.

| Label | Count | Notes |
|---|---|---|
| EMAIL | 200 | |
| PHONE | 250 | US formats plus UK `+44 20 7946 0xxx` |
| CARD | 100 | Published test numbers, plain or grouped |
| DOB | 200 | Only the date is labeled. The cue ("DOB:", "born", "Date of birth") sits beside it |
| ADDRESS | 100 | Street number + street + suffix, city, state, ZIP |
| IP | 100 | IPv4 and IPv6 documentation ranges |
| URL_ID | 50 | URLs with a long ID parameter |
| ID_NUMBER | 150 | `CASE-YYYY-NNNNNN` and `MBRNNNNNNN` |
| NAME_LISTED | 250 | Full names that appear in `names-list.txt` |
| NAME_CUE | 260 | Surnames after "Ms.", "Mr.", "client" or "participant". These come from a separate surname pool, never from the names list |

There are also 28 sensitive-context records (4 for each of the 7 families: health, mental_health, immigration, domestic_violence_shelter, minors, criminal_justice, substance_use) and 200 **negative** records: order numbers that fail the Luhn check, plain dates, invoice numbers, budget codes and public URLs. A detector must leave the negative records alone. They're how precision is measured.

## Why each value can't be real

| Value | Source |
|---|---|
| Emails | `example.org`, `example.com`, `example.net`: reserved for documentation (RFC 2606) |
| US phones | `555-0100` to `555-0199`: reserved for fictional use |
| UK phones | `020 7946 0000` to `0999`: Ofcom's range for drama |
| IPs | `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` (RFC 5737) and `2001:db8::/32` (RFC 3849) |
| Cards | Payment providers' published test numbers. They pass the Luhn check but are not accounts |
| SSNs | **None.** The pack does not handle Social Security numbers (owner decision, 2026-11-05). A test fails if an SSN-shaped value appears in any sample file |
| Names | Random first name + surname pairs. The surnames are deliberately uncommon. A pairing may match a real person by chance. It isn't anyone |
| Organization | "Lantern Hill Learning Collective (synthetic)", an invented name |
| Addresses | Real US city and state names, invented street names, random ZIPs |


## Deliberate edge cases

These are in `donors.csv` at fixed rows, so tests and evals can rely on them:

| Gift | Edge case |
|---|---|
| G-0005 | Anonymous donor |
| G-0010 | Tribute: in memory of |
| G-0015 | Tribute: in honor of |
| G-0020 | Missing email |
| G-0025 | Refund (negative amount) |
| G-0030 | Duplicate of G-0029 under a new gift ID |

## Stage-specific fixtures

Grant records (Stage 2), messy participant variants with hand-computed answer keys (Stage 3), meeting notes (Stage 4) and letter fixtures (Stage 5) are written in their own stages, under `samples/`. They follow the same rules.
