"""Stage 6 pack documents: required content is present and every file they point to exists."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def text(name):
    return (DOCS / name).read_text(encoding="utf-8")


class PackDocs(unittest.TestCase):
    def test_break_it_has_at_least_15_prompts_each_with_expected_behavior(self):
        rows = re.findall(r"^\| (\d+) \| [^|]+ \| ([^|]+) \| ([^|]+) \|$", text("BREAK-IT-CHECKLIST.md"), re.M)
        self.assertGreaterEqual(len(rows), 15)
        self.assertTrue(all(expected.strip() for _, _, expected in rows))

    def test_break_it_covers_every_group_in_the_spec(self):
        body = text("BREAK-IT-CHECKLIST.md")
        for group in ("Invent", "Sensitive", "Gift list", "Meeting notes", "Send / submit", "Skip privacy"):
            self.assertIn(f"| {group} |", body)

    def test_training_has_agenda_handout_five_question_quiz_and_feedback(self):
        body = text("TRAINING-30MIN.md")
        for heading in ("## 1. Agenda", "## 4. One-page handout", "## 5. Quiz", "## 6. Feedback form"):
            self.assertIn(heading, body)
        quiz = body.split("## 5. Quiz")[1].split("## 6.")[0]
        self.assertEqual(len(re.findall(r"^\d\. ", quiz, re.M)), 5)

    def test_governance_has_incident_process_and_review_cadence(self):
        body = text("GOVERNANCE.md")
        for item in ("Incident process", "Stop", "Contain", "Tell the data owner", "Quarterly review"):
            self.assertIn(item, body)

    def test_runbook_and_adoption_docs_have_their_sections(self):
        self.assertIn("## 8. Who to call", text("RUNBOOK.md"))
        self.assertIn("Never extrapolate", text("ADOPTION-METRICS.md"))

    def test_no_doc_is_still_an_outline(self):
        for doc in DOCS.glob("*.md"):
            self.assertNotIn("Status: outline", doc.read_text(encoding="utf-8"), doc.name)

    def test_sample_files_named_in_the_docs_exist(self):
        for doc in list(DOCS.glob("*.md")) + [ROOT / "README.md"]:
            for rel in set(re.findall(r"`(samples/[\w./-]+\.\w+)`", doc.read_text(encoding="utf-8"))):
                self.assertTrue((ROOT / rel).exists(), f"{doc.name} names missing {rel}")


class GuideAndRunSheet(unittest.TestCase):
    def test_eval_run_sheet_matches_the_eval_folders(self):
        import subprocess, sys
        res = subprocess.run([sys.executable, str(ROOT / "tools" / "make_eval_sheet.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_run_sheet_has_every_case_and_no_raw_regex(self):
        body = text("EVAL-RUN-SHEET.md")
        cases = [p for p in (ROOT / "evals").glob("*/*") if (p / "prompt.md").is_file()]
        self.assertEqual(len(re.findall(r"^### ", body, re.M)), len(cases))
        self.assertNotIn("matching the pattern", body)

    def test_guide_covers_install_cowork_each_skill_and_troubleshooting(self):
        body = text("GUIDE.md")
        for item in ("Customize", "Upload a skill", "Code execution and file creation", "Cowork",
                     "pii-guard", "grant-scout", "impact-report-builder", "board-minutes-tracker",
                     "donor-thank-you-writer", "Never upload it", "If something goes wrong", "EVAL-RUN-SHEET.md"):
            self.assertIn(item, body)


if __name__ == "__main__":
    unittest.main()
