#!/usr/bin/env python3
"""Exercise the publication checks with synthetic working trees only."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from check_resources import check_repository, heading_anchors, link_findings, privacy_findings


class PrivacyTests(unittest.TestCase):
    def test_flags_high_confidence_markers_without_echoing_the_value(self):
        samples = {
            "absolute-home-path": "/" + "Users/person/private/file.md",
            "private-key": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
            "provider-token": "ghp_" + "a" * 36,
            "literal-credential": 'app_secret = "' + "x" * 24 + '"',
            "signed-or-authenticated-url": "https://example.com/file?token=" + "x" * 24,
            "non-example-email": "person@" + "mail.invalid",
        }
        for rule, value in samples.items():
            with self.subTest(rule=rule):
                findings = privacy_findings("sample.md", "safe\n" + value)
                self.assertTrue(any(f.rule == rule and f.line == 2 for f in findings))
                self.assertNotIn(value, "\n".join(map(str, findings)))

    def test_windows_paths_and_url_credentials(self):
        path = "C:" + "\\Users\\person\\private.txt"
        url = "https://user:" + "password@example.com/page"
        self.assertEqual(privacy_findings("sample.txt", path)[0].rule, "absolute-home-path")
        self.assertIn("signed-or-authenticated-url", {f.rule for f in privacy_findings("sample.md", url)})

    def test_examples_and_technical_references_are_allowed(self):
        text = '\n'.join([
            "author@example.com user@docs.example.org fake@example.invalid",
            "https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/lib/src/parser.c",
            "https://open.feishu.cn/api/tools/open/api_definition?protocol=meta",
            'api_key = "<runtime-value>"',
            "func.func @f(%arg0 : i32) { return }",
        ])
        self.assertEqual(privacy_findings("sample.md", text), [])


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.file = self.root / "SKILL.md"
        (self.root / "references").mkdir()
        (self.root / "references/rules.md").write_text("# Rules\n\n## Two steps\n", encoding="utf-8")

    def check(self, text):
        return link_findings(self.root, self.file, text)

    def test_inline_reference_and_fragment_links(self):
        self.assertEqual(self.check(
            "[rules](references/rules.md#two-steps)\n"
            "[rules][r]\n[r]: <references/rules.md#rules>\n"
            "[web](https://example.com/anywhere#unverified)\n"), [])

    def test_missing_file_and_anchor_report_the_source_line(self):
        findings = self.check("ok\n[x](missing.md)\n[x](references/rules.md#missing)\n")
        self.assertEqual([(f.line, f.rule) for f in findings],
                         [(2, "missing-local-link"), (3, "missing-local-anchor")])

    def test_code_samples_do_not_require_real_targets(self):
        self.assertEqual(self.check(
            "```md\n[example](not-created.md)\n```\n"
            "~~~md\n[example](not-created.md)\n~~~\n"
            "`[example](not-created.md)`\n"), [])

    def test_escaping_the_repository_and_absolute_paths_are_rejected(self):
        findings = self.check("[x](../elsewhere.md)\n[x](/tmp/a.md)\n[x](file:///tmp/b.md)\n")
        self.assertEqual([f.rule for f in findings],
                         ["link-outside-repository", "absolute-local-link", "nonportable-file-link"])

    def test_encoded_paths_spaces_and_unicode_anchors(self):
        (self.root / "references/中文 rules.md").write_text("# 中文规则\n", encoding="utf-8")
        self.assertEqual(self.check("[x](<references/中文%20rules.md#中文规则>)"), [])

    def test_duplicate_and_code_formatted_heading_anchors(self):
        self.assertEqual(heading_anchors("## `tool` rules\n## `tool` rules\n```\n## hidden\n```\n"),
                         {"tool-rules", "tool-rules-1"})

    def test_parentheses_and_escaped_parentheses_in_link_destinations(self):
        target = self.root / "references/rules(offline).md"
        target.write_text("# Rules\n", encoding="utf-8")
        self.assertEqual(self.check(
            "[rules](references/rules(offline).md)\n"
            "[rules](references/rules\\(offline\\).md \"offline rules\")\n"), [])
        target.unlink()
        self.assertEqual([f.rule for f in self.check(
            "[rules](references/rules(offline).md)")], ["missing-local-link"])

    def test_heading_links_use_visible_text_and_duplicate_slugs_avoid_collisions(self):
        (self.root / "references/rules.md").write_text(
            "## [Visible title](https://example.com)\n"
            "## foo\n## foo-1\n## foo\n", encoding="utf-8")
        self.assertEqual(self.check(
            "[x](references/rules.md#visible-title)\n"
            "[x](references/rules.md#foo-2)\n"), [])

    def test_code_angle_brackets_and_setext_headings(self):
        (self.root / "references/rules.md").write_text(
            "## Use `list<T>`\n\n"
            "Setext title\n============\n\n"
            "Another\nmultiline title\n---------------\n", encoding="utf-8")
        self.assertEqual(self.check(
            "[x](references/rules.md#use-listt)\n"
            "[x](references/rules.md#setext-title)\n"
            "[x](references/rules.md#another-multiline-title)\n"), [])


class WorkingTreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text("private/\n", encoding="utf-8")
        (self.root / "private").mkdir()
        (self.root / "private/notes.md").write_text("person@" + "mail.invalid", encoding="utf-8")
        self.skill = self.root / "skills/sample"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# Sample\n", encoding="utf-8")

    def test_missing_validation_is_a_failure_then_a_nonempty_file_resolves_it(self):
        self.assertEqual([f.rule for f in check_repository(self.root)], ["missing-validation-cases"])
        (self.skill / "references").mkdir()
        validation = self.skill / "references/validation.md"
        validation.write_text("  \n", encoding="utf-8")
        self.assertEqual([f.rule for f in check_repository(self.root)], ["missing-validation-cases"])
        validation.write_text("# Validation\nA representative case.\n", encoding="utf-8")
        self.assertEqual(check_repository(self.root), [])

    def test_tracked_ignored_files_still_scanned_and_deleted_files_skipped(self):
        subprocess.run(["git", "add", "-f", "private/notes.md"], cwd=self.root, check=True)
        findings = check_repository(self.root)
        self.assertIn("non-example-email", {f.rule for f in findings})
        (self.root / "private/notes.md").unlink()
        self.assertNotIn("non-example-email", {f.rule for f in check_repository(self.root)})

    def test_cli_exit_status_and_diagnostic_redaction(self):
        value = "ghp_" + "z" * 36
        (self.root / "leak.md").write_text(value, encoding="utf-8")
        (self.root / "leak.PEM").write_text("-----BEGIN " + "PRIVATE KEY-----", encoding="utf-8")
        script = Path(__file__).with_name("check_resources.py")
        result = subprocess.run([sys.executable, str(script), "--root", str(self.root)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("leak.md:1: provider-token", result.stderr)
        self.assertIn("leak.PEM:1: private-key", result.stderr)
        self.assertNotIn(value, result.stdout + result.stderr)
        outside = subprocess.run([sys.executable, str(script), "--root", str(self.root / "private")],
                                 capture_output=True, text=True, check=False)
        # Git resolves to the parent worktree; this subdirectory must not be treated as its root.
        self.assertEqual(outside.returncode, 2)


if __name__ == "__main__":
    unittest.main()
