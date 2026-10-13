#!/usr/bin/env python3
"""Run the final guard on synthetic projects with two approved glossaries."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = '''label start:
    voice "voice/intro.ogg"
    e "{b}The Nexus State is unstable, [name].{/b}" nointeract with dissolve
    return
'''
TRANSLATION = '''# game/script.rpy:2
translate schinese intro_001:

    # voice "voice/intro.ogg"
    # e "{b}The Nexus State is unstable, [name].{/b}" nointeract with dissolve
    voice "voice/intro.ogg"
    e "{b}羁绊状态不稳定，[name]。{/b}" nointeract with dissolve

translate schinese strings:

    old "Return to Nexus State"
    new "回到羁绊状态"
'''


class GuardWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.target = self.project / "game/tl/schinese/script.rpy"
        self.target.parent.mkdir(parents=True)
        (self.project / "game/script.rpy").write_text(SOURCE, encoding="utf-8")
        self.guard = Path(__file__).with_name("translation_guard.py").resolve()

    def run_guard(self, translation, profile=None):
        self.target.write_text(translation, encoding="utf-8")
        before = self.target.read_bytes()
        command = [sys.executable, str(self.guard), "game/tl/schinese/script.rpy",
                   "--root", "game", "--warnings-as-errors"]
        if profile:
            command.extend(["--term-profile", profile])
        result = subprocess.run(command, cwd=self.project, capture_output=True,
                                text=True, encoding="utf-8", check=False)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertIn("Translation guard checked 1 file(s).", result.stdout)
        return result

    def test_default_baseline_accepts_its_glossary(self):
        self.assertEqual(self.run_guard(TRANSLATION).returncode, 0)

    def test_default_baseline_keeps_rejecting_its_known_term_mistake(self):
        result = self.run_guard(TRANSLATION.replace("羁绊状态", "枢纽状态"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("nexus_wrong", result.stdout)

    def test_generic_accepts_a_different_approved_glossary(self):
        result = self.run_guard(TRANSLATION.replace("羁绊状态", "枢纽状态"), "generic")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Errors: 0  Warnings: 0", result.stdout)

    def test_both_profiles_reject_protected_material_changes(self):
        mutations = {
            "tag_mismatch": ("{b}羁绊", "羁绊"),
            "interpolation_mismatch": ("，[name]。", "。"),
            "old_changed": ('old "Return to Nexus State"', 'old "回到羁绊状态"'),
            "comment_mismatch": ('# e "{b}The Nexus', '# e "{b}This Nexus'),
            "speaker_changed": ('    e "{b}羁绊', '    h "{b}羁绊'),
            "suffix_changed": ('{/b}" nointeract with dissolve\n\n', '{/b}"\n\n'),
            "voice_changed": ('    voice "voice/intro.ogg"', '    voice "voice/other.ogg"'),
            "block_shape": ('    voice "voice/intro.ogg"\n', ''),
        }
        for profile in ("baseline", "generic"):
            for issue, (old, new) in mutations.items():
                with self.subTest(profile=profile, issue=issue):
                    self.assertIn(old, TRANSLATION)
                    result = self.run_guard(TRANSLATION.replace(old, new), profile)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(issue, result.stdout)

    def test_generic_keeps_english_and_general_text_gates(self):
        for issue, text in (
            ("english_left", "回到 Nexus State"),
            ("english_left", "Return to Nexus State"),
            ("ascii_punctuation", "回到羁绊状态."),
            ("zero_width_space", "回到羁绊\u200b状态"),
        ):
            with self.subTest(issue=issue, text=text):
                result = self.run_guard(TRANSLATION.replace("回到羁绊状态", text), "generic")
                self.assertEqual(result.returncode, 1)
                self.assertIn(issue, result.stdout)


if __name__ == "__main__":
    unittest.main()
