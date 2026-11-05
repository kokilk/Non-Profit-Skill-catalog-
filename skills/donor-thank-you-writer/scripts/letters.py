#!/usr/bin/env python3
"""donor-thank-you-writer: check a gift list, segment donors, lint each letter. Stdlib only (3.9+).

Subcommands
  check    Validate the gift CSV: required columns, amounts and dates, duplicates, missing names or
           contact details, anonymous donors, tributes (in honor / in memory), recurring gifts,
           refunds, and which gifts need acknowledgment-letter content (thresholds from the config).
  segment  Assign first-time / repeat / lapsed / major / recurring using the org's thresholds from
           the config. Refuses if a threshold isn't set: no defaults are baked in.
  lint     Check one letter against its gift record and the impact-facts file: placeholders,
           donor name, amount, acknowledgment statements, numbers not backed by a fact, other
           donors' names, overclaim phrases, sensitive words, length and reading level.

The acknowledgment thresholds in assets/thank-you-config.json are US reference points to verify
with the org's accountant. This script does not give tax advice or decide deductibility.

Exit codes
  0  no issues (check) / segments assigned (segment) / letter passes (lint)
  1  issues the user must see (check) / letter has errors (lint)
  2  bad input: missing file, missing column, bad amount or date, threshold not set in config

Examples
  python3 letters.py check gifts.csv --config thank-you-config.json
  python3 letters.py segment gifts.csv --config thank-you-config.json --today 2026-11-05
  python3 letters.py lint letter-G-0001.md --gift-id G-0001 --gifts gifts.csv --facts impact-facts.json --config thank-you-config.json
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

VERSION = "0.1.0"
OK, FINDINGS, BAD_INPUT = 0, 1, 2
REQUIRED = ["gift_id", "donor_id", "first_name", "last_name", "gift_date", "amount"]
OVERCLAIM = ["single-handedly", "100% of your", "every penny", "every dollar goes", "saved lives", "life-saving",
             "changed lives forever", "transformed the community", "without you, none of"]
SENSITIVE = ["diagnos", "illness", "cancer", "divorce", "salary", "net worth", "wealth", "inheritance", "estate of",
             "bankrupt", "unemployed", "immigra"]
MAX_WORDS = 350


class InputError(Exception):
    """Bad input: stderr, exit 2."""


def load_json(path: str, label: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{label} missing or not valid JSON: {exc}")


def money(value: str) -> float | None:
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def load_gifts(path: str) -> list:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"gift file not found: {path}")
    rows = list(csv.DictReader(p.read_text(encoding="utf-8-sig").splitlines()))
    if not rows:
        raise InputError(f"no gifts in {path}")
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        raise InputError(f"gift file is missing column(s): {', '.join(missing)}")
    for r in rows:
        if money(r["amount"]) is None:
            raise InputError(f"{r['gift_id']}: amount {r['amount']!r} is not a number")
        try:
            dt.date.fromisoformat(r["gift_date"].strip())
        except ValueError:
            raise InputError(f"{r['gift_id']}: gift_date {r['gift_date']!r} must be YYYY-MM-DD")
    return rows


def yes(value) -> bool:
    return str(value or "").strip().lower() in ("yes", "y", "true", "1")


def ack_thresholds(config: dict) -> tuple:
    ack = config.get("acknowledgment") or {}
    a, q = ack.get("written_ack_min"), ack.get("quid_pro_quo_disclosure_over")
    if not isinstance(a, (int, float)) or not isinstance(q, (int, float)):
        raise InputError("config acknowledgment.written_ack_min and quid_pro_quo_disclosure_over must be numbers "
                         "(verify them with the org's accountant)")
    return a, q


# ------------------------------------------------------------------ check
def check(rows: list, config: dict) -> dict:
    ack_min, qpq_over = ack_thresholds(config)
    has_goods = "goods_services_value" in rows[0]
    seen, out = {}, []
    for r in rows:
        amount, flags, issues = money(r["amount"]), [], []
        anonymous = yes(r.get("anonymous"))
        named = r["first_name"].strip() or r["last_name"].strip()
        if not named:
            issues.append("no donor name: don't invent one; ask how the org addresses this donor")
        if anonymous:
            flags.append("anonymous: thank them personally, never list them publicly")
        if not (r.get("email", "").strip() or r.get("street", "").strip()):
            issues.append("no email or mailing address: no way to send the letter")
        tribute = r.get("tribute", "").strip()
        if tribute:
            flags.append(f"tribute ({tribute.split(' of ')[0]}): acknowledge the honoree with care; "
                         "a separate notice to the family needs its own address")
        if r.get("gift_type", "").strip().lower() == "recurring":
            flags.append("recurring gift")
        if amount <= 0:
            issues.append("refund or zero amount: no thank-you letter")
        key = (r["donor_id"], r["gift_date"], r["amount"])
        if key in seen:
            issues.append(f"possible duplicate of {seen[key]} (same donor, date and amount)")
        seen.setdefault(key, r["gift_id"])
        if amount >= ack_min:
            flags.append(f"written acknowledgment content needed (single gift of {ack_min:g} or more)")
        goods = money(r.get("goods_services_value", "")) if has_goods else None
        if goods and goods > 0 and amount > qpq_over:
            flags.append("goods or services received: include the disclosure statement with their value")
        elif not has_goods and amount >= ack_min:
            flags.append("[CONFIRM: were any goods or services given for this gift?]")
        out.append({"gift_id": r["gift_id"], "donor_id": r["donor_id"], "amount": amount, "issues": issues, "flags": flags})
    return {"gifts": out, "needs_attention": sum(bool(g["issues"]) for g in out),
            "note": "Thresholds are US reference points from the config; verify with the org's accountant. Not tax advice."}


# ------------------------------------------------------------------ segment
def segment(rows: list, config: dict, today: dt.date) -> dict:
    seg = config.get("segments") or {}
    major, lapsed = seg.get("major_gift_min"), seg.get("lapsed_after_months")
    if not isinstance(major, (int, float)) or not isinstance(lapsed, int):
        raise InputError("set segments.major_gift_min and segments.lapsed_after_months in the config with the org first; "
                         "there are no built-in defaults")
    by_donor: dict = {}
    for r in rows:
        if money(r["amount"]) > 0:
            by_donor.setdefault(r["donor_id"], []).append(r)
    out = []
    for r in rows:
        amount = money(r["amount"])
        if amount <= 0:
            continue
        date = dt.date.fromisoformat(r["gift_date"])
        earlier = sorted(dt.date.fromisoformat(x["gift_date"]) for x in by_donor[r["donor_id"]]
                         if dt.date.fromisoformat(x["gift_date"]) < date)
        segs = []
        if r.get("gift_type", "").strip().lower() == "recurring":
            segs.append("recurring")
        if amount >= major:
            segs.append("major")
        if not earlier:
            segs.append("first_time")
        elif (date - earlier[-1]).days > lapsed * 30:
            segs.append("lapsed_returning")
        else:
            segs.append("repeat")
        out.append({"gift_id": r["gift_id"], "donor_id": r["donor_id"], "amount": amount, "segments": segs})
    return {"today": today.isoformat(), "thresholds": {"major_gift_min": major, "lapsed_after_months": lapsed},
            "note": "History comes only from this file; donors with earlier gifts elsewhere may show as first-time.",
            "gifts": out}


# ------------------------------------------------------------------ lint
def fact_numbers(facts: dict) -> set:
    nums = set()
    for f in facts.get("facts", []):
        nums |= {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", str(f.get("text", "")))}
    return nums


def lint(letter: str, gift: dict, all_rows: list, facts: dict, config: dict) -> dict:
    errors, warnings = [], []
    low = letter.lower()
    ack_min, _ = ack_thresholds(config)
    amount = money(gift["amount"])
    placeholders = re.findall(r"\{[^}]*\}|\[(?:NEEDS FROM ORG|CONFIRM|VERIFY)[^\]]*\]|\bXX+\b", letter)
    if placeholders:
        errors.append(f"unresolved placeholder(s): {', '.join(sorted(set(placeholders))[:5])}")
    first = gift["first_name"].strip()
    if first and first.lower() not in low:
        errors.append(f"donor's name ({first}) does not appear in the letter")
    if not first and not gift["last_name"].strip() and re.search(r"^dear (?!friend)", low, re.M):
        errors.append("letter addresses a name, but the record has none: don't invent one")
    amounts = [money(a) for a in re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", letter)]
    if amounts and any(abs(a - amount) > 0.005 for a in amounts):
        errors.append(f"amount in letter ({', '.join(f'${a:,.2f}' for a in amounts)}) doesn't match the gift (${amount:,.2f})")
    if amount >= ack_min:
        legal = (config.get("org_legal_name") or "").strip()
        if not legal:
            errors.append("config org_legal_name is empty: the acknowledgment needs the org's legal name")
        elif legal.lower() not in low:
            errors.append(f"acknowledgment needs the org's legal name ({legal})")
        if not amounts:
            errors.append("acknowledgment needs the gift amount")
        if not re.search(r"no goods or services|goods or services (?:valued|worth|with a value)", low):
            errors.append("acknowledgment needs 'no goods or services were provided' or a description and value of what was")
        date = dt.date.fromisoformat(gift["gift_date"])
        forms = {date.isoformat(), f"{date:%B} {date.day}, {date.year}".lower(), f"{date.month}/{date.day}/{date.year}"}
        if not any(f in low for f in forms):
            errors.append("acknowledgment needs the gift date")
        if config.get("include_ein") and (config.get("ein") or "").strip() not in letter:
            errors.append("config says to include the EIN, and it's missing")
    allowed = fact_numbers(facts) | {f"{amount:g}", f"{amount:.2f}", str(int(amount))}
    allowed |= {str(dt.date.fromisoformat(gift["gift_date"]).year)}
    stripped = re.sub(r"\$\s?\d[\d,]*(?:\.\d{2})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", " ", letter)
    for d in (gift.get("gift_date", ""), config.get("ein", "")):
        if str(d or "").strip():
            stripped = stripped.replace(str(d), " ")
    stripped = re.sub(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
                      r"\s+\d{1,2},?\s+\d{4}", " ", stripped)
    loose = {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", stripped)} - allowed
    if loose:
        errors.append(f"number(s) not in the impact facts: {', '.join(sorted(loose))}. Use only supplied facts")
    for phrase in OVERCLAIM:
        if phrase in low and not any(phrase in str(f.get("text", "")).lower() for f in facts.get("facts", [])):
            errors.append(f"overclaim: '{phrase}'")
    others = {f"{r['first_name']} {r['last_name']}".strip() for r in all_rows
              if r["donor_id"] != gift["donor_id"] and r["first_name"].strip() and r["last_name"].strip()}
    named = sorted(n for n in others if n.lower() in low)
    if named:
        errors.append(f"mentions other donor(s): {', '.join(named)}")
    hits = [w for w in SENSITIVE if w in low]
    if hits:
        warnings.append(f"sensitive word(s) ({', '.join(hits)}): don't refer to the donor's circumstances")
    words = re.findall(r"[A-Za-z']+", letter)
    if len(words) > MAX_WORDS:
        warnings.append(f"{len(words)} words: aim for under {MAX_WORDS}")
    sentences = max(1, len(re.findall(r"[.!?]+", letter)))
    syll = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower())) - w.lower().endswith("e")) for w in words)
    grade = round(0.39 * len(words) / sentences + 11.8 * syll / max(1, len(words)) - 15.59, 1) if words else 0
    if grade > 10:
        warnings.append(f"reading level about grade {grade}: shorter sentences and plainer words")
    return {"gift_id": gift["gift_id"], "errors": errors, "warnings": warnings, "words": len(words),
            "reading_grade": grade, "passed": not errors}


# ------------------------------------------------------------------ cli
def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check gifts, segment donors, lint thank-you letters.",
                                 epilog="Exit codes: 0 ok; 1 issues or letter errors; 2 bad input.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "segment"):
        p = sub.add_parser(name)
        p.add_argument("gifts")
        p.add_argument("--config", required=True)
        p.add_argument("--today")
    p = sub.add_parser("lint")
    p.add_argument("letter")
    p.add_argument("--gift-id", required=True)
    p.add_argument("--gifts", required=True)
    p.add_argument("--facts", required=True)
    p.add_argument("--config", required=True)
    for p in sub.choices.values():
        p.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args(argv)
    try:
        config = load_json(args.config, "config")
        if args.cmd == "lint":
            rows = load_gifts(args.gifts)
            gift = next((r for r in rows if r["gift_id"] == args.gift_id), None)
            if gift is None:
                raise InputError(f"no gift {args.gift_id!r} in {args.gifts}")
            letter_path = Path(args.letter)
            if not letter_path.is_file():
                raise InputError(f"letter not found: {args.letter}")
            res = lint(letter_path.read_text(encoding="utf-8"), gift, rows, load_json(args.facts, "facts"), config)
            text = [f"letter lint {res['gift_id']}: {'PASS' if res['passed'] else 'FAIL'} "
                    f"({res['words']} words, reading grade ~{res['reading_grade']})"]
            text += [f"  error: {e}" for e in res["errors"]] + [f"  warning: {w}" for w in res["warnings"]]
            code = OK if res["passed"] else FINDINGS
        else:
            rows = load_gifts(args.gifts)
            today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
            if args.cmd == "check":
                res = check(rows, config)
                text = [f"gift check: {len(rows)} gift(s), {res['needs_attention']} need attention. {res['note']}"]
                for g in res["gifts"]:
                    if g["issues"] or g["flags"]:
                        text.append(f"- {g['gift_id']} ({g['donor_id']}, ${g['amount']:,.2f})")
                        text += [f"    ! {i}" for i in g["issues"]] + [f"    · {f}" for f in g["flags"]]
                code = FINDINGS if res["needs_attention"] else OK
            else:
                res = segment(rows, config, today)
                text = [f"segments (major >= ${res['thresholds']['major_gift_min']:,}, lapsed after "
                        f"{res['thresholds']['lapsed_after_months']} months). {res['note']}"]
                text += [f"- {g['gift_id']} {g['donor_id']} ${g['amount']:,.2f}: {', '.join(g['segments'])}" for g in res["gifts"]]
                code = OK
    except (InputError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT
    print(json.dumps(res, indent=2) if args.format == "json" else "\n".join(text))
    return code


if __name__ == "__main__":
    sys.exit(main())
