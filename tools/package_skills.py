#!/usr/bin/env python3
"""Package every skill in skills/ into dist/<name>.skill and dist/<name>.zip (identical). Stdlib only (3.9+).

Upload the .zip in Claude (Customize > Skills > + > Create skill > Upload a skill).

A .skill file is a zip with the skill folder at its root, the same format skill-creator's
package_skill.py writes. Excluded, as there: __pycache__/ and node_modules/ anywhere, an evals/
folder at the skill root, *.pyc and .DS_Store. Before zipping, each skill gets the same frontmatter
checks as skill-creator's quick_validate.py (which needs PyYAML, so isn't used here): allowed keys
only, kebab-case name of 64 characters or fewer, description of 1,024 characters or fewer with no
angle brackets, compatibility of 500 characters or fewer, and exactly one SKILL.md.

Usage
  python3 tools/package_skills.py              # all skills -> dist/
  python3 tools/package_skills.py --out /tmp/x pii-guard

Exit codes
  0  every requested skill packaged
  1  a skill failed validation (nothing written for it)
  2  bad input: unknown skill name
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
ROOT_EXCLUDE_DIRS = {"evals"}
EXCLUDE_FILES = {".DS_Store", ".gitkeep"}
EXCLUDE_GLOBS = {"*.pyc"}


def excluded(rel: Path) -> bool:
    parts = rel.parts
    return (any(p in EXCLUDE_DIRS for p in parts)
            or (len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS)
            or rel.name in EXCLUDE_FILES
            or any(fnmatch.fnmatch(rel.name, g) for g in EXCLUDE_GLOBS))


def validate(skill: Path) -> list:
    problems = []
    md = skill / "SKILL.md"
    if not md.is_file():
        return ["SKILL.md not found"]
    m = re.match(r"^---\n(.*?)\n---", md.read_text(encoding="utf-8"), re.S)
    if not m:
        return ["no YAML frontmatter"]
    fields = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    extra = set(fields) - ALLOWED
    if extra:
        problems.append(f"unexpected frontmatter key(s): {', '.join(sorted(extra))}")
    name, desc = fields.get("name", ""), fields.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        problems.append(f"bad name {name!r}")
    if not desc or len(desc) > 1024 or re.search(r"[<>]", desc):
        problems.append("description missing, over 1024 characters, or has angle brackets")
    if len(fields.get("compatibility", "")) > 500:
        problems.append("compatibility over 500 characters")
    mds = [p for p in skill.rglob("SKILL.md") if not excluded(p.relative_to(skill.parent))]
    if len(mds) != 1:
        problems.append(f"{len(mds)} SKILL.md files; a skill needs exactly one")
    return problems


def package(skill: Path, out: Path) -> tuple:
    problems = validate(skill)
    if problems:
        return None, problems
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{skill.name}.skill"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill.rglob("*")):
            rel = path.relative_to(skill.parent)
            if path.is_file() and not excluded(rel):
                zf.write(path, rel.as_posix())
    # Claude.ai's upload asks for a .zip; same bytes, second name.
    (out / f"{skill.name}.zip").write_bytes(target.read_bytes())
    return target, []


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Package skills into .skill files.",
                                 epilog="Exit codes: 0 all packaged; 1 validation failed; 2 unknown skill.")
    ap.add_argument("skills", nargs="*", help="skill names (default: all)")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)
    available = {p.parent.name: p.parent for p in (ROOT / "skills").glob("*/SKILL.md")}
    names = args.skills or sorted(available)
    unknown = [n for n in names if n not in available]
    if unknown:
        print(f"error: unknown skill(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    failed = False
    for name in names:
        target, problems = package(available[name], Path(args.out))
        if problems:
            failed = True
            print(f"FAILED {name}: " + "; ".join(problems))
        else:
            with zipfile.ZipFile(target) as zf:
                count = len(zf.namelist())
            print(f"packaged {name}: {target} ({count} files, {target.stat().st_size // 1024} KB)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
