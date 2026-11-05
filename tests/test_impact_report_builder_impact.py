"""Tests for skills/impact-report-builder/scripts/impact.py, against a hand-computed answer key."""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "samples" / "impact"
sys.path.insert(0, str(ROOT / "skills" / "impact-report-builder" / "scripts"))
import impact  # noqa: E402

KEY = json.loads((S / "answer-key.json").read_text(encoding="utf-8"))


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = impact.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def computed():
    header, rows, _ = impact.read_csv(str(S / "cohort.csv"))
    res = impact.run_metrics(header, rows, json.loads((S / "metrics-config.json").read_text()))
    return {m["name"]: m for m in res["metrics"]}, res


class AnswerKey(unittest.TestCase):
    def test_every_metric_matches_the_hand_computed_key(self):
        m, res = computed()
        self.assertEqual(res["rows_used"], KEY["rows_used"])
        self.assertEqual(m["people_served"]["overall"]["value"], KEY["people_served"])
        overall = m["completion_rate"]["overall"]
        self.assertEqual({k: overall[k] for k in ("numerator", "denominator", "value")}, KEY["completion_rate"]["overall"])
        sc = m["score_change"]["overall"]
        self.assertEqual({k: sc[k] for k in ("matched", "dropped", "pre_mean", "post_mean", "value")},
                         {k: KEY["score_change"][k] for k in ("matched", "dropped", "pre_mean", "post_mean", "value")})
        self.assertEqual(m["mean_pre_score"]["overall"]["value"], KEY["mean_pre_score"])
        self.assertEqual(m["median_pre_score"]["overall"]["value"], KEY["median_pre_score"])
        self.assertEqual(m["tutoring_enrolled"]["overall"]["value"], KEY["tutoring_enrolled"])

    def test_small_group_and_its_complement_are_suppressed(self):
        groups = {g["group"]: g for g in computed()[0]["completion_rate"]["groups"]}
        self.assertIn("fewer than 5", groups["Family Literacy"]["suppressed"])
        self.assertIn("complementary", groups["Job Readiness"]["suppressed"])
        self.assertNotIn("numerator", groups["Family Literacy"])
        self.assertEqual((groups["Tutoring"]["numerator"], groups["Tutoring"]["denominator"]), (10, 12))

    def test_rounding_is_half_up_not_half_even(self):
        self.assertEqual(impact.r2(10.625), 10.63)
        self.assertEqual(impact.r2(0.125), 0.13)


class Profile(unittest.TestCase):
    def test_profile_finds_duplicates_mixed_and_ambiguous_dates_and_blanks(self):
        code, out, _ = run("profile", S / "cohort.csv")
        self.assertEqual(code, 1)
        for text in ("1 exact duplicate", "repeated ID", "2 formats", "ambiguous date", "post_score: 4 blank"):
            self.assertIn(text, out)

    def test_profile_flags_identifying_columns(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / "d.csv"
            f.write_text("first_name,email,score\nA,a@example.org,1\nB,b@example.org,2\n", encoding="utf-8")
            res = json.loads(run("profile", f, "--format", "json")[1])
            self.assertTrue(any("first_name: looks identifying" in i for i in res["issues"]))
        finally:
            shutil.rmtree(tmp)

    def test_profile_clean_file_exits_0(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / "d.csv"
            f.write_text("program,count\nA,10\nB,12\nC,9\nD,11\n", encoding="utf-8")
            self.assertEqual(run("profile", f)[0], 0)
        finally:
            shutil.rmtree(tmp)

    def test_non_csv_or_missing_file_exits_2(self):
        self.assertEqual(run("profile", S / "draft-good.md")[0], 2)
        self.assertEqual(run("profile", S / "nope.csv")[0], 2)


class Metrics(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def config(self, metrics, **extra):
        p = self.tmp / "c.json"
        p.write_text(json.dumps(dict({"metrics": metrics}, **extra)), encoding="utf-8")
        return p

    def test_metrics_writes_json_with_provenance_and_exits_1_when_suppressing(self):
        out = self.tmp / "m.json"
        code, text, _ = run("metrics", S / "cohort.csv", "--config", S / "metrics-config.json", "--out", out)
        self.assertEqual(code, 1)
        res = json.loads(out.read_text())
        self.assertEqual(res["source_file"], "cohort.csv")
        self.assertEqual(len(res["source_sha256"]), 64)
        self.assertIn("org policy", text)

    def test_metric_records_rows_left_out_with_reasons(self):
        sc = computed()[0]["score_change"]["overall"]
        self.assertEqual(sc["excluded"], {"no matched pre and post score": 4})

    def test_unknown_column_kind_or_bad_config_exits_2(self):
        self.assertEqual(run("metrics", S / "cohort.csv", "--config",
                             self.config([{"name": "x", "kind": "mean", "column": "age"}]))[0], 2)
        self.assertEqual(run("metrics", S / "cohort.csv", "--config",
                             self.config([{"name": "x", "kind": "average", "column": "pre_score"}]))[0], 2)
        self.assertEqual(run("metrics", S / "cohort.csv", "--config", self.config([]))[0], 2)
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        self.assertEqual(run("metrics", S / "cohort.csv", "--config", bad)[0], 2)

    def test_metrics_without_suppression_exit_0(self):
        cfg = self.config([{"name": "n", "kind": "count_unique", "column": "participant_id"}])
        self.assertEqual(run("metrics", S / "cohort.csv", "--config", cfg)[0], 0)


INJECTED = {
    "wrong count": "We served 21 people this spring.",
    "wrong percent": "81% completed their program.",
    "rate with wrong denominator": "80.0% (16 of 21) completed.",
    "invented outcome": "Reading scores improved by 70%.",
    "suppressed group revealed": "In Family Literacy, 66.7% (2 of 3) completed.",
    "dropped participants miscounted": "5 participants had no ending score.",
    "wrong mean": "The average score rose by 11.5 points.",
    "made-up dollars": "Each completion cost $1,250.",
    "wrong median": "The median starting score was 47.",
    "rounded up past the truth": "Tutoring completion was 84%.",
}


class Verify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.metrics = cls.tmp / "metrics.json"
        run("metrics", S / "cohort.csv", "--config", S / "metrics-config.json", "--out", cls.metrics)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def check(self, text, *extra):
        draft = self.tmp / "d.md"
        draft.write_text(text, encoding="utf-8")
        return run("verify", draft, "--metrics", self.metrics, *extra)

    def test_good_draft_passes(self):
        code, out, _ = run("verify", S / "draft-good.md", "--metrics", self.metrics)
        self.assertEqual(code, 0, out)

    def test_every_injected_wrong_number_is_caught(self):
        missed = [label for label, text in INJECTED.items() if self.check(text)[0] != 1]
        self.assertEqual(missed, [], f"verifier missed: {missed}")

    def test_allowed_numbers_and_years_and_markers_pass(self):
        text = "In 2026 the funder's goal was 150 people. [NEEDS FROM ORG: number of volunteers, e.g. 35]"
        self.assertEqual(self.check(text, "--allow", "150")[0], 0)

    def test_bad_metrics_file_or_missing_draft_exits_2(self):
        self.assertEqual(run("verify", self.tmp / "none.md", "--metrics", self.metrics)[0], 2)
        self.assertEqual(self.check("x", "--allow", "ten")[0], 2)


if __name__ == "__main__":
    unittest.main()
