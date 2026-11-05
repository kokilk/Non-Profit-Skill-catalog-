"""Tests for skills/board-minutes-tracker/scripts/minutes.py: lint catches seeded errors; tracker rules."""

import contextlib
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOOD = (ROOT / "samples" / "minutes" / "minutes-good.md").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT / "skills" / "board-minutes-tracker" / "scripts"))
import minutes  # noqa: E402

MEMBERS = "Ana Ruiz, Ben Okoro, Chloe Varga, Dev Patel"

# One mutation of the good minutes per seeded error: (label, old text, new text).
SEEDED = [
    ("missing quorum", "- Quorum: present (8 of 9 directors)\n", ""),
    ("missing adjournment time", "- Adjourned: 8:12 pm", "- Adjourned:"),
    ("missing call to order", "- Called to order: 6:02 pm by Ana Ruiz, Chair", "- Called to order:"),
    ("missing attendance", "- Present: Ana Ruiz, Ben Okoro, Chloe Varga, Dev Patel, Ema Lindqvist, Farid Haddad, Gail Moreno, Hugo Brandt (8)\n", ""),
    ("missing seconder", "- Seconded by: Hugo Brandt\n", ""),
    ("missing outcome", "- Vote: 8 yes, 0 no\n- Outcome: carried", "- Vote: 8 yes, 0 no"),
    ("vote tally mismatch (7 yes + 2 no, 8 present)", "- Vote: 7 yes, 1 no", "- Vote: 7 yes, 2 no"),
    ("recusal without conflict declaration",
     "- Farid Haddad declared a conflict on the printing contract (a family member's business) and recused from the discussion and vote.",
     "- None declared."),
    ("discussion in executive session", "- Topic: personnel",
     "- Topic: personnel\n- The board discussed the director's missed deadlines and agreed a raise was not justified."),
    ("no DRAFT banner while not approved", "**DRAFT: not approved.** Prepared for review by the secretary.\n", ""),
    ("marked approved with unresolved CONFIRM items", "- Approved:", "- Approved: 2026-11-18"),
]


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = minutes.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


