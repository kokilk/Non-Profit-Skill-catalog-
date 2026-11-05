"""Tests for samples/generate.py: determinism, CLI contract, and that every value is synthetic."""

import contextlib
import csv
import hashlib
import importlib.util
import io
import ipaddress
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "samples" / "data"

_spec = importlib.util.spec_from_file_location("generate", ROOT / "samples" / "generate.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
STRUCTURED = ["EMAIL", "PHONE", "CARD"]


def run_main(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = gen.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def load_corpus():
    with open(DATA / "pii" / "corpus.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def load_csv(name):
    with open(DATA / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def labels_of(corpus, label_type):
    return [lab for rec in corpus for lab in rec["labels"] if lab["type"] == label_type]


class DeterminismAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_same_seed_gives_identical_files(self):
        first, _ = gen.build_all(gen.DEFAULT_SEED)
        second, _ = gen.build_all(gen.DEFAULT_SEED)
        self.assertEqual(first, second)

    def test_different_seed_gives_different_corpus(self):
        a, _ = gen.build_all(1)
        b, _ = gen.build_all(2)
        self.assertNotEqual(a["pii/corpus.jsonl"], b["pii/corpus.jsonl"])

    def test_committed_data_matches_generator(self):
        code, out, _ = run_main("--check", "--out", str(DATA))
        self.assertEqual(code, 0, out)

    def test_check_exits_1_and_names_the_file_when_data_was_edited(self):
        copy = self.tmp / "data"
        shutil.copytree(DATA, copy)
        with open(copy / "donors.csv", "a", encoding="utf-8") as fh:
            fh.write("hand-edited row\n")
        code, out, _ = run_main("--check", "--out", str(copy))
        self.assertEqual(code, 1)
        self.assertIn("donors.csv", out)

    def test_check_exits_2_when_folder_is_missing(self):
        code, _, err = run_main("--check", "--out", str(self.tmp / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_non_positive_seed_exits_2(self):
        code, _, err = run_main("--seed", "0", "--out", str(self.tmp / "x"))
        self.assertEqual(code, 2)
        self.assertIn("--seed", err)

    def test_out_path_that_is_a_file_exits_2(self):
        a_file = self.tmp / "file.txt"
        a_file.write_text("x", encoding="utf-8")
        code, _, err = run_main("--out", str(a_file))
        self.assertEqual(code, 2)
        self.assertIn("is a file", err)

    def test_write_then_check_round_trips(self):
        out_dir = self.tmp / "fresh"
        self.assertEqual(run_main("--out", str(out_dir))[0], 0)
        self.assertEqual(run_main("--check", "--out", str(out_dir))[0], 0)

    def test_summary_never_prints_sample_values(self):
        _, out, _ = run_main("--out", str(self.tmp / "s"))
        self.assertIsNone(EMAIL_RE.search(out), "summary printed an email address")
        for lab in labels_of(load_corpus(), "CARD")[:20]:
            self.assertNotIn(lab["value"], out)

    def test_json_format_summary_is_valid_json(self):
        _, out, _ = run_main("--out", str(self.tmp / "j"), "--format", "json")
        payload = json.loads(out)
        self.assertIn("manifest", payload)

    def test_manifest_hashes_match_files_on_disk(self):
        manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
        for rel, meta in manifest["files"].items():
            digest = hashlib.sha256((DATA / rel).read_bytes()).hexdigest()
            self.assertEqual(digest, meta["sha256"], rel)


class CorpusGroundTruth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()

    def test_every_label_span_matches_the_text(self):
        for rec in self.corpus:
            for lab in rec["labels"]:
                self.assertEqual(rec["text"][lab["start"]:lab["end"]], lab["value"], rec["id"])

    def test_every_record_is_marked_synthetic_with_a_unique_id(self):
        ids = [rec["id"] for rec in self.corpus]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(rec["synthetic"] is True for rec in self.corpus))

    def test_structured_types_have_at_least_100_labels_each(self):
        for label_type in STRUCTURED:
            self.assertGreaterEqual(len(labels_of(self.corpus, label_type)), 100, label_type)

    def test_us_phones_use_only_the_fictional_555_01xx_range(self):
        for lab in labels_of(self.corpus, "PHONE"):
            digits = re.sub(r"\D", "", lab["value"])
            if digits.startswith("44"):
                self.assertTrue(digits.startswith("442079460"), lab["value"])
            else:
                self.assertRegex(digits[-7:], r"^55501\d\d$", lab["value"])

    def test_ip_labels_are_documentation_ranges_only(self):
        doc_nets = [ipaddress.ip_network(n) for n in
                    ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")]
        for lab in labels_of(self.corpus, "IP"):
            addr = ipaddress.ip_address(lab["value"])
            self.assertTrue(any(addr in net for net in doc_nets if net.version == addr.version),
                            lab["value"])

    def test_card_labels_are_published_test_numbers_that_pass_luhn(self):
        for lab in labels_of(self.corpus, "CARD"):
            digits = re.sub(r"\D", "", lab["value"])
            self.assertIn(digits, gen.TEST_CARDS)
            self.assertTrue(gen.luhn_ok(digits))

    def test_no_ssn_shaped_values_anywhere_in_sample_data(self):
        ssn_shape = re.compile(r"(?<![\d-])\d{3}[- ]\d{2}[- ]\d{4}(?![\d-])")
        for path in DATA.rglob("*"):
            if path.is_file():
                self.assertIsNone(ssn_shape.search(path.read_text(encoding="utf-8")), path.name)

    def test_pii_guard_bundle_matches_samples(self):
        bundle = ROOT / "skills" / "pii-guard" / "assets" / "selftest"
        for rel in gen.BUNDLED:
            self.assertEqual((bundle / Path(rel).name).read_bytes(), (DATA / rel).read_bytes(), rel)

    def test_negative_records_have_no_labels(self):
        negatives = self.corpus[-gen.N_CORPUS_NEGATIVE:]
        self.assertTrue(all(not rec["labels"] for rec in negatives))
        self.assertTrue(all(not rec["context_families"] for rec in negatives))

    def test_order_numbers_in_negative_records_fail_luhn(self):
        found = 0
        for rec in self.corpus[-gen.N_CORPUS_NEGATIVE:]:
            for run in re.findall(r"\d{16}", rec["text"]):
                found += 1
                self.assertFalse(gen.luhn_ok(run), rec["id"])
        self.assertGreater(found, 0, "no 16-digit decoys found")

    def test_listed_and_cue_surname_pools_do_not_overlap(self):
        self.assertFalse(set(gen.LAST_NAMES_LISTED) & set(gen.LAST_NAMES_CUE))

    def test_every_listed_name_label_is_in_the_names_file(self):
        lines = (DATA / "pii" / "names-list.txt").read_text(encoding="utf-8").splitlines()
        names = {line for line in lines if line and not line.startswith("#")}
        for lab in labels_of(self.corpus, "NAME_LISTED"):
            self.assertIn(lab["value"], names)

    def test_every_sensitive_context_family_has_records(self):
        seen = {fam for rec in self.corpus for fam in rec["context_families"]}
        self.assertEqual(seen, set(gen.CONTEXT_PHRASES))

    def test_id_patterns_match_every_id_number_label(self):
        config = json.loads((DATA / "pii" / "id-patterns.json").read_text(encoding="utf-8"))
        patterns = [re.compile(p) for p in config["patterns"].values()]
        for lab in labels_of(self.corpus, "ID_NUMBER"):
            self.assertTrue(any(p.fullmatch(lab["value"]) for p in patterns), lab["value"])


class TablesAreSynthetic(unittest.TestCase):
    def test_all_emails_in_sample_files_use_reserved_domains(self):
        for path in DATA.rglob("*"):
            if path.is_file():
                for match in EMAIL_RE.finditer(path.read_text(encoding="utf-8")):
                    self.assertIn(match.group(1), gen.EMAIL_DOMAINS, f"{path.name}: {match.group(0)}")

    def test_donor_edge_cases_sit_at_the_documented_rows(self):
        rows = {r["gift_id"]: r for r in load_csv("donors.csv")}
        self.assertEqual(rows["G-0005"]["anonymous"], "yes")
        self.assertTrue(rows["G-0010"]["tribute"].startswith("in memory of "))
        self.assertTrue(rows["G-0015"]["tribute"].startswith("in honor of "))
        self.assertEqual(rows["G-0020"]["email"], "")
        self.assertEqual(rows["G-0025"]["amount"], "-50.00")
        same = {k: v for k, v in rows["G-0030"].items() if k != "gift_id"}
        self.assertEqual(same, {k: v for k, v in rows["G-0029"].items() if k != "gift_id"})

    def test_each_donor_id_always_maps_to_the_same_name(self):
        seen = {}
        for row in load_csv("donors.csv"):
            name = (row["first_name"], row["last_name"])
            self.assertEqual(seen.setdefault(row["donor_id"], name), name, row["gift_id"])

    def test_participants_have_no_name_or_contact_columns(self):
        columns = set(load_csv("participants.csv")[0])
        self.assertFalse(columns & {"first_name", "last_name", "name", "email", "phone", "street"})

    def test_participant_post_score_blank_only_when_not_completed(self):
        for row in load_csv("participants.csv"):
            self.assertEqual(row["post_score"] == "", row["completed"] == "no", row["participant_id"])


if __name__ == "__main__":
    unittest.main()
