"""Structure checks for every built skill (any skills/<name>/SKILL.md), against spec §3.1 and §3.5.

Mirrors skill-creator's quick_validate.py rules (allowed frontmatter keys, name and description
limits) without needing PyYAML, plus the pack's own standards S1-S5 and the eval case format.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
EVAL_MIN_CASES = {"grant-scout": 10}
EVAL_MIN_DEFAULT = 8


def built_skills():
    return sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))


def frontmatter(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError(f"{skill_md}: no frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(": ")
        if not sep or line.startswith(" "):
            raise AssertionError(f"{skill_md}: keep frontmatter to one 'key: value' per line: {line!r}")
        fields[key] = value
    return fields


class SkillStructure(unittest.TestCase):
    def test_at_least_one_skill_is_built(self):
        self.assertTrue(built_skills())

    def test_frontmatter_has_name_description_compatibility_and_nothing_else(self):  # S1
        for skill in built_skills():
            fields = frontmatter(skill / "SKILL.md")
            self.assertLessEqual(set(fields), ALLOWED_KEYS, skill.name)
            for key in ("name", "description", "compatibility"):
                self.assertTrue(fields.get(key), f"{skill.name}: missing {key}")
            self.assertEqual(fields["name"], skill.name)
            self.assertRegex(fields["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertLessEqual(len(fields["name"]), 64)
            self.assertLessEqual(len(fields["compatibility"]), 500)

    def test_frontmatter_values_are_safe_plain_yaml(self):
        for skill in built_skills():
            for key, value in frontmatter(skill / "SKILL.md").items():
                self.assertNotIn(": ", value, f"{skill.name}.{key}: ': ' breaks plain YAML")
                self.assertNotRegex(value, r"^[\[{>|*&!%@`'\"#]", f"{skill.name}.{key}")

    def test_description_pitch_fits_in_500_chars_with_use_for_and_not_for(self):  # S2
        for skill in built_skills():
            desc = frontmatter(skill / "SKILL.md")["description"]
            self.assertLessEqual(len(desc), 1024)
            self.assertNotRegex(desc, r"[<>]")
            head = desc[:500]
            self.assertRegex(head, r"\bUse (?:for|before|when)\b", skill.name)
            self.assertIn("even", head, f"{skill.name}: add the 'even one piece / even if' push")
            self.assertRegex(head, r"\bNot (?:for|legal|tax|a)\b", f"{skill.name}: needs a 'Not ...' clause")

    def test_skill_md_is_a_router_under_500_lines(self):  # S3
        for skill in built_skills():
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertLess(text.count("\n"), 500, skill.name)
            for heading in ("## How to work", "## The steps", "## Scripts", "## Connectors",
                            "## Boundaries", "## When this goes wrong", "## Reference files",
                            "## Opening message"):
                self.assertIn(heading, text, f"{skill.name}: missing {heading}")

    def test_exactly_one_skill_md_per_skill(self):
        for skill in built_skills():
            self.assertEqual(len(list(skill.rglob("SKILL.md"))), 1, skill.name)

    def test_every_reference_is_indexed_says_when_to_read_and_has_contents_if_long(self):  # S4
        for skill in built_skills():
            router = (skill / "SKILL.md").read_text(encoding="utf-8")
            for ref in sorted((skill / "references").glob("*.md")):
                text = ref.read_text(encoding="utf-8")
                self.assertIn(f"references/{ref.name}", router, f"{skill.name}: {ref.name} not indexed")
                self.assertIn("Read this", text[:800], f"{ref.name}: say when to read it")
                if text.count("\n") > 300:
                    self.assertIn("## Contents", text, f"{ref.name}: over 300 lines needs contents")
            for mentioned in set(re.findall(r"references/([\w.-]+\.md)", router)):
                self.assertTrue((skill / "references" / mentioned).is_file(), f"{skill.name}: {mentioned}")

    def test_no_walls_of_capitalized_musts(self):  # S5
        for skill in built_skills():
            for md in [skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]:
                text = md.read_text(encoding="utf-8")
                self.assertEqual(len(re.findall(r"\bMUST\b", text)), 0, md.name)
                self.assertLessEqual(len(re.findall(r"\b(?:ALWAYS|NEVER)\b", text)), 2, md.name)

    def test_every_script_has_a_unit_test_file(self):  # T1
        for skill in built_skills():
            for script in sorted((skill / "scripts").glob("*.py")):
                expected = ROOT / "tests" / f"test_{skill.name.replace('-', '_')}_{script.stem}.py"
                self.assertTrue(expected.is_file(), f"missing {expected.relative_to(ROOT)}")

    def test_skill_has_a_state_template_with_shared_fields(self):  # W6, spec 4.2
        import json
        for skill in built_skills():
            state = json.loads((skill / "assets" / "state-template.json").read_text(encoding="utf-8"))
            for key in ("schema_version", "created_with", "last_updated", "org", "progress", "change_log"):
                self.assertIn(key, state, f"{skill.name}: state template missing {key}")


class EvalCases(unittest.TestCase):
    def cases(self, skill):
        return sorted(p for p in (ROOT / "evals" / skill.name).glob("*") if p.is_dir())

    def test_each_skill_has_enough_cases_of_each_kind(self):  # E2
        for skill in built_skills():
            cases = self.cases(skill)
            self.assertGreaterEqual(len(cases), EVAL_MIN_CASES.get(skill.name, EVAL_MIN_DEFAULT), skill.name)
            kinds = [re.search(r"^tags: \[(\w+)", (c / "prompt.md").read_text(encoding="utf-8"), re.M).group(1)
                     for c in cases]
            self.assertGreaterEqual(kinds.count("happy"), 3, skill.name)
            self.assertGreaterEqual(kinds.count("boundary"), 3, skill.name)
            self.assertGreaterEqual(kinds.count("trap"), 2, skill.name)

    def test_each_case_follows_the_folder_format(self):  # E1, E3
        for skill in built_skills():
            for case in self.cases(skill):
                prompt = (case / "prompt.md").read_text(encoding="utf-8")
                self.assertTrue(prompt.startswith("---\n"), case.name)
                front = prompt.split("---\n")[1]
                for line in front.splitlines() + [l for g in (case / "graders").glob("*.md")
                                                  for l in g.read_text(encoding="utf-8").split("---\n")[1].splitlines()]:
                    key, _, value = line.partition(": ")
                    self.assertTrue(value.strip(), f"{case.name}: empty YAML value in {line!r}")
                    if not value.startswith(('"', "'", "[", "{")):
                        self.assertNotIn(": ", value, f"{case.name}: unquoted ': ' in {line!r}")
                graders = sorted((case / "graders").glob("*.md"))
                self.assertTrue(graders, f"{case.name}: no graders")
                for grader in graders:
                    pat = re.search(r"^pattern: '(.*)'$", grader.read_text(encoding="utf-8"), re.M)
                    if pat:
                        re.compile(pat.group(1))
                        self.assertNotIn("\\\\", pat.group(1), f"{grader}: double backslash in single-quoted YAML")
                    self.assertRegex(grader.name, r"^\d\d-[a-z0-9-]+\.md$", grader.name)
                    self.assertRegex(grader.read_text(encoding="utf-8"), r"^---\ntype: \w+", grader.name)
                if (case / "place-files.sh").exists() or (case / "case.yaml").exists():
                    self.assertTrue((case / "files").is_dir(), f"{case.name}: setup script but no files/ to copy")
                if (case / "files").is_dir():
                    case_yaml = (case / "case.yaml").read_text(encoding="utf-8")
                    self.assertIn('schema_version: "1.1"', case_yaml, case.name)
                    self.assertIn("scaffold_script: place-files.sh", case_yaml, case.name)
                    self.assertTrue((case / "place-files.sh").is_file(), case.name)


if __name__ == "__main__":
    unittest.main()
