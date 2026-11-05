#!/usr/bin/env python3
"""grant-scout pipeline: shortlist, deadlines and working-back schedules. Standard library only (3.9+).

Dates are computed here, never by hand. The working-back schedule counts back from the
funder's deadline:  submit_by = deadline - buffer_days;  review_start = submit_by - review_days;
draft_start = review_start - drafting_days. The day counts come from the org (pipeline.settings
in the state file, or flags on `add`), and every output shows which values were used.

Subcommands
  add          Put a verified, not-closed grant on the shortlist and compute its schedule
  update       Move a grant to a new stage, add a note or a follow-up date (logged)
  status       Days left, tier (passed / due soon / comfortable) and schedule for every entry
  export-csv   Write the shortlist as CSV for a tracker or spreadsheet

Stages: shortlisted, loi_drafting, loi_review, submitted_by_org, awarded, declined, withdrawn.
The org submits; this script only records that it happened.

Exit codes
  0  done; status shows nothing due soon, passed or infeasible
  1  status shows something the user must act on (due soon, passed, or a schedule that
     would have had to start in the past)
  2  bad input: missing file, unknown grant, unverified or closed grant, bad date or stage,
     state file changed while it was being read

Examples
  python3 pipeline.py add grant-pipeline-riverbend.json G-03 --today 2026-11-05
  python3 pipeline.py add grant-pipeline-riverbend.json G-05 --drafting-days 15
  python3 pipeline.py update grant-pipeline-riverbend.json G-03 --stage loi_drafting --follow-up 2026-11-20
  python3 pipeline.py status grant-pipeline-riverbend.json --today 2026-11-05
  python3 pipeline.py export-csv grant-pipeline-riverbend.json --out tracker.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import InputError, StateFile, check_record, grants_of, parse_date, today_from  # noqa: E402

OK, FINDINGS, BAD_INPUT = 0, 1, 2
STAGES = ("shortlisted", "loi_drafting", "loi_review", "submitted_by_org", "awarded", "declined", "withdrawn")
OPEN_STAGES = {"shortlisted", "loi_drafting", "loi_review"}
DEFAULT_SETTINGS = {"buffer_days": 2, "review_days": 5, "drafting_days": 10, "soon_days": 14}


def settings_of(state: dict) -> dict:
    saved = (state.get("pipeline") or {}).get("settings") or {}
    return {k: int(saved.get(k, v)) for k, v in DEFAULT_SETTINGS.items()}


def schedule(deadline, s: dict, today: dt.date) -> dict | None:
    if deadline is None:
        return None
    submit_by = deadline - dt.timedelta(days=s["buffer_days"])
    review_start = submit_by - dt.timedelta(days=s["review_days"])
    draft_start = review_start - dt.timedelta(days=s["drafting_days"])
    return {"draft_start": draft_start.isoformat(), "review_start": review_start.isoformat(),
            "submit_by": submit_by.isoformat(), "deadline": deadline.isoformat(),
            "feasible": draft_start >= today,
            "used": {k: s[k] for k in ("drafting_days", "review_days", "buffer_days")}}


def find_grant(state: dict, grant_id: str) -> dict:
    for g in grants_of(state):
        if g.get("id") == grant_id:
            return g
    raise InputError(f"no grant with id {grant_id!r} in the state file")


def entries_of(state: dict) -> list:
    return list((state.get("pipeline") or {}).get("entries") or [])


def log(state: dict, today: dt.date, summary: str, details: dict) -> list:
    old = list(state.get("change_log") or [])
    return old + [{"id": f"chg-{len(old) + 1:03d}", "date": today.isoformat(), "type": "pipeline",
                   "summary": summary, "details": details}]


def with_pipeline(state: dict, entries: list, settings: dict) -> dict:
    return dict(state, pipeline=dict(state.get("pipeline") or {}, settings=settings, entries=entries))


# ------------------------------------------------------------------ add / update
def cmd_add(args, sf: StateFile, today: dt.date) -> int:
    state = sf.data
    grant = find_grant(state, args.grant_id)
    check = check_record(grant, today, 10 ** 6)
    if not check["verified"]:
        raise InputError(f"{args.grant_id} is an unverified lead (missing {'; '.join(check['missing'])}). "
                         "Verify it on the funder's page before shortlisting.")
    deadline = parse_date(grant.get("deadline"))
    if grant.get("status") == "closed" or (deadline is not None and deadline < today):
        raise InputError(f"{args.grant_id} is closed or its deadline has passed")
    entries = entries_of(state)
    if any(e["grant_id"] == args.grant_id for e in entries):
        raise InputError(f"{args.grant_id} is already in the pipeline; use update")
    settings = settings_of(state)
    overrides = {k: getattr(args, k) for k in ("drafting_days", "review_days", "buffer_days")
                 if getattr(args, k) is not None}
    plan = schedule(deadline, dict(settings, **overrides), today)
    entry = {"grant_id": args.grant_id, "stage": "shortlisted", "added_on": today.isoformat(),
             "schedule": plan, "follow_up_on": None, "notes": []}
    new_state = with_pipeline(state, entries + [entry], settings)
    new_state["change_log"] = log(state, today, f"Shortlisted {args.grant_id}", {"schedule": plan})
    sf.save(new_state)
    msg = [f"Shortlisted {args.grant_id} ({grant.get('funder')} / {grant.get('program')})."]
    msg.append(render_schedule(plan) if plan else "Rolling deadline: no schedule; set a follow-up date.")
    emit(args.format, entry, "\n".join(msg))
    return OK


def cmd_update(args, sf: StateFile, today: dt.date) -> int:
    state = sf.data
    entries = entries_of(state)
    idx = next((i for i, e in enumerate(entries) if e["grant_id"] == args.grant_id), None)
    if idx is None:
        raise InputError(f"{args.grant_id} is not in the pipeline; use add first")
    if not (args.stage or args.note or args.follow_up):
        raise InputError("nothing to update: pass --stage, --note or --follow-up")
    follow = None
    if args.follow_up:
        follow = parse_date(args.follow_up)
        if follow is None:
            raise InputError(f"--follow-up must be YYYY-MM-DD, got {args.follow_up!r}")
    old = entries[idx]
    new = dict(old, stage=args.stage or old["stage"],
               follow_up_on=follow.isoformat() if follow else old.get("follow_up_on"),
               notes=list(old.get("notes") or []) + ([{"date": today.isoformat(), "text": args.note}]
                                                     if args.note else []))
    changes = {k: new[k] for k in ("stage", "follow_up_on") if new[k] != old.get(k)}
    new_state = with_pipeline(state, entries[:idx] + [new] + entries[idx + 1:], settings_of(state))
    new_state["change_log"] = log(state, today, f"Updated {args.grant_id}", dict(changes, note=args.note))
    sf.save(new_state)
    emit(args.format, new, f"Updated {args.grant_id}: " + (", ".join(f"{k} -> {v}" for k, v in changes.items())
                                                            or "note added"))
    return OK


# ------------------------------------------------------------------ status / export
def status_rows(state: dict, today: dt.date) -> list:
    settings = settings_of(state)
    rows = []
    for e in entries_of(state):
        grant = find_grant(state, e["grant_id"])
        deadline = parse_date(grant.get("deadline"))
        days_left = (deadline - today).days if deadline else None
        if deadline is None:
            tier = "rolling"
        elif days_left < 0:
            tier = "passed"
        elif days_left <= settings["soon_days"]:
            tier = "due soon"
        else:
            tier = "comfortable"
        plan = e.get("schedule")
        if plan and deadline:
            used = dict(settings, **plan.get("used", {}))
            plan = schedule(deadline, used, today)
        rows.append({"grant_id": e["grant_id"], "funder": grant.get("funder"), "program": grant.get("program"),
                     "stage": e["stage"], "deadline": grant.get("deadline"), "days_left": days_left,
                     "tier": tier, "schedule": plan, "follow_up_on": e.get("follow_up_on"),
                     "source_url": grant.get("source_url"), "checked_on": grant.get("checked_on")})
    return rows


def needs_action(row: dict) -> bool:
    if row["stage"] not in OPEN_STAGES:
        return False
    late_plan = row["schedule"] is not None and not row["schedule"]["feasible"]
    return row["tier"] in ("passed", "due soon") or late_plan


def render_schedule(plan: dict) -> str:
    used = plan["used"]
    line = (f"Schedule: start drafting {plan['draft_start']} -> internal review {plan['review_start']} -> "
            f"submit by {plan['submit_by']} (deadline {plan['deadline']}). Using {used['drafting_days']} "
            f"drafting, {used['review_days']} review and {used['buffer_days']} buffer days.")
    if not plan["feasible"]:
        line += " NOT FEASIBLE: drafting would have had to start already. Shorten the plan or skip this round."
    return line


def cmd_status(args, sf: StateFile, today: dt.date) -> int:
    rows = status_rows(sf.data, today)
    lines = [f"grant-scout pipeline status ({today.isoformat()}): {len(rows)} grant(s)"]
    for r in rows:
        left = "rolling" if r["days_left"] is None else f"{r['days_left']} days left"
        lines.append(f"- {r['grant_id']} {r['funder']} / {r['program']}: {r['stage']}; {left} ({r['tier']})"
                     + (f"; follow up {r['follow_up_on']}" if r["follow_up_on"] else ""))
        if r["schedule"] and r["stage"] in OPEN_STAGES:
            lines.append("    " + render_schedule(r["schedule"]))
    if not rows:
        lines.append("Nothing shortlisted yet.")
    emit(args.format, {"today": today.isoformat(), "entries": rows}, "\n".join(lines))
    return FINDINGS if any(needs_action(r) for r in rows) else OK


def cmd_export(args, sf: StateFile, today: dt.date) -> int:
    out = Path(args.out)
    if out.resolve() == sf.path.resolve():
        raise InputError("--out must not be the state file")
    rows = status_rows(sf.data, today)
    fields = ["grant_id", "funder", "program", "stage", "deadline", "days_left", "tier", "draft_start",
              "review_start", "submit_by", "follow_up_on", "source_url", "checked_on"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        plan = r["schedule"] or {}
        writer.writerow({**{k: r.get(k) for k in fields}, **{k: plan.get(k) for k in
                                                              ("draft_start", "review_start", "submit_by")}})
    out.write_text(buf.getvalue(), encoding="utf-8")
    emit(args.format, {"out": str(out), "rows": len(rows)}, f"Wrote {len(rows)} row(s) to {out}")
    return OK


# ------------------------------------------------------------------ cli
def emit(fmt: str, payload, text: str) -> None:
    print(json.dumps(payload, indent=2) if fmt == "json" else text)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shortlist, deadlines and working-back schedules.",
                                     epilog="Exit codes: 0 ok; 1 something due soon, passed or infeasible; "
                                            "2 bad input.")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("state", help="grant-pipeline-{slug}.json")
        p.add_argument("--today", help="date to count from (default: today)")
        p.add_argument("--format", choices=["md", "json"], default="md")

    p = sub.add_parser("add", help="shortlist a verified grant")
    common(p)
    p.add_argument("grant_id")
    for flag in ("drafting-days", "review-days", "buffer-days"):
        p.add_argument(f"--{flag}", type=int, help="override the org's setting for this grant")
    p.set_defaults(func=cmd_add)
    p = sub.add_parser("update", help="change stage, add a note or follow-up date")
    common(p)
    p.add_argument("grant_id")
    p.add_argument("--stage", choices=STAGES)
    p.add_argument("--note")
    p.add_argument("--follow-up", help="YYYY-MM-DD")
    p.set_defaults(func=cmd_update)
    p = sub.add_parser("status", help="days left, tiers and schedules")
    common(p)
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("export-csv", help="write the shortlist as CSV")
    common(p)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    try:
        if any((getattr(args, k, None) or 0) < 0 for k in ("drafting_days", "review_days", "buffer_days")):
            raise InputError("day counts must be zero or more")
        return args.func(args, StateFile(args.state), today_from(args.today))
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
