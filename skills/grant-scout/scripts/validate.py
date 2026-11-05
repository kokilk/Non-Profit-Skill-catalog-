#!/usr/bin/env python3
"""grant-scout validate: check every grant record for its source fields. Standard library only (3.9+).

The rule this enforces: no grant is "open" or "eligible" unless it has a source URL, a
checked_on date, and its deadline and eligibility text come from that source. Anything
else is an UNVERIFIED LEAD.

A record is verified only when all of these hold:
  - source_url is an http(s) URL; checked_on is a real date, not in the future
  - status is one of open, rolling, closed, unknown
  - an "open" grant has a deadline (YYYY-MM-DD) and a deadline_source
  - every eligibility criterion has text, kind (hard or preference) and source_quote_location
It also warns (does not unverify) when checked_on is older than --max-age-days, and flags
an "open" grant whose deadline has already passed.

Usage
  python3 validate.py grant-pipeline-{slug}.json [--today YYYY-MM-DD] [--max-age-days N] [--update]

--update writes each record's "verified" flag back into the state file (refuses if the file
changed while it was being read).

Exit codes
  0  every record is verified
  1  at least one record is unverified, stale, or marked open after its deadline
  2  bad input: missing or unreadable file, not JSON, no "grants" list, bad --today

Examples
  python3 validate.py grant-pipeline-riverbend.json
  python3 validate.py grant-pipeline-riverbend.json --today 2026-11-05 --format json
  python3 validate.py grant-pipeline-riverbend.json --update
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

VERSION = "0.1.0"
OK, FINDINGS, BAD_INPUT = 0, 1, 2
STATUSES = {"open", "rolling", "closed", "unknown"}
TYPES = {"federal", "state", "local", "foundation", "corporate"}
KINDS = {"hard", "preference"}


class InputError(Exception):
    """Bad input: reported on stderr, exit code 2."""


class StateFile:
    """Read a JSON state file and write it back only if nobody changed it in between."""

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.is_file():
            raise InputError(f"state file not found: {path}")
        self.raw = self.path.read_bytes()
        try:
            self.data = json.loads(self.raw)
        except json.JSONDecodeError as exc:
            raise InputError(f"{path} is not valid JSON: {exc}")
        if not isinstance(self.data, dict):
            raise InputError(f"{path} must hold a JSON object")

    def save(self, data: dict) -> None:
        if hashlib.sha256(self.path.read_bytes()).digest() != hashlib.sha256(self.raw).digest():
            raise InputError(f"{self.path} changed since it was read. Nothing was written; re-run.")
        body = dict(data, last_updated=dt.date.today().isoformat())
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def today_from(value: str | None) -> dt.date:
    if not value:
        return dt.date.today()
    parsed = parse_date(value)
    if parsed is None:
        raise InputError(f"--today must be YYYY-MM-DD, got {value!r}")
    return parsed


def grants_of(data: dict) -> list:
    grants = data.get("grants")
    if not isinstance(grants, list):
        raise InputError('state file has no "grants" list')
    return grants


def check_record(rec: dict, today: dt.date, max_age_days: int) -> dict:
    """Return {"id", "verified", "missing": [...], "warnings": [...]} for one grant record."""
    missing, warnings = [], []
    url = rec.get("source_url") or ""
    if not url.startswith(("http://", "https://")):
        missing.append("source_url (the funder's own page)")
    checked = parse_date(rec.get("checked_on"))
    if checked is None:
        missing.append("checked_on (YYYY-MM-DD)")
    elif checked > today:
        missing.append("checked_on is in the future")
    elif (today - checked).days > max_age_days:
        warnings.append(f"checked {(today - checked).days} days ago: re-check the funder page")
    status = rec.get("status")
    if status not in STATUSES:
        missing.append(f"status (one of {', '.join(sorted(STATUSES))})")
    if rec.get("type") not in TYPES:
        missing.append(f"type (one of {', '.join(sorted(TYPES))})")
    deadline = parse_date(rec.get("deadline"))
    if rec.get("deadline") and deadline is None:
        missing.append("deadline is not a YYYY-MM-DD date")
    if status == "open":
        if deadline is None:
            missing.append("deadline (an open grant needs one from the funder's page)")
        elif deadline < today:
            warnings.append(f"marked open but the deadline {deadline} has passed: treat as closed")
    if deadline is not None and not rec.get("deadline_source"):
        missing.append("deadline_source (where on the page the deadline is stated)")
    criteria = rec.get("eligibility_criteria")
    if not isinstance(criteria, list) or not criteria:
        missing.append("eligibility_criteria (at least one, from the funder's page)")
    else:
        for i, crit in enumerate(criteria, start=1):
            if not isinstance(crit, dict) or not crit.get("text"):
                missing.append(f"criterion {i}: text")
                continue
            if crit.get("kind") not in KINDS:
                missing.append(f"criterion {i}: kind (hard or preference)")
            if not crit.get("source_quote_location"):
                missing.append(f"criterion {i}: source_quote_location")
    return {"id": rec.get("id", "?"), "funder": rec.get("funder", ""), "program": rec.get("program", ""),
            "verified": not missing, "missing": missing, "warnings": warnings}


def render(results: list) -> str:
    ok = [r for r in results if r["verified"]]
    lines = [f"grant-scout validate: {len(ok)} of {len(results)} record(s) verified"]
    for r in results:
        mark = "verified" if r["verified"] else "UNVERIFIED LEAD"
        lines.append(f"- {r['id']} {r['funder']} / {r['program']}: {mark}")
        lines += [f"    missing: {m}" for m in r["missing"]]
        lines += [f"    warning: {w}" for w in r["warnings"]]
    if len(ok) < len(results):
        lines.append("Unverified leads may be mentioned only as leads to check, never as open or eligible.")
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check grant records for source fields.",
                                     epilog="Exit codes: 0 all verified; 1 unverified, stale or "
                                            "past-deadline records; 2 bad input.")
    parser.add_argument("state", help="grant-pipeline-{slug}.json")
    parser.add_argument("--today", help="date to check against (default: today)")
    parser.add_argument("--max-age-days", type=int, default=30,
                        help="warn when checked_on is older than this (default 30)")
    parser.add_argument("--update", action="store_true", help="write verified flags into the state file")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args(argv)
    try:
        today = today_from(args.today)
        state = StateFile(args.state)
        grants = grants_of(state.data)
        results = [check_record(g, today, args.max_age_days) for g in grants]
        if args.update:
            updated = [dict(g, verified=r["verified"]) for g, r in zip(grants, results)]
            state.save(dict(state.data, grants=updated))
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT
    payload = {"today": today.isoformat(), "results": results}
    print(json.dumps(payload, indent=2) if args.format == "json" else render(results))
    clean = all(r["verified"] and not r["warnings"] for r in results)
    return OK if clean else FINDINGS


if __name__ == "__main__":
    sys.exit(main())
