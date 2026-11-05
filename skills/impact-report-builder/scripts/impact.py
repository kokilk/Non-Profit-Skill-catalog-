#!/usr/bin/env python3
"""impact-report-builder: profile program data, compute metrics, verify a draft's numbers.
Standard library only (Python 3.9+). One file, three subcommands.

  profile  Columns, types, missing values, duplicates, bad dates, outliers, and columns that
           look identifying (recommend dropping them).
  metrics  Compute the metrics defined in a JSON config. Every number records its definition,
           rows used and rows left out (with reasons). Small groups are suppressed, including
           complementary suppression so a total minus the visible groups can't reveal one.
  verify   Find every number in a draft report and check it against metrics.json plus an
           allowed list. Any number not found fails. "X% (A of B)" is checked as a rate.

Config for `metrics` (JSON):
  {"min_cell": 5, "drop_exact_duplicates": true,
   "metrics": [
     {"name": "people_served", "kind": "count_unique", "column": "participant_id",
      "meaning": "Different people enrolled"},
     {"name": "completion_rate", "kind": "rate", "numerator_where": {"completed": "yes"},
      "group_by": "program"},
     {"name": "score_change", "kind": "change_pre_post", "id_column": "participant_id",
      "pre": "pre_score", "post": "post_score"}]}
  kinds: count_rows, count_unique, sum, mean, median, rate, change_pre_post
  optional on any metric: "where" {"column": value or [values]}, "group_by" "column"
  min_cell defaults to 5. It is an org policy choice, and the output says so.

Exit codes
  0  profile found no issues / metrics written / every number in the draft verified
  1  profile found issues / metrics include suppressed groups / unverified numbers in the draft
  2  bad input: missing file, bad CSV or config, unknown column or metric kind

Examples
  python3 impact.py profile program-data.csv
  python3 impact.py metrics program-data.csv --config metrics-config.json --out metrics.json
  python3 impact.py verify report-draft.md --metrics metrics.json --allow 2025,2026
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import statistics
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

VERSION = "0.1.0"
OK, FINDINGS, BAD_INPUT = 0, 1, 2
KINDS = {"count_rows", "count_unique", "sum", "mean", "median", "rate", "change_pre_post"}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")
IDENTIFYING = re.compile(r"name|e-?mail|phone|address|street|birth|dob|notes?|comment|ssn", re.I)
NUMBER = re.compile(r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(%?)(?![\w])")
RATE_PHRASE = re.compile(r"(\d+(?:\.\d+)?)%\s*\((\d[\d,]*) of (\d[\d,]*)\)")


class InputError(Exception):
    """Bad input: stderr, exit 2."""


def r2(x: float, places: int = 2) -> float:
    """Round half up (the way people round), not Python's half-to-even."""
    q = Decimal(1).scaleb(-places)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def read_csv(path: str) -> tuple:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"file not found: {path}")
    if p.suffix.lower() != ".csv":
        raise InputError(f"expected a .csv file (export the spreadsheet as CSV UTF-8): {path}")
    try:
        text = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"not UTF-8: {path}. Re-save as CSV UTF-8.")
    rows = list(csv.reader(text.splitlines()))
    if not rows or not any(rows[0]):
        raise InputError(f"no header row: {path}")
    header = [h.strip() for h in rows[0]]
    return header, [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows[1:] if any(r)], text


def as_number(value: str):
    try:
        return float(value.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None


def as_date(value: str):
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value.strip(), fmt).date(), fmt
        except ValueError:
            continue
    return None, None


