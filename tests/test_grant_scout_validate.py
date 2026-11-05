"""Tests for skills/grant-scout/scripts/validate.py."""

import sys
from pathlib import Path
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _grant_fixtures import TODAY, StateCase, golden_state, run
import validate


def one(**changes):
    rec = dict(golden_state()["grants"][0], **changes)
    return validate.check_record(rec, validate.today_from(TODAY), 30)


class CheckRecord(unittest.TestCase):
    def test_complete_record_is_verified(self):
        self.assertTrue(one()["verified"])

    def test_missing_source_url_makes_an_unverified_lead(self):
        r = one(source_url="")
        self.assertFalse(r["verified"])
        self.assertTrue(any("source_url" in m for m in r["missing"]))

    def test_open_grant_without_a_deadline_is_unverified(self):
        self.assertFalse(one(deadline=None, deadline_source="")["verified"])

    def test_deadline_without_deadline_source_is_unverified(self):
        self.assertFalse(one(deadline_source="")["verified"])

    def test_checked_on_in_the_future_or_not_a_date_is_unverified(self):
        self.assertFalse(one(checked_on="2027-01-01")["verified"])
        self.assertFalse(one(checked_on="last week")["verified"])

    def test_criterion_without_source_location_is_unverified(self):
        crit = [{"text": "Must be a 501(c)(3)", "kind": "hard"}]
        self.assertFalse(one(eligibility_criteria=crit)["verified"])

    def test_stale_check_warns_but_stays_verified(self):
        r = one(checked_on="2026-08-01")
        self.assertTrue(r["verified"])
        self.assertTrue(any("re-check" in w for w in r["warnings"]))

    def test_open_grant_past_its_deadline_warns(self):
        r = one(deadline="2026-10-01")
        self.assertTrue(any("has passed" in w for w in r["warnings"]))

    def test_rolling_grant_needs_no_deadline(self):
        self.assertTrue(one(status="rolling", deadline=None, deadline_source="")["verified"])


class ValidateCli(StateCase):
    def test_exit_1_when_any_record_is_unverified_and_names_it(self):
        code, out, _ = run(validate, self.state_file(), "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("G-09", out)
        self.assertIn("UNVERIFIED LEAD", out)

    def test_exit_0_when_every_record_is_verified(self):
        state = golden_state()
        state["grants"] = [g for g in state["grants"] if g["id"] in ("G-01", "G-03")]
        self.assertEqual(run(validate, self.state_file(state), "--today", TODAY)[0], 0)

    def test_update_writes_verified_flags_into_the_state_file(self):
        path = self.state_file()
        run(validate, path, "--today", TODAY, "--update")
        flags = {g["id"]: g["verified"] for g in self.load(path)["grants"]}
        self.assertTrue(flags["G-01"])
        self.assertFalse(flags["G-09"])

    def test_json_output_lists_every_record(self):
        out = run(validate, self.state_file(), "--today", TODAY, "--format", "json")[1]
        self.assertEqual(len(json.loads(out)["results"]), 12)

    def test_missing_file_bad_json_and_bad_today_exit_2(self):
        self.assertEqual(run(validate, self.tmp / "none.json")[0], 2)
        bad = self.tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        self.assertEqual(run(validate, bad)[0], 2)
        self.assertEqual(run(validate, self.state_file(), "--today", "05/11/2026")[0], 2)

    def test_state_without_grants_list_exits_2(self):
        self.assertEqual(run(validate, self.state_file({"profile": {}}))[0], 2)

    def test_state_changed_since_read_is_not_overwritten(self):
        path = self.state_file()
        sf = validate.StateFile(path)
        path.write_text(path.read_text().replace("G-01", "G-91"), encoding="utf-8")
        with self.assertRaises(validate.InputError):
            sf.save(sf.data)


if __name__ == "__main__":
    unittest.main()
