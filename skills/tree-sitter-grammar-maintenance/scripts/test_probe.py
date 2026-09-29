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
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import probe  # noqa: E402

SPEC = probe.load_spec(os.path.join(HERE, "..", "assets", "invariants", "mlir.json"))

# parse_command builds parsers into a cache; keep the fake ones out of the
# real one.
_PARSER_CACHE = tempfile.TemporaryDirectory()
os.environ["PROBE_PARSER_CACHE"] = _PARSER_CACHE.name
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


# A generic operation that binds nothing, swallowed whole by the body before
# it: `"bar"` survives only as a string literal, and nothing binds a result.
SWALLOWED_SRC = """\
%c = arith.constant 0 : index
"bar"() : () -> ()
"""
SWALLOWED_TREE = """\
(toplevel [0, 0] - [2, 0]
  (operation [0, 0] - [1, 18]
    lhs: (op_result [0, 0] - [0, 2]
      (value_use [0, 0] - [0, 2]))
    rhs: (custom_operation [0, 5] - [1, 18]
      name: (custom_op_name [0, 5] - [0, 19])
      (integer_literal [0, 20] - [0, 21])
      (type [0, 24] - [0, 29]
        (builtin_type [0, 24] - [0, 29]
          (index_type [0, 24] - [0, 29])))
      (string_literal [1, 0] - [1, 5]))))"""

# Correct code: the same kind of line inside a region belongs to that region.
NESTED_SRC = """\
%0 = scf.execute_region -> i32 {
  "foo"() : () -> ()
  scf.yield %c : i32
}
"""
NESTED_TREE = """\
(toplevel [0, 0] - [4, 0]
  (operation [0, 0] - [3, 1]
    lhs: (op_result [0, 0] - [0, 2]
      (value_use [0, 0] - [0, 2]))
    rhs: (custom_operation [0, 5] - [3, 1]
      name: (custom_op_name [0, 5] - [0, 23])
      (type [0, 27] - [0, 30]
        (builtin_type [0, 27] - [0, 30]
          (integer_type [0, 27] - [0, 30])))
      (region [0, 31] - [3, 1]
        (entry_block [1, 2] - [2, 20]
          (operation [1, 2] - [1, 20]
            rhs: (generic_operation [1, 2] - [1, 20]
              (string_literal [1, 2] - [1, 7])
              (function_type [1, 12] - [1, 20])))
          (operation [2, 2] - [2, 20]
            rhs: (custom_operation [2, 2] - [2, 20]
              name: (custom_op_name [2, 2] - [2, 11])
              (value_use [2, 12] - [2, 14])
              (type [2, 17] - [2, 20]
                (builtin_type [2, 17] - [2, 20]
                  (integer_type [2, 17] - [2, 20]))))))))))"""


def tree_of(text):
    tree = probe.parse_sexp(text)
    assert tree is not None
    return tree


def run(check_id, tree, src):
    inv = INVARIANTS[check_id]
    return probe.CHECKS[inv["kind"]](inv, tree, probe.scrub_lines(src, SKIP))


def count(tree, type_):
    return sum(1 for n in tree.walk() if n.type == type_)


def call(argv):
    """Run the command line; return (exit status, stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        status = probe.main(argv)
    return status, out.getvalue()


def python_tool(directory, name, source):
    """An executable that runs `source` with this interpreter.

    A script with a shebang on POSIX; on Windows, which has no shebangs, the
    script plus a `.cmd` shim -- the same shape npm installs -- returned as
    the thing to run.
    """
    if os.name != "nt":
        return write(os.path.join(directory, name),
                     f"#!{sys.executable}\n{source}", executable=True)
    script = write(os.path.join(directory, name + ".py"), source)
    return write(os.path.join(directory, name + ".cmd"),
                 f'@"{sys.executable}" "{script}" %*\n')


# The part of a fake tree-sitter CLI that answers `build -o LIB` with an
# empty library and leaves `files` holding the paths a `parse` was given.
FAKE_CLI_ARGS = """\
import sys
args = sys.argv[1:]
if args[0] == "build":
    open(args[args.index("-o") + 1], "w").close()
    sys.exit(0)
files, rest = [], iter(args[1:])
for a in rest:
    if a in ("--lib-path", "--lang-name"):
        next(rest)
    else:
        files.append(a)