# ------------------------------------------------------------------ profile
def profile(header: list, rows: list) -> dict:
    cols, issues = [], []
    seen, dups = set(), 0
    for row in rows:
        key = tuple(row[h] for h in header)
        dups += key in seen
        seen.add(key)
    if dups:
        issues.append(f"{dups} exact duplicate row(s)")
    for h in header:
        values = [row[h].strip() for row in rows]
        filled = [v for v in values if v]
        nums = [as_number(v) for v in filled]
        dates = [as_date(v) for v in filled]
        n_num = sum(n is not None for n in nums)
        n_date = sum(d[0] is not None for d in dates)
        kind = ("number" if filled and n_num == len(filled) else "date" if filled and n_date == len(filled)
                else "mixed" if 0 < n_num < len(filled) else "text")
        info = {"column": h, "type": kind, "missing": len(values) - len(filled),
                "missing_pct": r2(100 * (len(values) - len(filled)) / len(values), 1) if values else 0,
                "distinct": len(set(filled))}
        formats = {d[1] for d in dates if d[1]}
        if n_date and len(formats) > 1:
            info["date_formats"] = sorted(formats)
            issues.append(f"{h}: dates in {len(formats)} formats")
        ambiguous = [v for v in filled if re.fullmatch(r"(\d{1,2})/(\d{1,2})/\d{4}", v)
                     and all(int(x) <= 12 for x in v.split("/")[:2]) and v.split("/")[0] != v.split("/")[1]]
        if ambiguous:
            issues.append(f"{h}: {len(ambiguous)} ambiguous date(s) such as {ambiguous[0]} (day/month or month/day?): ask, don't guess")
        if 0 < n_date < len(filled) and n_date >= len(filled) / 2:
            issues.append(f"{h}: {len(filled) - n_date} value(s) don't parse as dates")
        if kind == "mixed":
            issues.append(f"{h}: mix of numbers and text")
        if kind == "number" and len(filled) >= 4:
            q1, _, q3 = statistics.quantiles([n for n in nums if n is not None], n=4)
            lo, hi = q1 - 3 * (q3 - q1), q3 + 3 * (q3 - q1)
            out = [n for n in nums if n is not None and (n < lo or n > hi)]
            if out:
                info["outliers"] = len(out)
                issues.append(f"{h}: {len(out)} extreme value(s) outside {r2(lo)} to {r2(hi)}")
        if re.search(r"(^|_)id$", h, re.I) and len(set(filled)) < len(filled):
            issues.append(f"{h}: {len(filled) - len(set(filled))} repeated ID(s)")
        if IDENTIFYING.search(h):
            info["identifying"] = True
            issues.append(f"{h}: looks identifying; drop it unless the report needs it (run pii-guard first)")
        if info["missing"]:
            issues.append(f"{h}: {info['missing']} blank ({info['missing_pct']}%)")
        cols.append(info)
    return {"rows": len(rows), "columns": cols, "issues": issues}


# ------------------------------------------------------------------ metrics
def matches(row: dict, where: dict | None) -> bool:
    for col, want in (where or {}).items():
        allowed = want if isinstance(want, list) else [want]
        if row.get(col, "").strip().lower() not in {str(a).lower() for a in allowed}:
            return False
    return True


def check_columns(m: dict, header: list) -> None:
    cols = [m.get(k) for k in ("column", "group_by", "id_column", "pre", "post") if m.get(k)]
    for key in ("where", "numerator_where"):
        cols += list((m.get(key) or {}).keys())
    missing = [c for c in cols if c not in header]
    if missing:
        raise InputError(f"metric {m.get('name')!r}: no such column(s) {', '.join(missing)}. Columns: {', '.join(header)}")


def compute(m: dict, rows: list) -> dict:
    """One metric over one set of rows. Returns value fields, n, and exclusions with reasons."""
    kind, excluded = m["kind"], {}
    if kind == "count_rows":
        return {"value": len(rows), "n": len(rows), "excluded": excluded}
    if kind == "count_unique":
        vals = [r[m["column"]].strip() for r in rows]
        blank = sum(not v for v in vals)
        if blank:
            excluded["blank " + m["column"]] = blank
        uniq = {v for v in vals if v}
        return {"value": len(uniq), "n": len(uniq), "excluded": excluded}
    if kind in ("sum", "mean", "median"):
        nums = [as_number(r[m["column"]]) for r in rows]
        bad = sum(n is None for n in nums)
        if bad:
            excluded["blank or not a number"] = bad
        good = [n for n in nums if n is not None]
        if not good:
            return {"value": None, "n": 0, "excluded": excluded}
        value = sum(good) if kind == "sum" else statistics.mean(good) if kind == "mean" else statistics.median(good)
        return {"value": r2(value), "n": len(good), "excluded": excluded}
    if kind == "rate":
        num = sum(matches(r, m["numerator_where"]) for r in rows)
        den = len(rows)
        return {"numerator": num, "denominator": den, "n": den,
                "value": r2(100 * num / den, 1) if den else None, "unit": "%", "excluded": excluded}
    # change_pre_post: matched participants only
    pairs, dropped = [], 0
    for r in rows:
        pre, post = as_number(r[m["pre"]]), as_number(r[m["post"]])
        if pre is None or post is None:
            dropped += 1
        else:
            pairs.append((pre, post))
    if dropped:
        excluded["no matched pre and post score"] = dropped
    if not pairs:
        return {"value": None, "n": 0, "matched": 0, "dropped": dropped, "excluded": excluded}
    pre_mean, post_mean = statistics.mean(p for p, _ in pairs), statistics.mean(q for _, q in pairs)
    return {"matched": len(pairs), "dropped": dropped, "n": len(pairs), "pre_mean": r2(pre_mean),
            "post_mean": r2(post_mean), "value": r2(post_mean - pre_mean), "excluded": excluded}


