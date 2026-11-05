#!/usr/bin/env python3
"""grant-scout rank: sort grants into ranked / needs checking / not eligible / closed / unverified.
Standard library only (Python 3.9+).

Reads the state file (org profile facts + grant records). For every criterion the answer is
pass, fail or unknown, never a guess. "unknown" is a first-class result: it comes with the
exact question that would settle it.

Buckets, in this order of precedence
  unverified     the record fails validate.py (no source URL, date or deadline source): a lead only
  closed         status closed, or an open grant whose deadline has passed
  not_eligible   any hard gate fails (tax status, geography, budget limit, required audit ...)
  needs_checking any hard gate is unknown, the status is unknown, or a registration is pending
  ranked         all hard gates pass: scored on the soft components below

Soft score (weights in assets/rank-weights.json, shown in every output; never a bare number)
  issue_match           share of the grant's issue areas the org works in
  award_fit             1 if the org's ask range sits inside the award range, 0.5 if it overlaps, 0 if not
  preferences_met       share of the funder's stated preferences the org meets
  deadline_feasibility  1 if the days left cover the org's days needed, 0.5 if half, 0 if less; rolling = 1
Unknown components are left out of the score and listed, so the score says how much it rests on.

Profile facts look like {"id": "F-03", "field": "tax_status", "value": "501(c)(3)", "source": "..."}.
A criterion's machine check looks like {"field": "tax_status", "op": "in", "value": ["501(c)(3)"]}.
Ops: in, not_in, equals, is_true, is_false, lte, gte, overlaps.

Exit codes
  0  every grant was evaluated with no unknowns or unverified leads
  1  results include unverified leads or unknowns the user must see (the normal case)
  2  bad input: missing file, bad JSON, duplicate profile fields, unknown op, bad weights

Examples
  python3 rank.py grant-pipeline-riverbend.json --today 2026-11-05
  python3 rank.py grant-pipeline-riverbend.json --format json
  python3 rank.py grant-pipeline-riverbend.json --weights my-weights.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import InputError, StateFile, check_record, grants_of, parse_date, today_from  # noqa: E402

OK, FINDINGS, BAD_INPUT = 0, 1, 2
DEFAULT_WEIGHTS = Path(__file__).resolve().parents[1] / "assets" / "rank-weights.json"
OPS = {"in", "not_in", "equals", "is_true", "is_false", "lte", "gte", "overlaps"}
COMPONENTS = ("issue_match", "award_fit", "preferences_met", "deadline_feasibility")
UNKNOWN_VALUES = (None, "", "unknown", [])


# ------------------------------------------------------------------ profile
def profile_index(state: dict) -> dict:
    facts = (state.get("profile") or {}).get("facts")
    if not isinstance(facts, list):
        raise InputError('state file has no "profile.facts" list')
    index: dict = {}
    for fact in facts:
        field = fact.get("field")
        if field in index:
            raise InputError(f"two profile facts for {field!r}: {index[field]['id']} and "
                             f"{fact.get('id')}. Keep one; I won't guess which is current.")
        index[field] = fact
    return index


def fact_value(profile: dict, field: str):
    fact = profile.get(field)
    value = None if fact is None else fact.get("value")
    return None if value in UNKNOWN_VALUES else value


# ------------------------------------------------------------------ criteria
def apply_op(op: str, have, want) -> bool:
    if op == "in":
        return have in want
    if op == "not_in":
        return have not in want
    if op == "equals":
        return have == want
    if op == "is_true":
        return have is True
    if op == "is_false":
        return have is False
    if op == "lte":
        return float(have) <= float(want)
    if op == "gte":
        return float(have) >= float(want)
    have_list = have if isinstance(have, list) else [have]
    return bool({str(h).lower() for h in have_list} & {str(w).lower() for w in want})


def evaluate_criterion(crit: dict, profile: dict) -> dict:
    check = crit.get("check")
    base = {"text": crit.get("text", ""), "kind": crit.get("kind"),
            "source": crit.get("source_quote_location", "")}
    if not isinstance(check, dict):
        return dict(base, result="unknown", question=f'Does the org meet this: "{base["text"]}"?')
    op, field = check.get("op"), check.get("field")
    if op not in OPS:
        raise InputError(f"criterion {base['text']!r}: unknown op {op!r} (use one of {', '.join(sorted(OPS))})")
    have = fact_value(profile, field)
    if have is None:
        return dict(base, result="unknown", field=field,
                    question=f'Profile has no answer for "{field}". Needed for: "{base["text"]}"')
    try:
        passed = apply_op(op, have, check.get("value"))
    except (TypeError, ValueError):
        return dict(base, result="unknown", field=field,
                    question=f'Profile value for "{field}" can\'t be compared for: "{base["text"]}"')
    fact_id = profile[field].get("id")
    return dict(base, result="pass" if passed else "fail", field=field, fact_id=fact_id)


def requirement_checks(grant: dict, profile: dict, deadline) -> list:
    """Turn the record's "requires" block into hard-gate results."""
    req = grant.get("requires") or {}
    out = []
    if req.get("sam_uei"):
        status = fact_value(profile, "sam_uei_status")
        text = "Applicant must be registered in SAM.gov with a UEI"
        if status == "registered":
            out.append({"text": text, "kind": "hard", "result": "pass", "fact_id": profile["sam_uei_status"]["id"]})
        else:
            when = f" before {deadline.isoformat()}" if deadline else ""
            out.append({"text": text, "kind": "hard", "result": "unknown",
                        "question": f"SAM.gov registration is '{status or 'not stated'}'. Registration can take "
                                    f"weeks [VERIFY: current processing time on SAM.gov]. Can it be "
                                    f"completed{when}?"})
    for key, field, text in (("audit", "audited_financials", "Audited financial statements required"),
                             ("match_funds", "can_provide_match", "Matching funds required")):
        if req.get(key):
            have = fact_value(profile, field)
            result = "unknown" if have is None else ("pass" if have is True else "fail")
            item = {"text": text, "kind": "hard", "result": result}
            if result == "unknown":
                item["question"] = f'Profile has no answer for "{field}". Needed for: "{text}"'
            else:
                item["fact_id"] = profile[field]["id"]
            out.append(item)
    if req.get("prior_relationship"):
        prior = fact_value(profile, "prior_funders") or []
        funder = (grant.get("funder") or "").lower()
        hit = any(funder == str(p).lower() for p in prior)
        out.append({"text": "Funder only considers organizations it already knows (prior relationship)",
                    "kind": "hard", "result": "pass" if hit else "unknown",
                    **({} if hit else {"question": f"Has the org been funded by or invited by {grant.get('funder')}?"})})
    return out