class Lint(unittest.TestCase):
    def test_good_minutes_pass_with_confirm_warning(self):
        res = minutes.lint(GOOD)
        self.assertTrue(res["passed"], res["errors"])
        self.assertEqual(res["unresolved_confirm"], 3)

    def test_every_seeded_error_is_caught_on_its_own(self):
        missed = []
        for label, old, new in SEEDED:
            self.assertEqual(GOOD.count(old), 1, f"seed {label!r} doesn't apply")
            if minutes.lint(GOOD.replace(old, new))["passed"]:
                missed.append(label)
        self.assertEqual(missed, [], f"lint missed: {missed}")

    def test_tally_error_names_the_numbers(self):
        res = minutes.lint(GOOD.replace("- Vote: 7 yes, 1 no", "- Vote: 7 yes, 2 no"))
        self.assertTrue(any("= 9, but 8 present" in e for e in res["errors"]))

    def test_seconder_marked_confirm_is_a_warning_not_a_pass_through(self):
        res = minutes.lint(GOOD.replace("- Seconded by: Hugo Brandt", "- Seconded by: [CONFIRM: not in the notes]"))
        self.assertTrue(any("Seconded by" in w for w in res["warnings"]))

    def test_voice_vote_without_tally_is_accepted(self):
        self.assertTrue(minutes.lint(GOOD.replace("- Vote: 8 yes, 0 no", "- Vote: voice vote"))["passed"])

    def test_cli_exit_codes(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            bad = tmp / "m.md"
            bad.write_text(GOOD.replace("- Seconded by: Hugo Brandt\n", ""), encoding="utf-8")
            self.assertEqual(run("lint", ROOT / "samples/minutes/minutes-good.md")[0], 0)
            self.assertEqual(run("lint", bad)[0], 1)
            self.assertEqual(run("lint", tmp / "none.md")[0], 2)
        finally:
            shutil.rmtree(tmp)


class TrackerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.t = self.tmp / "action-tracker-board.json"
        run("init", self.t, "--body", "Board of Directors", "--members", MEMBERS)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def add(self, *extra):
        return run("add", self.t, *extra)

    def test_add_with_absolute_date_and_named_member(self):
        code, out, _ = self.add("--text", "Send the audit RFP", "--owner", "ana ruiz", "--due", "2026-11-15")
        self.assertEqual(code, 0)
        action = json.loads(self.t.read_text())["actions"][0]
        self.assertEqual((action["id"], action["owner"], action["due"]), ("A-001", "Ana Ruiz", "2026-11-15"))

    def test_relative_date_is_refused_without_an_anchor(self):
        code, _, err = self.add("--text", "Forecast", "--owner", "Dev Patel", "--due", "next meeting")
        self.assertEqual(code, 2)
        self.assertIn("anchor", err)

    def test_due_in_days_from_a_confirmed_anchor(self):
        self.add("--text", "Forecast", "--owner", "Dev Patel", "--due-in-days", "35", "--anchor", "2026-10-14")
        self.assertEqual(json.loads(self.t.read_text())["actions"][0]["due"], "2026-11-18")

    def test_the_board_is_not_an_owner(self):
        code, _, err = self.add("--text", "Review bylaws", "--owner", "the board", "--due", "2026-12-01")
        self.assertEqual(code, 2)
        self.assertIn("which person", err)

    def test_owner_must_be_on_the_member_list(self):
        self.assertEqual(self.add("--text", "x", "--owner", "Zed Unknown", "--due", "2026-12-01")[0], 2)

    def test_init_refuses_to_overwrite_an_existing_tracker(self):
        self.assertEqual(run("init", self.t, "--body", "Board", "--members", "A B")[0], 2)

    def test_list_overdue_and_by_owner_with_exit_1_when_overdue(self):
        self.add("--text", "RFP", "--owner", "Ana Ruiz", "--due", "2026-11-15")
        self.add("--text", "Forecast", "--owner", "Dev Patel", "--due", "2026-12-15")
        code, out, _ = run("list", self.t, "--overdue", "--today", "2026-11-20")
        self.assertEqual(code, 1)
        self.assertIn("5 days overdue", out)
        self.assertNotIn("Forecast", out)
        self.assertIn("Forecast", run("list", self.t, "--owner", "Dev Patel", "--today", "2026-11-20")[1])

    def test_close_then_digest_shows_nothing_overdue(self):
        self.add("--text", "RFP", "--owner", "Ana Ruiz", "--due", "2026-11-15")
        self.assertEqual(run("close", self.t, "A-001", "--note", "Sent", "--today", "2026-11-14")[0], 0)
        code, out, _ = run("digest", self.t, "--today", "2026-11-20")
        self.assertEqual(code, 0)
        self.assertIn("Nothing open", out)
        self.assertEqual(run("close", self.t, "A-001")[0], 2)

    def test_digest_groups_by_owner_and_says_drafts_are_not_sent(self):
        self.add("--text", "RFP", "--owner", "Ana Ruiz", "--due", "2026-11-15")
        self.add("--text", "Forecast", "--owner", "Dev Patel", "--due", "2026-12-15")
        out = run("digest", self.t, "--today", "2026-11-20")[1]
        self.assertIn("Ana Ruiz:", out)
        self.assertIn("never sent without the user's OK", out)

    def test_export_csv_and_change_log(self):
        self.add("--text", "RFP", "--owner", "Ana Ruiz", "--due", "2026-11-15")
        out = self.tmp / "actions.csv"
        self.assertEqual(run("export-csv", self.t, "--out", out)[0], 0)
        self.assertEqual(list(csv.DictReader(out.open()))[0]["owner"], "Ana Ruiz")
        self.assertEqual(len(json.loads(self.t.read_text())["change_log"]), 2)

    def test_tracker_changed_since_read_is_not_overwritten(self):
        tr = minutes.Tracker(str(self.t))
        self.t.write_text(self.t.read_text().replace("Board of Directors", "Board"), encoding="utf-8")
        with self.assertRaises(minutes.InputError):
            tr.save(tr.data)


if __name__ == "__main__":
    unittest.main()