def suppress(groups: list, min_cell: int) -> list:
    """Hide groups below min_cell; if exactly one is hidden, hide the next smallest too."""
    out = [dict(g, suppressed=None) for g in groups]
    small = [g for g in out if g["n"] < min_cell]
    for g in small:
        g["suppressed"] = f"fewer than {min_cell}"
    if len(small) == 1 and len(out) > 1:
        rest = sorted((g for g in out if not g["suppressed"]), key=lambda g: (g["n"], g["group"]))
        if rest:
            rest[0]["suppressed"] = "complementary (so the total can't reveal the hidden group)"
    for g in out:
        if g["suppressed"]:
            for key in ("value", "numerator", "denominator", "n", "pre_mean", "post_mean", "matched", "dropped"):
                g.pop(key, None)
    return out


def run_metrics(header: list, rows: list, config: dict) -> dict:
    if not isinstance(config.get("metrics"), list) or not config["metrics"]:
        raise InputError('config needs a non-empty "metrics" list')
    min_cell = int(config.get("min_cell", 5))
    notes = [f"Groups smaller than {min_cell} are suppressed (min_cell is an org policy choice)."]
    if config.get("drop_exact_duplicates"):
        seen, kept = set(), []
        for r in rows:
            key = tuple(r[h] for h in header)
            if key not in seen:
                seen.add(key)
                kept.append(r)
        if len(kept) < len(rows):
            notes.append(f"Dropped {len(rows) - len(kept)} exact duplicate row(s) before computing.")
        rows = kept
    results = []
    for m in config["metrics"]:
        if m.get("kind") not in KINDS:
            raise InputError(f"metric {m.get('name')!r}: kind must be one of {', '.join(sorted(KINDS))}")
        if m["kind"] in ("count_unique", "sum", "mean", "median") and not m.get("column"):
            raise InputError(f"metric {m.get('name')!r}: needs a column")
        if m["kind"] == "rate" and not m.get("numerator_where"):
            raise InputError(f"metric {m.get('name')!r}: a rate needs numerator_where")
        if m["kind"] == "change_pre_post" and not all(m.get(k) for k in ("pre", "post")):
            raise InputError(f"metric {m.get('name')!r}: needs pre and post columns")
        check_columns(m, header)
        scoped = [r for r in rows if matches(r, m.get("where"))]
        out_of_scope = len(rows) - len(scoped)
        result = {"name": m["name"], "kind": m["kind"], "meaning": m.get("meaning", ""),
                  "definition": {k: v for k, v in m.items() if k not in ("name", "meaning")},
                  "overall": compute(m, scoped)}
        if out_of_scope:
            result["overall"]["excluded"]["outside the metric's filter"] = out_of_scope
        if result["overall"]["n"] < min_cell:
            result["overall"] = {"suppressed": f"fewer than {min_cell}", "excluded": result["overall"]["excluded"]}
        if m.get("group_by"):
            names = sorted({r[m["group_by"]].strip() for r in scoped})
            groups = [dict(compute(m, [r for r in scoped if r[m["group_by"]].strip() == g]), group=g) for g in names]
            result["groups"] = suppress(groups, min_cell)
        results.append(result)
    return {"generated_with": f"impact-report-builder {VERSION}", "min_cell": min_cell,
            "rows_used": len(rows), "notes": notes, "metrics": results}


def render_metrics(res: dict) -> str:
    lines = [f"Metrics ({res['rows_used']} rows). " + " ".join(res["notes"])]
    for m in res["metrics"]:
        lines.append(f"- {m['name']}: {fmt_result(m['overall'])}" + (f"  ({m['meaning']})" if m["meaning"] else ""))
        for g in m.get("groups", []):
            lines.append(f"    {g['group']}: " + (f"suppressed, {g['suppressed']}" if g["suppressed"] else fmt_result(g)))
    return "\n".join(lines)


def fmt_result(r: dict) -> str:
    if r.get("suppressed"):
        return f"suppressed, {r['suppressed']}"
    if "numerator" in r:
        text = f"{r['value']}% ({r['numerator']} of {r['denominator']})"
    elif "matched" in r:
        text = (f"change {r['value']} (pre {r.get('pre_mean')} -> post {r.get('post_mean')}; "
                f"{r['matched']} matched, {r['dropped']} dropped)")
    else:
        text = f"{r['value']} (n={r['n']})"
    left = r.get("excluded") or {}
    return text + ("; left out: " + ", ".join(f"{v} {k}" for k, v in left.items()) if left else "")


