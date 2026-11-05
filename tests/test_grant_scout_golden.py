"""Golden set for grant-scout (spec §6.12), synthetic version (owner decision 2026-11-05).

12 invented grant programs x 3 invented org profiles, answers keyed by hand BEFORE rank.py
was run. Scores: eligibility bucket, ranked order and score, deadline, and source present.
Never checked against any real funder page.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "samples" / "grants"
sys.path.insert(0, str(ROOT / "skills" / "grant-scout" / "scripts"))
import rank  # noqa: E402
import validate  # noqa: E402

KEY = json.loads((GOLD / "golden-key.json").read_text(encoding="utf-8"))
GRANTS = json.loads((GOLD / "golden-grants.json").read_text(encoding="utf-8"))["grants"]
PROFILES = json.loads((GOLD / "golden-profiles.json").read_text(encoding="utf-8"))
BUCKETS = ("needs_checking", "not_eligible", "closed", "unverified")


def run_golden(profile_name):
    state = {"profile": {"facts": PROFILES[profile_name]["facts"]}, "grants": GRANTS}
    return rank.rank(state, validate.today_from(KEY["today"]), rank.load_weights(None))


def misses():
    """Every disagreement between rank.py and the hand key, as readable lines."""
    found = []
    for name in ("riverbend", "eastgate", "coastline"):
        result, want = run_golden(name), KEY[name]
        got_ranked = [[e["id"], e["score"]] for e in result["ranked"]]
        if got_ranked != want["ranked"]:
            found.append(f"{name}: ranked {got_ranked} != key {want['ranked']}")
        for bucket in BUCKETS:
            got = sorted(e["id"] for e in result[bucket])
            if got != sorted(want[bucket]):
                found.append(f"{name}: {bucket} {got} != key {sorted(want[bucket])}")
        for e in result["ranked"] + result["needs_checking"]:
            if e["deadline"] != KEY["deadlines"].get(e["id"]):
                found.append(f"{name}: {e['id']} deadline {e['deadline']} != key {KEY['deadlines'].get(e['id'])}")
            if not str(e["source_url"]).startswith("https://"):
                found.append(f"{name}: {e['id']} shown without a source URL")
    return found


class GoldenSet(unittest.TestCase):
    def test_golden_set_matches_the_hand_keyed_answers(self):
        problems = misses()
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_golden_set_covers_every_bucket(self):
        seen = set()
        for name in ("riverbend", "eastgate", "coastline"):
            result = run_golden(name)
            seen |= {b for b in ("ranked",) + BUCKETS if result[b]}
        self.assertEqual(seen, {"ranked", *BUCKETS})

    def test_golden_data_is_synthetic(self):
        for grant in GRANTS:
            self.assertTrue(grant["funder"].endswith("(synthetic)"), grant["id"])
            if grant["source_url"]:
                self.assertIn(".example.org/", grant["source_url"])
        for profile in PROFILES.values():
            self.assertTrue(profile["name"].endswith("(synthetic)"))


if __name__ == "__main__":
    for line in misses() or ["no misses"]:
        print(line)
