#!/usr/bin/env python3
"""Synthetic sample data for the nonprofit skill pack. Standard library only (Python 3.9+).

Every value is invented, and every identifier comes from a reserved or
documented-fictional range, so no real person is described:
  emails      example.org / example.com / example.net (RFC 2606 reserved domains)
  phones      NNN-555-0100..0199 (US fictional range); +44 20 7946 0xxx (UK drama range)
  IPs         192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 (RFC 5737), 2001:db8::/32 (RFC 3849)
  cards       payment providers' published test card numbers (pass the Luhn check, never real accounts)
  SSNs        none. The pack does not handle Social Security numbers at all (owner decision,
              2026-11-05), so no SSN-shaped values appear anywhere.
  names       random first + last name pairs from common-name lists; organizations are invented

The output is deterministic: the same seed always produces byte-identical files, on any
Python version from 3.9 up. The tests depend on that.

Files written (under --out, default samples/data)
  donors.csv               gift list for donor-thank-you-writer and pii-guard
  participants.csv         program data (aggregate-able) for impact-report-builder
  pii/corpus.jsonl         labeled text records for pii-guard detector recall and precision
  pii/names-list.txt       a "names file" an org would supply (NAME_LISTED detector)
  pii/id-patterns.json     an org's ID-number patterns (ID_NUMBER detector)
  MANIFEST.json            seed, generator version, sha256 and counts for every file

When --out is the default, the three pii/ files are also copied to
skills/pii-guard/assets/selftest/, so the packaged skill can run its selftest on its own.

Exit codes
  0  files written, or --check found no differences
  1  --check found files that differ from what the generator produces
  2  bad input (bad seed, output path is a file, --check on a missing folder)

Examples
  python3 samples/generate.py                      # write samples/data
  python3 samples/generate.py --check              # verify committed files are current
  python3 samples/generate.py --out /tmp/x --format json
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import random
import sys
from pathlib import Path

GENERATOR_VERSION = "0.2.0"
DEFAULT_SEED = 20261105
DEFAULT_OUT = Path(__file__).resolve().parent / "data"
# pii-guard ships its own copy of the corpus (a packaged skill cannot see samples/).
DEFAULT_BUNDLE = Path(__file__).resolve().parents[1] / "skills" / "pii-guard" / "assets" / "selftest"
BUNDLED = ["pii/corpus.jsonl", "pii/names-list.txt", "pii/id-patterns.json"]

N_DONOR_ROWS = 60
N_DONORS = 45
N_PARTICIPANTS = 120
N_CORPUS_POSITIVE = 1250  # ~100+ of each structured type, so 99% recall is measurable
N_CORPUS_NEGATIVE = 200

# ------------------------------------------------------------------ pools
FIRST_NAMES = [
    "Avery", "Blake", "Casey", "Dana", "Elliot", "Frankie", "Gray", "Harper",
    "Indigo", "Jordan", "Kendall", "Logan", "Morgan", "Noel", "Oakley", "Parker",
    "Quinn", "Reese", "Sawyer", "Taylor", "Umi", "Val", "Wren", "Yael",
    "Amara", "Bodhi", "Cyrus", "Delphine", "Emeka", "Farida", "Gideon", "Hollis",
    "Ines", "Jun", "Kaveh", "Lucia", "Mateo", "Nadia", "Osei", "Priya",
]
# Two disjoint surname pools, so a name is either "listed" or "cue-only" in the corpus,
# never both. That keeps the ground truth unambiguous.
LAST_NAMES_LISTED = [
    "Ashgrove", "Brindle", "Copperfield", "Dunmore", "Eastwick", "Fairbank",
    "Glenhaven", "Hartwell", "Ivesdale", "Juniper", "Kestrel", "Larkspur",
    "Mossley", "Northcote", "Oakhurst", "Pemberly", "Quillon", "Rainsford",
    "Stillwater", "Thornbury",
]
LAST_NAMES_CUE = [
    "Umberfield", "Vantwood", "Willowmere", "Yarrowby", "Zephyrine", "Alderjay",
    "Brackenridge", "Calloway", "Dewberry", "Elmstead", "Foxglove", "Greystoke",
    "Hazelmoor", "Ironwood", "Jessamine", "Kingsley",
]
STREETS = [
    "Alder", "Birchwood", "Cedar Hollow", "Dogwood", "Elmwood", "Fernbrook",
    "Garnet", "Hawthorn", "Ivy Bend", "Juniper Ridge", "Kingfisher", "Linden",
    "Meadowlark", "Nettle", "Orchard", "Primrose",
]
STREET_SUFFIXES = ["St", "Street", "Ave", "Avenue", "Rd", "Road", "Ln", "Lane",
                   "Dr", "Drive", "Blvd", "Ct", "Court", "Way"]
CITIES = [("Springfield", "IL"), ("Riverton", "WY"), ("Fairview", "OR"),
          ("Georgetown", "TX"), ("Franklin", "TN"), ("Salem", "MA"),
          ("Madison", "WI"), ("Clinton", "IA")]
EMAIL_DOMAINS = ["example.org", "example.com", "example.net"]
AREA_CODES = ["212", "303", "312", "404", "503", "608", "615", "720", "802", "919"]
# Published test card numbers (Visa, Mastercard, Amex, Discover). All pass Luhn.
TEST_CARDS = [
    "4111111111111111", "4012888888881881", "5555555555554444",
    "5105105105105100", "378282246310005", "371449635398431",
    "6011111111111117", "6011000990139424",
]
IP_PREFIXES = ["192.0.2.", "198.51.100.", "203.0.113."]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
PROGRAMS = ["After-School Tutoring", "Job Readiness", "Family Literacy"]
COHORTS = ["2026-spring", "2026-fall"]
AGE_BANDS = ["14-17", "18-24", "25-34", "35-49", "50-64", "65+"]
CAMPAIGNS = ["Spring Appeal", "Year-End Appeal", "Gala 2026", "Online"]
ORG_NAME = "Lantern Hill Learning Collective (synthetic)"

# Sensitive-context families and the phrases that carry them. pii-guard flags
# context, it does not redact it; some families raise the data to Red.
CONTEXT_PHRASES = {
    "health": "was hospitalized for a chronic condition",
    "mental_health": "is seeing a counselor for depression",
    "immigration": "is waiting on an asylum hearing and has no visa yet",
    "domestic_violence_shelter": "moved into the confidential shelter after the protective order",
    "minors": "has a 9-year-old daughter enrolled at the elementary school",
    "criminal_justice": "is on probation after a conviction last year",
    "substance_use": "is in recovery and attends a methadone clinic",
}


# --------------------------------------------------------------- helpers
def luhn_ok(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class Gen:
    """All randomness flows through one seeded generator, so output is reproducible."""

    def __init__(self, seed):
        self.r = random.Random(seed)

    def pick(self, seq):
        return self.r.choice(seq)

    def num(self, lo, hi):
        return self.r.randint(lo, hi)

    # identifier makers -------------------------------------------------
    def listed_name(self):
        return f"{self.pick(FIRST_NAMES)} {self.pick(LAST_NAMES_LISTED)}"

    def cue_surname(self):
        return self.pick(LAST_NAMES_CUE)

    def email(self, first=None, last=None):
        first = first or self.pick(FIRST_NAMES)
        last = last or self.pick(LAST_NAMES_LISTED + LAST_NAMES_CUE)
        style = self.num(0, 2)
        local = [f"{first}.{last}", f"{first[0]}{last}", f"{first}{self.num(10, 99)}"][style]
        return f"{local.lower()}@{self.pick(EMAIL_DOMAINS)}"

    def phone_us(self):
        area, line = self.pick(AREA_CODES), f"01{self.num(0, 99):02d}"
        fmt = self.num(0, 3)
        return [f"({area}) 555-{line}", f"{area}-555-{line}",
                f"{area}.555.{line}", f"+1 {area} 555 {line}"][fmt]

    def phone_intl(self):
        return f"+44 20 7946 0{self.num(0, 999):03d}"

    def card(self):
        number = self.pick(TEST_CARDS)
        style = self.num(0, 2)
        if style == 0 or len(number) != 16:
            return number
        sep = " " if style == 1 else "-"
        return sep.join(number[i:i + 4] for i in range(0, 16, 4))

    def non_luhn_16(self):
        while True:
            digits = "".join(str(self.num(0, 9)) for _ in range(16))
            if digits[0] != "0" and not luhn_ok(digits):
                return digits

    def date(self, start_year, end_year):
        start = dt.date(start_year, 1, 1).toordinal()
        end = dt.date(end_year, 12, 31).toordinal()
        return dt.date.fromordinal(self.num(start, end))

    def date_text(self, day):
        fmt = self.num(0, 2)
        if fmt == 0:
            return day.strftime("%m/%d/%Y")
        if fmt == 1:
            return day.isoformat()
        return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"

    def address(self):
        city, state = self.pick(CITIES)
        return (f"{self.num(10, 9899)} {self.pick(STREETS)} {self.pick(STREET_SUFFIXES)}, "
                f"{city}, {state} {self.num(10000, 99899):05d}")

    def ipv4(self):
        return f"{self.pick(IP_PREFIXES)}{self.num(1, 254)}"

    def ipv6(self):
        return f"2001:db8:{self.num(0, 0xffff):x}::{self.num(1, 0xffff):x}"

    def url_id(self):
        token = "".join(self.pick("0123456789abcdef") for _ in range(24))
        return f"https://portal.example.org/case?id={token}"

    def case_id(self):
        if self.num(0, 1):
            return f"CASE-{self.num(2020, 2026)}-{self.num(0, 999999):06d}"
        return f"MBR{self.num(0, 9999999):07d}"


# ---------------------------------------------------------------- corpus
# Templates are lists of literal strings and (TYPE, maker) slots. Labeled slots
# record their character span; unlabeled "decoy" slots must NOT be detected.
POSITIVE_TEMPLATES = [
    ["Please email ", ("EMAIL",), " about the volunteer schedule."],
    ["Reach the donor at ", ("PHONE",), " after 5pm."],
    ["Her UK contact number is ", ("PHONE_INTL",), "."],
    ["Intake form: member ", ("ID_NUMBER",), ", verified by the front desk."],
    ["Card on file ", ("CARD",), " was declined for the monthly gift."],
    ["DOB: ", ("DOB",), ". Returning participant."],
    ["The applicant was born ", ("DOB",), " and lives nearby."],
    ["Date of birth ", ("DOB",), " confirmed at intake."],
    ["Mail the receipt to ", ("ADDRESS",), "."],
    ["Login came from ", ("IP",), " at 9:14 this morning."],
    ["Audit log shows ", ("IPV6",), " accessed the file."],
    ["Open the record at ", ("URL_ID",), " to review."],
    ["Case number ", ("ID_NUMBER",), " is due for review."],
    [("NAME_LISTED",), " volunteered at the spring book fair."],
    ["Thank you note drafted for ", ("NAME_LISTED",), "."],
    ["Ms. ", ("NAME_CUE",), " asked about the tutoring waitlist."],
    ["Mr. ", ("NAME_CUE",), " dropped off the signed forms."],
    ["Our client ", ("NAME_CUE",), " finished the job readiness course."],
    ["Participant ", ("NAME_CUE",), " missed two sessions."],
    [("NAME_LISTED",), " (", ("EMAIL",), ", ", ("PHONE",), ") renewed their membership."],
    ["Donor ", ("NAME_LISTED",), " lives at ", ("ADDRESS",), "."],
    ["Client ", ("NAME_CUE",), ", DOB ", ("DOB",), ", phone ", ("PHONE",), "."],
    ["Refund issued to card ", ("CARD",), " for ", ("NAME_LISTED",), "."],
    ["Follow up with ", ("EMAIL",), " and ", ("EMAIL",), " before the board meeting."],
    ["Member ", ("ID_NUMBER",), " called from ", ("PHONE",), "."],
]
NEGATIVE_TEMPLATES = [
    ["Order #", ("ORDER",), " shipped on ", ("PLAIN_DATE",), "."],
    ["Invoice ", ("INVOICE",), " totals $", ("AMOUNT",), "."],
    ["The board meets on ", ("PLAIN_DATE",), " in Room ", ("ROOM",), "."],
    ["We served ", ("COUNT",), " families in ", ("YEAR",), "."],
    ["Read our annual report at https://www.example.org/annual-report."],
    ["Budget line ", ("BUDGET_CODE",), " covers printing and postage."],
    ["Tracking reference ", ("ORDER",), " was logged by the warehouse."],
    ["The grant period runs from ", ("PLAIN_DATE",), " to ", ("PLAIN_DATE",), "."],
    ["Version 3.11.2 of the database was installed on ", ("PLAIN_DATE",), "."],
    ["Call the main office line during business hours."],
]
CONTEXT_TEMPLATES = [
    ["Ms. ", ("NAME_CUE",), " {phrase}."],
    ["Our client {phrase}."],
    ["A participant mentioned that she {phrase}."],
]


def fill_slot(g, kind):
    makers = {
        "EMAIL": g.email, "PHONE": g.phone_us, "PHONE_INTL": g.phone_intl,
        "CARD": g.card, "ADDRESS": g.address, "IP": g.ipv4,
        "IPV6": g.ipv6, "URL_ID": g.url_id, "ID_NUMBER": g.case_id,
        "NAME_LISTED": g.listed_name, "NAME_CUE": g.cue_surname,
        "DOB": lambda: g.date_text(g.date(1940, 2008)),
        "ORDER": g.non_luhn_16,
        "PLAIN_DATE": lambda: g.date_text(g.date(2025, 2027)),
        "INVOICE": lambda: f"INV-{g.num(1000, 9999)}",
        "AMOUNT": lambda: f"{g.num(50, 9000):,}.{g.num(0, 99):02d}",
        "ROOM": lambda: str(g.num(100, 450)),
        "COUNT": lambda: str(g.num(40, 900)),
        "YEAR": lambda: str(g.num(2019, 2026)),
        "BUDGET_CODE": lambda: f"{g.num(4000, 7999)}-{g.num(10, 99)}",
    }
    return makers[kind]()


# Slot kinds that become labels, and the label type they map to.
LABEL_TYPE = {
    "EMAIL": "EMAIL", "PHONE": "PHONE", "PHONE_INTL": "PHONE",
    "CARD": "CARD", "DOB": "DOB", "ADDRESS": "ADDRESS", "IP": "IP", "IPV6": "IP",
    "URL_ID": "URL_ID", "ID_NUMBER": "ID_NUMBER", "NAME_LISTED": "NAME_LISTED",
    "NAME_CUE": "NAME_CUE",
}


def render(g, template, phrase=None):
    text, labels = "", []
    for part in template:
        if isinstance(part, str):
            text += part.replace("{phrase}", phrase or "")
            continue
        kind = part[0]
        value = fill_slot(g, kind)
        if kind in LABEL_TYPE:
            labels.append({"type": LABEL_TYPE[kind], "start": len(text),
                           "end": len(text) + len(value), "value": value})
        text += value
    return text, labels


def build_corpus(g):
    records, listed = [], set()
    for i in range(N_CORPUS_POSITIVE):
        text, labels = render(g, POSITIVE_TEMPLATES[i % len(POSITIVE_TEMPLATES)])
        listed.update(l["value"] for l in labels if l["type"] == "NAME_LISTED")
        records.append({"text": text, "labels": labels, "context_families": []})
    families = sorted(CONTEXT_PHRASES)
    for i, family in enumerate(families * 4):
        template = CONTEXT_TEMPLATES[i % len(CONTEXT_TEMPLATES)]
        text, labels = render(g, template, CONTEXT_PHRASES[family])
        records.append({"text": text, "labels": labels, "context_families": [family]})
    for i in range(N_CORPUS_NEGATIVE):
        text, labels = render(g, NEGATIVE_TEMPLATES[i % len(NEGATIVE_TEMPLATES)])
        records.append({"text": text, "labels": labels, "context_families": []})
    for n, rec in enumerate(records, start=1):
        rec["id"] = f"pii-{n:04d}"
        rec["synthetic"] = True
    return records, sorted(listed)


# --------------------------------------------------------------- tables
def build_donors(g):
    donors = []
    for d in range(1, N_DONORS + 1):
        first, last = g.pick(FIRST_NAMES), g.pick(LAST_NAMES_LISTED)
        city, state = g.pick(CITIES)
        donors.append({
            "donor_id": f"D-{d:03d}", "first_name": first, "last_name": last,
            "email": g.email(first, last), "phone": g.phone_us(),
            "street": f"{g.num(10, 9899)} {g.pick(STREETS)} {g.pick(STREET_SUFFIXES)}",
            "city": city, "state": state, "zip": f"{g.num(10000, 99899):05d}",
        })
    rows = []
    for i in range(1, N_DONOR_ROWS + 1):
        gift_type = g.pick(["one-time", "one-time", "one-time", "recurring"])
        amount = g.pick([25, 35, 50, 75, 100, 150, 250, 500, 1000, 2500])
        rows.append({
            "gift_id": f"G-{i:04d}", **g.pick(donors),
            "gift_date": g.date(2026, 2026).isoformat(), "amount": f"{amount:.2f}",
            "gift_type": gift_type, "campaign": g.pick(CAMPAIGNS),
            "tribute": "", "anonymous": "no", "synthetic": "yes",
        })
    # Deliberate edge cases, at fixed rows so tests and evals can rely on them.
    rows[4]["anonymous"] = "yes"
    rows[9]["tribute"] = f"in memory of {g.pick(FIRST_NAMES)} {g.pick(LAST_NAMES_LISTED)}"
    rows[14]["tribute"] = f"in honor of {g.pick(FIRST_NAMES)} {g.pick(LAST_NAMES_LISTED)}"
    rows[19]["email"] = ""
    rows[24]["amount"] = "-50.00"  # refund
    rows[29] = dict(rows[28], gift_id="G-0030")  # duplicate of G-0029 under a new gift_id
    return rows


def build_participants(g):
    rows = []
    for i in range(1, N_PARTICIPANTS + 1):
        pre = g.num(20, 70)
        completed = g.r.random() < 0.8
        post = min(100, pre + g.num(-5, 25)) if completed else None
        rows.append({
            "participant_id": f"P-{i:04d}", "program": g.pick(PROGRAMS),
            "cohort": g.pick(COHORTS), "age_band": g.pick(AGE_BANDS),
            "enrolled_on": g.date(2026, 2026).isoformat(),
            "pre_score": str(pre), "post_score": "" if post is None else str(post),
            "completed": "yes" if completed else "no", "synthetic": "yes",
        })
    return rows


# --------------------------------------------------------------- output
def csv_text(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def build_all(seed):
    """Return {relative_path: text} for every file. Pure: no disk access."""
    g = Gen(seed)
    donors = build_donors(g)
    participants = build_participants(g)
    corpus, listed = build_corpus(g)
    files = {
        "donors.csv": csv_text(donors),
        "participants.csv": csv_text(participants),
        "pii/corpus.jsonl": "".join(json.dumps(r, sort_keys=True) + "\n" for r in corpus),
        "pii/names-list.txt": "# Synthetic names file (one name per line). Not real people.\n"
                              + "".join(n + "\n" for n in listed),
        "pii/id-patterns.json": json.dumps({
            "synthetic": True,
            "patterns": {"CASE": r"\bCASE-\d{4}-\d{6}\b", "MEMBER": r"\bMBR\d{7}\b"},
        }, indent=2, sort_keys=True) + "\n",
    }
    label_counts = {}
    for rec in corpus:
        for lab in rec["labels"]:
            label_counts[lab["type"]] = label_counts.get(lab["type"], 0) + 1
    manifest = {
        "generator_version": GENERATOR_VERSION, "seed": seed, "synthetic": True,
        "org_name": ORG_NAME,
        "files": {p: {"sha256": hashlib.sha256(t.encode("utf-8")).hexdigest(),
                      "lines": t.count("\n")} for p, t in sorted(files.items())},
        "counts": {"donor_rows": len(donors), "participant_rows": len(participants),
                   "corpus_records": len(corpus), "listed_names": len(listed),
                   "corpus_labels": dict(sorted(label_counts.items()))},
    }
    files["MANIFEST.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return files, manifest


def compare(out, files):
    """Return the list of relative paths that are missing or differ on disk."""
    drift = []
    for rel, text in sorted(files.items()):
        path = out / rel
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(rel)
    return drift


def write(out, files):
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def report(fmt, payload, lines):
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Write or check the pack's synthetic sample data.",
        epilog="Exit codes: 0 ok; 1 --check found differences; 2 bad input.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output folder (default: samples/data next to this script)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"random seed (default {DEFAULT_SEED}); must be positive")
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit 1 if files on disk differ from the generator")
    parser.add_argument("--format", choices=["md", "json"], default="md",
                        help="summary format (default md)")
    args = parser.parse_args(argv)

    if args.seed <= 0:
        print(f"error: --seed must be a positive whole number, got {args.seed}", file=sys.stderr)
        return 2
    if args.out.exists() and not args.out.is_dir():
        print(f"error: --out is a file, not a folder: {args.out}", file=sys.stderr)
        return 2

    files, manifest = build_all(args.seed)
    counts = manifest["counts"]
    bundle = args.out.resolve() == DEFAULT_OUT
    bundle_files = {Path(rel).name: files[rel] for rel in BUNDLED}
    if args.check:
        if not args.out.is_dir():
            print(f"error: nothing to check, folder not found: {args.out}", file=sys.stderr)
            return 2
        drift = compare(args.out, files)
        if bundle:
            drift += [f"(pii-guard bundle) {p}" for p in compare(DEFAULT_BUNDLE, bundle_files)]
        report(args.format, {"ok": not drift, "differs": drift},
               ["Sample data is current." if not drift else
                "Sample data differs from the generator. Re-run without --check:"]
               + [f"  - {p}" for p in drift])
        return 1 if drift else 0

    write(args.out, files)
    if bundle:
        write(DEFAULT_BUNDLE, bundle_files)
    # Only file names, counts and hashes are printed: never sample values.
    lines = [f"Wrote {len(files)} files to {args.out} (seed {args.seed}):"]
    lines += [f"  - {p}  ({m['lines']} lines, sha256 {m['sha256'][:12]})"
              for p, m in manifest["files"].items()]
    lines.append(f"Corpus labels: {counts['corpus_labels']}")
    report(args.format, {"out": str(args.out), "manifest": manifest}, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