"""

# Stands in for the tree-sitter CLI: one tree per file, one operation with an
# op_result for each line that starts with `%`.
FAKE_CLI = FAKE_CLI_ARGS + """\
for path in files:
    n = sum(1 for line in open(path) if line.startswith("%"))
    out = [f"(toplevel [0, 0] - [{n}, 0]"]
    for i in range(n):
        out += [f"  (operation [{i}, 0] - [{i}, 6]",
                f"    lhs: (op_result [{i}, 0] - [{i}, 2]))"]
    print("\\n".join(out) + ")")
"""


def blocks(text):
    """`probe` output per invariant: {id: its summary line and what follows}."""
    found, current = {}, None
    for line in text.splitlines():
        m = re.match(r"(?:OK|HIT)\s+(\S+)", line)
        if m:
            current = found.setdefault(m.group(1), [line])
        elif current is not None and line.startswith(" "):
            current.append(line)
        else:
            current = None
    return {key: "\n".join(lines) for key, lines in found.items()}


def write(path, text, executable=False):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if executable:
        os.chmod(path, 0o755)
    return path


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
                         [(4, 'MISSING "}": return', 'MISSING "}"')])

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


class Invariants(unittest.TestCase):
    def test_a_lost_binding_is_reported_with_what_swallowed_it(self):
        self.assertEqual(run("op-result-binding", tree_of(LOST_TREE), LOST_SRC),
                         [(2, "%res = arith.addi %cst0, %arg0 : i32",
                           "value_use in custom_operation")])

    def test_a_region_less_body_running_on_is_reported(self):
        [(row, _, mode)] = run("custom-body-boundary", tree_of(LOST_TREE), LOST_SRC)
        self.assertEqual((row, mode), (2, "custom_operation without a region"))

    def test_a_body_running_past_its_region_is_reported(self):
        [(row, _, mode)] = run("custom-body-boundary", tree_of(AFTER_REGION_TREE),
                               AFTER_REGION_SRC)
        self.assertEqual((row, mode), (4, "custom_operation running on after its region"))

    def test_a_wrapped_header_is_not_a_binding(self):
        for check in ("op-result-binding", "custom-body-boundary"):
            self.assertEqual(run(check, tree_of(WRAPPED_TREE), WRAPPED_SRC), [], check)

    def test_a_swallowed_operation_that_binds_nothing_is_reported(self):
        tree = tree_of(SWALLOWED_TREE)
        # Neither binding check can see it: no line binds a lost result.
        for check in ("op-result-binding", "custom-body-boundary"):
            self.assertEqual(run(check, tree, SWALLOWED_SRC), [], check)
        [(row, detail, mode)] = run("custom-body-generic-op", tree, SWALLOWED_SRC)
        self.assertEqual((row, mode), (2, "custom_operation without a region"))
        self.assertIn('"bar"() : () -> ()', detail)

    def test_a_generic_operation_inside_a_region_is_not_flagged(self):
        self.assertEqual(run("custom-body-generic-op", tree_of(NESTED_TREE), NESTED_SRC), [])

    def test_a_bound_generic_operation_is_left_to_the_binding_check(self):
        line = '%x = "foo"() : () -> i32'
        self.assertIsNone(re.search(INVARIANTS["custom-body-generic-op"]["line"], line))
        self.assertIsNotNone(re.search(INVARIANTS["custom-body-boundary"]["line"], line))

    def test_the_corpus_count_skips_operand_assignments(self):
        pat = re.compile(SPEC["corpus_invariants"][0]["line"])
        self.assertTrue(pat.match('%a, %b = "test.op"() : () -> (i32, i32)'))
        self.assertFalse(pat.match("    %b = %y) -> (f32, f32) {"))

    def test_examples_reach_across_files_first(self):
        hits = [("a", 1), ("a", 2), ("a", 3), ("b", 1), ("c", 1)]
        self.assertEqual(probe.examples(hits, 3), [("a", 1), ("b", 1), ("c", 1)])
        self.assertEqual(len(probe.examples(hits, 10)), 5)

    def test_the_retired_whole_node_exemption_is_refused(self):
        spec = {"language": "x", "files": [], "invariants": [
            {"id": "old", "kind": "span_guard", "node": "n", "line": "x",
             "allow_if_child": ["region"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = write(os.path.join(tmp, "spec.json"), json.dumps(spec))
            with self.assertRaises(SystemExit):
                probe.load_spec(path)


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

    def report(self, entry, rows, show=5):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            flagged = probe.report_counts(entry, rows, len(rows), show)
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

    def test_show_zero_prints_the_summary_line_only(self):
        entry = {"node": "op_result", "compare": "ranked"}
        _, text = self.report(entry, [("a.mlir", 2, 3), ("b.mlir", 5, 4)], show=0)
        self.assertEqual(text.strip().splitlines(), [
            "HIT  op_result: 2 of 2 file(s) differ from the reference parser, "
            "1 above it and 1 below"])

    def test_an_unknown_compare_mode_is_refused(self):
        with self.assertRaises(SystemExit):
            self.report({"node": "x", "compare": "informational"}, [("a.mlir", 1, 1)])

    def test_a_limit_spreads_across_the_set(self):
        self.assertEqual(probe.spread_sample(list(range(100)), 4), [0, 25, 50, 75])
        self.assertEqual(probe.spread_sample([1, 2], 5), [1, 2])

    def test_an_undeclared_tool_is_refused_with_the_spec_hint(self):
        with self.assertRaises(SystemExit) as caught:
            probe.declared_tool(None, SPEC["normalizer"])
        self.assertIn("mlir-opt", str(caught.exception.code))

    def test_a_tool_failing_the_self_check_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrong = python_tool(tmp, "opt", "print('define void @f()')\n")
            with self.assertRaises(SystemExit):
                probe.run_self_check(wrong, SPEC["normalizer"], SPEC, tmp)
            right = python_tool(tmp, "mlir-opt",
                                "print('\"func.func\"() ({}) : () -> ()')\n")
            probe.run_self_check(right, SPEC["normalizer"], SPEC, tmp)

    def test_a_comparison_of_nothing_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "examples"))
            write(os.path.join(tmp, "examples", "pipeline.mlir"), "// RUN: a pass pipeline\n")
            # Passes the self-check, then declines every real input.
            tool = python_tool(tmp, "mlir-opt", (
                "import sys\n"
                "if not any('self-check' in a for a in sys.argv[1:]):\n"
                "    sys.exit(1)\n"
                "print('\"func.func\"() ({}) : () -> ()')\n"))
            spec = os.path.join(HERE, "..", "assets", "invariants", "mlir.json")
            status, text = call(["skeleton", "--repo", tmp, "--spec", spec, "--tool", tool])
        self.assertEqual(status, 2)
        self.assertIn("NOTHING WAS COMPARED", text)


class Corpus(unittest.TestCase):
    INV = SPEC["corpus_invariants"][0]
    # The shape `memref.extract_strided_metadata` had: two names on one line,
    # and a binding lost on the next -- two lines, two nodes, nothing flagged.
    MASKED = """\
