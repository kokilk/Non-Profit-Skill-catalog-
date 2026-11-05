"""Tests for skills/donor-thank-you-writer/scripts/letters.py: letter lint catches seeded errors; gift checks."""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "samples" / "letters"
GIFTS = ROOT / "samples" / "data" / "donors.csv"
CONFIG = S / "thank-you-config.json"
TEMPLATE_CONFIG = ROOT / "skills" / "donor-thank-you-writer" / "assets" / "thank-you-config.json"
GOOD = (S / "letter-G-0001.md").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT / "skills" / "donor-thank-you-writer" / "scripts"))
import letters  # noqa: E402

OTHER_DONOR = "Morgan Glenhaven"
SEEDED = [
    ("wrong amount", "$250.00", "$500.00"),
    ("donor name missing", "Dear Noel,", "Dear Friend,"),
    ("invented number", "120 children", "150 children"),
    ("invented statistic", "We'd love to show you", "98% of our students improved. We'd love to show you"),
    ("overclaim", "gifts like yours help make that possible", "your gift single-handedly made that possible"),
    ("other donor named", "With gratitude,", f"{OTHER_DONOR} gave too!\n\nWith gratitude,"),
    ("no goods-or-services statement", "No goods or services were provided in exchange for this contribution.", ""),
    ("legal name missing", "Lantern Hill Learning Collective (synthetic)", "Lantern Hill"),
    ("gift date missing", " on June 11, 2026", ""),
    ("placeholder left in", "It arrived just as", "{impact_fact} It arrived just as"),
    ("marker left in", "It arrived just as", "[NEEDS FROM ORG: camp photo] It arrived just as"),
]


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = letters.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def lint_text(text, gift_id="G-0001"):
    rows = letters.load_gifts(str(GIFTS))
    gift = next(r for r in rows if r["gift_id"] == gift_id)
    facts = json.loads((S / "impact-facts.json").read_text())
    return letters.lint(text, gift, rows, facts, json.loads(CONFIG.read_text()))


class LetterLint(unittest.TestCase):
    def test_good_letter_passes(self):
        res = lint_text(GOOD)
        self.assertTrue(res["passed"], res["errors"])

    def test_every_seeded_error_is_caught_on_its_own(self):
        missed = []
        for label, old, new in SEEDED:
            self.assertEqual(GOOD.count(old), 1, f"seed {label!r} doesn't apply")
            if lint_text(GOOD.replace(old, new))["passed"]:
                missed.append(label)
        self.assertEqual(missed, [], f"lint missed: {missed}")

    def test_small_gift_letter_needs_no_acknowledgment_statements(self):
        small = "Dear Val,\n\nThank you for your gift of $50.00. Our tutors met with 312 students this year.\n\nWarmly,\nJo"
        rows = letters.load_gifts(str(GIFTS))
        gift = dict(next(r for r in rows if r["gift_id"] == "G-0003"), first_name="Val", amount="50.00")
        res = letters.lint(small, gift, rows, json.loads((S / "impact-facts.json").read_text()), json.loads(CONFIG.read_text()))
        self.assertTrue(res["passed"], res["errors"])

    def test_sensitive_words_warn(self):
        res = lint_text(GOOD.replace("It arrived", "We hope your recovery from cancer is going well. It arrived"))
        self.assertTrue(any("sensitive" in w for w in res["warnings"]))

    def test_cli_exit_codes(self):
        base = ["--gift-id", "G-0001", "--gifts", GIFTS, "--facts", S / "impact-facts.json", "--config", CONFIG]
        self.assertEqual(run("lint", S / "letter-G-0001.md", *base)[0], 0)
        tmp = Path(tempfile.mkdtemp())
        try:
            bad = tmp / "l.md"
            bad.write_text(GOOD.replace("$250.00", "$500.00"), encoding="utf-8")
            self.assertEqual(run("lint", bad, *base)[0], 1)
            self.assertEqual(run("lint", tmp / "none.md", *base)[0], 2)
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(run("lint", S / "letter-G-0001.md", "--gift-id", "G-9999", *base[2:])[0], 2)


class GiftCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_check_flags_refund_duplicate_anonymous_tribute_and_acknowledgment(self):
        code, out, _ = run("check", GIFTS, "--config", CONFIG, "--format", "json")
        self.assertEqual(code, 1)
        g = {x["gift_id"]: x for x in json.loads(out)["gifts"]}
        self.assertTrue(any("refund" in i for i in g["G-0025"]["issues"]))
        self.assertTrue(any("duplicate of G-0029" in i for i in g["G-0030"]["issues"]))
        self.assertTrue(any("anonymous" in f for f in g["G-0005"]["flags"]))
        self.assertTrue(any("tribute (in memory)" in f for f in g["G-0010"]["flags"]))
        self.assertTrue(any("written acknowledgment" in f for f in g["G-0001"]["flags"]))
        self.assertFalse(any("written acknowledgment" in f for f in g["G-0003"]["flags"]))

    def test_goods_and_services_value_triggers_disclosure(self):
        f = self.tmp / "g.csv"
        f.write_text("gift_id,donor_id,first_name,last_name,email,gift_date,amount,goods_services_value\n"
                     "G-1,D-1,Pat,Lee,pat@example.org,2026-10-01,300.00,80\n", encoding="utf-8")
        g = json.loads(run("check", f, "--config", CONFIG, "--format", "json")[1])["gifts"][0]
        self.assertTrue(any("disclosure" in x for x in g["flags"]))

    def test_missing_name_is_an_issue_not_invented(self):
        f = self.tmp / "g.csv"
        f.write_text("gift_id,donor_id,first_name,last_name,email,gift_date,amount\nG-1,D-1,,,x@example.org,2026-10-01,40\n",
                     encoding="utf-8")
        g = json.loads(run("check", f, "--config", CONFIG, "--format", "json")[1])["gifts"][0]
        self.assertTrue(any("don't invent" in i for i in g["issues"]))

    def test_bad_amount_date_or_missing_column_exits_2(self):
        for body in ("gift_id,donor_id,first_name,last_name,gift_date,amount\nG-1,D-1,A,B,2026-10-01,lots\n",
                     "gift_id,donor_id,first_name,last_name,gift_date,amount\nG-1,D-1,A,B,10/01/2026,40\n",
                     "gift_id,first_name,last_name,gift_date,amount\nG-1,A,B,2026-10-01,40\n"):
            f = self.tmp / "g.csv"
            f.write_text(body, encoding="utf-8")
            self.assertEqual(run("check", f, "--config", CONFIG)[0], 2)


class Segment(unittest.TestCase):
    def test_segment_refuses_until_the_org_sets_thresholds(self):
        code, _, err = run("segment", GIFTS, "--config", TEMPLATE_CONFIG)
        self.assertEqual(code, 2)
        self.assertIn("no built-in defaults", err)

    def test_segment_assigns_major_recurring_first_time_and_repeat(self):
        out = json.loads(run("segment", GIFTS, "--config", CONFIG, "--format", "json")[1])
        segs = {g["gift_id"]: g["segments"] for g in out["gifts"]}
        self.assertIn("major", segs["G-0002"])
        self.assertIn("recurring", segs["G-0007"])
        self.assertNotIn("G-0025", segs)  # refund: no letter
        self.assertTrue(any("first_time" in s for s in segs.values()))
        self.assertTrue(any("repeat" in s for s in segs.values()))


if __name__ == "__main__":
    unittest.main()
