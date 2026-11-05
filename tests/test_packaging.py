"""Stage 6: package all five skills, then install and run them from the packages alone.

Each .skill is unzipped into a fresh temp folder and its scripts are run there with `python3 -I`
(isolated: no access to the repo's code), using only files inside the package plus the user's
own input files. This checks the packages are self-contained. It does not test uploading
to Claude itself.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import package_skills  # noqa: E402

SKILLS = ["pii-guard", "grant-scout", "impact-report-builder", "board-minutes-tracker", "donor-thank-you-writer"]


class Packaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / "dist"
        cls.code = package_skills.main(["--out", str(cls.dist)])
        cls.installed = cls.tmp / "installed"
        for skill in SKILLS:
            with zipfile.ZipFile(cls.dist / f"{skill}.skill") as zf:
                zf.extractall(cls.installed)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def run_script(self, skill, script, *args, cwd=None):
        path = self.installed / skill / "scripts" / script
        return subprocess.run([sys.executable, "-I", str(path), *map(str, args)], capture_output=True, text=True,
                              cwd=cwd or self.tmp)

    def test_all_five_skills_package(self):
        self.assertEqual(self.code, 0)
        self.assertEqual(sorted(p.stem for p in self.dist.glob("*.skill")), sorted(SKILLS))
        for skill in SKILLS:
            self.assertEqual((self.dist / f"{skill}.zip").read_bytes(), (self.dist / f"{skill}.skill").read_bytes())

    def test_packages_hold_skill_md_and_exclude_evals_and_caches(self):
        for skill in SKILLS:
            names = zipfile.ZipFile(self.dist / f"{skill}.skill").namelist()
            self.assertIn(f"{skill}/SKILL.md", names)
            self.assertTrue(all(n.startswith(f"{skill}/") for n in names), skill)
            self.assertFalse([n for n in names if "/evals/" in n or "__pycache__" in n or n.endswith((".pyc", ".DS_Store"))])

    def test_every_packaged_script_runs_help_from_the_package_alone(self):
        for script in self.installed.glob("*/scripts/*.py"):
            res = subprocess.run([sys.executable, "-I", str(script), "--help"], capture_output=True, text=True, cwd=self.tmp)
            self.assertEqual(res.returncode, 0, f"{script}: {res.stderr}")
            self.assertIn("Exit codes", res.stdout + (script.read_text()), script.name)

    def test_pii_guard_selftest_runs_on_its_bundled_corpus(self):
        res = self.run_script("pii-guard", "scan.py", "selftest")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Recall target 99%", res.stdout)

    def test_grant_scout_validates_and_ranks_from_the_package(self):
        state = json.loads((self.installed / "grant-scout" / "assets" / "state-template.json").read_text())
        gold = json.loads((ROOT / "samples" / "grants" / "golden-grants.json").read_text())["grants"]
        state["grants"] = gold[:3]
        state["profile"]["facts"] = json.loads((ROOT / "samples" / "grants" / "golden-profiles.json").read_text())["riverbend"]["facts"]
        path = self.tmp / "grant-pipeline-test.json"
        path.write_text(json.dumps(state))
        self.assertEqual(self.run_script("grant-scout", "validate.py", path, "--today", "2026-11-05").returncode, 0)
        res = self.run_script("grant-scout", "rank.py", path, "--today", "2026-11-05")
        self.assertIn("Ranked", res.stdout, res.stderr)

    def test_impact_metrics_run_with_the_packaged_example_config(self):
        cfg = self.installed / "impact-report-builder" / "assets" / "metrics-config-example.json"
        res = self.run_script("impact-report-builder", "impact.py", "metrics", ROOT / "samples/impact/cohort.csv", "--config", cfg)
        self.assertIn("people_served: 20", res.stdout, res.stderr)

    def test_minutes_lint_and_letters_check_run_from_the_package(self):
        res = self.run_script("board-minutes-tracker", "minutes.py", "lint", ROOT / "samples/minutes/minutes-good.md")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        res = self.run_script("donor-thank-you-writer", "letters.py", "segment", ROOT / "samples/data/donors.csv",
                              "--config", self.installed / "donor-thank-you-writer" / "assets" / "thank-you-config.json")
        self.assertEqual(res.returncode, 2, "template config must refuse until the org sets thresholds")

    def test_validation_failure_writes_nothing(self):
        bad = self.tmp / "bad-skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: Bad Name\ndescription: x\n---\n", encoding="utf-8")
        target, problems = package_skills.package(bad, self.tmp / "out2")
        self.assertIsNone(target)
        self.assertTrue(problems)
        self.assertFalse((self.tmp / "out2").exists())


if __name__ == "__main__":
    unittest.main()