================================================================================
masked loss
================================================================================

%a, %b = "t.two"() : () -> (i32, i32)
%c = arith.addi %a, %b : i32

--------------------------------------------------------------------------------

(toplevel
  (operation
    lhs: (op_result
      (value_use))
    lhs: (op_result
      (value_use))
    rhs: (generic_operation
      (string_literal)
      (function_type)))
  (operation
    rhs: (custom_operation
      name: (custom_op_name)
      (value_use)
      (value_use)
      (type))))
"""
    GROUP = """\
================================================================================
result group
================================================================================

%x:2 = "t.two"() : () -> (i32, i32)

--------------------------------------------------------------------------------

(toplevel
  (operation
    lhs: (op_result
      (value_use))
    rhs: (generic_operation
      (string_literal)
      (function_type))))
"""

    def case(self, text):
        [(_, src, tree)] = list(probe.split_corpus(text))
        return src, tree

    def test_names_are_counted_not_lines(self):
        src, tree = self.case(self.MASKED)
        self.assertEqual(probe.corpus_balance(self.INV, src, tree), (3, 2))
        by_line = {k: v for k, v in self.INV.items() if k != "count_regex"}
        self.assertEqual(probe.corpus_balance(by_line, src, tree), (2, 2))

    def test_a_result_group_is_one_name(self):
        src, tree = self.case(self.GROUP)
        self.assertEqual(probe.corpus_balance(self.INV, src, tree), (1, 1))

    def test_a_cst_case_is_counted_in_its_own_format(self):
        # A `:cst` case records `parse --cst` lines, not an S-expression;
        # counted as one, its binding read as lost.
        src = "%z = test.make %a : i32\n"
        tree = ("\n0:0  - 1:0   toplevel\n0:0  - 0:23    operation\n"
                "0:0  - 0:2       lhs: op_result\n0:0  - 0:2         value_use\n"
                "0:0  - 0:1           \"%\"\n")
        self.assertEqual(probe.corpus_balance(self.INV, src, tree), (1, 1))

    def test_a_wrapped_affine_bound_is_not_a_binding(self):
        # `%i = max ...` continues `affine.for` on the line above; the case
        # that pins it in tree-sitter-mlir read as a lost binding.
        line = re.compile(self.INV["line"])
        for bound in ("      %i = max affine_map<()[s0] -> (s0)>()[%n] to 10 {",
                      "  %i = 0 to 10 {", "  %j = min #map(%i)"):
            self.assertIsNone(line.match(bound), bound)
        for binding in ("  %m = minimum.op %a", '%x = "t.op"() : () -> i32'):
            self.assertIsNotNone(line.match(binding), binding)

    def test_the_corpus_command_reports_the_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "test", "corpus"))
            write(os.path.join(tmp, "test", "corpus", "cases.txt"),
                  self.MASKED + "\n" + self.GROUP)
            spec = os.path.join(HERE, "..", "assets", "invariants", "mlir.json")
            status, text = call(["corpus", "--repo", tmp, "--spec", spec])
        self.assertEqual(status, 1)
        self.assertIn("1/2 case(s): 1 short by 1 op_result, 0 over", text)
        self.assertIn("'masked loss'  3 in input, 2 in expected tree", text)


class Commands(unittest.TestCase):
    """`probe` and `census` through the command line, on captured CLI output.

    Each piece they are built from is tested above, yet a probe that exited 0
    with hits, filed hits under the wrong invariant, or dropped every file
    after the first, and a census that stopped writing shapes, all passed.
    """

    def repo(self, tmp, sources, cli):
        os.makedirs(os.path.join(tmp, "examples"))
        for name, text in sources.items():
            write(os.path.join(tmp, "examples", name), text)
        return write(os.path.join(tmp, "spec.json"), json.dumps(dict(SPEC, cli=[cli])))

    def canned_cli(self, tmp, trees):
        """A CLI that prints the captured tree for each file, by file name."""
        return python_tool(tmp, "canned-tree-sitter", FAKE_CLI_ARGS + (
            "import json, os\n"
            f"trees = json.loads({json.dumps(json.dumps(trees))})\n"
            "for path in files:\n"
            "    print(trees[os.path.basename(path)])\n"))

    def test_probe_files_each_hit_under_its_invariant(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = self.canned_cli(tmp, {"good.mlir": GOOD_TREE, "lost.mlir": LOST_TREE})
            spec = self.repo(tmp, {"good.mlir": GOOD_SRC, "lost.mlir": LOST_SRC}, cli)
            status, text = call(["probe", "--repo", tmp, "--spec", spec])
            quiet_status, quiet = call(["probe", "--repo", tmp, "--spec", spec,
                                        "--show", "0"])
            clean_status, _ = call(["probe", "--repo", tmp, "--spec", spec,
                                    "--files", "examples/good.mlir"])
        self.assertEqual((status, quiet_status, clean_status), (1, 1, 0))
        found = blocks(text)
        self.assertIn("1 hit(s) in 1 file(s), 1 mode(s)", found["op-result-binding"])
        self.assertIn("value_use in custom_operation", found["op-result-binding"])
        self.assertIn(os.path.join("examples", "lost.mlir") + ":2: %res = arith.addi",
                      found["op-result-binding"])
        self.assertIn("custom_operation without a region", found["custom-body-boundary"])
        for clean in ("no-error-node", "block-label", "custom-body-generic-op"):
            self.assertTrue(found[clean].startswith("OK"), clean)
        # --show 0 leaves one summary line per invariant and nothing under it.
        self.assertEqual(len(blocks(quiet)), len(SPEC["invariants"]))
        self.assertEqual([line for line in quiet.splitlines() if line.startswith(" ")], [])

    def test_a_census_feeds_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = python_tool(tmp, "fake-tree-sitter", FAKE_CLI)
            spec = self.repo(tmp, {"a.mlir": "%x = y\n", "b.mlir": "%x = y\n"}, cli)
            before = os.path.join(tmp, "before.json")
            after = os.path.join(tmp, "after.json")
            self.assertEqual(call(["census", "--repo", tmp, "--spec", spec,
                                   "--out", before])[0], 0)
            write(os.path.join(tmp, "examples", "b.mlir"), "%x = y\n%z = w\n")
            call(["census", "--repo", tmp, "--spec", spec, "--out", after])
            with open(before, encoding="utf-8") as fh:
                payload = json.load(fh)
            status, text = call(["diff", before, after])
        self.assertEqual(payload["kind"], "census")
        self.assertEqual(sorted(payload["shapes"]), sorted(payload["files"]))
        self.assertEqual(status, 1)
        self.assertIn("node counts changed: 1", text)
        self.assertIn(os.path.join("examples", "b.mlir"), text)


class SkeletonRuns(unittest.TestCase):
    """`skeleton --out` and `diff` around a grammar change."""

    # Stands in for mlir-opt: passes the self-check, prints each input back,
    # and invents one extra result for a file named unnamed.mlir -- the way
    # generic form names a result the source left unnamed.
    FAKE_OPT = (
        "import sys\n"
        "if any('self-check' in a for a in sys.argv[1:]):\n"
        "    print('\"func.func\"() ({}) : () -> ()')\n"
        "    sys.exit(0)\n"
        "path = sys.argv[-1]\n"
        "sys.stdout.write(open(path).read())\n"
        "if path.endswith('unnamed.mlir'):\n"
        "    print('%9 = z')\n")

    def test_a_run_is_saved_for_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "examples"))
            for name in ("named.mlir", "unnamed.mlir"):
                write(os.path.join(tmp, "examples", name), "%x = y\n")
            spec = dict(SPEC, cli=[python_tool(tmp, "fake-tree-sitter", FAKE_CLI)])
            spec_path = write(os.path.join(tmp, "spec.json"), json.dumps(spec))
            tool = python_tool(tmp, "mlir-opt", self.FAKE_OPT)
            out = os.path.join(tmp, "run.json")
            status, text = call(["skeleton", "--repo", tmp, "--spec", spec_path,
                                 "--tool", tool, "--out", out, "--jobs", "2"])
            with open(out, encoding="utf-8") as fh:
                run = json.load(fh)
        self.assertEqual(status, 1)  # the unnamed result: grammar 1, reference 2
        self.assertEqual(run["kind"], "skeleton")
        self.assertEqual(run["declined"], [])
        results = [c["node"] for c in run["counts"]].index("op_result")
        named = os.path.join("examples", "named.mlir")
        unnamed = os.path.join("examples", "unnamed.mlir")
        self.assertEqual(run["files"][named][results], [1, 1])
        self.assertEqual(run["files"][unnamed][results], [1, 2])

    def payloads(self, before, after, tmp):
        def one(name, files):
            return write(os.path.join(tmp, name), json.dumps({
                "kind": "skeleton", "language": "mlir", "declined": [],
                "counts": [{"node": "op_result", "label": "results bound",
                            "compare": "ranked"}],
                "files": {rel: [pair] for rel, pair in files.items()}}))
        return one("before.json", before), one("after.json", after)

    def test_a_fix_may_only_move_files_closer(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = self.payloads(
                {"a": [5, 8], "b": [3, 3], "c": [2, 4], "d": [2, 2], "e": [2, 2]},
                {"a": [8, 8], "b": [3, 3], "c": [1, 4], "d": [2, 3], "e": [3, 2]}, tmp)
            status, text = call(["diff", before, after])
        self.assertEqual(status, 1)
        self.assertIn("1 closer, 1 further, 1 newly above the reference, "
                      "reference side moved in 1", text)
        for line in ("a: gap -3 -> +0", "c: gap -2 -> -3", "d: reference 2 -> 3",
                     "e: gap +0 -> +1"):
            self.assertIn(line, text)

    def test_only_closer_is_a_clean_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = self.payloads({"a": [5, 8]}, {"a": [7, 8]}, tmp)
            self.assertEqual(call(["diff", before, after])[0], 0)

    def test_a_census_does_not_diff_against_a_skeleton_run(self):
        counts, shape = probe.census_entry(tree_of(GOOD_TREE))
        with tempfile.TemporaryDirectory() as tmp:
            census = write(os.path.join(tmp, "census.json"), json.dumps(
                {"kind": "census", "language": "x", "files": {"f": counts},
                 "shapes": {"f": shape}}))
            skeleton, _ = self.payloads({"a": [1, 1]}, {"a": [1, 1]}, tmp)
            self.assertEqual(call(["diff", census, skeleton])[0], 2)


class Census(unittest.TestCase):
    def test_a_shape_change_with_equal_counts_is_a_blast_radius(self):
        before = tree_of("(toplevel [0, 0] - [2, 0]\n  (operation [0, 0] - [0, 9]))")
        after = tree_of("(toplevel [0, 0] - [2, 0]\n  (operation [0, 0] - [1, 5]))")
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name, tree in (("before", before), ("after", after)):
                counts, shape = probe.census_entry(tree)
                payload = {"language": "x", "files": {"f.mlir": counts},
                           "shapes": {"f.mlir": shape}}
                paths.append(write(os.path.join(tmp, name + ".json"), json.dumps(payload)))
            status, text = call(["diff"] + paths)
        self.assertEqual(status, 1)
        self.assertIn("same counts, different shape (a span, parent or field moved): 1",
                      text)

    def test_an_identical_census_is_inert(self):
        counts, shape = probe.census_entry(tree_of(GOOD_TREE))
        payload = json.dumps({"language": "x", "files": {"f": counts},
                              "shapes": {"f": shape}})
        with tempfile.TemporaryDirectory() as tmp:
            a = write(os.path.join(tmp, "a.json"), payload)
            b = write(os.path.join(tmp, "b.json"), payload)
            self.assertEqual(call(["diff", a, b])[0], 0)


class Speed(unittest.TestCase):
    """The faster paths must give exactly the answers the plain ones did."""

    def test_walk_keeps_pre_order(self):
        def recursive(node):
            yield node
            for child in node.children:
                yield from recursive(child)
        tree = tree_of(AFTER_REGION_TREE)
        self.assertEqual([id(n) for n in tree.walk()], [id(n) for n in recursive(tree)])

    def test_parallel_parsing_gives_the_sequential_answer_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = [python_tool(tmp, "fake-tree-sitter", FAKE_CLI), "parse"]
            files = [write(os.path.join(tmp, f"f{i}.mlir"), "%x = y\n" * i)
                     for i in range(1, 6)]
            args = types.SimpleNamespace(batch=2, jobs=1)
            sequential = list(probe.map_files(tmp, cli, files, args,
                                              probe.census_file, None))
            args.jobs = 3
            parallel = list(probe.map_files(tmp, cli, files, args,
                                            probe.census_file, None))
        self.assertEqual([path for path, _ in sequential], files)
        self.assertEqual(parallel, sequential)
        self.assertEqual(sequential[2][1][0]["op_result"], 3)

    def test_the_repository_cli_is_called_directly(self):
        with tempfile.TemporaryDirectory() as repo:
            bin_dir = os.path.join(repo, "node_modules", ".bin")
            os.makedirs(bin_dir)
            local = python_tool(bin_dir, "tree-sitter", "print('tree-sitter 0.27.0')\n")
            [found] = probe.resolve_cli({}, repo)
            self.assertEqual(os.path.normcase(found), os.path.normcase(local))

    def test_each_checkout_parses_with_the_parser_built_from_its_own_src(self):
        # `tree-sitter parse` in a worktree picked the main checkout's grammar
        # from the CLI config, so a before/after measured one parser twice.
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "log")
            cli = python_tool(tmp, "fake-tree-sitter", (
                "import json, os, sys\n"
                f"open({log!r}, 'a').write(json.dumps([os.getcwd()] + sys.argv[1:]) + '\\n')\n"
                ) + FAKE_CLI_ARGS)
            spec = {"language": "mlir", "cli": [cli]}
            main, worktree = os.path.join(tmp, "main"), os.path.join(tmp, "wt")
            for repo, source in ((main, "old"), (worktree, "new")):
                os.makedirs(os.path.join(repo, "src"))
                write(os.path.join(repo, "src", "parser.c"), source)
            cmd_main = probe.parse_command(spec, main)
            cmd_wt = probe.parse_command(spec, worktree)
            again = probe.parse_command(spec, worktree)
            with open(log) as fh:
                builds = [call for call in map(json.loads, fh) if call[1] == "build"]
            # Compared as files: Windows may spell one temp directory two ways.
            built_in_worktree = os.path.samefile(builds[1][0], worktree)
        lib_main = cmd_main[cmd_main.index("--lib-path") + 1]
        lib_wt = cmd_wt[cmd_wt.index("--lib-path") + 1]
        self.assertNotEqual(lib_main, lib_wt)
        self.assertEqual(cmd_wt, again)
        # Built once per checkout content, each in its own checkout.
        self.assertEqual(len(builds), 2)
        self.assertTrue(built_in_worktree)
        self.assertEqual(builds[1][2], "-o")
        self.assertEqual(cmd_wt[-4:], ["--lib-path", lib_wt, "--lang-name", "mlir"])

    def test_npx_is_the_fallback_and_a_spec_cli_wins(self):
        with tempfile.TemporaryDirectory() as repo:
            self.assertEqual(probe.resolve_cli({}, repo)[1:], ["--no-install", "tree-sitter"])
            self.assertEqual(probe.resolve_cli({"cli": ["/nowhere/ts", "-q"]}, repo),
                             ["/nowhere/ts", "-q"])


class Portability(unittest.TestCase):
    """What differs on Windows: code pages, line endings, no shebangs."""

    def test_tool_output_is_read_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = python_tool(tmp, "say", (
                "import sys\n"
                "sys.stdout.buffer.write('\\u00e4 \\u2192 \\u00e9'.encode('utf-8'))\n"))
            self.assertEqual(probe._run([tool]), "\u00e4 \u2192 \u00e9")

    def test_the_skill_digest_ignores_line_endings(self):
        digests = []
        for eol in (b"\n", b"\r\n"):
            with tempfile.TemporaryDirectory() as tmp:
                with open(os.path.join(tmp, "SKILL.md"), "wb") as fh:
                    fh.write(b"one" + eol + b"two" + eol)
                saved, probe.SKILL_DIR = probe.SKILL_DIR, tmp
                try:
                    digests.append(probe.skill_digest())
                finally:
                    probe.SKILL_DIR = saved
        self.assertEqual(digests[0], digests[1])


class Provenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        write(os.path.join(self.repo, "package-lock.json"), json.dumps(
            {"packages": {"node_modules/tree-sitter-cli": {"version": "0.27.0"}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def spec_with_cli(self, version):
        cli = python_tool(self.repo, "fake-cli", f"print('tree-sitter {version}')\n")
        return write(os.path.join(self.repo, "spec.json"), json.dumps(
            {"language": "x", "files": [], "invariants": [], "cli": [cli]}))

    def test_a_cli_matching_the_lock_is_recorded(self):
        status, text = call(["provenance", "--repo", self.repo,
                             "--spec", self.spec_with_cli("0.27.0")])
        self.assertEqual(status, 0)
        self.assertIn("- **CLI version:** `0.27.0`, lock says `0.27.0`", text)
        self.assertIn("the reference comparison did not run", text)

    def test_a_cli_drifted_from_the_lock_is_flagged(self):
        status, text = call(["provenance", "--repo", self.repo,
                             "--spec", self.spec_with_cli("0.26.12")])
        self.assertEqual(status, 1)
        self.assertIn("MISMATCH", text)

    def test_a_repository_without_a_lock_file_says_so(self):
        os.remove(os.path.join(self.repo, "package-lock.json"))
        write(os.path.join(self.repo, "package.json"),
              json.dumps({"devDependencies": {"tree-sitter-cli": "^0.26.11"}}))
        self.assertIsNone(probe.locked_cli(self.repo)[0])
        self.assertIn("^0.26.11", probe.locked_cli(self.repo)[1])

    def pin(self, version):
        os.makedirs(os.path.join(self.repo, ".github", "workflows"), exist_ok=True)
        write(os.path.join(self.repo, ".github", "workflows", "ci.yml"),
              "jobs:\n  test:\n    steps:\n      - uses: tree-sitter/setup-action/cli@v2\n"
              f"        with:\n          tree-sitter-ref: v{version}\n")

    def test_a_ci_pin_drifted_from_the_lock_is_flagged(self):
        # CI installed 0.26.12 under a 0.27.0 lock, and its fuzzer failed a
        # correct `:cst` case -- local runs could not show it.
        self.pin("0.26.12")
        status, text = call(["provenance", "--repo", self.repo,
                             "--spec", self.spec_with_cli("0.27.0")])
        self.assertEqual(status, 1)
        self.assertIn("- **CLI in CI:** MISMATCH: `0.26.12` in "
                      + os.path.join(".github", "workflows", "ci.yml") + ":6", text)

    def test_a_literal_pin_matching_the_lock_is_recorded_as_hand_synced(self):
        self.pin("0.27.0")
        status, text = call(["provenance", "--repo", self.repo,
                             "--spec", self.spec_with_cli("0.27.0")])
        self.assertEqual(status, 0)
        self.assertIn("- **CLI in CI:** `0.27.0` in 1 literal pin(s) -- synced by hand",
                      text)

    def test_a_version_computed_in_a_composite_action_is_found(self):
        # The cure for the drift: an action under .github/actions reads the
        # lock and passes an expression, not a literal.
        action = os.path.join(self.repo, ".github", "actions", "setup")
        os.makedirs(action)
        write(os.path.join(action, "action.yml"),
              "runs:\n  steps:\n    - uses: tree-sitter/setup-action/cli@v2\n"
              "      with:\n        tree-sitter-ref: ${{ steps.cli.outputs.ref }}\n")
        status, text = call(["provenance", "--repo", self.repo,
                             "--spec", self.spec_with_cli("0.27.0")])
        self.assertEqual(status, 0)
        self.assertIn("computed at run time (`${{ steps.cli.outputs.ref }}` in "
                      + os.path.join(".github", "actions", "setup", "action.yml")
                      + ":5)", text)


class CensusGroups(unittest.TestCase):
    def test_files_that_moved_the_same_way_are_one_group(self):
        before = {"a": {"op_result": 1}, "b": {"op_result": 2},
                  "c": {"op_result": 1, "region": 2}}
        after = {"a": {"op_result": 3}, "b": {"op_result": 4},
                 "c": {"op_result": 2, "region": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            paths = [write(os.path.join(tmp, n + ".json"), json.dumps(
                {"kind": "census", "language": "x", "files": files, "shapes": {}}))
                for n, files in (("before", before), ("after", after))]
            status, text = call(["diff"] + paths)
        self.assertEqual(status, 1)
        self.assertIn("node counts changed: 3, in 2 group(s) by the types that moved", text)
        self.assertIn("2 file(s): op_result +4", text)
        # The odd one out keeps its own line instead of hiding in a file list.
        self.assertIn("1 file(s): op_result +1, region -1", text)


class CorpusBefore(unittest.TestCase):
    """`corpus --before REV` on a regenerated corpus."""

    BEFORE = """\
