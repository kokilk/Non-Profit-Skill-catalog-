"""Tests for skills/grant-scout/scripts/pipeline.py."""

import sys
from pathlib import Path
import csv
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _grant_fixtures import TODAY, StateCase, golden_state, run
import pipeline


class Schedule(unittest.TestCase):
    def test_working_back_schedule_counts_back_from_the_deadline(self):
        import datetime as dt
        plan = pipeline.schedule(dt.date(2027, 2, 15), dict(pipeline.DEFAULT_SETTINGS), dt.date(2026, 11, 5))
        self.assertEqual((plan["submit_by"], plan["review_start"], plan["draft_start"]),
                         ("2027-02-13", "2027-02-08", "2027-01-29"))
        self.assertTrue(plan["feasible"])

    def test_schedule_that_would_start_in_the_past_is_infeasible(self):
        import datetime as dt
        plan = pipeline.schedule(dt.date(2026, 11, 20), dict(pipeline.DEFAULT_SETTINGS), dt.date(2026, 11, 5))
        self.assertFalse(plan["feasible"])


class PipelineCli(StateCase):
    def add(self, path, gid, *extra):
        return run(pipeline, "add", path, gid, "--today", TODAY, *extra)

    def test_add_shortlists_a_verified_grant_and_logs_it(self):
        path = self.state_file()
        code, out, _ = self.add(path, "G-01")
        self.assertEqual(code, 0)
        self.assertIn("submit by 2027-02-13", out)
        state = self.load(path)
        self.assertEqual(state["pipeline"]["entries"][0]["stage"], "shortlisted")
        self.assertEqual(state["change_log"][-1]["summary"], "Shortlisted G-01")

    def test_add_refuses_unverified_closed_unknown_and_duplicate_grants(self):
        path = self.state_file()
        self.assertEqual(self.add(path, "G-09")[0], 2)
        self.assertEqual(self.add(path, "G-08")[0], 2)
        self.assertEqual(self.add(path, "G-77")[0], 2)
        self.add(path, "G-01")
        self.assertEqual(self.add(path, "G-01")[0], 2)

    def test_add_with_override_shows_the_days_used(self):
        code, out, _ = self.add(self.state_file(), "G-06", "--drafting-days", "20")
        self.assertEqual(code, 0)
        self.assertIn("Using 20 drafting", out)

    def test_rolling_grant_has_no_schedule(self):
        code, out, _ = self.add(self.state_file(), "G-03")
        self.assertEqual(code, 0)
        self.assertIn("Rolling deadline", out)

    def test_update_changes_stage_appends_log_and_keeps_old_entries(self):
        path = self.state_file()
        self.add(path, "G-01")
        code, _, _ = run(pipeline, "update", path, "G-01", "--stage", "loi_drafting", "--note", "Draft started",
                         "--follow-up", "2026-11-20", "--today", TODAY)
        self.assertEqual(code, 0)
        state = self.load(path)
        entry = state["pipeline"]["entries"][0]
        self.assertEqual((entry["stage"], entry["follow_up_on"]), ("loi_drafting", "2026-11-20"))
        self.assertEqual(len(state["change_log"]), 2)

    def test_update_rejects_unknown_grant_bad_date_or_nothing_to_do(self):
        path = self.state_file()
        self.add(path, "G-01")
        self.assertEqual(run(pipeline, "update", path, "G-02", "--stage", "loi_review")[0], 2)
        self.assertEqual(run(pipeline, "update", path, "G-01", "--follow-up", "soon")[0], 2)
        self.assertEqual(run(pipeline, "update", path, "G-01")[0], 2)

    def test_status_flags_due_soon_and_infeasible_with_exit_1(self):
        state = golden_state("coastline")
        path = self.state_file(state)
        self.add(path, "G-04")  # deadline 2026-11-20: 15 days left
        code, out, _ = run(pipeline, "status", path, "--today", "2026-11-10")
        self.assertEqual(code, 1)
        self.assertIn("10 days left (due soon)", out)
        self.assertIn("NOT FEASIBLE", out)

    def test_status_exit_0_when_everything_is_comfortable(self):
        path = self.state_file()
        self.add(path, "G-06")
        self.assertEqual(run(pipeline, "status", path, "--today", TODAY)[0], 0)

    def test_export_csv_writes_one_row_per_entry(self):
        path = self.state_file()
        self.add(path, "G-01")
        self.add(path, "G-03")
        out = self.tmp / "tracker.csv"
        self.assertEqual(run(pipeline, "export-csv", path, "--out", out, "--today", TODAY)[0], 0)
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        self.assertEqual([r["grant_id"] for r in rows], ["G-01", "G-03"])
        self.assertEqual(rows[0]["submit_by"], "2027-02-13")

    def test_export_refuses_to_overwrite_the_state_file(self):
        path = self.state_file()
        self.assertEqual(run(pipeline, "export-csv", path, "--out", path)[0], 2)
        json.loads(path.read_text())  # still intact

    def test_negative_day_counts_exit_2(self):
        self.assertEqual(self.add(self.state_file(), "G-01", "--drafting-days", "-3")[0], 2)


if __name__ == "__main__":
    unittest.main()
