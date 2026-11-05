"""Shared synthetic fixtures for the grant-scout tests (not a test module)."""

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "grant-scout" / "scripts"))
GOLD = ROOT / "samples" / "grants"
TODAY = "2026-11-05"


def golden_state(profile="riverbend"):
    grants = json.loads((GOLD / "golden-grants.json").read_text(encoding="utf-8"))["grants"]
    facts = json.loads((GOLD / "golden-profiles.json").read_text(encoding="utf-8"))[profile]["facts"]
    return {"schema_version": "1.0", "created_with": "grant-scout 0.1.0", "profile": {"facts": facts},
            "grants": copy.deepcopy(grants), "change_log": []}


def run(module, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = module.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


class StateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def state_file(self, state=None, name="grant-pipeline-test.json"):
        path = self.tmp / name
        path.write_text(json.dumps(state if state is not None else golden_state()), encoding="utf-8")
        return path

    def load(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
