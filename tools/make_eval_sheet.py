#!/usr/bin/env python3
"""Turn evals/<skill>/<case>/ folders into docs/EVAL-RUN-SHEET.md: a checklist for running the evals by hand
in Claude chat or Cowork. Standard library only (Python 3.9+). Re-run after any eval change.

Each grader becomes one check a person can tick:
  llm          its PASS / FAIL statement
  tool_used    "Claude used the <skill> skill" or "Claude ran <script> <subcommand>"
  regex        "The reply (or file) does / does not contain ..."
  file_exists  "No file matching ... was created"

Usage
  python3 tools/make_eval_sheet.py            # writes docs/EVAL-RUN-SHEET.md
  python3 tools/make_eval_sheet.py --check    # exit 1 if the sheet is out of date

Exit codes
  0  written, or up to date
  1  --check: the sheet differs from the eval folders
  2  bad input: an eval case without prompt.md or graders
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
OUT = ROOT / "docs" / "EVAL-RUN-SHEET.md"
ORDER = ["pii-guard", "grant-scout", "impact-report-builder", "board-minutes-tracker", "donor-thank-you-writer"]


def front(text: str) -> tuple:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(": ")
        fields[key.strip()] = value.strip()
    return fields, m.group(2).strip()


PATTERN_WORDS = {
    r"555[\s.-]?01\d\d": "any phone number (the sample numbers all look like 555-01xx)",
    r"66\.7|2 of 3|4 of 5": "a Family Literacy or Job Readiness rate (\"66.7\", \"2 of 3\" or \"4 of 5\")",
    r"@example\.(org|com|net)": "any email address (the sample addresses end in @example.org, .com or .net)",
    r"@example\.(org|com|net)|555[\s.-]?01\d\d": "any email address or phone number from the file",
    r"@example\.org": "any email address from the file (ending @example.org)",
    r"Ashgrove|Brindle|Copperfield|Dunmore|Eastwick|Hartwell": "any participant surname from roster.csv (Ashgrove, Brindle, Copperfield, Dunmore, Eastwick, Hartwell)",
    r"Dear Indigo Eastwick": "the restored letter (\"Dear Indigo Eastwick\")",
    r"F-\d\d": "at least one profile fact ID such as F-03",
    r"\[FIRST_NAME_\d+\],\[LAST_NAME_\d+\]": "masked name columns such as [FIRST_NAME_1],[LAST_NAME_1]",
    r"priya\.ashgrove@example\.org": "Priya's email address (priya.ashgrove@example.org)",
}


def plain_pattern(p: str) -> str:
    return PATTERN_WORDS.get(p, f"text matching the pattern `{p}`")


def check_text(fields: dict, body: str, skill: str) -> tuple:
    kind = fields.get("type")
    if kind == "llm":
        return "judge", body.replace("\n", "<br>")
    if kind == "tool_used":
        if fields.get("tool") == "Skill":
            return "skill-on only", f"Claude used the **{skill}** skill (look for it in the reply's activity or steps)."
        m = re.search(r"([\w-]+)\\\.py(?:\[\^\"\]\*\\b(\w[\w-]*))?", fields.get("input_match", ""))
        script = f"{m.group(1)}.py" + (f" {m.group(2)}" if m and m.group(2) else "") if m else "the skill's script"
        return "check", f"Claude ran **`{script}`** (visible in the code or analysis steps)."
    if kind == "regex":
        target = fields.get("target", "last_message")
        where = "Claude's final reply"
        fm = re.search(r"path:\s*([^}\s]+)", target)
        if fm:
            where = f"the file `{fm.group(1)}`"
        verb = "does **not** contain" if fields.get("match") == "not_contains" else "contains"
        pat = fields.get("pattern", "").strip("'")
        return "check", f"{where[0].upper() + where[1:]} {verb} {plain_pattern(pat)}."
    if kind == "file_exists":
        return "check", f"No file matching `{fields.get('path', '').strip(chr(39))}` was created."
    return "check", f"(grader type {kind})"


def build() -> str:
    lines = ["# Eval run sheet (manual)", "",
             "Generated from `evals/` by `tools/make_eval_sheet.py`. Don't edit by hand: change the eval case and re-run the script.", "",
             "## How to run these by hand", "",
             "1. Install the skills (`docs/GUIDE.md` §4). In **Customize → Skills**, you'll switch the skill being tested **on** for the first run and **off** for the second.",
             "2. For each case: start a **new chat**, attach the files listed (from `evals/<skill>/<case>/files/` in the pack folder), and paste the prompt exactly.",
             "3. Let Claude finish. Then tick each check: ✅ pass or ❌ fail. For \"judge\" checks, read the PASS and FAIL statements and decide which one is true.",
             "4. Do the same case again in a new chat with the skill **switched off**. Checks marked *skill-on only* don't count in the off run.",
             "5. Fill in the totals at the end and copy them into the README. Report raw counts (\"31 of 40 checks\"), the model and the date. One run per case is a small sample: say so.",
             "",
             "All data is synthetic. Never paste real donor, client or board data into these tests.", ""]
    totals = []
    for skill in ORDER:
        cases = sorted(p for p in (EVALS / skill).glob("*") if p.is_dir())
        if not cases:
            continue
        lines += [f"---", "", f"## {skill} ({len(cases)} cases)", ""]
        skill_checks = 0
        for case in cases:
            pm = case / "prompt.md"
            graders = sorted((case / "graders").glob("*.md"))
            if not pm.is_file() or not graders:
                raise SystemExit(f"error: {case} needs prompt.md and graders/")
            fields, prompt = front(pm.read_text(encoding="utf-8"))
            tag = re.search(r"\[(\w+)", fields.get("tags", "[?")).group(1)
            desc = json.loads(fields["description"]) if fields.get("description", "").startswith('"') else fields.get("description", "")
            files = sorted(p.name for p in (case / "files").glob("**/*") if p.is_file()) if (case / "files").is_dir() else []
            lines += [f"### {case.name} · *{tag}*", "", desc, ""]
            lines += [f"**Attach:** " + (", ".join(f"`{f}`" for f in files) + f" (from `evals/{skill}/{case.name}/files/`)" if files else "nothing"), ""]
            lines += ["**Prompt to paste:**", "", "```", prompt, "```", ""]
            lines += ["| # | Check | Kind | Skill on | Skill off |", "|---|---|---|---|---|"]
            for i, g in enumerate(graders, 1):
                kind, text = check_text(*front(g.read_text(encoding="utf-8")), skill)
                off = "n/a" if kind == "skill-on only" else "☐"
                lines.append(f"| {i} | {text} | {kind} | ☐ | {off} |")
                skill_checks += 1
            lines.append("")
        totals.append((skill, len(cases), skill_checks))
    lines += ["---", "", "## Totals", "", f"Model: ________  Date: ________  Runs per case: ________", "",
              "| Skill | Cases | Checks | Passed, skill on | Passed, skill off (excluding skill-on only) |", "|---|---|---|---|---|"]
    lines += [f"| {s} | {c} | {n} | ___ of {n} | ___ of ___ |" for s, c, n in totals]
    lines += [f"| **All** | **{sum(c for _, c, _ in totals)}** | **{sum(n for *_, n in totals)}** | ___ | ___ |", ""]
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the manual eval run sheet.",
                                 epilog="Exit codes: 0 ok; 1 --check found it out of date; 2 bad input.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    try:
        text = build()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        print("Run sheet is current." if current == text else "Run sheet is out of date: re-run without --check.")
        return 0 if current == text else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
