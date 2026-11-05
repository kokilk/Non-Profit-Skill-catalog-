#!/usr/bin/env python3
"""board-minutes-tracker: lint draft minutes and keep the action tracker. Standard library only (3.9+).

Subcommands
  lint        Check draft minutes (in the form of assets/minutes-template.md): quorum, call to
              order and adjournment times, every motion's mover, seconder and outcome, vote tallies
              that add up to the members present, conflict-of-interest declarations for recusals,
              executive session with no discussion text, unresolved [CONFIRM] markers, DRAFT banner.
  init        Create the action tracker for a body (board or committee) with its member list.
  add         Add an action item. The owner must be a named person on the member list (not "the
              board"); the due date must be absolute (YYYY-MM-DD) or computed from a confirmed
              anchor date with --due-in-days N --anchor YYYY-MM-DD.
  list        Open actions; --owner NAME, --overdue, --all (include closed).
  close       Close an action, with an optional note.
  digest      Open actions grouped by owner, overdue first: the basis for reminder drafts.
  export-csv  Write all actions as CSV.

Exit codes
  0  lint: no errors (warnings may be listed) / tracker command done / nothing overdue
  1  lint: errors found / list or digest: something is overdue
  2  bad input: missing file, bad date, owner not on the member list, tracker changed while read

Examples
  python3 minutes.py lint minutes-2026-10-14.md
  python3 minutes.py init action-tracker-board.json --body "Board of Directors" --members "Ana Ruiz, Ben Okoro"
  python3 minutes.py add action-tracker-board.json --text "Send the audit RFP" --owner "Ana Ruiz" --due 2026-11-15 --meeting 2026-10-14
  python3 minutes.py add action-tracker-board.json --text "Draft budget" --owner "Ben Okoro" --due-in-days 14 --anchor 2026-10-14
  python3 minutes.py digest action-tracker-board.json --today 2026-11-20
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path

VERSION = "0.1.0"
OK, FINDINGS, BAD_INPUT = 0, 1, 2
GROUP_OWNERS = {"the board", "board", "committee", "the committee", "everyone", "all", "staff", "tbd", "team"}
EXEC_OK = re.compile(r"^\s*[-*]?\s*(?:entered|left|returned|resumed|topic|members present)\b", re.I)


class InputError(Exception):
    """Bad input: stderr, exit 2."""


def parse_date(value: str, label: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InputError(f"{label} must be an absolute date YYYY-MM-DD, got {value!r}. For a relative date "
                         "('by next meeting', 'in two weeks'), confirm the anchor date with the user and use "
                         "--due-in-days N --anchor YYYY-MM-DD.")


# ------------------------------------------------------------------ lint
def field(text: str, name: str) -> str | None:
    m = re.search(rf"^[ \t]*[-*]?[ \t]*{name}[ \t]*:[ \t]*(.*)$", text, re.I | re.M)  # stay on one line
    return m.group(1).strip() if m else None


def section(text: str, title: str) -> str | None:
    m = re.search(rf"^##\s+{title}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.I | re.M | re.S)
    return m.group(1) if m else None


def blank(value: str | None) -> bool:
    return value is None or not value.strip() or value.strip().startswith("[CONFIRM") or value.strip() in ("-", "?")


def present_count(text: str) -> int | None:
    present = field(text, "Present")
    if blank(present):
        return None
    m = re.search(r"\((\d+)\)\s*$", present)
    return int(m.group(1)) if m else len([p for p in present.split(",") if p.strip()])


def lint(text: str) -> dict:
    errors, warnings = [], []
    approved = field(text, "Approved")
    is_approved = bool(approved and re.search(r"\d{4}-\d{2}-\d{2}", approved))
    has_banner = bool(re.search(r"^\**\s*DRAFT", text, re.M))
    unresolved = len(re.findall(r"\[CONFIRM:", text))
    if not is_approved and not has_banner:
        errors.append("No DRAFT banner: minutes must say 'DRAFT: not approved' until the board approves them")
    if is_approved and unresolved:
        errors.append(f"Marked approved but {unresolved} [CONFIRM] item(s) are unresolved")
    if unresolved:
        warnings.append(f"{unresolved} unresolved [CONFIRM] item(s): settle them before approval")
    for name, label in (("Quorum", "quorum"), ("Called to order", "call-to-order time"), ("Adjourned", "adjournment time")):
        if blank(field(text, name)):
            errors.append(f"Missing {label} ('{name}:' line)")
    present = present_count(text)
    if present is None:
        errors.append("Missing attendance ('Present:' line with names)")
    any_recusal = False
    for m in re.finditer(r"^###\s+Motion\b([^\n]*)\n(.*?)(?=^#{2,3}\s|\Z)", text, re.M | re.S):
        title, body = m.group(1).strip(" :") or "(untitled)", m.group(2)
        for name in ("Moved by", "Seconded by", "Outcome"):
            value = field(body, name)
            if value is None or not value.strip():
                errors.append(f"Motion {title}: missing '{name}'")
            elif value.startswith("[CONFIRM"):
                warnings.append(f"Motion {title}: '{name}' still to confirm")
        vote = field(body, "Vote")
        if vote and not vote.startswith("[CONFIRM"):
            nums = {k: int(v) for v, k in re.findall(r"(\d+)\s*(yes|no|abstain\w*|recus\w*)", vote, re.I)}
            nums = {k.lower()[:5]: v for k, v in nums.items()}
            if nums.get("recus"):
                any_recusal = True
            total = sum(nums.values())
            if nums and present is not None and total != present:
                parts = " + ".join(f"{v} {k}" for k, v in nums.items())
                errors.append(f"Motion {title}: vote {parts} = {total}, but {present} present. Record abstentions, "
                              "recusals or members who left, or [CONFIRM] the tally")
    coi = section(text, "Conflicts of interest")
    if any_recusal and (coi is None or not re.search(r"\w", re.sub(r"(?i)none( declared)?\.?", "", coi))):
        errors.append("A member recused but no conflict-of-interest declaration is recorded")
    execs = section(text, "Executive session")
    if execs:
        talk = [ln.strip() for ln in execs.splitlines()
                if ln.strip() and not EXEC_OK.match(ln) and not ln.strip().lower().startswith(("none", "no executive"))]
        if talk:
            errors.append(f"Executive session has {len(talk)} line(s) of discussion: record only times and the "
                          "topic category (e.g. 'Topic: personnel')")
    return {"errors": errors, "warnings": warnings, "unresolved_confirm": unresolved,
            "approved": is_approved, "passed": not errors}


# ------------------------------------------------------------------ tracker
class Tracker:
    def __init__(self, path: str, must_exist: bool = True):
        self.path = Path(path)
        if not self.path.is_file():
            if must_exist:
                raise InputError(f"tracker not found: {path} (create it with init)")
            self.raw, self.data = None, None
            return
        self.raw = self.path.read_bytes()
        try:
            self.data = json.loads(self.raw)
        except json.JSONDecodeError as exc:
            raise InputError(f"{path} is not valid JSON: {exc}")

    def save(self, data: dict) -> None:
        now = self.path.read_bytes() if self.path.is_file() else None
        if (now is None) != (self.raw is None) or (now is not None and
                                                   hashlib.sha256(now).digest() != hashlib.sha256(self.raw).digest()):
            raise InputError(f"{self.path} changed since it was read. Nothing written; re-run.")
        body = dict(data, last_updated=dt.date.today().isoformat())
        self.path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def logged(data: dict, summary: str) -> list:
    old = list(data.get("change_log") or [])
    return old + [{"id": f"chg-{len(old) + 1:03d}", "date": dt.date.today().isoformat(), "summary": summary}]


def resolve_owner(data: dict, owner: str) -> str:
    if owner.strip().lower() in GROUP_OWNERS:
        raise InputError(f"owner {owner!r} is a group: ask which person will do it")
    members = {m.lower(): m for m in data.get("members", [])}
    if owner.strip().lower() not in members:
        raise InputError(f"owner {owner!r} is not on the member list ({', '.join(data.get('members', []))}). "
                         "Ask for a named person, or add them with init --members if they belong")
    return members[owner.strip().lower()]


def open_actions(data: dict, today: dt.date, owner: str | None = None, overdue_only: bool = False,
                 include_closed: bool = False) -> list:
    rows = []
    for a in data.get("actions", []):
        if a["status"] == "closed" and not include_closed:
            continue
        if owner and a["owner"].lower() != owner.lower():
            continue
        days = (dt.date.fromisoformat(a["due"]) - today).days
        late = a["status"] == "open" and days < 0
        if overdue_only and not late:
            continue
        rows.append(dict(a, days_left=days, overdue=late))
    return sorted(rows, key=lambda r: (not r["overdue"], r["due"], r["id"]))


def cmd_init(args) -> tuple:
    t = Tracker(args.tracker, must_exist=False)
    if t.data is not None:
        raise InputError(f"{args.tracker} already exists")
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    if not members:
        raise InputError("--members needs at least one name")
    data = {"schema_version": "1.0", "created_with": f"board-minutes-tracker {VERSION}", "last_updated": "",
            "org": {"name": args.org or "", "slug": ""}, "body": args.body, "members": members,
            "actions": [], "progress": {}, "change_log": []}
    data["change_log"] = logged(data, f"Tracker created for {args.body} with {len(members)} members")
    t.save(data)
    return {"tracker": args.tracker, "members": members}, f"Created {args.tracker} for {args.body} ({len(members)} members)."


def cmd_add(args) -> tuple:
    t = Tracker(args.tracker)
    data = t.data
    if not args.text.strip():
        raise InputError("--text is empty")
    owner = resolve_owner(data, args.owner)
    if args.due and args.due_in_days is not None:
        raise InputError("use either --due or --due-in-days with --anchor, not both")
    if args.due:
        due = parse_date(args.due, "--due")
    elif args.due_in_days is not None and args.anchor:
        due = parse_date(args.anchor, "--anchor") + dt.timedelta(days=args.due_in_days)
    else:
        raise InputError("a due date is required: --due YYYY-MM-DD, or --due-in-days N with a confirmed --anchor date")
    action = {"id": f"A-{len(data.get('actions', [])) + 1:03d}", "text": args.text.strip(), "owner": owner,
              "due": due.isoformat(), "meeting": args.meeting or "", "status": "open", "closed_on": None, "notes": []}
    new = dict(data, actions=list(data.get("actions", [])) + [action])
    new["change_log"] = logged(data, f"Added {action['id']} for {owner}, due {action['due']}")
    t.save(new)
    return action, f"Added {action['id']}: {action['text']} (owner {owner}, due {action['due']})."


def cmd_close(args) -> tuple:
    t = Tracker(args.tracker)
    actions = list(t.data.get("actions", []))
    idx = next((i for i, a in enumerate(actions) if a["id"] == args.action_id), None)
    if idx is None:
        raise InputError(f"no action {args.action_id!r}")
    if actions[idx]["status"] == "closed":
        raise InputError(f"{args.action_id} is already closed")
    today = parse_date(args.today, "--today") if args.today else dt.date.today()
    notes = list(actions[idx].get("notes") or []) + ([{"date": today.isoformat(), "text": args.note}] if args.note else [])
    actions[idx] = dict(actions[idx], status="closed", closed_on=today.isoformat(), notes=notes)
    new = dict(t.data, actions=actions)
    new["change_log"] = logged(t.data, f"Closed {args.action_id}")
    t.save(new)
    return actions[idx], f"Closed {args.action_id}."


def line(a: dict) -> str:
    when = f"{-a['days_left']} days overdue" if a["overdue"] else f"due {a['due']} ({a['days_left']} days)"
    state = "closed" if a["status"] == "closed" else when
    return f"- {a['id']} {a['text']} | {a['owner']} | {state}"


def cmd_list(args, today: dt.date) -> tuple:
    rows = open_actions(Tracker(args.tracker).data, today, args.owner, args.overdue, args.all)
    text = [f"{len(rows)} action(s)"] + [line(r) for r in rows]
    return rows, "\n".join(text), any(r["overdue"] for r in rows)


def cmd_digest(args, today: dt.date) -> tuple:
    rows = open_actions(Tracker(args.tracker).data, today)
    owners: dict = {}
    for r in rows:
        owners.setdefault(r["owner"], []).append(r)
    text = [f"Open actions by owner ({today.isoformat()}). Reminder drafts are never sent without the user's OK."]
    for owner, items in sorted(owners.items()):
        text.append(f"\n{owner}:")
        text += [line(i) for i in items]
    if not rows:
        text.append("Nothing open.")
    return owners, "\n".join(text), any(r["overdue"] for r in rows)


def cmd_export(args, today: dt.date) -> tuple:
    rows = open_actions(Tracker(args.tracker).data, today, include_closed=True)
    out = Path(args.out)
    if out.resolve() == Path(args.tracker).resolve():
        raise InputError("--out must not be the tracker file")
    fields = ["id", "text", "owner", "due", "status", "closed_on", "meeting", "overdue"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue(), encoding="utf-8")
    return {"out": str(out), "rows": len(rows)}, f"Wrote {len(rows)} action(s) to {out}."


# ------------------------------------------------------------------ cli
def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint draft minutes and keep the action tracker.",
                                 epilog="Exit codes: 0 ok; 1 lint errors or overdue actions; 2 bad input.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lint")
    p.add_argument("minutes")
    p = sub.add_parser("init")
    p.add_argument("tracker")
    p.add_argument("--body", required=True)
    p.add_argument("--members", required=True, help="comma-separated names")
    p.add_argument("--org")
    p = sub.add_parser("add")
    p.add_argument("tracker")
    p.add_argument("--text", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--due")
    p.add_argument("--due-in-days", type=int)
    p.add_argument("--anchor", help="confirmed anchor date for --due-in-days")
    p.add_argument("--meeting", help="meeting date the action came from")
    p = sub.add_parser("close")
    p.add_argument("tracker")
    p.add_argument("action_id")
    p.add_argument("--note")
    for name in ("list", "digest"):
        p = sub.add_parser(name)
        p.add_argument("tracker")
        if name == "list":
            p.add_argument("--owner")
            p.add_argument("--overdue", action="store_true")
            p.add_argument("--all", action="store_true", help="include closed actions")
    p = sub.add_parser("export-csv")
    p.add_argument("tracker")
    p.add_argument("--out", required=True)
    for p in sub.choices.values():
        p.add_argument("--format", choices=["md", "json"], default="md")
        if not any(a.dest == "today" for a in p._actions):
            p.add_argument("--today", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args(argv)
    try:
        today = parse_date(args.today, "--today") if args.today else dt.date.today()
        late = False
        if args.cmd == "lint":
            path = Path(args.minutes)
            if not path.is_file():
                raise InputError(f"file not found: {args.minutes}")
            res = lint(path.read_text(encoding="utf-8"))
            text = [f"minutes lint: {'PASS' if res['passed'] else 'FAIL'}"]
            text += [f"  error: {e}" for e in res["errors"]] + [f"  warning: {w}" for w in res["warnings"]]
            payload, msg, late = res, "\n".join(text), not res["passed"]
        elif args.cmd in ("list", "digest"):
            payload, msg, late = (cmd_list if args.cmd == "list" else cmd_digest)(args, today)
        elif args.cmd == "export-csv":
            payload, msg = cmd_export(args, today)
        else:
            payload, msg = {"init": cmd_init, "add": cmd_add, "close": cmd_close}[args.cmd](args)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT
    print(json.dumps(payload, indent=2, default=str) if args.format == "json" else msg)
    return FINDINGS if late else OK


if __name__ == "__main__":
    sys.exit(main())
