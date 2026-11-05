"""Pack-wide guards: skeleton present, Python files stdlib-only, 3.9-compatible and network-free.

These run over every .py file in the pack, so later stages are checked automatically.
"""

import ast
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ["pii-guard", "grant-scout", "impact-report-builder",
          "board-minutes-tracker", "donor-thank-you-writer"]
DOCS = ["GOVERNANCE.md", "RUNBOOK.md", "TRAINING-30MIN.md", "BREAK-IT-CHECKLIST.md",
        "DATA-TIERS.md", "ADOPTION-METRICS.md"]
NETWORK_MODULES = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "poplib",
                   "imaplib", "telnetlib", "xmlrpc", "requests", "httpx", "aiohttp", "asyncio"}
README_SECTIONS = ["Owner and status", "What each skill does", "Design decisions", "Data tiers",
                   "Known limits", "Assumptions to verify", "Folder structure",
                   "Packaging and installing", "Maintenance", "Changelog"]


def python_files():
    return sorted(p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def top_level_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


class Skeleton(unittest.TestCase):
    def test_skill_docs_and_eval_folders_exist(self):
        for skill in SKILLS:
            self.assertTrue((ROOT / "skills" / skill).is_dir(), skill)
        for doc in DOCS:
            self.assertTrue((ROOT / "docs" / doc).is_file(), doc)
        for path in ("README.md", "STANDARDS.md", "samples/README.md", "evals/README.md"):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_plugin_manifest_is_in_claude_plugin_folder_with_kebab_case_name(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertRegex(manifest["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertIn("version", manifest)

    def test_readme_has_every_required_section(self):
        headings = re.findall(r"^#+ (.+)$", (ROOT / "README.md").read_text(encoding="utf-8"), re.M)
        for section in README_SECTIONS:
            self.assertTrue(any(section.lower() in h.lower() for h in headings), section)

    def test_readme_states_that_uploading_sends_data_to_the_model(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("uploading a file to a chat sends it to the model", text)

    def test_standards_checklist_lists_every_spec_id(self):
        text = (ROOT / "STANDARDS.md").read_text(encoding="utf-8")
        for ident in [f"S{i}" for i in range(1, 6)] + [f"W{i}" for i in range(1, 10)]:
            self.assertRegex(text, rf"\| {ident} \|", ident)


class PythonFiles(unittest.TestCase):
    def test_there_is_at_least_one_python_file_to_check(self):
        self.assertTrue(python_files())

    def test_python_files_parse_as_python_3_9(self):
        for path in python_files():
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))

    def test_python_files_import_no_network_modules(self):
        for path in python_files():
            bad = top_level_imports(path) & NETWORK_MODULES
            self.assertFalse(bad, f"{path.relative_to(ROOT)} imports {sorted(bad)}")

    @unittest.skipUnless(hasattr(sys, "stdlib_module_names"), "needs Python 3.10+ to list stdlib")
    def test_python_files_import_only_the_standard_library(self):
        local = {p.stem for p in python_files()}
        for path in python_files():
            extra = top_level_imports(path) - set(sys.stdlib_module_names) - local
            self.assertFalse(extra, f"{path.relative_to(ROOT)} imports {sorted(extra)}")

    def test_scripts_document_exit_codes_in_their_docstring(self):
        for path in python_files():
            if path.parent.name in ("scripts", "samples"):
                doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
                self.assertIn("Exit codes", doc, path.relative_to(ROOT))


if __name__ == "__main__":
    unittest.main()
