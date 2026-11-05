"""Tests for skills/pii-guard/scripts/scan.py: detectors, and every subcommand's happy and failure paths."""

import contextlib
import csv
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONORS = ROOT / "samples" / "data" / "donors.csv"

_spec = importlib.util.spec_from_file_location("pii_scan", ROOT / "skills" / "pii-guard" / "scripts" / "scan.py")
scan = importlib.util.module_from_spec(_spec)
sys.modules["pii_scan"] = scan  # dataclasses look the module up by name
_spec.loader.exec_module(scan)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = scan.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def types_in(text, **kw):
    return [f.type for f in scan.detect(text, **kw)]


def donor_emails():
    with open(DONORS, encoding="utf-8", newline="") as fh:
        return [r["email"] for r in csv.DictReader(fh) if r["email"]]


class Detectors(unittest.TestCase):
    def test_email_is_detected_and_masked_keeping_only_the_domain(self):
        (f,) = scan.detect("Write to jane.doe@example.org today.")
        self.assertEqual(f.type, "EMAIL")
        self.assertEqual(scan.mask("EMAIL", f.value), "j***@example.org")

    def test_common_us_phone_formats_are_detected(self):
        for phone in ("(212) 555-0147", "212-555-0147", "212.555.0147", "+1 212 555 0147"):
            self.assertEqual(types_in(f"Call {phone} now."), ["PHONE"], phone)

    def test_plain_long_number_without_separators_is_not_a_phone(self):
        self.assertEqual(types_in("Budget line 2125550147 covers postage."), [])

    def test_card_number_passing_luhn_is_detected_in_grouped_form(self):
        self.assertEqual(types_in("Card 4111 1111 1111 1111 declined."), ["CARD"])

    def test_sixteen_digit_order_number_failing_luhn_is_not_a_card(self):
        self.assertFalse(scan.luhn_ok("4111111111111112"))
        self.assertEqual(types_in("Order #4111111111111112 shipped."), [])

    def test_date_is_flagged_only_next_to_a_birth_cue(self):
        self.assertEqual(types_in("DOB: 03/14/1987."), ["DOB"])
        self.assertEqual(types_in("The board meets on 03/14/2027."), [])

    def test_street_address_with_city_state_and_zip_is_one_finding(self):
        (f,) = scan.detect("Mail it to 5130 Fernbrook Ave, Riverton, WY 13495.")
        self.assertEqual((f.type, f.value), ("ADDRESS", "5130 Fernbrook Ave, Riverton, WY 13495"))

    def test_ipv4_and_ipv6_are_detected_but_a_clock_time_is_not(self):
        self.assertEqual(types_in("From 203.0.113.9 and 2001:db8::1 at 9:14."), ["IP", "IP"])

    def test_url_with_long_id_is_flagged_but_public_page_is_not(self):
        self.assertEqual(types_in("See https://portal.example.org/case?id=a1b2c3d4e5f6a7b8."), ["URL_ID"])
        self.assertEqual(types_in("See https://www.example.org/annual-report."), [])

    def test_id_numbers_come_only_from_the_org_patterns(self):
        text = "Case CASE-2026-000123 is open."
        self.assertEqual(types_in(text), [])
        rx = scan.load_id_patterns(str(ROOT / "skills/pii-guard/assets/selftest/id-patterns.json"))
        self.assertEqual(types_in(text, id_res=rx), ["ID_NUMBER"])

    def test_listed_names_match_case_insensitively_as_whole_names(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("# staff\nRowan Ashby\n")
        try:
            names = scan.load_names(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(types_in("rowan ashby called.", names_re=names), ["NAME_LISTED"])
        self.assertEqual(types_in("Rowanberry Ashbyville called.", names_re=names), [])

    def test_name_after_a_cue_is_low_confidence_and_stopwords_are_skipped(self):
        (f,) = scan.detect("Ms. Calloway asked about tutoring.")
        self.assertEqual((f.type, f.value, f.confidence), ("NAME_CUE", "Calloway", "low"))
        self.assertEqual(types_in("Contact Client Services for help."), [])

    def test_each_sensitive_context_family_is_flagged(self):
        samples = {"health": "was hospitalized", "mental_health": "sees a therapist",
                   "immigration": "asylum hearing", "domestic_violence_shelter": "at the shelter",
                   "minors": "her 8-year-old son", "criminal_justice": "on probation",
                   "substance_use": "attends a methadone clinic"}
        for family, phrase in samples.items():
            self.assertIn(family, {h.family for h in scan.detect_context(f"She {phrase}.")}, family)

    def test_redaction_tokens_are_not_detected_as_identifiers(self):
        self.assertEqual(types_in("[EMAIL_1] [NAME_2] [PHONE_3] [FIRST_NAME_4] [ADDRESS_5]"), [])
        self.assertEqual(scan.detect_context("[EMAIL_1] [NAME_2]"), [])


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.private = self.tmp / "private"
        self.private.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path


class ScanCommand(TempDirCase):
    def test_scan_exits_0_when_nothing_is_found_and_says_it_is_not_proof(self):
        code, out, _ = run("scan", self.write("a.txt", "We served 412 households in 2026."))
        self.assertEqual(code, 0)
        self.assertIn("not proof", out)

    def test_scan_exits_1_and_masks_values_by_default(self):
        code, out, _ = run("scan", DONORS)
        self.assertEqual(code, 1)
        for email in donor_emails():
            self.assertNotIn(email, out)
        self.assertIn("AMBER", out)

    def test_scan_reports_csv_findings_by_column_and_flags_identifying_headers(self):
        payload = json.loads(run("scan", DONORS, "--format", "json")[1])
        self.assertEqual(payload["findings"]["EMAIL"]["where"], "email (59)")
        self.assertIn("first_name", payload["identifying_columns"])

    def test_scan_reveal_prints_raw_values_and_warns_on_stderr(self):
        code, out, err = run("scan", self.write("a.txt", "Email pat@example.org"), "--reveal")
        self.assertEqual(code, 1)
        self.assertIn("pat@example.org", out)
        self.assertIn("WARNING", err)

    def test_scan_suggests_red_for_card_numbers_and_sensitive_context(self):
        path = self.write("a.txt", "Card 4111111111111111.\nShe is in recovery.")
        payload = json.loads(run("scan", path, "--format", "json")[1])
        self.assertEqual(payload["suggested_tier"], "red")
        self.assertEqual(set(payload["red_reasons"]), {"CARD", "substance_use"})

    def test_scan_reads_text_from_stdin(self):
        old = sys.stdin
        sys.stdin = io.StringIO("call 212-555-0101")
        try:
            code, out, _ = run("scan", "-")
        finally:
            sys.stdin = old
        self.assertEqual(code, 1)
        self.assertIn("PHONE", out)

    def test_scan_unsupported_file_type_exits_2(self):
        code, _, err = run("scan", self.write("a.docx", "x"))
        self.assertEqual(code, 2)
        self.assertIn("Export", err)

    def test_scan_missing_file_exits_2(self):
        self.assertEqual(run("scan", self.tmp / "missing.txt")[0], 2)

    def test_scan_invalid_id_pattern_exits_2(self):
        bad = self.write("ids.json", json.dumps({"patterns": {"CASE": "CASE-(\\d"}}))
        code, _, err = run("scan", self.write("a.txt", "x"), "--id-patterns", bad)
        self.assertEqual(code, 2)
        self.assertIn("not a valid regular expression", err)

    def test_scan_names_file_with_very_short_entries_exits_2(self):
        names = self.write("names.txt", "Al\nRowan Ashby\n")
        self.assertEqual(run("scan", self.write("a.txt", "x"), "--names", names)[0], 2)


class RedactCommand(TempDirCase):
    def redact(self, src, *extra, out="out.csv"):
        return run("redact", src, "--out", self.tmp / out, "--map", self.private / "map.json", *extra)

    def test_redact_keeps_same_token_for_same_email_across_rows_and_runs(self):
        src = self.write("a.txt", "a@example.org then b@example.org then a@example.org")
        self.assertEqual(self.redact(src, out="1.txt")[0], 0)
        self.assertEqual((self.tmp / "1.txt").read_text(), "[EMAIL_1] then [EMAIL_2] then [EMAIL_1]")
        src2 = self.write("b.txt", "Reply to b@example.org")
        self.assertEqual(self.redact(src2, out="2.txt")[0], 0)
        self.assertEqual((self.tmp / "2.txt").read_text(), "Reply to [EMAIL_2]")

    def test_redact_donor_list_leaves_no_raw_emails_and_masks_name_columns(self):
        code, _, _ = self.redact(DONORS, "--mask-columns", "first_name,last_name")
        self.assertEqual(code, 0)
        body = (self.tmp / "out.csv").read_text()
        for email in donor_emails():
            self.assertNotIn(email, body)
        rows = list(csv.DictReader(io.StringIO(body)))
        self.assertTrue(all(r["first_name"].startswith("[FIRST_NAME_") for r in rows))

    def test_redact_refuses_red_data_and_writes_nothing(self):
        src = self.write("notes.txt", "Client Rowan is on probation. Card 4111111111111111.")
        code, out, _ = self.redact(src, out="o.txt")
        self.assertEqual(code, 1)
        self.assertIn("Redaction refused", out)
        self.assertFalse((self.tmp / "o.txt").exists())
        self.assertFalse((self.private / "map.json").exists())

    def test_redact_proceeds_when_the_red_column_is_dropped(self):
        src = self.write("d.csv", "name,email,notes\nPat,pat@example.org,on probation\n")
        code, _, _ = self.redact(src, "--drop-columns", "notes")
        self.assertEqual(code, 0)
        self.assertEqual((self.tmp / "out.csv").read_text().splitlines()[0], "name,email")

    def test_redact_mapping_file_is_owner_only(self):
        self.redact(self.write("a.txt", "pat@example.org"), out="o.txt")
        mode = stat.S_IMODE((self.private / "map.json").stat().st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o600)

    def test_redact_refuses_mapping_file_inside_a_git_repository(self):
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        code, _, err = run("redact", self.write("a.txt", "pat@example.org"), "--out", self.tmp / "o.txt",
                           "--map", repo / "map.json")
        self.assertEqual(code, 2)
        self.assertIn("git repository", err)

    def test_redact_refuses_synced_folder_unless_allowed_and_then_warns(self):
        synced = self.tmp / "Dropbox" / "map.json"
        src = self.write("a.txt", "pat@example.org")
        self.assertEqual(run("redact", src, "--out", self.tmp / "o.txt", "--map", synced)[0], 2)
        code, _, err = run("redact", src, "--out", self.tmp / "o.txt", "--map", synced, "--allow-synced")
        self.assertEqual(code, 0)
        self.assertIn("WARNING", err)

    def test_redact_will_not_overwrite_the_input_or_an_existing_output(self):
        src = self.write("a.txt", "pat@example.org")
        self.assertEqual(run("redact", src, "--out", src, "--map", self.private / "m.json")[0], 2)
        self.write("exists.txt", "x")
        self.assertEqual(self.redact(src, out="exists.txt")[0], 2)

    def test_redact_keep_leaves_the_chosen_type_in_place(self):
        src = self.write("a.txt", "pat@example.org, 212-555-0101")
        self.assertEqual(self.redact(src, "--keep", "PHONE", out="o.txt")[0], 0)
        self.assertEqual((self.tmp / "o.txt").read_text(), "[EMAIL_1], 212-555-0101")

    def test_redact_unknown_column_or_type_exits_2(self):
        self.assertEqual(self.redact(DONORS, "--drop-columns", "nope")[0], 2)
        self.assertEqual(self.redact(DONORS, "--keep", "SSN")[0], 2)

    def test_mapping_file_changed_since_read_is_not_overwritten(self):
        path = self.private / "map.json"
        self.redact(self.write("a.txt", "pat@example.org"), out="o.txt")
        mapping = scan.MappingFile(path)
        mapping.token_for("EMAIL", "new@example.org")
        path.write_text(path.read_text().replace("pat@", "pt@"))
        with self.assertRaises(scan.InputError):
            mapping.save()


class VerifyCommand(TempDirCase):
    def test_verify_passes_on_a_redacted_copy(self):
        run("redact", DONORS, "--out", self.tmp / "r.csv", "--map", self.private / "m.json")
        code, out, _ = run("verify", self.tmp / "r.csv")
        self.assertEqual(code, 0)
        self.assertIn("not an anonymized one", out)

    def test_verify_fails_when_an_identifier_is_left(self):
        code, out, _ = run("verify", self.write("a.txt", "[EMAIL_1] and 212-555-0101"))
        self.assertEqual(code, 1)
        self.assertIn("PHONE 1", out)

    def test_verify_fails_when_red_context_is_present(self):
        self.assertEqual(run("verify", self.write("a.txt", "[NAME_1] is on parole."))[0], 1)

    def test_verify_low_confidence_names_warn_but_fail_only_with_strict(self):
        path = self.write("a.txt", "Ms. Calloway called [PHONE_1].")
        self.assertEqual(run("verify", path)[0], 0)
        self.assertEqual(run("verify", path, "--strict")[0], 1)

    def test_verify_missing_file_exits_2(self):
        self.assertEqual(run("verify", self.tmp / "nope.csv")[0], 2)


class RestoreCommand(TempDirCase):
    def test_restore_puts_original_values_back_and_never_prints_them(self):
        run("redact", self.write("a.txt", "pat@example.org"), "--out", self.tmp / "r.txt",
            "--map", self.private / "m.json")
        draft = self.write("draft.md", "Thanks [EMAIL_1]!")
        code, out, _ = run("restore", draft, "--map", self.private / "m.json", "--out", self.private / "f.md")
        self.assertEqual(code, 0)
        self.assertEqual((self.private / "f.md").read_text(), "Thanks pat@example.org!")
        self.assertNotIn("pat@example.org", out)

    def test_restore_reports_unknown_tokens_with_exit_1(self):
        run("redact", self.write("a.txt", "pat@example.org"), "--out", self.tmp / "r.txt",
            "--map", self.private / "m.json")
        draft = self.write("draft.md", "[EMAIL_1] [EMAIL_9]")
        code, out, _ = run("restore", draft, "--map", self.private / "m.json", "--out", self.private / "f.md")
        self.assertEqual(code, 1)
        self.assertIn("[EMAIL_9]", out)

    def test_restore_missing_mapping_file_exits_2(self):
        code, _, _ = run("restore", self.write("d.md", "x"), "--map", self.tmp / "none.json",
                         "--out", self.private / "f.md")
        self.assertEqual(code, 2)

    def test_restore_refuses_to_write_into_a_git_repository(self):
        run("redact", self.write("a.txt", "pat@example.org"), "--out", self.tmp / "r.txt",
            "--map", self.private / "m.json")
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        code, _, _ = run("restore", self.write("d.md", "[EMAIL_1]"), "--map", self.private / "m.json",
                         "--out", repo / "f.md")
        self.assertEqual(code, 2)


class SelftestCommand(TempDirCase):
    def test_selftest_meets_the_recall_target_on_the_bundled_corpus(self):
        code, out, _ = run("selftest", "--format", "json")
        self.assertEqual(code, 0)
        result = json.loads(out)["corpus"]["detectors"]
        for ftype in scan.RECALL_TARGET_TYPES:
            self.assertGreaterEqual(result[ftype]["recall"], scan.RECALL_TARGET, ftype)

    def test_selftest_exits_1_when_a_recall_target_is_missed(self):
        rec = {"text": "write to pat at example dot org", "context_families": [],
               "labels": [{"type": "EMAIL", "start": 9, "end": 31, "value": "pat at example dot org"}]}
        corpus = self.write("c.jsonl", json.dumps(rec) + "\n")
        code, out, _ = run("selftest", "--corpus", corpus, "--holdout", "")
        self.assertEqual(code, 1)
        self.assertIn("MISSED for EMAIL", out)

    def test_selftest_missing_corpus_exits_2(self):
        self.assertEqual(run("selftest", "--corpus", self.tmp / "none.jsonl")[0], 2)

    def test_holdout_markup_becomes_exact_spans(self):
        (rec,) = scan.parse_holdout("Call {{PHONE|212 555 0101}} now ## context=health")
        self.assertEqual(rec["text"], "Call 212 555 0101 now")
        lab = rec["labels"][0]
        self.assertEqual(rec["text"][lab["start"]:lab["end"]], "212 555 0101")
        self.assertEqual(rec["context_families"], ["health"])


class Cli(unittest.TestCase):
    def test_help_documents_the_exit_codes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            scan.main(["--help"])
        self.assertIn("Exit codes", out.getvalue())

    def test_missing_subcommand_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            scan.main([])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