================================================================================
two bindings
================================================================================

%a = t.one
%b = t.two

--------------------------------------------------------------------------------

(toplevel
  (operation
    lhs: (op_result
      (value_use))
    rhs: (custom_operation
      name: (custom_op_name)
      (value_use)))
  (operation
    rhs: (custom_operation
      name: (custom_op_name))))
"""
    # The fix moves the trailing value_use into the next operation's op_result:
    # its preorder position changes, its place among the leaves does not.
    REGROUPED = BEFORE.replace("""\
      name: (custom_op_name)
      (value_use)))
  (operation
    rhs:""", """\
      name: (custom_op_name)))
  (operation
    lhs: (op_result
      (value_use))
    rhs:""")

    def run_git(self, repo, *argv):
        subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c",
                        "user.email=t@example.com"] + list(argv),
                       check=True, capture_output=True)

    def diff(self, after):
        spec = os.path.join(HERE, "..", "assets", "invariants", "mlir.json")
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "test", "corpus"))
            corpus = os.path.join(tmp, "test", "corpus", "cases.txt")
            write(corpus, self.BEFORE)
            self.run_git(tmp, "init", "-q")
            self.run_git(tmp, "add", ".")
            self.run_git(tmp, "commit", "-q", "-m", "corpus")
            write(corpus, after)
            return call(["corpus", "--repo", tmp, "--spec", spec,
                         "--before", "HEAD"])

    def test_a_regrouping_is_sorted_by_the_types_that_moved(self):
        status, text = self.diff(self.REGROUPED)
        self.assertEqual(status, 0)
        self.assertIn("1 case(s) changed, 0 new, 0 removed", text)
        self.assertIn("1 case(s): op_result +1", text)
        self.assertNotIn("!!", text)

    def test_a_moved_leaf_is_read_first(self):
        moved = self.BEFORE.replace("      (value_use)))", "      (bare_id)))")
        status, text = self.diff(moved)
        self.assertEqual(status, 1)
        self.assertIn("'two bindings' -- leaves moved, appeared or vanished", text)

    def test_a_changed_input_is_not_a_regeneration(self):
        status, text = self.diff(self.REGROUPED.replace("%b = t.two", "%b = t.too"))
        self.assertEqual(status, 1)
        self.assertIn("'two bindings' -- input changed", text)


if __name__ == "__main__":
    unittest.main()