# ------------------------------------------------------------------ verify
def known_numbers(metrics: dict) -> set:
    found = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            found.add(float(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in ("definition",):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(metrics.get("metrics", []))
    return found


def number_ok(value: float, decimals: int, known: set) -> bool:
    return any(r2(k, decimals) == value for k in known)


def verify(text: str, metrics: dict, allowed: set) -> dict:
    known = known_numbers(metrics) | allowed
    rates = [g for m in metrics.get("metrics", []) for g in [m["overall"], *m.get("groups", [])] if "numerator" in g]
    problems, checked = [], 0
    clean = re.sub(r"\[(?:NEEDS FROM ORG|CONFIRM|VERIFY):[^\]]*\]", "", text)
    for m in NUMBER.finditer(clean):
        raw = m.group(0)
        value = float(m.group(1).replace(",", "") + (m.group(2) or ""))
        decimals = len(m.group(2)) - 1 if m.group(2) else 0
        checked += 1
        is_year = not m.group(3) and not raw.startswith("$") and "," not in raw and 1900 <= value <= 2100 and decimals == 0
        if is_year or number_ok(value, decimals, known):
            continue
        line = clean.count("\n", 0, m.start()) + 1
        problems.append({"number": raw, "line": line, "problem": "not in metrics.json or the allowed list"})
    for m in RATE_PHRASE.finditer(clean):
        pct, num, den = float(m.group(1)), int(m.group(2).replace(",", "")), int(m.group(3).replace(",", ""))
        decimals = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
        if not any(g["numerator"] == num and g["denominator"] == den and r2(g["value"], decimals) == pct for g in rates):
            line = clean.count("\n", 0, m.start()) + 1
            problems.append({"number": m.group(0), "line": line,
                             "problem": "percentage, numerator and denominator don't match any computed rate"})
    return {"numbers_checked": checked, "problems": problems, "passed": not problems}


# ------------------------------------------------------------------ cli
def emit(fmt: str, payload: dict, text: str) -> None:
    print(json.dumps(payload, indent=2) if fmt == "json" else text)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Profile program data, compute metrics, verify a draft.",
                                 epilog="Exit codes: 0 ok; 1 issues, suppressed groups or unverified numbers; 2 bad input.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile", help="check a CSV before computing anything")
    p.add_argument("csv")
    p = sub.add_parser("metrics", help="compute metrics from a JSON config")
    p.add_argument("csv")
    p.add_argument("--config", required=True)
    p.add_argument("--out", help="write metrics.json here")
    p = sub.add_parser("verify", help="check every number in a draft")
    p.add_argument("draft")
    p.add_argument("--metrics", required=True)
    p.add_argument("--allow", default="", help="comma-separated extra numbers allowed (page numbers, funder's figures)")
    for p in sub.choices.values():
        p.add_argument("--format", choices=["md", "json"], default="md")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "profile":
            header, rows, _ = read_csv(args.csv)
            res = profile(header, rows)
            text = [f"Profile: {res['rows']} rows, {len(res['columns'])} columns"]
            text += [f"- {c['column']}: {c['type']}, {c['missing']} blank, {c['distinct']} distinct" for c in res["columns"]]
            text += ["Issues:"] + [f"  - {i}" for i in res["issues"]] if res["issues"] else ["No issues found."]
            emit(args.format, res, "\n".join(text))
            return FINDINGS if res["issues"] else OK
        if args.cmd == "metrics":
            header, rows, raw = read_csv(args.csv)
            try:
                config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise InputError(f"config is missing or not valid JSON: {exc}")
            res = run_metrics(header, rows, config)
            res["source_file"] = Path(args.csv).name
            res["source_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if args.out:
                Path(args.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
            emit(args.format, res, render_metrics(res) + (f"\nWrote {args.out}" if args.out else ""))
            suppressed = any(g.get("suppressed") for m in res["metrics"] for g in [m["overall"], *m.get("groups", [])])
            return FINDINGS if suppressed else OK
        draft = Path(args.draft)
        if not draft.is_file():
            raise InputError(f"draft not found: {args.draft}")
        try:
            metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputError(f"metrics file is missing or not valid JSON: {exc}")
        try:
            allowed = {float(a.strip()) for a in args.allow.split(",") if a.strip()}
        except ValueError:
            raise InputError("--allow takes comma-separated numbers")
        res = verify(draft.read_text(encoding="utf-8"), metrics, allowed)
        text = [f"verify: {res['numbers_checked']} numbers checked: {'PASS' if res['passed'] else 'FAIL'}"]
        text += [f"  line {p['line']}: {p['number']}: {p['problem']}" for p in res["problems"]]
        emit(args.format, res, "\n".join(text))
        return OK if res["passed"] else FINDINGS
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