# ------------------------------------------------------------------ scoring
def score_components(grant: dict, profile: dict, prefs: list, today: dt.date, deadline, weights: dict) -> dict:
    comps = {}
    org_areas, grant_areas = fact_value(profile, "issue_areas"), grant.get("issue_areas") or []
    if org_areas and grant_areas:
        org = {a.lower() for a in org_areas}
        comps["issue_match"] = round(sum(a.lower() in org for a in grant_areas) / len(grant_areas), 3)
    ask, award = fact_value(profile, "ask_amount"), grant.get("award_range") or {}
    if isinstance(ask, dict) and award.get("min") is not None and award.get("max") is not None:
        lo, hi, a_lo, a_hi = ask.get("min"), ask.get("max"), award["min"], award["max"]
        if lo is not None and hi is not None:
            comps["award_fit"] = 1.0 if a_lo <= lo and hi <= a_hi else (0.5 if lo <= a_hi and a_lo <= hi else 0.0)
    known_prefs = [p for p in prefs if p["result"] != "unknown"]
    if known_prefs:
        comps["preferences_met"] = round(sum(p["result"] == "pass" for p in known_prefs) / len(known_prefs), 3)
    if grant.get("status") == "rolling":
        comps["deadline_feasibility"] = 1.0
    elif deadline is not None:
        needed = fact_value(profile, "days_needed_per_application") or weights["default_days_needed"]
        left = (deadline - today).days
        comps["deadline_feasibility"] = 1.0 if left >= needed else (0.5 if left >= needed / 2 else 0.0)
    w = weights["weights"]
    used = [c for c in COMPONENTS if c in comps]
    total = sum(w[c] for c in used)
    score = round(100 * sum(w[c] * comps[c] for c in used) / total) if total else None
    return {"score": score, "components": comps, "unknown_components": [c for c in COMPONENTS if c not in comps]}


