#!/usr/bin/env python3
"""Regression tests for fix_terms.py. Standard library only.

The imported copy ran every TERM_FIXES pattern against the original line, so
only the last matching pattern survived and the printed count also counted the
discarded matches. These tests pin the cumulative behaviour, the immunity of
reference comments and control lines, and the no-op second run.

Run from anywhere:  python3 scripts/test_fix_terms.py
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fix_terms  # noqa: E402


TRANSLATION = """\
# game/script.rpy:2
translate schinese start_abc:
    # h "Haelo said Elie to Guardians"
    h "哈罗和埃利是监护人，伴游在陪护。"
    old "哈罗 must stay English"
    voice "voice/line1.ogg"
"""

FIXED_LINE = 'h "海洛和艾利是守护者，陪侍在陪侍。"'


class FixTermsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "script.rpy")
        self.write(TRANSLATION)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self):
        with open(self.path, encoding="utf-8") as handle:
            return handle.read()

    def fix(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return fix_terms.fix_file(self.path)

    def test_one_pass_fixes_every_term_on_a_line(self):
        changes = self.fix()
        self.assertEqual(changes, 5)
        self.assertIn(FIXED_LINE, self.read())

    def test_reference_and_control_lines_are_untouched(self):
        self.fix()
        text = self.read()
        self.assertIn('# h "Haelo said Elie to Guardians"', text)
        self.assertIn('old "哈罗 must stay English"', text)
        self.assertIn('voice "voice/line1.ogg"', text)
        self.assertIn("translate schinese start_abc:", text)

    def test_string_table_new_line_is_fixed(self):
        self.write("translate schinese strings:\n    old \"Haelo\"\n    new \"哈罗\"\n")
        self.assertEqual(self.fix(), 1)
        self.assertIn('new "海洛"', self.read())
        self.assertIn('old "Haelo"', self.read())

    def test_second_run_is_a_no_op(self):
        self.fix()
        after_first = self.read()
        self.assertEqual(self.fix(), 0)
        self.assertEqual(self.read(), after_first)


if __name__ == "__main__":
    unittest.main()
