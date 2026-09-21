#!/usr/bin/env python3
"""Structural-invariant prober for tree-sitter grammars.

A parse that reports no ERROR is not evidence that the tree is correct. A
permissive fallback rule can absorb valid syntax into a wrong shape and still
exit 0. This script checks a parsed file set against declared structural
invariants, and can take a node census so a grammar change's blast radius is
measurable instead of assumed.

It shells out to the repository's own tree-sitter CLI and reads the standard
S-expression output. Standard library only; nothing is written into the parser
repository.

Usage:
    probe.py probe   --repo DIR --spec FILE [--id ID]... [--files GLOB]
    probe.py corpus  --repo DIR --spec FILE
    probe.py skeleton --repo DIR --spec FILE [--tool PATH] [--limit N]
    probe.py census  --repo DIR --spec FILE --out FILE
    probe.py diff    BEFORE.json AFTER.json

Exit status: 0 when every selected invariant holds, 1 on any hit, 2 on a
tooling or configuration failure. A hit is a candidate for review, not a
confirmed bug -- triage it against the language's contract document.
"""

from __future__ import annotations

import argparse
import glob as globlib
import json
import os
import re
import shutil
import subprocess
import sys

# --------------------------------------------------------------------------
# S-expression tree
# --------------------------------------------------------------------------

_TOKEN = re.compile(
    r'(?P<open>\()'
    r'|(?P<close>\))'
    r'|(?P<field>[A-Za-z_][A-Za-z0-9_]*:)'
    r'|(?P<range>\[\s*\d+\s*,\s*\d+\s*\])'
    r'|(?P<string>"(?:[^"\\]|\\.)*")'
    r'|(?P<name>[^\s()\[\]]+)'
    r'|(?P<ws>\s+)'
)


class Node:
    __slots__ = ("type", "field", "start", "end", "children", "parent")

    def __init__(self, type_, field, parent):
        self.type = type_
        self.field = field
        self.parent = parent
        self.start = (0, 0)
        self.end = (0, 0)
        self.children = []

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def has_child(self, types):
        return any(c.type in types for c in self.children)

    def has_descendant(self, types):
        return any(n.type in types for n in self.walk() if n is not self)


def parse_sexp(text):
    """Build a Node tree from `tree-sitter parse` S-expression output."""
    root = None
    stack = []
    pending_field = None
    expect_name = False
    ranges = []

    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "open":
            expect_name = True
            continue
        if expect_name and kind in ("name", "string"):
            node = Node(m.group(0), pending_field, stack[-1] if stack else None)
            pending_field = None
            expect_name = False
            ranges = []
            if stack:
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
            continue
        if kind == "field":
            pending_field = m.group(0)[:-1]
            continue
        if kind == "range":
            if not stack:
                continue
            r, c = (int(x) for x in re.findall(r"\d+", m.group(0)))
            ranges.append((r, c))
            if len(ranges) == 1:
                stack[-1].start = (r, c)
            elif len(ranges) == 2:
                stack[-1].end = (r, c)
            continue
        if kind == "close":
            if stack:
                stack.pop()
                ranges = []
            continue
    return root


# --------------------------------------------------------------------------
# Parsing a file set
# --------------------------------------------------------------------------


