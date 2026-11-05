#!/usr/bin/env python3
"""pii-guard: find and mask personal and sensitive information. Standard library only (Python 3.9+).

One file, no installs: a non-technical person can download this file alone and run it.
Run it on your own computer BEFORE uploading anything. Uploading a file to a chat sends
it to the model; redaction only protects data when it happens first.

Subcommands
  scan      Report what was found: counts by type, where, masked examples, a suggested tier.
            Never prints raw values unless --reveal (local terminal use only).
  redact    Write a redacted copy plus a LOCAL mapping file (token -> original value).
            Refuses when Red data is present (card numbers, sensitive context).
  verify    Re-scan a redacted copy. Fails if any identifier or Red context is left.
  restore   Put the original values back into a finished draft, locally, from the mapping file.
  selftest  Measure recall and precision per detector on the bundled synthetic corpus.

Inputs: .txt, .md, .text, .log (plain text) or .csv. Use "-" to read text from stdin.
Export other formats (Word, Excel, PDF) to CSV or plain text first.

Detectors: EMAIL, PHONE, CARD (Luhn-checked), DOB (only dates next to a birth cue),
ADDRESS (best effort), IP, URL_ID, ID_NUMBER (your patterns, --id-patterns),
NAME_LISTED (your names file, --names), NAME_CUE (low confidence: a capitalized name after
"Ms.", "client", "participant" ...), SENSITIVE_CONTEXT (flags health, mental health,
immigration, domestic violence or shelter, minors, criminal justice and substance use
context; it is flagged, not redacted, and makes the data Red).
Social Security numbers are not detected: they are out of scope for this pack.

Exit codes
  0  ok: nothing found (scan), redaction written (redact), clean (verify), all tokens restored
     (restore), recall targets met (selftest)
  1  findings or warnings you must look at: something was found (scan), redaction refused
     because Red data is present (redact), something is left over (verify), unknown tokens
     (restore), a recall target missed (selftest)
  2  bad input or error: missing or unreadable file, unsupported format, bad pattern file,
     unsafe mapping-file location, a mapping file that changed while it was being used

Examples
  python3 scan.py scan donors.csv --names names.txt
  python3 scan.py scan notes.txt --id-patterns id-patterns.json --format json
  python3 scan.py redact donors.csv --out donors-redacted.csv --map ~/private/donors-map.json \\
      --mask-columns first_name,last_name --drop-columns notes
  python3 scan.py verify donors-redacted.csv
  python3 scan.py restore report-draft.md --map ~/private/donors-map.json --out report-final.md
  python3 scan.py selftest
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import ipaddress
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

VERSION = "0.1.0"
OK, FINDINGS, BAD_INPUT = 0, 1, 2
SKILL_DIR = Path(__file__).resolve().parents[1]
SELFTEST_DIR = SKILL_DIR / "assets" / "selftest"
TEXT_SUFFIXES = {".txt", ".md", ".text", ".log"}
RECALL_TARGET = 0.99
RECALL_TARGET_TYPES = ("EMAIL", "PHONE", "CARD")
MAX_LOCATIONS = 10

# When two findings overlap, the earlier type in this list wins.
PRIORITY = ["URL_ID", "EMAIL", "ID_NUMBER", "CARD", "IP", "PHONE", "DOB", "ADDRESS",
            "NAME_LISTED", "NAME_CUE"]
RED_TYPES = {"CARD"}
# Everything except the low-confidence name heuristic must be gone after redaction.
VERIFY_FAIL_TYPES = set(PRIORITY) - {"NAME_CUE"}
TOKEN_TYPE = {"NAME_LISTED": "NAME", "NAME_CUE": "NAME", "URL_ID": "URL"}
TOKEN_RE = re.compile(r"\[[A-Z][A-Z0-9_]*_\d+\]")
SYNCED_MARKERS = ("dropbox", "onedrive", "google drive", "googledrive", "icloud",
                  "mobile documents", "cloudstorage", "box sync", "/box/")


class InputError(Exception):
    """Bad input: reported on stderr, exit code 2."""


@dataclass(frozen=True)
class Finding:
    type: str
    start: int
    end: int
    value: str
    confidence: str = "high"


@dataclass(frozen=True)
class ContextHit:
    family: str
    start: int
    end: int


# ------------------------------------------------------------------ patterns
MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
         r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
DATE = (rf"(?:\d{{1,2}}/\d{{1,2}}/\d{{2,4}}|\d{{4}}-\d{{2}}-\d{{2}}|{MONTH}\.? \d{{1,2}},? \d{{4}}"
        rf"|\d{{1,2}} {MONTH}\.? \d{{4}})")
STREET_SUFFIX = (r"(?:St|Street|Ave|Avenue|Rd|Road|Ln|Lane|Dr|Drive|Blvd|Boulevard|Ct|Court|Way|"
                 r"Pl|Place|Ter|Terrace|Pkwy|Parkway|Cir|Circle|Hwy|Highway)")
PATTERNS = {
    "EMAIL": re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "PHONE_US": re.compile(r"(?<![\w+])(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\d)"),
    "PHONE_INTL": re.compile(r"(?<![\w+])\+\d{1,3}(?:[\s.-]\(?\d{1,5}\)?){2,6}(?!\d)"),
    "CARD": re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])"),
    "DOB": re.compile(rf"(?i:\b(?:DOB|D\.O\.B\.?|date of birth|birth ?date|born(?: on)?)\s*[:\-]?\s*)({DATE})"),
    "ADDRESS": re.compile(rf"\b\d{{1,6}}\s+(?:[A-Z][A-Za-z'.-]*\s+){{1,3}}{STREET_SUFFIX}\b\.?"
                          r"(?:,\s*[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?"),
    "IPV4": re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\d|\.\d)"),
    "IPV6": re.compile(r"(?<![\w:])[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?![\w:])"),
    "URL": re.compile(r"https?://[^\s<>\"'()]+"),
    "NAME_CUE": re.compile(r"(?:\b(?:Mr|Mrs|Ms|Mx|Dr|Miss)\.?\s+|(?i:\b(?:client|participant|patient|"
                           r"resident|student|tenant|member|donor|volunteer)\s+))"
                           r"([A-Z][a-z'\u2019-]+(?:\s+[A-Z][a-z'\u2019-]+)?)"),
}
URL_ID_PART = re.compile(r"(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{12,}")
NAME_CUE_STOPWORDS = {"Services", "Portal", "Intake", "Handbook", "Survey", "Count", "List",
                      "Record", "Records", "Form", "Forms", "Notes", "Data", "Support", "Program",
                      "Programs", "Center", "Fund", "Day", "Of", "The", "And", "Appreciation"}
CONTEXT_FAMILIES = {
    "health": r"hospitali[sz]ed|hospital|diagnos\w*|chronic (?:condition|illness)|cancer|chemotherapy|"
              r"HIV|diabetes|disabilit\w*|medication|surgery|pregnan\w*|medical condition",
    "mental_health": r"depressi\w*|anxiety|counselou?r|therap(?:y|ist)|psychiatr\w*|PTSD|suicid\w*|"
                     r"bipolar|schizophreni\w*|mental health",
    "immigration": r"asylum|visa|undocumented|deport\w*|immigration status|green card|refugee|"
                   r"ICE detention",
    "domestic_violence_shelter": r"shelter|protective order|restraining order|domestic violence|"
                                 r"abuser|safe house",
    "minors": r"\d{1,2}-year-old (?:daughter|son|child|girl|boy)|juvenile|foster child|"
              r"elementary school|middle school|kindergarten|minor child",
    "criminal_justice": r"probation|parole|convict\w*|arrest\w*|incarcerat\w*|jail|prison|felony|"
                        r"misdemeanou?r|criminal record",
    "substance_use": r"in recovery|methadone|rehab\w*|sobriety|overdos\w*|relapse\w*|"
                     r"substance use|addiction",
}
CONTEXT_RES = {fam: re.compile(rf"\b(?:{pat})\b", re.I) for fam, pat in CONTEXT_FAMILIES.items()}
HEADER_HINTS = re.compile(r"name|e-?mail|phone|mobile|address|street|zip|postal|birth|dob|"
                          r"notes?|comment|case|client|account|card", re.I)


# ------------------------------------------------------------------ detection
def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def _raw_findings(text: str, names_re: re.Pattern | None, id_res: list) -> list:
    out = [Finding("EMAIL", m.start(), m.end(), m.group()) for m in PATTERNS["EMAIL"].finditer(text)]
    for key in ("PHONE_US", "PHONE_INTL"):
        for m in PATTERNS[key].finditer(text):
            if 8 <= len(re.sub(r"\D", "", m.group())) <= 15:
                out.append(Finding("PHONE", m.start(), m.end(), m.group()))
    for m in PATTERNS["CARD"].finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and len(set(digits)) > 1 and luhn_ok(digits):
            out.append(Finding("CARD", m.start(), m.end(), m.group()))
    out += [Finding("DOB", m.start(1), m.end(1), m.group(1)) for m in PATTERNS["DOB"].finditer(text)]
    out += [Finding("ADDRESS", m.start(), m.end(), m.group(), "medium")
            for m in PATTERNS["ADDRESS"].finditer(text)]
    out += [Finding("IP", m.start(), m.end(), m.group()) for m in PATTERNS["IPV4"].finditer(text)]
    for m in PATTERNS["IPV6"].finditer(text):
        try:
            if m.group().count(":") >= 2 and ipaddress.IPv6Address(m.group()):
                out.append(Finding("IP", m.start(), m.end(), m.group()))
        except ValueError:
            pass
    for m in PATTERNS["URL"].finditer(text):
        url = m.group().rstrip(".,;:!?")
        if any(URL_ID_PART.fullmatch(p) for p in re.split(r"[/?&=#]", url.split("://", 1)[1])[1:]):
            out.append(Finding("URL_ID", m.start(), m.start() + len(url), url))
    for rx in id_res:
        out += [Finding("ID_NUMBER", m.start(), m.end(), m.group()) for m in rx.finditer(text)]
    if names_re is not None:
        out += [Finding("NAME_LISTED", m.start(), m.end(), m.group()) for m in names_re.finditer(text)]
    for m in PATTERNS["NAME_CUE"].finditer(text):
        if m.group(1).split()[0] not in NAME_CUE_STOPWORDS:
            out.append(Finding("NAME_CUE", m.start(1), m.end(1), m.group(1), "low"))
    return out


def detect(text: str, names_re: re.Pattern | None = None, id_res: list | None = None) -> list:
    """Non-overlapping findings, in text order. Higher-priority types win overlaps."""
    ranked = sorted(_raw_findings(text, names_re, id_res or []),
                    key=lambda f: (PRIORITY.index(f.type), -(f.end - f.start), f.start))
    kept: list = []
    for f in ranked:
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    return sorted(kept, key=lambda f: f.start)


def detect_context(text: str) -> list:
    return [ContextHit(fam, m.start(), m.end())
            for fam, rx in CONTEXT_RES.items() for m in rx.finditer(text)]


def mask(ftype: str, value: str) -> str:
    """A display form that shows the kind of value without revealing it."""
    if ftype == "EMAIL":
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}"
    if ftype in ("PHONE", "CARD", "ID_NUMBER"):
        return "***" + re.sub(r"\W", "", value)[-2:]
    if ftype in ("NAME_LISTED", "NAME_CUE"):
        return " ".join(w[:1] + "***" for w in value.split())
    if ftype == "URL_ID":
        return value.split("://", 1)[0] + "://" + value.split("://", 1)[1].split("/", 1)[0] + "/***"
    return {"DOB": "[date]", "ADDRESS": "[street address]", "IP": "[ip address]"}.get(ftype, "***")


# ------------------------------------------------------------------ inputs
def load_names(path: str | None) -> re.Pattern | None:
    if not path:
        return None
    names = [ln.strip() for ln in read_text(path).splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    short = [n for n in names if len(n) < 3]
    if short:
        raise InputError(f"names file has entries shorter than 3 characters (would over-match): {len(short)}")
    if not names:
        raise InputError(f"names file is empty: {path}")
    alts = sorted({r"\s+".join(map(re.escape, n.split())) for n in names}, key=len, reverse=True)
    return re.compile(rf"(?<!\w)(?:{'|'.join(alts)})(?!\w)", re.I)


def load_id_patterns(path: str | None) -> list:
    if not path:
        return []
    try:
        config = json.loads(read_text(path))
        patterns = config["patterns"]
        if not isinstance(patterns, dict) or not patterns:
            raise KeyError
    except (json.JSONDecodeError, KeyError, TypeError):
        raise InputError(f'id-patterns file must be JSON like {{"patterns": {{"CASE": "regex"}}}}: {path}')
    compiled = []
    for label, pattern in patterns.items():
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise InputError(f"id pattern {label!r} is not a valid regular expression: {exc}")
    return compiled


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    p = Path(path)
    if not p.is_file():
        raise InputError(f"file not found: {path}")
    try:
        return p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"not UTF-8 text: {path}. Export it as UTF-8 CSV or plain text first.")


def load_input(path: str) -> dict:
    """Return {"kind": "text"|"csv", "text": str} or {"kind": "csv", "header": [...], "rows": [[...]]}."""
    suffix = Path(path).suffix.lower() if path != "-" else ".txt"
    if suffix == ".csv":
        rows = list(csv.reader(io.StringIO(read_text(path))))
        if not rows or not any(rows[0]):
            raise InputError(f"CSV has no header row: {path}")
        return {"kind": "csv", "header": rows[0], "rows": rows[1:]}
    if suffix in TEXT_SUFFIXES:
        return {"kind": "text", "text": read_text(path)}
    raise InputError(f"unsupported file type {suffix!r}. Export it to .csv or plain .txt first.")


def cells(data: dict):
    """Yield (location, text) pairs: ("line", None) for text, (row_number, column) for CSV."""
    if data["kind"] == "text":
        yield None, data["text"]
        return
    for r, row in enumerate(data["rows"], start=2):
        for c, value in enumerate(row):
            col = data["header"][c] if c < len(data["header"]) else f"column {c + 1}"
            yield (r, col), value


# ------------------------------------------------------------------ scan
def analyze(data: dict, names_re, id_res) -> dict:
    by_type: dict = {}
    contexts: dict = {}
    for loc, text in cells(data):
        for f in detect(text, names_re, id_res):
            where = f"line {text.count(chr(10), 0, f.start) + 1}" if loc is None else loc[1]
            by_type.setdefault(f.type, []).append((where, f))
        for hit in detect_context(text):
            where = f"line {text.count(chr(10), 0, hit.start) + 1}" if loc is None else loc[1]
            contexts.setdefault(hit.family, []).append(where)
    red_reasons = [t for t in by_type if t in RED_TYPES] + sorted(contexts)
    tier = "red" if red_reasons else ("amber" if by_type else "green-or-unknown")
    hints = [h for h in data.get("header", []) if HEADER_HINTS.search(h)]
    return {"by_type": by_type, "contexts": contexts, "tier": tier,
            "red_reasons": red_reasons, "header_hints": hints}


def _where_summary(wheres: list) -> str:
    counts: dict = {}
    for w in wheres:
        counts[w] = counts.get(w, 0) + 1
    if all(w.startswith("line ") for w in counts):
        shown = list(counts)[:MAX_LOCATIONS]
        more = len(counts) - len(shown)
        return ", ".join(shown) + (f" (+{more} more)" if more else "")
    return ", ".join(f"{w} ({n})" for w, n in counts.items())


def scan_payload(path: str, data: dict, result: dict, reveal: bool, names_used: bool, ids_used: bool) -> dict:
    types = {}
    for ftype in PRIORITY:
        items = result["by_type"].get(ftype, [])
        if items:
            examples = []
            for _, f in items:
                shown = f.value if reveal else mask(ftype, f.value)
                if shown not in examples:
                    examples.append(shown)
            types[ftype] = {"count": len(items), "where": _where_summary([w for w, _ in items]),
                            "examples": examples[:3], "confidence": items[0][1].confidence}
    notes = ["Pattern scanning cannot guarantee it found every name or identifier. Review before use."]
    if not names_used:
        notes.append("No names file given (--names): people's names are only caught after cues "
                     "like 'Ms.' or 'client', at low confidence.")
    if not ids_used:
        notes.append("No ID patterns given (--id-patterns): case numbers and member IDs are not checked.")
    if "NAME_CUE" in types:
        notes.append("NAME_CUE findings are a heuristic (low confidence): expect misses and false alarms.")
    return {"file": path, "kind": data["kind"], "suggested_tier": result["tier"],
            "red_reasons": result["red_reasons"], "findings": types,
            "sensitive_context": {fam: _where_summary(w) for fam, w in sorted(result["contexts"].items())},
            "identifying_columns": result["header_hints"], "notes": notes,
            "values_shown": "raw (--reveal)" if reveal else "masked"}


def render_scan_md(p: dict) -> str:
    lines = [f"pii-guard scan: {p['file']} ({p['kind']})"]
    tier = p["suggested_tier"].upper()
    if p["red_reasons"]:
        lines.append(f"Suggested tier: RED because of {', '.join(p['red_reasons'])}. "
                     "Stop: do not process this with other skills. Use an aggregate or "
                     "de-identified version, or ask the data policy owner.")
    elif p["findings"]:
        lines.append("Suggested tier: AMBER (identifies individuals). Confirm with the user.")
    else:
        lines.append(f"Suggested tier: {tier}. No findings. That is not proof the data is safe: "
                     "the scanner only knows the patterns listed in --help.")
    if p["findings"]:
        lines.append(f"Findings ({p['values_shown']} values):")
        for ftype, info in p["findings"].items():
            lines.append(f"  {ftype:<12}{info['count']:>5}  {info['where']}   e.g. "
                         f"{', '.join(info['examples'])}   [{info['confidence']} confidence]")
    if p["sensitive_context"]:
        lines.append("Sensitive context (flagged, not redacted):")
        lines += [f"  {fam:<27}{where}" for fam, where in p["sensitive_context"].items()]
    if p["identifying_columns"]:
        lines.append("Columns whose names suggest identifying data: " + ", ".join(p["identifying_columns"]))
    lines += ["Notes:"] + [f"  - {n}" for n in p["notes"]]
    return "\n".join(lines)


def cmd_scan(args) -> int:
    data = load_input(args.input)
    names_re, id_res = load_names(args.names), load_id_patterns(args.id_patterns)
    if args.reveal:
        print("WARNING: --reveal prints raw values. Local terminal only; never paste this into a chat.",
              file=sys.stderr)
    result = analyze(data, names_re, id_res)
    payload = scan_payload(args.input, data, result, args.reveal, bool(names_re), bool(id_res))
    emit(args.format, payload, render_scan_md(payload))
    return FINDINGS if payload["findings"] or payload["sensitive_context"] else OK


# ------------------------------------------------------------------ mapping file
def unsafe_location(path: Path) -> str | None:
    resolved = path.expanduser().resolve()
    lowered = str(resolved).lower() + "/"
    marker = next((m for m in SYNCED_MARKERS if m in lowered), None)
    if marker:
        return f"it looks like a synced folder ({marker.strip('/')})"
    for parent in resolved.parents:
        if (parent / ".git").exists():
            return f"it is inside a git repository ({parent})"
    return None


class MappingFile:
    """The token <-> value map. Holds raw values, so it stays local and owner-only."""

    def __init__(self, path: Path):
        self.path = path
        self.raw = path.read_bytes() if path.is_file() else None
        self.digest = hashlib.sha256(self.raw).hexdigest() if self.raw is not None else None
        data = json.loads(self.raw) if self.raw else {}
        if self.raw and data.get("created_with", "").split(" ")[0] != "pii-guard":
            raise InputError(f"{path} is not a pii-guard mapping file")
        self.tokens = dict(data.get("tokens", {}))
        self.index = dict(data.get("index", {}))
        self.counters = dict(data.get("counters", {}))

    def token_for(self, ttype: str, value: str) -> str:
        key = f"{ttype}|{normalize(ttype, value)}"
        if key not in self.index:
            self.counters[ttype] = self.counters.get(ttype, 0) + 1
            token = f"[{ttype}_{self.counters[ttype]}]"
            self.index[key] = token
            self.tokens[token] = value
        return self.index[key]

    def save(self):
        now = self.path.read_bytes() if self.path.is_file() else None
        if (hashlib.sha256(now).hexdigest() if now is not None else None) != self.digest:
            raise InputError(f"{self.path} changed since it was read. Nothing was written. Re-run.")
        payload = {"schema_version": "1.0", "created_with": f"pii-guard {VERSION}",
                   "last_updated": dt.date.today().isoformat(),
                   "warning": "Contains the original values. Keep it on this computer. Never upload it.",
                   "tokens": self.tokens, "index": self.index, "counters": self.counters}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)


def normalize(ttype: str, value: str) -> str:
    if ttype in ("PHONE", "CARD"):
        digits = re.sub(r"\D", "", value)
        return digits[1:] if ttype == "PHONE" and len(digits) == 11 and digits[0] == "1" else digits
    return " ".join(value.lower().split())


def check_private_path(path: Path, allow_synced: bool, what: str) -> None:
    reason = unsafe_location(path)
    if reason and not allow_synced:
        raise InputError(f"refusing to write the {what} to {path}: {reason}. It holds original "
                         "values. Choose a private local folder, or pass --allow-synced if you "
                         "are sure (not recommended).")
    if reason:
        print(f"WARNING: writing the {what} where {reason}. It holds original values.", file=sys.stderr)


# ------------------------------------------------------------------ redact
def redact_text(text: str, mapping: MappingFile, names_re, id_res, keep: set) -> tuple:
    counts: dict = {}
    out = text
    for f in reversed(detect(text, names_re, id_res)):
        if f.type in keep:
            continue
        ttype = TOKEN_TYPE.get(f.type, f.type)
        out = out[:f.start] + mapping.token_for(ttype, f.value) + out[f.end:]
        counts[f.type] = counts.get(f.type, 0) + 1
    return out, counts


def column_token_type(column: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", column.upper()).strip("_") or "COLUMN"


def redaction_blockers(data: dict, names_re, id_res) -> list:
    blockers = []
    for loc, text in cells(data):
        where = "the text" if loc is None else f"column {loc[1]!r}"
        blockers += [f"CARD in {where}" for f in detect(text, names_re, id_res) if f.type in RED_TYPES]
        blockers += [f"{h.family} context in {where}" for h in detect_context(text)]
    return sorted(set(blockers))


def split_columns(spec: str | None, header: list, flag: str) -> list:
    cols = [c.strip() for c in (spec or "").split(",") if c.strip()]
    missing = [c for c in cols if c not in header]
    if missing:
        raise InputError(f"{flag}: no such column(s): {', '.join(missing)}. Columns: {', '.join(header)}")
    return cols


def cmd_redact(args) -> int:
    src, out, map_path = Path(args.input), Path(args.out), Path(args.map).expanduser()
    if out.resolve() == src.resolve():
        raise InputError("--out must be a new file, not the input")
    if out.exists() and not args.overwrite:
        raise InputError(f"{out} already exists. Pass --overwrite to replace it.")
    check_private_path(map_path, args.allow_synced, "mapping file")
    data = load_input(args.input)
    names_re, id_res = load_names(args.names), load_id_patterns(args.id_patterns)
    keep = {k.strip().upper() for k in (args.keep or "").split(",") if k.strip()}
    unknown = keep - set(PRIORITY)
    if unknown:
        raise InputError(f"--keep: unknown type(s) {', '.join(sorted(unknown))}. Types: {', '.join(PRIORITY)}")
    if data["kind"] == "text" and (args.drop_columns or args.mask_columns):
        raise InputError("--drop-columns and --mask-columns only apply to CSV files")
    if data["kind"] == "csv":
        drop = split_columns(args.drop_columns, data["header"], "--drop-columns")
        masked = split_columns(args.mask_columns, data["header"], "--mask-columns")
        keep_idx = [i for i, h in enumerate(data["header"]) if h not in drop]
        data = {"kind": "csv", "header": [data["header"][i] for i in keep_idx],
                "rows": [[row[i] if i < len(row) else "" for i in keep_idx] for row in data["rows"]]}
    blockers = redaction_blockers(data, names_re, id_res)
    if blockers:
        lines = ["Redaction refused: this file contains Red data. Redacting it would not make it",
                 "safe to use, so nothing was written. Remove or drop the Red parts first",
                 "(e.g. --drop-columns), or work from an aggregate version. Exceptions are the",
                 "data policy owner's decision.", "Found:"] + [f"  - {b}" for b in blockers]
        emit(args.format, {"refused": True, "red": blockers}, "\n".join(lines))
        return FINDINGS
    mapping = MappingFile(map_path)
    totals: dict = {}
    if data["kind"] == "text":
        text, totals = redact_text(data["text"], mapping, names_re, id_res, keep)
        body = text
    else:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(data["header"])
        for row in data["rows"]:
            new_row = []
            for col, value in zip(data["header"], row):
                if col in masked and value.strip():
                    new_row.append(mapping.token_for(column_token_type(col), value.strip()))
                    totals[f"column:{col}"] = totals.get(f"column:{col}", 0) + 1
                    continue
                cell, counts = redact_text(value, mapping, names_re, id_res, keep)
                for k, v in counts.items():
                    totals[k] = totals.get(k, 0) + v
                new_row.append(cell)
            writer.writerow(new_row)
        body = buf.getvalue()
    mapping.save()
    out.write_text(body, encoding="utf-8")
    payload = {"refused": False, "redacted_copy": str(out), "mapping_file": str(map_path),
               "replaced": dict(sorted(totals.items())), "kept": sorted(keep),
               "dropped_columns": drop if data["kind"] == "csv" else []}
    lines = [f"Redacted copy: {out}", f"Mapping file (LOCAL ONLY, never upload): {map_path}",
             "Replaced: " + (", ".join(f"{k} {v}" for k, v in payload["replaced"].items()) or "nothing")]
    if payload["dropped_columns"]:
        lines.append("Dropped columns: " + ", ".join(payload["dropped_columns"]))
    if keep:
        lines.append("Left in place at your request: " + ", ".join(sorted(keep)))
    lines.append(f"Next: run  python3 scan.py verify {out}  and review the copy before using it.")
    emit(args.format, payload, "\n".join(lines))
    return OK


# ------------------------------------------------------------------ verify
def cmd_verify(args) -> int:
    data = load_input(args.input)
    result = analyze(data, load_names(args.names), load_id_patterns(args.id_patterns))
    left = {t: len(v) for t, v in result["by_type"].items() if t in VERIFY_FAIL_TYPES}
    warn = {t: len(v) for t, v in result["by_type"].items() if t not in VERIFY_FAIL_TYPES}
    contexts = sorted(result["contexts"])
    passed = not left and not contexts and not (args.strict and warn)
    payload = {"file": args.input, "passed": passed, "identifiers_left": left,
               "low_confidence_left": warn, "sensitive_context": contexts}
    lines = [f"pii-guard verify: {args.input}: {'PASS' if passed else 'FAIL'}"]
    if left:
        lines.append("Identifiers still present: " + ", ".join(f"{t} {n}" for t, n in left.items()))
    if contexts:
        lines.append("Red context still present: " + ", ".join(contexts))
    if warn:
        lines.append("Possible names left (low confidence, check by eye): "
                     + ", ".join(f"{t} {n}" for t, n in warn.items()))
    lines.append("This is a redacted copy, not an anonymized one: small groups and rare "
                 "combinations can still identify people. Review before use.")
    emit(args.format, payload, "\n".join(lines))
    return OK if passed else FINDINGS


# ------------------------------------------------------------------ restore
def cmd_restore(args) -> int:
    map_path, out = Path(args.map).expanduser(), Path(args.out)
    if not map_path.is_file():
        raise InputError(f"mapping file not found: {map_path}")
    if out.resolve() == Path(args.input).resolve():
        raise InputError("--out must be a new file, not the input")
    check_private_path(out, args.allow_synced, "restored file")
    mapping = MappingFile(map_path)
    text = read_text(args.input)
    unknown = sorted({t for t in TOKEN_RE.findall(text) if t not in mapping.tokens})
    restored = TOKEN_RE.sub(lambda m: mapping.tokens.get(m.group(), m.group()), text)
    count = sum(1 for t in TOKEN_RE.findall(text) if t in mapping.tokens)
    out.write_text(restored, encoding="utf-8")
    payload = {"restored_file": str(out), "tokens_restored": count, "unknown_tokens": unknown}
    lines = [f"Restored {count} token(s) into {out}. This file holds original values: keep it local."]
    if unknown:
        lines.append("Tokens not in the mapping file (left as they are): " + ", ".join(unknown))
    emit(args.format, payload, "\n".join(lines))
    return FINDINGS if unknown else OK


# ------------------------------------------------------------------ selftest
def parse_holdout(text: str) -> list:
    """Hand-written records: one per line, values marked {{TYPE|value}}, '## context=a,b' at the end."""
    records = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        body, _, ctx = line.partition(" ## context=")
        labels, plain, pos = [], "", 0
        for m in re.finditer(r"\{\{([A-Z_]+)\|(.+?)\}\}", body):
            plain += body[pos:m.start()]
            labels.append({"type": m.group(1), "start": len(plain),
                           "end": len(plain) + len(m.group(2)), "value": m.group(2)})
            plain += m.group(2)
            pos = m.end()
        plain += body[pos:]
        records.append({"text": plain, "labels": labels,
                        "context_families": [c for c in ctx.strip().split(",") if c]})
    return records


def score(records: list, names_re, id_res) -> dict:
    stats = {t: {"tp": 0, "fn": 0, "fp": 0} for t in PRIORITY}
    ctx = {f: {"tp": 0, "fn": 0, "fp": 0} for f in CONTEXT_FAMILIES}
    for rec in records:
        found = detect(rec["text"], names_re, id_res)
        labels = rec["labels"]
        for lab in labels:
            hit = any(f.type == lab["type"] and f.start < lab["end"] and lab["start"] < f.end for f in found)
            stats[lab["type"]]["tp" if hit else "fn"] += 1
        for f in found:
            if not any(lab["type"] == f.type and f.start < lab["end"] and lab["start"] < f.end for lab in labels):
                stats[f.type]["fp"] += 1
        flagged = {h.family for h in detect_context(rec["text"])}
        for fam in ctx:
            truth = fam in rec["context_families"]
            if truth:
                ctx[fam]["tp" if fam in flagged else "fn"] += 1
            elif fam in flagged:
                ctx[fam]["fp"] += 1

    def rates(s):
        labelled, predicted = s["tp"] + s["fn"], s["tp"] + s["fp"]
        return dict(s, recall=round(s["tp"] / labelled, 4) if labelled else None,
                    precision=round(s["tp"] / predicted, 4) if predicted else None)
    return {"records": len(records), "detectors": {t: rates(s) for t, s in stats.items()},
            "context": {f: rates(s) for f, s in ctx.items()}}


def render_score(title: str, result: dict) -> list:
    lines = [f"{title}: {result['records']} records",
             f"  {'type':<34}{'found':>7}{'missed':>8}{'false+':>8}{'recall':>9}{'precision':>11}"]
    for group in ("detectors", "context"):
        for name, s in result[group].items():
            if s["tp"] + s["fn"] + s["fp"] == 0:
                continue
            rec = "n/a" if s["recall"] is None else f"{s['tp']}/{s['tp'] + s['fn']}"
            prec = "n/a" if s["precision"] is None else f"{s['tp']}/{s['tp'] + s['fp']}"
            label = name if group == "detectors" else f"context:{name}"
            lines.append(f"  {label:<34}{s['tp']:>7}{s['fn']:>8}{s['fp']:>8}{rec:>9}{prec:>11}")
    return lines


def cmd_selftest(args) -> int:
    corpus_path = Path(args.corpus)
    if not corpus_path.is_file():
        raise InputError(f"corpus not found: {corpus_path}")
    try:
        corpus = [json.loads(ln) for ln in corpus_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except json.JSONDecodeError as exc:
        raise InputError(f"corpus is not valid JSON lines: {exc}")
    names_re, id_res = load_names(args.names), load_id_patterns(args.id_patterns)
    main_result = score(corpus, names_re, id_res)
    holdout = None
    if args.holdout and Path(args.holdout).is_file():
        holdout = score(parse_holdout(read_text(args.holdout)), names_re, id_res)
    missed = [t for t in RECALL_TARGET_TYPES
              if (main_result["detectors"][t]["recall"] or 0) < RECALL_TARGET]
    payload = {"corpus": main_result, "holdout": holdout, "recall_target": RECALL_TARGET,
               "target_types": list(RECALL_TARGET_TYPES), "targets_missed": missed}
    lines = render_score("Synthetic corpus (template-built)", main_result)
    if holdout:
        lines += [""] + render_score("Hand-written holdout (formats the generator does not make)", holdout)
    lines += ["", f"Recall target {RECALL_TARGET:.0%} on {', '.join(RECALL_TARGET_TYPES)} (corpus): "
              + ("met" if not missed else "MISSED for " + ", ".join(missed)),
              "These numbers describe synthetic text. Real documents will score lower."]
    emit(args.format, payload, "\n".join(lines))
    return FINDINGS if missed else OK


# ------------------------------------------------------------------ cli
def emit(fmt: str, payload: dict, markdown: str) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) if fmt == "json" else markdown)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scan.py", description=__doc__.split("\n\n")[0],
        epilog="Exit codes: 0 ok; 1 findings or warnings you must look at; 2 bad input or error. "
               "Run `scan.py <subcommand> --help` for details.")
    parser.add_argument("--version", action="version", version=f"pii-guard {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, detectors=True):
        p.add_argument("--format", choices=["md", "json"], default="md", help="output format (default md)")
        if detectors:
            p.add_argument("--names", help="names file: one full name per line (clients, staff, donors)")
            p.add_argument("--id-patterns", help='JSON {"patterns": {"LABEL": "regex"}} for case or member IDs')

    p = sub.add_parser("scan", help="report findings, masked", epilog="Exit: 0 nothing found; 1 findings; 2 bad input.")
    p.add_argument("input", help="file to scan (.csv, .txt, .md) or - for stdin")
    p.add_argument("--reveal", action="store_true", help="print raw values (local terminal only)")
    common(p)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("redact", help="write a redacted copy and a local mapping file",
                       epilog="Exit: 0 written; 1 refused (Red data present); 2 bad input.")
    p.add_argument("input")
    p.add_argument("--out", required=True, help="redacted copy to write (new file)")
    p.add_argument("--map", required=True, help="mapping file path (local, private; reused if it exists)")
    p.add_argument("--keep", help="comma-separated types to leave in place, e.g. ADDRESS,DOB")
    p.add_argument("--drop-columns", help="CSV: columns to remove entirely")
    p.add_argument("--mask-columns", help="CSV: columns whose whole cell becomes a token (e.g. first_name)")
    p.add_argument("--overwrite", action="store_true", help="replace --out if it exists")
    p.add_argument("--allow-synced", action="store_true", help="allow the mapping file in a synced folder or git repo")
    common(p)
    p.set_defaults(func=cmd_redact)

    p = sub.add_parser("verify", help="re-scan a redacted copy",
                       epilog="Exit: 0 clean; 1 identifiers or Red context left; 2 bad input.")
    p.add_argument("input")
    p.add_argument("--strict", action="store_true", help="also fail on low-confidence name findings")
    common(p)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("restore", help="put original values back into a draft, locally",
                       epilog="Exit: 0 all tokens restored; 1 unknown tokens; 2 bad input.")
    p.add_argument("input", help="draft containing tokens like [EMAIL_1]")
    p.add_argument("--map", required=True)
    p.add_argument("--out", required=True, help="restored file to write (never printed)")
    p.add_argument("--allow-synced", action="store_true")
    common(p, detectors=False)
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("selftest", help="recall and precision on the bundled synthetic corpus",
                       epilog="Exit: 0 recall targets met; 1 a target missed; 2 bad input.")
    p.add_argument("--corpus", default=str(SELFTEST_DIR / "corpus.jsonl"))
    p.add_argument("--holdout", default=str(SELFTEST_DIR / "holdout.txt"))
    p.add_argument("--names", default=str(SELFTEST_DIR / "names-list.txt"))
    p.add_argument("--id-patterns", default=str(SELFTEST_DIR / "id-patterns.json"))
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.set_defaults(func=cmd_selftest)
    return parser


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT
    except OSError as exc:
        print(f"error: {exc.strerror or exc}: {getattr(exc, 'filename', '')}", file=sys.stderr)
        return BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
