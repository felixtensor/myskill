#!/usr/bin/env python3
"""Regression tests for probe.py. Standard library only; no tree-sitter needed.

The CLI output below was captured from tree-sitter 0.27.0 on tree-sitter-mlir,
so a change in the CLI's output format shows up here before it corrupts an
audit. The invariants under test are the shipped ones in
assets/invariants/mlir.json, not copies.

Run from anywhere:  python3 scripts/test_probe.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import probe  # noqa: E402

SPEC = probe.load_spec(os.path.join(HERE, "..", "assets", "invariants", "mlir.json"))
INVARIANTS = {inv["id"]: inv for inv in SPEC["invariants"]}
SKIP = re.compile(SPEC["skip_line"])

GOOD_SRC = '%c = "test.c"() : () -> i32\n'
GOOD_TREE = """\
(toplevel [0, 0] - [1, 0]
  (operation [0, 0] - [0, 27]
    lhs: (op_result [0, 0] - [0, 2]
      (value_use [0, 0] - [0, 2]))
    rhs: (generic_operation [0, 5] - [0, 27]
      (string_literal [0, 5] - [0, 13])
      (function_type [0, 18] - [0, 27]
        (type [0, 24] - [0, 27]
          (builtin_type [0, 24] - [0, 27]
            (integer_type [0, 24] - [0, 27])))))))"""

# Missing its closing brace. The MISSING "}" is anonymous, so the tree does not
# show it; only the summary line after the tree does.
UNCLOSED_SRC = """\
func.func @g() {
  %0 = "test.a"() : () -> i32
  %1 = "test.b"() : () -> i32
  return
"""
UNCLOSED_TREE = """\
(toplevel [0, 0] - [4, 0]
  (operation [0, 0] - [3, 8]
    rhs: (custom_operation [0, 0] - [3, 8]
      (func_operation [0, 0] - [3, 8]
        sym_name: (symbol_ref_id [0, 10] - [0, 12])
        arguments: (func_arg_list [0, 12] - [0, 14])
        body: (region [0, 15] - [3, 8]
          (entry_block [1, 2] - [3, 8]
            (operation [1, 2] - [1, 29]
              lhs: (op_result [1, 2] - [1, 4]
                (value_use [1, 2] - [1, 4]))
              rhs: (generic_operation [1, 7] - [1, 29]
                (string_literal [1, 7] - [1, 15])
                (function_type [1, 20] - [1, 29]
                  (type [1, 26] - [1, 29]
                    (builtin_type [1, 26] - [1, 29]
                      (integer_type [1, 26] - [1, 29]))))))
            (operation [2, 2] - [2, 29]
              lhs: (op_result [2, 2] - [2, 4]
                (value_use [2, 2] - [2, 4]))
              rhs: (generic_operation [2, 7] - [2, 29]
                (string_literal [2, 7] - [2, 15])
                (function_type [2, 20] - [2, 29]
                  (type [2, 26] - [2, 29]
                    (builtin_type [2, 26] - [2, 29]
                      (integer_type [2, 26] - [2, 29]))))))
            (operation [3, 2] - [3, 8]
              rhs: (custom_operation [3, 2] - [3, 8]
                name: (custom_op_name [3, 2] - [3, 8])))))))))"""
UNCLOSED_SUMMARY = ('/x/unclosed.mlir  \tParse:    1.33 ms\t    64 bytes/ms\t'
                    '(MISSING "}" [3, 8] - [3, 8])')

NAMED_SRC = '%a, %b = "test.op"() : () -> (i32, i32)\n'
NAMED_TREE = """\
(toplevel [0, 0] - [1, 0]
  (operation [0, 0] - [0, 39]
    lhs: (op_result [0, 0] - [0, 2]
      (value_use [0, 0] - [0, 2]))
    lhs: (op_result [0, 4] - [0, 6]
      (value_use [0, 4] - [0, 6]))
    rhs: (generic_operation [0, 9] - [0, 39]
      (string_literal [0, 9] - [0, 18])
      (function_type [0, 23] - [0, 39]
        (type [0, 30] - [0, 33]
          (builtin_type [0, 30] - [0, 33]
            (integer_type [0, 30] - [0, 33])))
        (type [0, 35] - [0, 38]
          (builtin_type [0, 35] - [0, 38]
            (integer_type [0, 35] - [0, 38])))))))"""

# How MLIR's generic printer spells NAMED_SRC.
GROUPED_SRC = '%0:2 = "test.op"() : () -> (i32, i32)\n'
GROUPED_TREE = """\
(toplevel [0, 0] - [1, 0]
  (operation [0, 0] - [0, 37]
    lhs: (op_result [0, 0] - [0, 4]
      (value_use [0, 0] - [0, 4]))
    rhs: (generic_operation [0, 7] - [0, 37]
      (string_literal [0, 7] - [0, 16])
      (function_type [0, 21] - [0, 37]
        (type [0, 28] - [0, 31]
          (builtin_type [0, 28] - [0, 31]
            (integer_type [0, 28] - [0, 31])))
        (type [0, 33] - [0, 36]
          (builtin_type [0, 33] - [0, 36]
            (integer_type [0, 33] - [0, 36])))))))"""

# The open result-binding defect: the first body takes `%res` and the `=`.
LOST_SRC = """\
%cst0 = arith.constant 0 : i32
%res = arith.addi %cst0, %arg0 : i32
"""
LOST_TREE = """\
(toplevel [0, 0] - [2, 0]
  (operation [0, 0] - [1, 6]
    lhs: (op_result [0, 0] - [0, 5]
      (value_use [0, 0] - [0, 5]))
    rhs: (custom_operation [0, 8] - [1, 6]
      name: (custom_op_name [0, 8] - [0, 22])
      (integer_literal [0, 23] - [0, 24])
      (type [0, 27] - [0, 30]
        (builtin_type [0, 27] - [0, 30]
          (integer_type [0, 27] - [0, 30])))
      (value_use [1, 0] - [1, 4])))
  (operation [1, 7] - [1, 36]
    rhs: (custom_operation [1, 7] - [1, 36]
      name: (custom_op_name [1, 7] - [1, 17])
      (value_use [1, 18] - [1, 23])
      (value_use [1, 25] - [1, 30])
      (type [1, 33] - [1, 36]
        (builtin_type [1, 33] - [1, 36]
          (integer_type [1, 33] - [1, 36]))))))"""

# The same defect after a region closes -- invisible while nodes holding a
# region were exempted from the boundary check outright.
AFTER_REGION_SRC = """\
%0 = scf.execute_region -> i32 {
  scf.yield %c : i32
}
%1 = arith.addi %0, %0 : i32
"""
AFTER_REGION_TREE = """\
(toplevel [0, 0] - [4, 0]
  (operation [0, 0] - [3, 4]
    lhs: (op_result [0, 0] - [0, 2]
      (value_use [0, 0] - [0, 2]))
    rhs: (custom_operation [0, 5] - [3, 4]
      name: (custom_op_name [0, 5] - [0, 23])
      (type [0, 27] - [0, 30]
        (builtin_type [0, 27] - [0, 30]
          (integer_type [0, 27] - [0, 30])))
      (region [0, 31] - [2, 1]
        (entry_block [1, 2] - [1, 20]
          (operation [1, 2] - [1, 20]
            rhs: (custom_operation [1, 2] - [1, 20]
              name: (custom_op_name [1, 2] - [1, 11])
              (value_use [1, 12] - [1, 14])
              (type [1, 17] - [1, 20]
                (builtin_type [1, 17] - [1, 20]
                  (integer_type [1, 17] - [1, 20])))))))
      (value_use [3, 0] - [3, 2])))
  (operation [3, 5] - [3, 28]
    rhs: (custom_operation [3, 5] - [3, 28]
      name: (custom_op_name [3, 5] - [3, 15])
      (value_use [3, 16] - [3, 18])
      (value_use [3, 20] - [3, 22])
      (type [3, 25] - [3, 28]
        (builtin_type [3, 25] - [3, 28]
          (integer_type [3, 25] - [3, 28]))))))"""

# Correct code: a header wrapped across lines starts a line with `%b = %y`.
WRAPPED_SRC = """\
%r:2 = scf.for %i = %lb to %ub step %s iter_args(%a = %x,
    %b = %y) -> (f32, f32) {
  scf.yield %a, %b : f32, f32
}
"""
WRAPPED_TREE = """\
(toplevel [0, 0] - [4, 0]
  (operation [0, 0] - [3, 1]
    lhs: (op_result [0, 0] - [0, 4]
      (value_use [0, 0] - [0, 4]))
    rhs: (custom_operation [0, 7] - [3, 1]
      name: (custom_op_name [0, 7] - [0, 14])
      (value_use [0, 15] - [0, 17])
      (value_use [0, 20] - [0, 23])
      (bare_id [0, 24] - [0, 26])
      (value_use [0, 27] - [0, 30])
      (bare_id [0, 31] - [0, 35])
      (value_use [0, 36] - [0, 38])
      (bare_id [0, 39] - [0, 48])
      (value_use [0, 49] - [0, 51])
      (value_use [0, 54] - [0, 56])
      (value_use [1, 4] - [1, 6])
      (value_use [1, 9] - [1, 11])
      (type [1, 17] - [1, 20]
        (builtin_type [1, 17] - [1, 20]
          (float_type [1, 17] - [1, 20])))
      (type [1, 22] - [1, 25]
        (builtin_type [1, 22] - [1, 25]
          (float_type [1, 22] - [1, 25])))
      (region [1, 27] - [3, 1]
        (entry_block [2, 2] - [2, 29]
          (operation [2, 2] - [2, 29]
            rhs: (custom_operation [2, 2] - [2, 29]
              name: (custom_op_name [2, 2] - [2, 11])
              (value_use [2, 12] - [2, 14])
              (value_use [2, 16] - [2, 18])
              (type [2, 21] - [2, 24]
                (builtin_type [2, 21] - [2, 24]
                  (float_type [2, 21] - [2, 24])))
              (type [2, 26] - [2, 29]
                (builtin_type [2, 26] - [2, 29]
                  (float_type [2, 26] - [2, 29]))))))))))"""


def tree_of(text):
    tree = probe.parse_sexp(text)
    assert tree is not None
    return tree


def run(check_id, tree, src):
    inv = INVARIANTS[check_id]
    return probe.CHECKS[inv["kind"]](inv, tree, probe.scrub_lines(src, SKIP))


def count(tree, type_):
    return sum(1 for n in tree.walk() if n.type == type_)


class ParseOutput(unittest.TestCase):
    FILES = ["/x/good.mlir", "/x/unclosed.mlir", "/x/grouped.mlir"]
    STDOUT = "\n".join([GOOD_TREE, UNCLOSED_TREE, UNCLOSED_SUMMARY, GROUPED_TREE]) + "\n"

    def test_an_error_summary_does_not_replace_the_tree(self):
        pairs = probe.split_parse_output(self.STDOUT, self.FILES)
        self.assertEqual([path for path, _ in pairs], self.FILES)
        tree = pairs[1][1]
        self.assertEqual(tree.type, "toplevel")
        self.assertEqual(count(tree, "op_result"), 2)
        [missing] = [n for n in tree.walk() if n.type == "MISSING"]
        self.assertEqual((missing.start, missing.detail), ((3, 8), '"}"'))

    def test_a_file_with_an_error_gets_no_false_hits(self):
        tree = probe.split_parse_output(self.STDOUT, self.FILES)[1][1]
        self.assertEqual(run("op-result-binding", tree, UNCLOSED_SRC), [])
        self.assertEqual(run("no-error-node", tree, UNCLOSED_SRC),
                         [(4, 'MISSING "}": return')])

    def test_an_error_the_tree_already_shows_is_not_added_twice(self):
        stdout = ("(toplevel [0, 0] - [2, 0]\n  (ERROR [1, 2] - [1, 13]))\n"
                  "/x/u.mlir\tParse:    0.06 ms\t   598 bytes/ms\t"
                  "(ERROR [1, 2] - [1, 13])\n")
        [(_, tree)] = probe.split_parse_output(stdout, ["/x/u.mlir"])
        self.assertEqual(count(tree, "ERROR"), 1)

    def test_a_summary_naming_another_file_is_refused(self):
        with self.assertRaises(SystemExit):
            probe.split_parse_output(GOOD_TREE + "\n" + UNCLOSED_SUMMARY, ["/x/good.mlir"])

    def test_an_unrecognised_line_is_refused(self):
        with self.assertRaises(SystemExit):
            probe.split_parse_output(GOOD_TREE + "\nsomething a later CLI prints\n",
                                     ["/x/good.mlir"])

    def test_two_trees_read_as_one_are_refused(self):
        with self.assertRaises(SystemExit):
            probe.parse_sexp(GOOD_TREE + "\n" + GROUPED_TREE)

    def test_a_quoted_parenthesis_stays_a_token(self):
        tree = tree_of("(toplevel [0, 0] - [1, 0]\n  (ERROR [0, 0] - [0, 1]\n"
                       "    (UNEXPECTED '(' [0, 0] - [0, 1])))")
        [error] = tree.children
        [unexpected] = error.children
        self.assertEqual((unexpected.type, unexpected.detail), ("UNEXPECTED", "'('"))
        self.assertEqual(unexpected.children, [])


class Skeleton(unittest.TestCase):
    def test_a_result_group_counts_as_its_size(self):
        [entry] = [e for e in SPEC["normalizer"]["counts"] if e["node"] == "op_result"]
        named = probe.measure(tree_of(NAMED_TREE), entry, NAMED_SRC.encode().split(b"\n"))
        grouped = probe.measure(tree_of(GROUPED_TREE), entry,
                                GROUPED_SRC.encode().split(b"\n"))
        self.assertEqual((named, grouped), (2, 2))
        # The plain node count is what reported "grammar counts more" here.
        self.assertEqual((count(tree_of(NAMED_TREE), "op_result"),
                          count(tree_of(GROUPED_TREE), "op_result")), (2, 1))

    def report(self, entry, rows):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            flagged = probe.report_counts(entry, rows, len(rows), show=5)
        return flagged, out.getvalue()

    def test_a_ceiling_flags_only_the_grammar_counting_more(self):
        entry = {"node": "region", "compare": "ceiling", "why": "the module wrapper"}
        self.assertFalse(self.report(entry, [("a.mlir", 3, 4)])[0])
        flagged, text = self.report(entry, [("a.mlir", 3, 4), ("b.mlir", 9, 8)])
        self.assertTrue(flagged)
        self.assertIn("b.mlir: grammar 9, reference 8 (+1)", text)
        self.assertNotIn("a.mlir:", text)

    def test_ranked_flags_both_directions(self):
        entry = {"node": "op_result", "compare": "ranked"}
        self.assertFalse(self.report(entry, [("a.mlir", 2, 2)])[0])
        self.assertTrue(self.report(entry, [("a.mlir", 2, 3)])[0])

    def test_an_unknown_compare_mode_is_refused(self):
        with self.assertRaises(SystemExit):
            self.report({"node": "x", "compare": "informational"}, [("a.mlir", 1, 1)])


class Invariants(unittest.TestCase):
    def test_a_lost_binding_is_reported(self):
        self.assertEqual(run("op-result-binding", tree_of(LOST_TREE), LOST_SRC),
                         [(2, "%res = arith.addi %cst0, %arg0 : i32")])

    def test_a_region_less_body_running_on_is_reported(self):
        hits = run("custom-body-boundary", tree_of(LOST_TREE), LOST_SRC)
        self.assertEqual([row for row, _ in hits], [2])

    def test_a_body_running_past_its_region_is_reported(self):
        hits = run("custom-body-boundary", tree_of(AFTER_REGION_TREE), AFTER_REGION_SRC)
        self.assertEqual([row for row, _ in hits], [4])

    def test_a_wrapped_header_is_not_a_binding(self):
        for check in ("op-result-binding", "custom-body-boundary"):
            self.assertEqual(run(check, tree_of(WRAPPED_TREE), WRAPPED_SRC), [], check)

    def test_the_corpus_count_skips_operand_assignments(self):
        pat = re.compile(SPEC["corpus_invariants"][0]["line"])
        self.assertTrue(pat.match('%a, %b = "test.op"() : () -> (i32, i32)'))
        self.assertFalse(pat.match("    %b = %y) -> (f32, f32) {"))

    def test_the_retired_whole_node_exemption_is_refused(self):
        spec = {"language": "x", "files": [], "invariants": [
            {"id": "old", "kind": "span_guard", "node": "n", "line": "x",
             "allow_if_child": ["region"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "spec.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(spec, fh)
            with self.assertRaises(SystemExit):
                probe.load_spec(path)


if __name__ == "__main__":
    unittest.main()
