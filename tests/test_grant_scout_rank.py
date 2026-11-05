"""Tests for skills/grant-scout/scripts/rank.py (bucket logic; the full matrix is in the golden test)."""

import sys
from pathlib import Path
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _grant_fixtures import TODAY, StateCase, golden_state, run
import rank
import validate


def ranked(state):
    return rank.rank(state, validate.today_from(TODAY), rank.load_weights(None))


def ids(result, bucket):
    return [e["id"] for e in result[bucket]]


class Criteria(unittest.TestCase):
    def test_missing_profile_fact_gives_unknown_with_a_question_not_a_guess(self):
        crit = {"text": "Must serve a rural area", "kind": "hard", "source_quote_location": "Eligibility",
                "check": {"field": "service_area_type", "op": "in", "value": ["rural"]}}
        r = rank.evaluate_criterion(crit, {})
        self.assertEqual(r["result"], "unknown")
        self.assertIn("service_area_type", r["question"])

    def test_criterion_without_a_machine_check_is_unknown(self):
        r = rank.evaluate_criterion({"text": "At least one paid staff member", "kind": "hard"}, {})
        self.assertEqual(r["result"], "unknown")

    def test_pass_records_which_fact_was_used(self):
        profile = {"tax_status": {"id": "F-02", "field": "tax_status", "value": "501(c)(3)"}}
        crit = {"text": "501(c)(3)", "kind": "hard", "check": {"field": "tax_status", "op": "in", "value": ["501(c)(3)"]}}
        self.assertEqual(rank.evaluate_criterion(crit, profile)["fact_id"], "F-02")

    def test_unknown_op_is_bad_input(self):
        with self.assertRaises(validate.InputError):
            rank.evaluate_criterion({"text": "x", "kind": "hard", "check": {"field": "a", "op": "approx", "value": 1}}, {})


class Buckets(unittest.TestCase):
    def test_non_501c3_org_is_excluded_from_a_501c3_only_grant_with_the_reason(self):
        result = ranked(golden_state("eastgate"))
        entry = next(e for e in result["not_eligible"] if e["id"] == "G-01")
        self.assertTrue(any(c["result"] == "fail" and "501(c)(3)" in c["text"] for c in entry["hard_gates"]))

    def test_closed_and_past_deadline_grants_are_never_ranked(self):
        result = ranked(golden_state())
        self.assertEqual(sorted(ids(result, "closed")), ["G-07", "G-08"])
        self.assertNotIn("G-08", ids(result, "ranked") + ids(result, "needs_checking"))

    def test_unverified_records_are_leads_only(self):
        result = ranked(golden_state())
        self.assertEqual(sorted(ids(result, "unverified")), ["G-09", "G-10"])

    def test_unregistered_sam_uei_needs_checking_with_lead_time_warning(self):
        state = golden_state("riverbend")
        for fact in state["profile"]["facts"]:
            if fact["field"] == "sam_uei_status":
                fact["value"] = "not_registered"
        entry = next(e for e in ranked(state)["needs_checking"] if e["id"] == "G-01")
        self.assertTrue(any("SAM.gov" in q and "weeks" in q for q in entry["questions"]))

    def test_unknown_status_goes_to_needs_checking(self):
        state = golden_state()
        state["grants"][0]["status"] = "unknown"
        self.assertIn("G-01", ids(ranked(state), "needs_checking"))

    def test_score_comes_with_its_components_and_weights(self):
        result = ranked(golden_state())
        top = result["ranked"][0]
        self.assertIn("components", top)
        self.assertEqual(set(result["weights"]), set(rank.COMPONENTS))

    def test_duplicate_profile_fields_are_refused(self):
        state = golden_state()
        state["profile"]["facts"].append({"id": "F-99", "field": "tax_status", "value": "other"})
        with self.assertRaises(validate.InputError):
            ranked(state)


class RankCli(StateCase):
    def test_markdown_output_shows_weights_and_sources(self):
        code, out, _ = run(rank, self.state_file(), "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("Weights: issue_match 0.4", out)
        self.assertIn("Not eligible, because:", out)

    def test_exit_0_when_nothing_is_unknown_or_unverified(self):
        state = golden_state()
        state["grants"] = [g for g in state["grants"] if g["id"] in ("G-01", "G-06")]
        self.assertEqual(run(rank, self.state_file(state), "--today", TODAY)[0], 0)

    def test_bad_weights_file_exits_2(self):
        weights = self.tmp / "w.json"
        weights.write_text(json.dumps({"weights": {"issue_match": 1}}), encoding="utf-8")
        self.assertEqual(run(rank, self.state_file(), "--weights", weights)[0], 2)

    def test_state_without_profile_exits_2(self):
        self.assertEqual(run(rank, self.state_file({"grants": []}))[0], 2)


if __name__ == "__main__":
    unittest.main()