def load_weights(path: str | None) -> dict:
    p = Path(path) if path else DEFAULT_WEIGHTS
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        w = data["weights"]
        if set(w) != set(COMPONENTS) or any(not isinstance(v, (int, float)) or v < 0 for v in w.values()):
            raise ValueError
        int(data["default_days_needed"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise InputError(f"weights file must hold non-negative numbers for {', '.join(COMPONENTS)} "
                         f"and a default_days_needed: {p}")
    return data


# ------------------------------------------------------------------ ranking
def rank(state: dict, today: dt.date, weights: dict, max_age_days: int = 30) -> dict:
    profile = profile_index(state)
    buckets = {"ranked": [], "needs_checking": [], "not_eligible": [], "closed": [], "unverified": []}
    for grant in grants_of(state):
        head = {"id": grant.get("id"), "funder": grant.get("funder"), "program": grant.get("program"),
                "source_url": grant.get("source_url"), "checked_on": grant.get("checked_on")}
        validity = check_record(grant, today, max_age_days)
        if not validity["verified"]:
            buckets["unverified"].append(dict(head, missing=validity["missing"]))
            continue
        deadline = parse_date(grant.get("deadline"))
        if grant["status"] == "closed" or (grant["status"] == "open" and deadline < today):
            reason = "page says closed" if grant["status"] == "closed" else f"deadline {deadline} has passed"
            buckets["closed"].append(dict(head, reason=reason))
            continue
        crits = [evaluate_criterion(c, profile) for c in grant["eligibility_criteria"]]
        hard = [c for c in crits if c["kind"] == "hard"] + requirement_checks(grant, profile, deadline)
        prefs = [c for c in crits if c["kind"] == "preference"]
        entry = dict(head, deadline=grant.get("deadline"), status=grant["status"], hard_gates=hard,
                     preferences=prefs, warnings=validity["warnings"])
        if any(c["result"] == "fail" for c in hard):
            buckets["not_eligible"].append(entry)
            continue
        questions = [c["question"] for c in hard if c["result"] == "unknown"]
        if grant["status"] == "unknown":
            questions.insert(0, "Is the program accepting applications now? The page doesn't say.")
        entry.update(score_components(grant, profile, prefs, today, deadline, weights))
        if questions:
            buckets["needs_checking"].append(dict(entry, questions=questions))
        else:
            buckets["ranked"].append(entry)
    buckets["ranked"].sort(key=lambda e: (-(e["score"] or 0), e["id"] or ""))
    return {"today": today.isoformat(), "weights": weights["weights"],
            "default_days_needed": weights["default_days_needed"], **buckets}


def render(r: dict) -> str:
    w = ", ".join(f"{k} {v}" for k, v in r["weights"].items())
    lines = [f"grant-scout rank ({r['today']}). Weights: {w}."]
    if r["ranked"]:
        lines.append("\nRanked (all hard gates pass):")
        for e in r["ranked"]:
            comps = ", ".join(f"{k} {v}" for k, v in e["components"].items())
            gaps = f"; not scored: {', '.join(e['unknown_components'])}" if e["unknown_components"] else ""
            lines.append(f"- {e['id']} {e['funder']} / {e['program']}: score {e['score']} ({comps}{gaps}); "
                         f"deadline {e['deadline'] or e['status']}; source {e['source_url']} (checked {e['checked_on']})")
    if r["needs_checking"]:
        lines.append("\nNeeds checking (no hard gate fails, but some are unknown):")
        for e in r["needs_checking"]:
            lines.append(f"- {e['id']} {e['funder']} / {e['program']}")
            lines += [f"    ? {q}" for q in e["questions"]]
    if r["not_eligible"]:
        lines.append("\nNot eligible, because:")
        for e in r["not_eligible"]:
            fails = [c for c in e["hard_gates"] if c["result"] == "fail"]
            lines.append(f"- {e['id']} {e['funder']} / {e['program']}: "
                         + "; ".join(f"{c['text']} ({c.get('source') or 'requires block'})" for c in fails))
    if r["closed"]:
        lines.append("\nClosed:")
        lines += [f"- {e['id']} {e['funder']} / {e['program']}: {e['reason']}" for e in r["closed"]]
    if r["unverified"]:
        lines.append("\nUnverified leads (not ranked; never present as open or eligible):")
        lines += [f"- {e['id']} {e['funder']} / {e['program']}: missing {'; '.join(e['missing'])}"
                  for e in r["unverified"]]
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank grants against the org profile.",
                                     epilog="Exit codes: 0 no unknowns or unverified leads; 1 results "
                                            "include them; 2 bad input.")
    parser.add_argument("state", help="grant-pipeline-{slug}.json")
    parser.add_argument("--today", help="date to rank against (default: today)")
    parser.add_argument("--weights", help="weights JSON (default: assets/rank-weights.json)")
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args(argv)
    try:
        result = rank(StateFile(args.state).data, today_from(args.today), load_weights(args.weights),
                      args.max_age_days)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return BAD_INPUT
    print(json.dumps(result, indent=2) if args.format == "json" else render(result))
    return FINDINGS if result["needs_checking"] or result["unverified"] else OK


if __name__ == "__main__":
    sys.exit(main())