def resolve_files(repo, patterns):
    out = []
    for pat in patterns:
        hits = globlib.glob(os.path.join(repo, pat), recursive=True)
        out.extend(sorted(h for h in hits if os.path.isfile(h)))
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def parse_batch(repo, cli, files):
    """Parse files in one CLI invocation; yield (path, Node) pairs."""
    proc = subprocess.run(
        cli + ["parse"] + files,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if not proc.stdout.strip():
        raise SystemExit(
            "tree-sitter parse produced no output.\n" + proc.stderr.strip()
        )
    chunks = re.split(r"^(?=\()", proc.stdout, flags=re.M)
    chunks = [c for c in chunks if c.strip()]
    if len(chunks) != len(files):
        raise SystemExit(
            "parse output does not line up with the input file list "
            f"({len(chunks)} trees for {len(files)} files). "
            "Re-run with a smaller --batch, or check the CLI version."
        )
    for path, chunk in zip(files, chunks):
        yield path, parse_sexp(chunk)


# --------------------------------------------------------------------------
# Invariants
# --------------------------------------------------------------------------


def source_lines(path, skip_re):
    lines = []
    for raw in open(path, encoding="utf-8", errors="replace").read().splitlines():
        lines.append(("" if skip_re and skip_re.search(raw) else raw, raw))
    return lines


def check_line_produces(inv, tree, lines):
    """Every line matching `line` must start a node of type `node`."""
    want = set(inv["node"]) if isinstance(inv["node"], list) else {inv["node"]}
    rows = {n.start[0] for n in tree.walk() if n.type in want}
    pat = re.compile(inv["line"])
    hits = []
    for row, (scrubbed, raw) in enumerate(lines):
        if scrubbed and pat.search(scrubbed) and row not in rows:
            hits.append((row + 1, raw.strip()))
    return hits


def check_no_node(inv, tree, lines):
    """No node of the listed types may appear at all (ERROR / MISSING)."""
    want = set(inv["node"]) if isinstance(inv["node"], list) else {inv["node"]}
    hits = []
    for n in tree.walk():
        if n.type in want:
            row = n.start[0]
            raw = lines[row][1].strip() if row < len(lines) else ""
            hits.append((row + 1, f"{n.type}: {raw}"))
    return hits


def check_span_guard(inv, tree, lines):
    """A node must not span a line that starts a new sibling construct.

    This is the machine-checkable form of a boundary-preservation rule: a
    permissive body may look however it likes, but it may not swallow the
    following construct.
    """
    want = set(inv["node"]) if isinstance(inv["node"], list) else {inv["node"]}
    allow = set(inv.get("allow_if_child", []))
    pat = re.compile(inv["line"])
    hits = []
    for n in tree.walk():
        if n.type not in want or n.start[0] == n.end[0]:
            continue
        if allow and n.has_descendant(allow):
            continue
        for row in range(n.start[0] + 1, min(n.end[0] + 1, len(lines))):
            scrubbed, raw = lines[row]
            if scrubbed and pat.search(scrubbed):
                hits.append(
                    (row + 1, f"absorbed into {n.type} opened on line "
                              f"{n.start[0] + 1}: {raw.strip()}")
                )
                break
    return hits


CHECKS = {
    "line_produces": check_line_produces,
    "no_node": check_no_node,
    "span_guard": check_span_guard,
}


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def load_spec(path):
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
    except OSError as exc:
        raise SystemExit(f"cannot read spec {path}: {exc.strerror}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"spec {path} is not valid JSON: {exc}")
    for key in ("language", "files", "invariants"):
        if key not in spec:
            raise SystemExit(f"spec is missing required key: {key}")
    return spec


def iter_trees(repo, spec, args):
    cli = spec.get("cli", ["npx", "--no-install", "tree-sitter"])
    patterns = args.files or spec["files"]
    files = resolve_files(repo, patterns)
    if not files:
        raise SystemExit(f"no files matched: {patterns}")
    # The CLI resolves a language from the grammar repository it runs in, so it
    # is run from there even when the files under audit live somewhere else --
    # mlir-opt-normalized output, a bug report attachment, a consumer's
    # sources. Paths handed to it are absolute, so the cwd only selects the
    # grammar.
    cwd = os.path.abspath(getattr(args, "grammar_repo", None) or repo)
    skip_re = re.compile(spec["skip_line"]) if spec.get("skip_line") else None
    batch = args.batch
    for i in range(0, len(files), batch):
        for path, tree in parse_batch(cwd, cli, files[i:i + batch]):
            if tree is None:
                raise SystemExit(f"could not read a tree for {path}")
            yield path, tree, source_lines(path, skip_re)


def cmd_probe(args):
    spec = load_spec(args.spec)
    repo = os.path.abspath(args.repo)
    selected = [
        inv for inv in spec["invariants"]
        if not args.id or inv["id"] in args.id
    ]
    if not selected:
        raise SystemExit(f"no invariant matched --id {args.id}")

    results = {inv["id"]: [] for inv in selected}
    n_files = 0
    for path, tree, lines in iter_trees(repo, spec, args):
        n_files += 1
        rel = os.path.relpath(path, repo)
        for inv in selected:
            check = CHECKS.get(inv["kind"])
            if check is None:
                raise SystemExit(f"unknown invariant kind: {inv['kind']}")
            for row, detail in check(inv, tree, lines):
                results[inv["id"]].append((rel, row, detail))

    total = 0
    for inv in selected:
        hits = results[inv["id"]]
        total += len(hits)
        status = "OK  " if not hits else "HIT "
        print(f"{status} {inv['id']}  (layer {inv.get('layer', '?')})  "
              f"{len(hits)} hit(s)")
        if hits:
            print(f"     {inv.get('why', '').strip()}")
            by_file = {}
            for rel, row, detail in hits:
                by_file.setdefault(rel, []).append((row, detail))
            for rel in sorted(by_file, key=lambda r: -len(by_file[r])):
                rows = by_file[rel]
                print(f"     {rel}  ({len(rows)})")
                for row, detail in rows[:args.show]:
                    print(f"       {row}: {detail}")
                if len(rows) > args.show:
                    print(f"       ... {len(rows) - args.show} more")
    print(f"\n{n_files} file(s) parsed, {total} hit(s) total.")
    print("A hit is a candidate. Triage it against the contract document "
          "before touching the grammar.")
    return 1 if total else 0


def split_corpus(text):
    """Yield (name, input, expected_tree) for each case in a corpus file.

    The corpus format is a header fenced by `=` rules, the input, a `-` rule,
    and the expected S-expression. Header attribute lines (`:skip`, `:error`,
    `:language`) are not part of the name.
    """
    parts = re.split(r"^={3,}[ \t]*$", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        header = parts[i].strip().splitlines()
        name = header[0].strip() if header else "?"
        body = parts[i + 1]
        split = re.split(r"^-{3,}[ \t]*$", body, maxsplit=1, flags=re.M)
        if len(split) != 2:
            continue
        yield name, split[0], split[1]


def cmd_corpus(args):
    """Check the corpus against itself: no parser is needed.

    The corpus is the persistent AST contract. If its expected trees were
    accepted from `--update` without being read, a parser defect is recorded
    there as the intended result, and every gate goes green on the wrong tree.
    This compares each case's input against its own expected tree.
    """
    spec = load_spec(args.spec)
    repo = os.path.abspath(args.repo)
    checks = [
        inv for inv in spec.get("corpus_invariants", [])
        if not args.id or inv["id"] in args.id
    ]
    if not checks:
        raise SystemExit("spec declares no corpus_invariants")
    files = resolve_files(repo, spec.get("corpus_files", ["test/corpus/*.txt"]))
    if not files:
        raise SystemExit("no corpus files matched")

    total = 0
    for inv in checks:
        pat = re.compile(inv["line"])
        node = re.compile(r"\(%s\b" % re.escape(inv["node"]))
        hits, n_cases, lost = [], 0, 0
        for path in files:
            rel = os.path.relpath(path, repo)
            text = open(path, encoding="utf-8", errors="replace").read()
            for name, src, tree in split_corpus(text):
                want = sum(1 for ln in src.splitlines() if pat.match(ln))
                if not want:
                    continue
                n_cases += 1
                got = len(node.findall(tree))
                if got < want:
                    lost += want - got
                    hits.append((rel, name, want, got))
        total += len(hits)
        status = "OK  " if not hits else "HIT "
        print(f"{status} {inv['id']}  (layer {inv.get('layer', '?')})  "
              f"{len(hits)}/{n_cases} case(s), {lost} missing {inv['node']}")
        if hits:
            print(f"     {inv.get('why', '').strip()}")
            hits.sort(key=lambda h: h[3] - h[2])
            for rel, name, want, got in hits[:args.show]:
                print(f"       {rel}: {name!r}  {want} in input, "
                      f"{got} in expected tree")
            if len(hits) > args.show:
                print(f"       ... {len(hits) - args.show} more")
    if total:
        print("\nAn expected tree that contradicts its own input was accepted "
              "without being read. Fix the grammar first, then regenerate and "
              "read the corpus diff -- never the other way round.")
    return 1 if total else 0


def cmd_skeleton(args):
    """Compare the parser against the language's own reference implementation.

    There is no AST to diff against: a compiler's in-memory IR is what is left
    *after* parsing, with the surface syntax already consumed, so it has no
    node-for-node correspondence with a CST. What it does still agree on is the
    skeleton -- how many operations, how many results each one binds, how the
    regions and blocks nest. Those are decided by syntax and survive parsing.

    So rather than mapping a CST onto an IR (a second interpreter, which would
    then need verifying itself), normalize the input with the reference tool and
    parse *its* output with the same grammar. Both sides are then CSTs and the
    mapping is the identity. A disagreement is the grammar reading the program
    differently from the language's own parser -- with no judgement call left.

    This only reaches inputs the reference tool accepts. Pass pipelines,
    expected-error tests and split files are outside it, which is why the
    broad ERROR/MISSING sweep still earns its place.
    """
    import tempfile

    spec = load_spec(args.spec)
    norm = spec.get("normalizer")
    if not norm:
        raise SystemExit("spec declares no normalizer; skeleton needs one")
    repo = os.path.abspath(args.repo)
    cli = spec.get("cli", ["npx", "--no-install", "tree-sitter"])
    command = list(norm["command"])
    if args.tool:
        command[0] = args.tool
    tool = shutil.which(command[0])
    if tool is None:
        raise SystemExit(
            f"reference parser '{command[0]}' not found on PATH.\n"
            "This check is the strongest evidence available, so do not skip it\n"
            "silently -- ask the user where the tool lives and pass it:\n"
            f"    --tool /path/to/{os.path.basename(command[0])}\n"
            "Its version does not need to match the pinned examples; a version\n"
            "difference shows up as files the tool rejects, not as false hits."
        )
    command[0] = tool

    files = resolve_files(repo, args.files or spec["files"])
    if args.limit:
        files = files[:args.limit]
    counts_spec = norm.get("counts", [{"node": "op_result", "exact": True}])

    def counts(tree):
        c = {}
        for n in tree.walk():
            c[n.type] = c.get(n.type, 0) + 1
        return c

    rejected, compared, mismatches = 0, 0, []
    informational = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(0, len(files), args.batch):
            batch = files[i:i + args.batch]
            pairs = []
            for src in batch:
                dst = os.path.join(tmp, f"{len(pairs)}_{os.path.basename(src)}")
                proc = subprocess.run(command + [src], capture_output=True,
                                      text=True)
                if proc.returncode != 0 or not proc.stdout.strip():
                    rejected += 1
                    continue
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(proc.stdout)
                pairs.append((src, dst))
            if not pairs:
                continue
            orig = dict(parse_batch(repo, cli, [p[0] for p in pairs]))
            gen = dict(parse_batch(repo, cli, [p[1] for p in pairs]))
            for src, dst in pairs:
                compared += 1
                co, cg = counts(orig[src]), counts(gen[dst])
                rel = os.path.relpath(src, repo)
                for entry in counts_spec:
                    node = entry["node"]
                    a, b = co.get(node, 0), cg.get(node, 0)
                    if entry.get("compare") == "ranked":
                        if a != b:
                            mismatches.append((rel, node, a, b))
                    else:
                        informational.setdefault(node, []).append(b - a)

    print(f"compared: {compared} file(s)   "
          f"not accepted by the reference tool: {rejected}")
    if rejected:
        print("  (pass pipelines, expected-error tests and split files are "
              "outside this check by nature, not a parser signal)")
    print()
    for entry in counts_spec:
        node = entry["node"]
        if entry.get("compare") == "ranked":
            bad = [m for m in mismatches if m[1] == node]
            over = [m for m in bad if m[2] > m[3]]
            under = sorted((m for m in bad if m[2] < m[3]),
                           key=lambda m: m[2] - m[3])
            status = "OK  " if not bad else "HIT "
            print(f"{status} {node}: {len(bad)} of {compared} file(s) differ "
                  f"from the reference parser")
            if entry.get("why"):
                print(f"     {entry['why'].strip()}")
            if over:
                print(f"     !! {len(over)} file(s) where the GRAMMAR FOUND MORE "
                      f"than the reference -- always a defect, triage first:")
                for rel, _n, a, b in over[:args.show]:
                    print(f"        {rel}: grammar {a}, reference {b} "
                          f"({a - b:+d})")
            if under:
                print(f"     {len(under)} file(s) where the grammar found fewer, "
                      f"largest shortfall first:")
                for rel, _n, a, b in under[:args.show]:
                    print(f"        {rel}: grammar {a}, reference {b} "
                          f"({a - b:+d})")
                if len(under) > args.show:
                    print(f"        ... {len(under) - args.show} more")
                if entry.get("caveat"):
                    print(f"     caveat: {entry['caveat'].strip()}")
        else:
            deltas = informational.get(node, [])
            if deltas:
                uniq = sorted(set(deltas))
                print(f"--   {node}: delta {uniq[0]:+d}..{uniq[-1]:+d} "
                      f"(informational; {entry.get('why', '').strip()})")
    return 1 if mismatches else 0


def cmd_census(args):
    spec = load_spec(args.spec)
    repo = os.path.abspath(args.repo)
    census = {}
    for path, tree, _lines in iter_trees(repo, spec, args):
        rel = os.path.relpath(path, repo)
        counts = {}
        for n in tree.walk():
            counts[n.type] = counts.get(n.type, 0) + 1
        census[rel] = counts
    payload = {"language": spec["language"], "files": census}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    total = {}
    for counts in census.values():
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v
    print(f"census: {len(census)} file(s), {sum(total.values())} node(s), "
          f"{len(total)} distinct type(s) -> {args.out}")
    return 0


def cmd_diff(args):
    before = json.load(open(args.before, encoding="utf-8"))["files"]
    after = json.load(open(args.after, encoding="utf-8"))["files"]

    common = set(before) & set(after)

    def totals(c):
        """Count over the shared file set only, so a changed input set does
        not masquerade as a parser behaviour change."""
        t = {}
        for f in common:
            for k, v in c[f].items():
                t[k] = t.get(k, 0) + v
        return t

    tb, ta = totals(before), totals(after)
    keys = sorted(set(tb) | set(ta))
    changed_types = [(k, tb.get(k, 0), ta.get(k, 0)) for k in keys
                     if tb.get(k, 0) != ta.get(k, 0)]

    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    # Only a file present in BOTH censuses can show a parser behaviour change.
    # After an upstream sync the added list is expected and carries no signal.
    changed = sorted(f for f in common if before[f] != after[f])

    if not changed_types and not changed and not added and not removed:
        print("no node-census change: the grammar change is inert on this "
              "file set.")
        return 0

    if changed_types:
        print(f"node types changed: {len(changed_types)}")
        for k, b, a in changed_types:
            print(f"  {k:40s} {b:7d} -> {a:7d}  ({a - b:+d})")

    print(f"\nfiles present in both, parsing differently: {len(changed)}")
    for f in changed[:args.show]:
        print(f"  {f}")
    if len(changed) > args.show:
        print(f"  ... {len(changed) - args.show} more")

    if added or removed:
        print(f"\nfile set also moved: +{len(added)} added, "
              f"-{len(removed)} removed (expected after an input sync; "
              f"no parser signal)")

    print("\nOnly the 'parsing differently' list is a blast radius. A fix "
          "aimed at one construct that moves unrelated files needs an "
          "explanation; after a sync, this list should normally be empty.")
    return 1 if (changed_types or changed) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--repo", required=True, help="grammar repository root")
        p.add_argument("--spec", required=True, help="invariant spec JSON")
        p.add_argument("--files", nargs="*", help="override the spec's globs")
        p.add_argument("--batch", type=int, default=60,
                       help="files per CLI invocation (default 60)")
        p.add_argument("--grammar-repo",
                       help="the grammar repository whose parser to use, when "
                            "--repo holds files from somewhere else (normalized "
                            "output, an attached reproducer). Defaults to --repo.")

    p = sub.add_parser("probe", help="check structural invariants")
    common(p)
    p.add_argument("--id", action="append", default=[],
                   help="only run this invariant (repeatable)")
    p.add_argument("--show", type=int, default=5,
                   help="hits to print per file (default 5)")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("corpus", help="check the corpus against its own inputs")
    p.add_argument("--repo", required=True, help="grammar repository root")
    p.add_argument("--spec", required=True, help="invariant spec JSON")
    p.add_argument("--id", action="append", default=[])
    p.add_argument("--show", type=int, default=10)
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser(
        "skeleton",
        help="compare the grammar against the language's reference parser")
    common(p)
    p.add_argument("--tool", help="override the normalizer executable")
    p.add_argument("--limit", type=int, help="only the first N files")
    p.add_argument("--show", type=int, default=10)
    p.set_defaults(func=cmd_skeleton)

    p = sub.add_parser("census", help="record a node census")
    common(p)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_census)

    p = sub.add_parser("diff", help="diff two censuses")
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--show", type=int, default=20)
    p.set_defaults(func=cmd_diff)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(f"error: {exc.code}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    sys.exit(main())
