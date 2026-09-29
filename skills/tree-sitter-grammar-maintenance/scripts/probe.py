#!/usr/bin/env python3
"""Structural-invariant prober for tree-sitter grammars.

A parse that reports no ERROR is not evidence that the tree is correct. A
permissive fallback rule can absorb valid syntax into a wrong shape and still
exit 0. This script compares the grammar against the language's own parser,
checks a parsed file set against declared structural invariants, and can take
a node census so a grammar change's blast radius is measurable instead of
assumed.

It shells out to the repository's own tree-sitter CLI and reads the standard
S-expression output. Standard library only; nothing is written into the parser
repository.

Usage:
    probe.py provenance --repo DIR [--spec FILE] [--tool PATH]
    probe.py skeleton   --repo DIR --spec FILE --tool PATH [--limit N] [--out FILE]
    probe.py corpus     --repo DIR --spec FILE [--before REV]
    probe.py probe      --repo DIR --spec FILE [--id ID]... [--files GLOB]
    probe.py census     --repo DIR --spec FILE --out FILE
    probe.py diff       BEFORE.json AFTER.json   (two censuses or two skeletons)

Exit status: 0 when every selected check holds, 1 on any hit, 2 on a tooling
or configuration failure, including a comparison that compared nothing. A hit
is a candidate for review, not a confirmed bug -- triage it against the
language's contract document.
"""

from __future__ import annotations

import argparse
import datetime
import glob as globlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_MODES = 10
# Tool output is UTF-8. Left to the locale, Windows decodes it with the ANSI
# code page and fails on the first non-ASCII string attribute.
TEXT = {"text": True, "encoding": "utf-8", "errors": "replace"}

# --------------------------------------------------------------------------
# S-expression tree
# --------------------------------------------------------------------------

_TOKEN = re.compile(
    r'(?P<open>\()'
    r'|(?P<close>\))'
    r'|(?P<field>[A-Za-z_][A-Za-z0-9_]*:)'
    r'|(?P<range>\[\s*(?P<row>\d+)\s*,\s*(?P<col>\d+)\s*\])'
    # A MISSING or UNEXPECTED node names its token quoted, and the token may
    # be a parenthesis; read unquoted, it would open or close a node.
    r'|(?P<string>"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
    r'|(?P<name>[^\s()\[\]]+)'
    r'|(?P<ws>\s+)'
)


class Node:
    __slots__ = ("type", "field", "start", "end", "children", "parent", "detail")

    def __init__(self, type_, field, parent):
        self.type = type_
        self.field = field
        self.parent = parent
        self.start = (0, 0)
        self.end = (0, 0)
        self.children = []
        self.detail = None  # the token a MISSING or UNEXPECTED node stands for

    def walk(self):
        # Pre-order with an explicit stack: nested `yield from` passed every
        # node up through one generator per level, and dominated the checks.
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))


def parse_sexp(text):
    """Build a Node tree from one file's `tree-sitter parse` S-expression."""
    root = None
    stack = []
    pending_field = None
    expect_name = False
    expect_detail = None
    ranges = 0

    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "open":
            expect_name = True
            expect_detail = None
            continue
        if expect_name and kind in ("name", "string"):
            if root is not None and not stack:
                # Keeping the newer node would silently replace a whole tree.
                raise SystemExit(
                    "parse output holds a second tree where one was expected; "
                    "refusing to guess which one belongs to the file")
            node = Node(m.group(0), pending_field, stack[-1] if stack else None)
            pending_field = None
            expect_name = False
            ranges = 0
            if stack:
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
            expect_detail = node if node.type in ("MISSING", "UNEXPECTED") else None
            continue
        if kind == "field":
            pending_field = m.group(0)[:-1]
            continue
        if kind == "range":
            expect_detail = None
            if not stack:
                continue
            r, c = int(m.group("row")), int(m.group("col"))
            ranges += 1
            if ranges == 1:
                stack[-1].start = (r, c)
            elif ranges == 2:
                stack[-1].end = (r, c)
            continue
        if kind in ("name", "string") and expect_detail is not None:
            expect_detail.detail = m.group(0)
            expect_detail = None
            continue
        if kind == "close":
            if stack:
                stack.pop()
                ranges = 0
            continue
    return root


def deepest_at(node, point):
    """The innermost node whose span contains `point` (row, byte column)."""
    while True:
        for c in node.children:
            if c.start <= point < c.end:
                node = c
                break
        else:
            return node


def shape_digest(node):
    """A short hash of a tree's named nodes, fields and ranges, in order."""
    h = hashlib.sha1()
    stack = [node]
    while stack:
        n = stack.pop()
        if n is None:
            h.update(b")")
            continue
        h.update(f"({n.field or ''}:{n.type}{n.start}{n.end}{n.detail or ''}".encode())
        stack.append(None)
        stack.extend(reversed(n.children))
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------
# Parsing a file set
# --------------------------------------------------------------------------

# After the tree of a file with a parse error, `tree-sitter parse` prints one
# more line: the file name, timings, and the file's first ERROR or MISSING node.
_SUMMARY = re.compile(
    r"^(?P<path>.*?)\s*\tParse:.*?"
    r"\((?P<type>ERROR|MISSING)"
    r"(?:\s+(?P<what>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|[^\s\[\]()]+))?"
    r"\s*\[(?P<r0>\d+), (?P<c0>\d+)\] - \[(?P<r1>\d+), (?P<c1>\d+)\]\)\s*$"
)


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


def spread_sample(files, n):
    """n files evenly spaced through the list, rather than the first n.

    Sorted paths cluster by directory, so the first n would cover a few
    dialects only. Evenly spaced picks reach across the set and stay
    deterministic, so two runs with the same --limit compare the same files.
    """
    if not n or n >= len(files):
        return files
    step = len(files) / n
    return [files[int(k * step)] for k in range(n)]


def split_parse_output(stdout, files):
    """Pair `tree-sitter parse` output with the files it was given.

    Each tree starts with an unindented `(` and its children are indented. A
    file with a parse error is followed by a summary line that belongs to no
    tree. Read as tree text, that line opens a second top-level node; kept as
    the root, it replaced the whole tree with one error node, and every check
    on that file then ran against nothing. The line is evidence all the same:
    a MISSING token is usually anonymous, so the named-node tree does not show
    it at all. It is attached to its tree instead of being dropped.
    """
    trees = []
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        if line.startswith("("):
            trees.append([[line], None])
        elif "\tParse:" in line:
            named = line.split("\tParse:")[0].strip()
            owner = files[len(trees) - 1] if 0 < len(trees) <= len(files) else None
            if owner is None or os.path.basename(named) != os.path.basename(owner):
                raise SystemExit(
                    f"parse output is misaligned: an error summary names {named!r} "
                    f"where the tree belongs to {owner!r}. Check the CLI version.")
            trees[-1][1] = _SUMMARY.match(line)
        elif line[0].isspace() and trees:
            trees[-1][0].append(line)
        else:
            raise SystemExit(
                "unrecognised line in tree-sitter parse output; refusing to "
                f"guess what it belongs to. Check the CLI version:\n  {line[:200]}")
    if len(trees) != len(files):
        raise SystemExit(
            "parse output does not line up with the input file list "
            f"({len(trees)} trees for {len(files)} files). "
            "Re-run with a smaller --batch, or check the CLI version.")
    pairs = []
    for path, (lines, summary) in zip(files, trees):
        tree = parse_sexp("\n".join(lines))
        if tree is None:
            raise SystemExit(f"could not read a tree for {path}")
        if summary:
            attach_first_error(tree, summary)
        pairs.append((path, tree))
    return pairs


def attach_first_error(tree, m):
    """Add the CLI's reported first error to the tree, unless already there."""
    start = (int(m["r0"]), int(m["c0"]))
    if any(n.type == m["type"] and n.start == start for n in tree.walk()):
        return  # an ERROR, or a named MISSING node, the tree already shows
    node = Node(m["type"], None, tree)
    node.start, node.end = start, (int(m["r1"]), int(m["c1"]))
    node.detail = m["what"]
    tree.children.append(node)


def parse_batch(repo, cmd, files):
    """Parse files in one CLI invocation; return (path, Node) pairs.

    `cmd` is the whole parse command up to the file names, from
    parse_command.
    """
    proc = subprocess.run(
        cmd + files,
        cwd=repo,
        capture_output=True,
        **TEXT,
    )
    if not proc.stdout.strip():
        raise SystemExit(
            "tree-sitter parse produced no output.\n" + proc.stderr.strip()
        )
    return split_parse_output(proc.stdout, files)


# --------------------------------------------------------------------------
# Invariants
# --------------------------------------------------------------------------


def source_lines(path, skip_re):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return scrub_lines(fh.read(), skip_re)


def scrub_lines(text, skip_re):
    """(scrubbed, raw) per row. Rows split on newlines only, as tree-sitter's do."""
    lines = []
    for raw in text.split("\n"):
        raw = raw.rstrip("\r")
        lines.append(("" if skip_re and skip_re.search(raw) else raw, raw))
    return lines


def _types(value):
    return set(value) if isinstance(value, list) else {value}


def outermost(node, types):
    """Descendants of the given types, without looking inside them."""
    found, stack = [], list(node.children)
    while stack:
        d = stack.pop()
        if d.type in types:
            found.append(d)
        else:
            stack.extend(d.children)
    return found


# Each check returns (row, detail, mode) per hit. The mode names what the hit
# looks like structurally, so that a thousand hits with one cause read as one
# finding: triage clusters, not files.


def check_line_produces(inv, tree, lines):
    """Every line matching `line` must start a node of type `node`.

    The mode is the innermost node that holds the line's first token instead
    -- `value_use in custom_operation` for a binding a body swallowed.
    """
    want = _types(inv["node"])
    rows = {n.start[0] for n in tree.walk() if n.type in want}
    pat = re.compile(inv["line"])
    hits = []
    for row, (scrubbed, raw) in enumerate(lines):
        if scrubbed and pat.search(scrubbed) and row not in rows:
            holder = deepest_at(tree, (row, len(raw) - len(raw.lstrip())))
            mode = (f"{holder.type} in {holder.parent.type}" if holder.parent
                    else f"nothing below {holder.type}")
            hits.append((row + 1, raw.strip(), mode))
    return hits


def check_no_node(inv, tree, lines):
    """No node of the listed types may appear at all (ERROR / MISSING)."""
    want = _types(inv["node"])
    hits = []
    for n in tree.walk():
        if n.type in want:
            row = n.start[0]
            raw = lines[row][1].strip() if row < len(lines) else ""
            what = f"{n.type} {n.detail}" if n.detail else n.type
            mode = what if n.detail else (
                f"{n.type} in {n.parent.type}" if n.parent else n.type)
            hits.append((row + 1, f"{what}: {raw}", mode))
    return hits


def check_span_guard(inv, tree, lines):
    """A node must not span a line that starts a new sibling construct.

    This is the machine-checkable form of a boundary-preservation rule: a
    permissive body may look however it likes, but it may not swallow the
    following construct.

    For a node holding one of the `check_after_last` types -- a region, say --
    only the rows after the last one are checked. Rows up to its close belong
    to the node's own header and to nested constructs, which are checked as
    nodes of their own; a header wrapped across lines can legitimately start
    a line with `%b = %y`. After the close nothing of the node's own is left
    that could start such a line, so a body still running there has absorbed
    the next construct. Exempting these nodes outright hid exactly that.
    """
    want = _types(inv["node"])
    after = sorted(set(inv.get("check_after_last", [])))
    pat = re.compile(inv["line"])
    hits = []
    for n in tree.walk():
        if n.type not in want or n.start[0] == n.end[0]:
            continue
        first = n.start[0] + 1
        ends = [d.end[0] for d in outermost(n, set(after))] if after else []
        if ends:
            first = max(first, max(ends) + 1)
            mode = f"{n.type} running on after its {'/'.join(after)}"
        else:
            mode = n.type + (f" without a {'/'.join(after)}" if after else "")
        for row in range(first, min(n.end[0] + 1, len(lines))):
            scrubbed, raw = lines[row]
            if scrubbed and pat.search(scrubbed):
                hits.append(
                    (row + 1, f"absorbed into {n.type} opened on line "
                              f"{n.start[0] + 1}: {raw.strip()}", mode)
                )
                break
    return hits


CHECKS = {
    "line_produces": check_line_produces,
    "no_node": check_no_node,
    "span_guard": check_span_guard,
}


def examples(hits, n):
    """Up to n hits, one per file before any file gets a second."""
    by_file = {}
    for h in hits:
        by_file.setdefault(h[0], []).append(h)
    queues = sorted(by_file.values(), key=len, reverse=True)
    out, depth = [], 0
    while len(out) < n and any(depth < len(q) for q in queues):
        for q in queues:
            if depth < len(q) and len(out) < n:
                out.append(q[depth])
        depth += 1
    return out


# --------------------------------------------------------------------------
# Measuring
# --------------------------------------------------------------------------


def read_bytes_lines(path):
    """A file's rows as bytes: tree-sitter columns are byte offsets."""
    with open(path, "rb") as fh:
        return fh.read().split(b"\n")


def node_text(node, lines):
    """The source text a node spans, given its file's read_bytes_lines."""
    (r0, c0), (r1, c1) = node.start, node.end
    if r0 >= len(lines):
        return ""
    if r0 == r1:
        chunk = lines[r0][c0:c1]
    else:
        tail = lines[r1][:c1] if r1 < len(lines) else b""
        chunk = b"\n".join([lines[r0][c0:]] + lines[r0 + 1:r1] + [tail])
    return chunk.decode("utf-8", "replace")


def measure(tree, entry, lines):
    """How much of `entry["node"]` a tree holds.

    A plain node count by default. With `weight_regex`, a node whose text
    matches counts as the integer the regex captures and any other node as
    one -- so `%0:2` counts as the two results it binds, the same as `%a, %b`.
    """
    weight = re.compile(entry["weight_regex"]) if entry.get("weight_regex") else None
    total = 0
    for n in tree.walk():
        if n.type != entry["node"]:
            continue
        m = weight.search(node_text(n, lines)) if weight else None
        total += int(m.group(1)) if m else 1
    return total


def census_entry(tree):
    """A file's node counts and the digest of its shape."""
    counts = {}
    for n in tree.walk():
        counts[n.type] = counts.get(n.type, 0) + 1
    return counts, shape_digest(tree)


# --------------------------------------------------------------------------
# Tools and provenance
# --------------------------------------------------------------------------


def _run(cmd, cwd=None):
    """stdout of a command that succeeded, stripped; None otherwise."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, **TEXT,
                              timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def resolve_tool(tool):
    """Absolute path of a declared tool, or None if it cannot be executed."""
    if os.path.isfile(tool) and os.access(tool, os.X_OK):
        return os.path.abspath(tool)
    found = shutil.which(tool)
    return os.path.abspath(found) if found else None


def tool_version(tool):
    """The line of `tool --version` that names a version, if any."""
    try:
        proc = subprocess.run([tool, "--version"], capture_output=True,
                              timeout=60, **TEXT)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = [ln.strip() for ln in (proc.stdout + proc.stderr).splitlines()
             if ln.strip()]
    for ln in lines:
        if "version" in ln.lower():
            return ln
    return lines[0] if lines else ""


def declared_tool(tool, norm):
    """The reference parser the user declared, verified; never a search."""
    if not tool:
        hint = norm.get("tool_hint", "the language's own parser")
        raise SystemExit(
            "no reference parser declared.\n"
            "Do NOT search for one. A comparison against a binary nobody chose\n"
            "reads as authoritative while resting on nothing; the value of this\n"
            "evidence is that its provenance is known.\n\n"
            f"Ask the user which tool to use -- {hint} --\n"
            "then pass it with --tool, and record the path in the audit record\n"
            "so the next pass can reuse it.")
    path = resolve_tool(tool)
    if path is None:
        raise SystemExit(
            f"declared reference parser is not executable: {tool}\n"
            "Confirm the path with the user rather than substituting another.")
    return path


def run_self_check(tool, norm, spec, tmp):
    """Refuse a declared tool that is not the kind of tool the spec needs.

    A wrong answer to "which tool?" must fail loudly here instead of quietly
    producing numbers: LLVM's `opt`, for one, is not an MLIR tool at all.
    """
    check = norm.get("self_check")
    if not check:
        raise SystemExit(
            "the spec's normalizer declares no self_check; a declared tool must "
            "be verified before its output is trusted")
    ext = os.path.splitext(spec["files"][0])[1] if spec.get("files") else ""
    path = os.path.join(tmp, "self-check" + ext)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(check["input"])
    proc = subprocess.run([tool] + norm.get("args", []) + [path],
                          capture_output=True, **TEXT)
    if proc.returncode != 0 or check["expect"] not in proc.stdout:
        raise SystemExit(
            f"{tool} failed the spec's self-check: it did not normalize\n"
            f"    {' '.join(check['input'].split())}\n"
            f"into output containing {check['expect']}. It is probably not the\n"
            "right tool. Ask the user for the right one; do not fall back to\n"
            f"searching.\nstderr: {proc.stderr.strip()[:200]}")


def locked_cli(repo):
    """The tree-sitter-cli version CI resolves, and where that came from."""
    lock = os.path.join(repo, "package-lock.json")
    if os.path.isfile(lock):
        with open(lock, encoding="utf-8") as fh:
            entry = json.load(fh).get("packages", {}).get(
                "node_modules/tree-sitter-cli", {})
        if entry.get("version"):
            return entry["version"], "package-lock.json"
        return None, "package-lock.json has no tree-sitter-cli entry"
    try:
        with open(os.path.join(repo, "package.json"), encoding="utf-8") as fh:
            want = json.load(fh).get("devDependencies", {}).get("tree-sitter-cli")
    except (OSError, json.JSONDecodeError):
        want = None
    if want:
        return None, (f"no package-lock.json; package.json asks for `{want}`, so "
                      "CI takes the newest release in that range")
    return None, "no package-lock.json and no tree-sitter-cli dependency"


CI_CLI_PIN = re.compile(r"^\s*tree-sitter-(?:ref|version)\s*:\s*(\S.*?)\s*$", re.M)
CI_CLI_LITERAL = re.compile(r"[\"']?v?(\d+\.\d+\.\d+)[\"']?$")


def ci_cli_pins(repo):
    """[(file, line, version or None, raw value)] for each CLI input CI sets.

    The lock file says what local runs use; a workflow may still install
    another release. When CI pinned 0.26.12 under a 0.27.0 lock, its fuzzer
    compared a `:cst` corpus case as an S-expression and failed a correct
    tree -- no local measurement could have shown that. A literal pin is
    synced by hand, since dependency bots bump the lock and not the workflow;
    a value computed at run time (version None) is read from somewhere else,
    which is the cure, and the place it reads is what to check.
    """
    pins = []
    for sub in ("workflows", "actions"):
        pattern = os.path.join(repo, ".github", sub, "**", "*.y*ml")
        for path in sorted(globlib.glob(pattern, recursive=True)):
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in CI_CLI_PIN.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                literal = CI_CLI_LITERAL.fullmatch(m.group(1))
                pins.append((os.path.relpath(path, repo), line,
                             literal.group(1) if literal else None, m.group(1)))
    return pins


def skill_digest():
    """A hash of this skill's own files: the same for a checkout or a copy,
    whatever line endings the checkout chose."""
    h = hashlib.sha1()
    for dirpath, dirnames, filenames in os.walk(SKILL_DIR):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d != "__pycache__")
        for name in sorted(filenames):
            if name.startswith(".") or name.endswith(".pyc"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, SKILL_DIR).replace(os.sep, "/")
            h.update(rel.encode() + b"\0")
            with open(path, "rb") as fh:
                h.update(fh.read().replace(b"\r\n", b"\n"))
            h.update(b"\0")
    return h.hexdigest()[:12]


def skill_identity():
    name = os.path.basename(SKILL_DIR)
    if _run(["git", "rev-parse", "--is-inside-work-tree"], SKILL_DIR) == "true":
        sha = _run(["git", "log", "-1", "--format=%h", "--", "."], SKILL_DIR)
        dirty = _run(["git", "status", "--porcelain", "--", "."], SKILL_DIR)
        where = f"@ `{sha}`" if sha else "not committed yet"
        if dirty:
            where += " with local changes"
    else:
        where = "installed copy"
    return f"`{name}` {where}, content `{skill_digest()}`"


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
    for inv in spec["invariants"]:
        if "allow_if_child" in inv:
            raise SystemExit(
                f"invariant {inv.get('id')!r} uses allow_if_child, which exempted "
                "whole nodes and hid bodies that run on past their own region. "
                "Use check_after_last instead.")
    return spec


def resolve_cli(spec, grammar_repo):
    """The command that runs the grammar repository's tree-sitter CLI.

    A spec's `cli` is used as given. Otherwise the repository's own
    node_modules/.bin/tree-sitter -- the binary `npx --no-install` would pick
    -- is called directly, which saves starting npm on every call; npx is
    the fallback. Looking names up with shutil.which also finds the `.cmd`
    shims npm installs on Windows, which a bare name handed to subprocess
    does not.
    """
    if spec.get("cli"):
        cli = list(spec["cli"])
        cli[0] = shutil.which(cli[0]) or cli[0]
        return cli
    local = shutil.which("tree-sitter",
                         path=os.path.join(grammar_repo, "node_modules", ".bin"))
    if local:
        return [local]
    return [shutil.which("npx") or "npx", "--no-install", "tree-sitter"]


def parse_command(spec, grammar_repo):
    """The command that parses with this checkout's parser, and no other.

    `tree-sitter parse FILE` picks a grammar by file extension among every
    grammar the CLI knows -- the ones under `parser-directories` in its
    config too -- and caches one compiled parser per language name. In a
    second checkout of the same grammar, a worktree holding a change, it
    parsed with the first checkout's grammar: `--grammar-path` did not
    change that, and neither did a separate TREE_SITTER_LIBDIR. A
    before/after comparison then measures one parser twice. So build this
    checkout's parser once, keyed by the content of its `src/`, outside the
    repository, and hand it to `parse --lib-path`.
    """
    cli = resolve_cli(spec, grammar_repo)
    digest = hashlib.sha256()
    src = os.path.join(grammar_repo, "src")
    for root, dirs, names in os.walk(src):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(root, name)
            digest.update(os.path.relpath(path, src).replace(os.sep, "/").encode())
            with open(path, "rb") as fh:
                digest.update(fh.read())
    ext = {"win32": ".dll", "darwin": ".dylib"}.get(sys.platform, ".so")
    cache = os.environ.get("PROBE_PARSER_CACHE") or os.path.join(
        tempfile.gettempdir(), "tree-sitter-probe-parsers")
    lib = os.path.join(cache, f"{spec['language']}-{digest.hexdigest()[:16]}{ext}")
    if not os.path.isfile(lib):
        os.makedirs(cache, exist_ok=True)
        part = f"{lib[:-len(ext)]}.{os.getpid()}{ext}"
        proc = subprocess.run(cli + ["build", "-o", part], cwd=grammar_repo,
                              capture_output=True, **TEXT)
        if proc.returncode != 0 or not os.path.isfile(part):
            raise SystemExit(f"`{' '.join(cli)} build` failed in {grammar_repo}:\n"
                             + (proc.stderr or proc.stdout).strip())
        try:
            os.replace(part, lib)
        except OSError:
            if not os.path.isfile(lib):  # another run built it first otherwise
                raise
    return cli + ["parse", "--lib-path", lib, "--lang-name", spec["language"]]


def grammar_cwd(args, repo):
    # The CLI resolves a language from the grammar repository it runs in, so it
    # is run from there even when the files under audit live somewhere else --
    # reference-normalized output, a bug report attachment, a consumer's
    # sources. Paths handed to it are absolute, so the cwd only selects the
    # grammar.
    return os.path.abspath(getattr(args, "grammar_repo", None) or repo)


def spec_files(repo, spec, args):
    patterns = args.files or spec["files"]
    files = resolve_files(repo, patterns)
    if not files:
        raise SystemExit(f"no files matched: {patterns}")
    return files


def _reduce_batch(job):
    """Parse one batch and keep only what the reducer extracts per file."""
    reducer, cwd, cmd, files, context = job
    return [(path, reducer(path, tree, context))
            for path, tree in parse_batch(cwd, cmd, files)]


def map_files(cwd, cmd, files, args, reducer, context):
    """Yield (path, reducer(path, tree, context)) for each file, in order.

    Building trees from the CLI's output is most of a run's time, so batches
    are parsed in worker processes. Trees stay in the worker; only the small
    result a reducer extracts -- hits, counts -- comes back, and results
    arrive in input order whatever the number of workers.
    """
    jobs = [(reducer, cwd, cmd, files[i:i + args.batch], context)
            for i in range(0, len(files), args.batch)]
    if args.jobs > 1 and len(jobs) > 1:
        try:
            pool = ProcessPoolExecutor(max_workers=min(args.jobs, len(jobs)))
        except (OSError, NotImplementedError):
            pool = None  # no process support here; parse in this process
        if pool is not None:
            with pool:
                for results in pool.map(_reduce_batch, jobs):
                    yield from results
            return
    for job in jobs:
        yield from _reduce_batch(job)


def probe_file(path, tree, context):
    """Each selected invariant's hits in one file."""
    selected, skip_line = context
    lines = source_lines(path, re.compile(skip_line) if skip_line else None)
    return [CHECKS[inv["kind"]](inv, tree, lines) for inv in selected]


def census_file(path, tree, context):
    """A file's node counts and shape digest."""
    return census_entry(tree)


def measure_file(path, tree, counts_spec):
    """What the tree holds of each quantity the skeleton compares."""
    lines = read_bytes_lines(path)
    return [measure(tree, entry, lines) for entry in counts_spec]


def cmd_provenance(args):
    """Print what produced this pass's numbers, ready for the audit record.

    A reference-parser line is only reusable if it holds an absolute path, and
    one pass's numbers only compare with another's if the toolchain and the
    method behind them are known. Typed by hand, these went missing.
    """
    repo = os.path.abspath(args.repo)
    spec = load_spec(args.spec) if args.spec else {}
    cli = resolve_cli(spec, repo)
    status = 0

    sha = _run(["git", "rev-parse", "--short", "HEAD"], repo)
    if sha:
        branch = _run(["git", "branch", "--show-current"], repo) or "(detached HEAD)"
        dirty = _run(["git", "status", "--porcelain", "--untracked-files=no"], repo)
        commit = f"`{branch}` @ `{sha}`" + (", with uncommitted changes" if dirty else "")
    else:
        commit = "not a git checkout"

    found = re.search(r"\d+\.\d+\.\d+", _run(cli + ["--version"], repo) or "")
    locked, source = locked_cli(repo)
    if not found:
        cli_line = (f"cannot run `{' '.join(cli)} --version` -- repair the "
                    "toolchain before measuring anything")
        status = 2
    elif locked and locked != found.group(0):
        cli_line = (f"`{found.group(0)}`, lock says `{locked}` -- MISMATCH: these "
                    "numbers are not from the parser CI builds")
        status = 1
    elif locked:
        cli_line = f"`{found.group(0)}`, lock says `{locked}`"
    else:
        cli_line = f"`{found.group(0)}`; {source}"

    pins = ci_cli_pins(repo)
    want = locked or (found.group(0) if found else None)
    literal = [p for p in pins if p[2]]
    derived = [p for p in pins if not p[2]]
    drifted = [p for p in literal if want and p[2] != want]
    if not pins:
        ci_line = "no `tree-sitter-ref` / `tree-sitter-version` in `.github`"
    elif drifted:
        ci_line = ("MISMATCH: " + ", ".join(f"`{v}` in {f}:{n}" for f, n, v, _ in drifted)
                   + f" -- CI runs another CLI than `{want}`")
        status = max(status, 1)
    elif literal:
        ci_line = (f"`{want}` in {len(literal)} literal pin(s) -- synced by hand, "
                   "so the next lock bump drifts from it")
    else:
        f, n, _, raw = derived[0]
        ci_line = (f"computed at run time (`{raw}` in {f}:{n}) -- confirm it "
                   "reads the lock")

    if args.tool:
        path = resolve_tool(args.tool)
        if path is None:
            tool_line = f"`{args.tool}` is not executable -- confirm it with the user"
            status = 2
        else:
            version = tool_version(path)
            tool_line = f"`{path}`" + (f" ({version})" if version else "")
    else:
        tool_line = "not declared -- the reference comparison did not run"

    print(f"- **Date:** {datetime.date.today().isoformat()}")
    print(f"- **Branch / commit:** {commit}")
    print(f"- **CLI version:** {cli_line}")
    print(f"- **CLI in CI:** {ci_line}")
    print(f"- **Reference parser:** {tool_line}")
    print(f"- **Skill:** {skill_identity()}")
    return status


def cmd_probe(args):
    spec = load_spec(args.spec)
    repo = os.path.abspath(args.repo)
    selected = [
        inv for inv in spec["invariants"]
        if not args.id or inv["id"] in args.id
    ]
    if not selected:
        raise SystemExit(f"no invariant matched --id {args.id}")
    for inv in selected:
        if inv["kind"] not in CHECKS:
            raise SystemExit(f"unknown invariant kind: {inv['kind']}")

    files = spec_files(repo, spec, args)
    cwd = grammar_cwd(args, repo)
    results = {inv["id"]: [] for inv in selected}
    n_files = 0
    for path, per_inv in map_files(cwd, parse_command(spec, cwd), files, args,
                                   probe_file, (selected, spec.get("skip_line"))):
        n_files += 1
        rel = os.path.relpath(path, repo)
        for inv, hits in zip(selected, per_inv):
            for row, detail, mode in hits:
                results[inv["id"]].append((rel, row, detail, mode))

    total = 0
    for inv in selected:
        hits = results[inv["id"]]
        total += len(hits)
        layer = inv.get("layer", "?")
        if not hits:
            print(f"OK   {inv['id']}  (layer {layer})  0 hit(s)")
            continue
        modes = {}
        for hit in hits:
            modes.setdefault(hit[3], []).append(hit)
        print(f"HIT  {inv['id']}  (layer {layer})  {len(hits)} hit(s) in "
              f"{len({h[0] for h in hits})} file(s), {len(modes)} mode(s)")
        if not args.show:
            continue
        print(f"     {inv.get('why', '').strip()}")
        ranked = sorted(modes.items(), key=lambda kv: -len(kv[1]))
        for mode, group in ranked[:MAX_MODES]:
            print(f"     {len(group)} hit(s) in {len({h[0] for h in group})} "
                  f"file(s): {mode}")
            for rel, row, detail, _mode in examples(group, args.show):
                print(f"       {rel}:{row}: {detail}")
        if len(ranked) > MAX_MODES:
            print(f"     ... {len(ranked) - MAX_MODES} more mode(s)")
    print(f"\n{n_files} file(s) parsed, {total} hit(s) total.")
    print("A hit is a candidate. Triage each mode against the contract document "
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


# A `:cst` case records `parse --cst` output, one node per line after its
# range -- `1:0  - 1:2      lhs: op_result` -- instead of an S-expression.
CST_RANGE = r"\d+:\d+\s+-\s+\d+:\d+"


def is_cst(tree):
    return re.match(r"\s*" + CST_RANGE, tree) is not None


def corpus_balance(inv, src, tree):
    """(how many the input binds, how many nodes the expected tree holds).

    A line matching `line` counts once, or -- with `count_regex` -- once per
    match of that regex inside the matched text, so `%a, %b =` counts two
    and `%x:2 =` one, exactly as many as the nodes a correct tree holds.
    Counted by line, a line binding several names covers for a binding
    lost elsewhere in the same case.
    """
    pat = re.compile(inv["line"])
    each = re.compile(inv["count_regex"]) if inv.get("count_regex") else None
    want = 0
    for ln in src.splitlines():
        m = pat.match(ln)
        if m:
            want += sum(1 for _ in each.finditer(m.group(0))) if each else 1
    if is_cst(tree):
        got = len(re.findall(r"^\s*%s\s+(?:\w+:\s+)?%s\b"
                             % (CST_RANGE, re.escape(inv["node"])), tree, re.M))
    else:
        got = len(re.findall(r"\(%s\b" % re.escape(inv["node"]), tree))
    return want, got


CORPUS_LEAF = re.compile(r"\((\w+)\)")
CORPUS_INNER = re.compile(r"\((\w+)(?=\s)")


def corpus_at(repo, rev, paths):
    """{(corpus file, case name): (input, tree)} as committed at `rev`.

    A file absent at `rev` contributes nothing, so its cases read as new.
    """
    cases = {}
    for path in paths:
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        res = subprocess.run(["git", "-C", repo, "show", f"{rev}:{rel}"],
                             capture_output=True, encoding="utf-8",
                             errors="replace")
        if res.returncode != 0:
            continue
        for name, src, tree in split_corpus(res.stdout):
            cases[(os.path.basename(path), name)] = (src, tree)
    return cases


def corpus_shape_diff(before, after):
    """Sort the changed cases of a regenerated corpus by what moved.

    `--update` rewrites expected trees with no judgement in it. A fix that
    only regroups -- a node moving to its neighbour's parent -- keeps every
    input and the document order of every leaf, and changes only the inner
    node types it meant to; such cases group by those types, and each group
    is one thing to confirm. A case whose input or leaf order moved is not a
    regrouping, and is where the reading starts. Comparing preorder instead
    would flag every correct regrouping, because the moved node's position
    in a preorder walk changes with its parent.
    """
    groups, flagged = {}, []
    for key in sorted(set(before) & set(after)):
        (b_src, b_tree), (a_src, a_tree) = before[key], after[key]
        if b_src.strip() == a_src.strip() and b_tree.split() == a_tree.split():
            continue
        if b_src.strip() != a_src.strip():
            flagged.append((key, "input changed"))
        elif is_cst(b_tree) or is_cst(a_tree):
            flagged.append((key, "a `:cst` case, whose anonymous tokens are the "
                                 "point; compare it by eye"))
            continue
        elif CORPUS_LEAF.findall(b_tree) != CORPUS_LEAF.findall(a_tree):
            flagged.append((key, "leaves moved, appeared or vanished"))
        delta = {}
        for t in CORPUS_INNER.findall(a_tree):
            delta[t] = delta.get(t, 0) + 1
        for t in CORPUS_INNER.findall(b_tree):
            delta[t] = delta.get(t, 0) - 1
        delta = {t: d for t, d in delta.items() if d}
        g = groups.setdefault(tuple(sorted(delta)), {"cases": [], "delta": {}})
        g["cases"].append(key)
        for t, d in delta.items():
            g["delta"][t] = g["delta"].get(t, 0) + d
    new = sorted(set(after) - set(before))
    gone = sorted(set(before) - set(after))
    return groups, flagged, new, gone


def describe_delta(delta):
    return ", ".join(f"{t} {d:+d}" for t, d in sorted(delta.items())) or \
        "no node type moved (nesting or a field changed)"


def report_corpus_diff(repo, rev, files, show):
    before = corpus_at(repo, rev, files)
    after = {}
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for name, src, tree in split_corpus(fh.read()):
                after[(os.path.basename(path), name)] = (src, tree)
    groups, flagged, new, gone = corpus_shape_diff(before, after)
    n_changed = sum(len(g["cases"]) for g in groups.values())
    print(f"\ncorpus against {rev}: {n_changed} case(s) changed, "
          f"{len(new)} new, {len(gone)} removed")
    if n_changed:
        print(f"  grouped by the inner node types that moved "
              f"({len(groups)} group(s)):")
    ordered = sorted(groups.values(), key=lambda g: (-len(g["cases"]),
                                                     sorted(g["delta"])))
    for g in ordered:
        print(f"    {len(g['cases'])} case(s): {describe_delta(g['delta'])}")
        for f, name in g["cases"][:min(show, 3)]:
            print(f"      {f}: {name!r}")
        if show and len(g["cases"]) > min(show, 3):
            print(f"      ... {len(g['cases']) - min(show, 3)} more")
    for (f, name), why in flagged:
        print(f"  !! {f}: {name!r} -- {why}; read this case first")
    for f, name in new[:show]:
        print(f"  new: {f}: {name!r} -- hand-written, so read it against the "
              f"contract, not against this diff")
    return len(flagged)


def cmd_corpus(args):
    """Check the corpus against itself: no parser is needed.

    The corpus is the persistent AST contract. If its expected trees were
    accepted from `--update` without being read, a parser defect is recorded
    there as the intended result, and every gate goes green on the wrong tree.
    This compares each case's input against its own expected tree: exactly
    when the invariant counts what each line binds, and only for a shortfall
    when it counts lines. With `--before REV` it also sorts the cases that
    changed since that revision by what moved.
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
        exact = bool(inv.get("count_regex"))
        hits, n_cases = [], 0
        for path in files:
            rel = os.path.relpath(path, repo)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for name, src, tree in split_corpus(text):
                want, got = corpus_balance(inv, src, tree)
                if not want:
                    continue
                n_cases += 1
                if got < want or (exact and got > want):
                    hits.append((rel, name, want, got))
        total += len(hits)
        if n_cases == 0:
            print(f"NONE {inv['id']}: no corpus case exercises this at all -- "
                  f"that is a coverage gap, not a pass")
            total += 1
            continue
        short = [h for h in hits if h[3] < h[2]]
        over = [h for h in hits if h[3] > h[2]]
        status = "OK  " if not hits else "HIT "
        print(f"{status} {inv['id']}  (layer {inv.get('layer', '?')})  "
              f"{len(hits)}/{n_cases} case(s): {len(short)} short by "
              f"{sum(w - g for _r, _n, w, g in short)} {inv['node']}"
              + (f", {len(over)} over" if exact else ""))
        if hits and args.show:
            print(f"     {inv.get('why', '').strip()}")
            hits.sort(key=lambda h: -abs(h[3] - h[2]))
            for rel, name, want, got in hits[:args.show]:
                print(f"       {rel}: {name!r}  {want} in input, "
                      f"{got} in expected tree")
            if len(hits) > args.show:
                print(f"       ... {len(hits) - args.show} more")
    if total and args.show:
        print("\nAn expected tree that contradicts its own input was accepted "
              "without being read. Fix the grammar first, then regenerate and "
              "read the corpus diff -- never the other way round.")
    if args.before:
        total += report_corpus_diff(repo, args.before, files, args.show)
    return 1 if total else 0


def cmd_skeleton(args):
    """Compare the parser against the language's own reference implementation.

    There is no AST to diff against: a compiler's in-memory IR is what is left
    *after* parsing, with the surface syntax already consumed, so it has no
    node-for-node correspondence with a CST. What it does still agree on is the
    skeleton -- how many results each operation binds, how the regions and
    blocks nest. Those are decided by syntax and survive parsing.

    So rather than mapping a CST onto an IR (a second interpreter, which would
    then need verifying itself), normalize the input with the reference tool and
    parse *its* output with the same grammar. Both sides are then CSTs and the
    mapping is the identity. A disagreement is the grammar reading the program
    differently from the language's own parser.

    Compare quantities the printer preserves, not node counts that happen to
    track them: a printer may regroup what the source spelled out, as MLIR's
    generic form prints `%a, %b = ...` as `%0:2 = ...`. A spec entry's
    `weight_regex` makes the count mean the quantity.

    Deliberately no discovery of the tool. Searching PATH lands on whatever is
    there -- for MLIR, possibly LLVM's `opt`, which is a different tool
    entirely -- and yields confident numbers whose provenance nobody checked.

    This only reaches inputs the reference tool accepts. Pass pipelines and
    expected-error tests are outside it, which is why the broad ERROR/MISSING
    sweep still earns its place.
    """
    spec = load_spec(args.spec)
    norm = spec.get("normalizer")
    if not norm:
        raise SystemExit("spec declares no normalizer; skeleton needs one")
    counts_spec = norm.get("counts")
    if not counts_spec:
        raise SystemExit("the spec's normalizer declares no counts to compare")
    repo = os.path.abspath(args.repo)
    cwd = grammar_cwd(args, repo)
    tool = declared_tool(args.tool, norm)
    command = [tool] + norm.get("args", [])

    files = spread_sample(resolve_files(repo, args.files or spec["files"]),
                          args.limit)
    if not files:
        raise SystemExit("no files matched")

    def normalize(src):
        proc = subprocess.run(command + [src], capture_output=True, **TEXT)
        return proc.stdout if proc.returncode == 0 and proc.stdout.strip() else None

    rejected, compared = 0, 0
    measured = [[] for _ in counts_spec]  # per entry: (rel, grammar, reference)
    with tempfile.TemporaryDirectory() as tmp:
        run_self_check(tool, norm, spec, tmp)
        version = tool_version(tool)
        print(f"reference parser: {tool}" + (f"  ({version})" if version else ""))
        # One tool process per file, side by side; map keeps input order.
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            outputs = list(pool.map(normalize, files))
        pairs, declined = [], []
        for k, (src, out) in enumerate(zip(files, outputs)):
            if out is None:
                rejected += 1
                declined.append(os.path.relpath(src, repo))
                continue
            dst = os.path.join(tmp, f"{k}_{os.path.basename(src)}")
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(out)
            pairs.append((src, dst))
        both = [path for pair in pairs for path in pair]
        counts = dict(map_files(cwd, parse_command(spec, cwd), both, args,
                                measure_file, counts_spec)) if both else {}
        for src, dst in pairs:
            compared += 1
            rel = os.path.relpath(src, repo)
            for k in range(len(counts_spec)):
                measured[k].append((rel, counts[src][k], counts[dst][k]))

    print(f"compared: {compared} file(s)   "
          f"not accepted by the reference tool: {rejected}")
    if compared == 0:
        # An empty comparison must never read as a pass. Reporting OK here is
        # how an audit ends up green having checked nothing.
        print(
            "\nNOTHING WAS COMPARED. This is not a pass.\n"
            "Every selected file was declined by the reference parser, so this\n"
            "evidence line produced no result at all. Usual causes: the file\n"
            "selection is too narrow (a --limit that lands only on pass\n"
            "pipelines or expected-error tests), or the tool is from a release\n"
            "whose syntax has moved. Widen the selection, or say in the report\n"
            "that the reference comparison did not run."
        )
        return 2
    if rejected:
        print("  (inputs the tool declines -- pass pipelines, expected-error "
              "tests, syntax from another release -- are a coverage limit, "
              "not a parser signal)")
    if args.out:
        write_skeleton(args.out, spec, tool, version, counts_spec, measured,
                       declined)
        print(f"  -> {args.out}")
    print()
    differs = False
    for entry, rows in zip(counts_spec, measured):
        differs = report_counts(entry, rows, compared, args.show) or differs
    return 1 if differs else 0


def write_skeleton(out, spec, tool, version, counts_spec, measured, declined):
    """Save one skeleton run for `diff`: a scratch file, like a census."""
    files = {}
    for rows in measured:
        for rel, grammar, reference in rows:
            files.setdefault(rel, []).append([grammar, reference])
    payload = {
        "kind": "skeleton",
        "language": spec["language"],
        "tool": tool,
        "tool_version": version,
        "counts": [{"node": e["node"], "label": e.get("label"),
                    "compare": e.get("compare", "ranked")} for e in counts_spec],
        "declined": declined,
        "files": files,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)


def diff_skeletons(before, after, show):
    """Compare two skeleton runs taken around a grammar change.

    Per file and quantity, the gap is grammar minus reference, and a fix
    should only move gaps towards zero. Three things say otherwise, and each
    is flagged: a file whose reference side moved, a file that moved further
    from the reference, and a file newly above it. The reference side is the
    grammar reading the tool's generic output, so a change there means the
    edit reached the generic path the whole comparison stands on -- the
    control that must not move. Further, on a `ceiling` quantity, is also
    how a newly swallowed operation shows: no single run can see it.
    """
    keys_b = [(e["node"], e.get("label")) for e in before["counts"]]
    keys_a = [(e["node"], e.get("label")) for e in after["counts"]]
    fb, fa = before["files"], after["files"]
    common = sorted(set(fb) & set(fa))
    print(f"skeleton diff: {len(common)} file(s) compared in both runs")
    worse = False
    for key in (k for k in keys_b if k in keys_a):
        i, j = keys_b.index(key), keys_a.index(key)
        moved, above, further, closer = [], [], [], []
        for rel in common:
            (gb, rb), (ga, ra) = fb[rel][i], fa[rel][j]
            if rb != ra:
                moved.append((rel, f"reference {rb} -> {ra}", abs(ra - rb)))
            elif ga > ra and gb <= rb:
                above.append((rel, f"gap {gb - rb:+d} -> {ga - ra:+d}", ga - ra))
            elif abs(ga - ra) > abs(gb - rb):
                further.append((rel, f"gap {gb - rb:+d} -> {ga - ra:+d}",
                                abs(ga - ra) - abs(gb - rb)))
            elif abs(ga - ra) < abs(gb - rb):
                closer.append((rel, f"gap {gb - rb:+d} -> {ga - ra:+d}",
                               abs(gb - rb) - abs(ga - ra)))
        bad = bool(moved or above or further)
        worse = worse or bad
        label = key[0] + (f", {key[1]}" if key[1] else "")
        print(f"{'HIT ' if bad else 'OK  '} {label}: {len(closer)} closer, "
              f"{len(further)} further, {len(above)} newly above the "
              f"reference, reference side moved in {len(moved)}")
        for title, rows in (
                ("reference side moved -- the change reached the generic path",
                 moved),
                ("newly above the reference -- always a defect", above),
                ("further from the reference", further),
                ("closer to the reference", closer)):
            if rows and show:
                print(f"     {title}:")
                for rel, what, _size in sorted(rows, key=lambda r: -r[2])[:show]:
                    print(f"        {rel}: {what}")
                if len(rows) > show:
                    print(f"        ... {len(rows) - show} more")
    only = len(set(fb) ^ set(fa))
    if only:
        print(f"\ncompared in one run only: {only} file(s) -- a different "
              "tool, or inputs that moved; no parser signal")
    return 1 if worse else 0


def report_counts(entry, rows, compared, show):
    """Print one compared quantity; return whether anything was flagged.

    `rows` holds (file, grammar count, reference count). How to read a
    difference depends on the entry's `compare`:

    ranked   -- both directions are leads. Above the reference is always a
                defect; below it is ranked, largest shortfall first.
    ceiling  -- the reference may legitimately count more, for the reason in
                `why`; that direction is summarised, not ranked. A grammar
                count above it has no such reason and is flagged. Treating
                both directions as noise hid a grammar that invents regions.
    """
    label = entry["node"] + (f", {entry['label']}" if entry.get("label") else "")
    over = sorted((r for r in rows if r[1] > r[2]), key=lambda r: r[2] - r[1])
    under = sorted((r for r in rows if r[1] < r[2]), key=lambda r: r[1] - r[2])
    mode = entry.get("compare", "ranked")
    if mode not in ("ranked", "ceiling"):
        raise SystemExit(f"unknown compare mode for {entry['node']}: {mode}")
    flagged = over if mode == "ceiling" else over + under

    status = "HIT " if flagged else "OK  "
    if mode == "ranked":
        print(f"{status} {label}: {len(flagged)} of {compared} file(s) differ "
              f"from the reference parser, {len(over)} above it and "
              f"{len(under)} below")
    else:
        print(f"{status} {label}: {len(over)} of {compared} file(s) above the "
              f"reference; {len(under)} below it, as expected "
              f"({entry.get('why', '').strip()})")
    if not show:
        return bool(flagged)
    if mode == "ranked" and entry.get("why") and flagged:
        print(f"     {entry['why'].strip()}")
    if over:
        print(f"     !! {len(over)} file(s) where the GRAMMAR COUNTS MORE than the "
              f"reference -- structure the language's parser does not see; "
              f"triage first:")
        for rel, a, b in over[:show]:
            print(f"        {rel}: grammar {a}, reference {b} ({a - b:+d})")
        if len(over) > show:
            print(f"        ... {len(over) - show} more")
    if mode == "ranked" and under:
        print(f"     {len(under)} file(s) where the grammar counts fewer, "
              f"largest shortfall first:")
        for rel, a, b in under[:show]:
            print(f"        {rel}: grammar {a}, reference {b} ({a - b:+d})")
        if len(under) > show:
            print(f"        ... {len(under) - show} more")
        if entry.get("caveat"):
            print(f"     caveat: {entry['caveat'].strip()}")
    return bool(flagged)


def cmd_census(args):
    spec = load_spec(args.spec)
    repo = os.path.abspath(args.repo)
    files = spec_files(repo, spec, args)
    cwd = grammar_cwd(args, repo)
    census, shapes = {}, {}
    for path, (counts, shape) in map_files(cwd, parse_command(spec, cwd), files,
                                           args, census_file, None):
        rel = os.path.relpath(path, repo)
        census[rel], shapes[rel] = counts, shape
    # The shapes are digests for one before/after comparison, written to a
    # scratch path -- not a baseline, and never kept in the repository.
    payload = {"kind": "census", "language": spec["language"],
               "files": census, "shapes": shapes}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    total = {}
    for counts in census.values():
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v
    print(f"census: {len(census)} file(s), {sum(total.values())} node(s), "
          f"{len(total)} distinct type(s) -> {args.out}")
    return 0


def moved_type_groups(before, after, files):
    """Group files by the set of node types whose count moved in them.

    A fix moves most files the same way, and those are one change to explain.
    The small group that moved a type nobody expected is the lead, and in a
    flat file list it hides among hundreds of the expected kind.
    """
    groups = {}
    for f in files:
        b, a = before[f], after[f]
        delta = {t: a.get(t, 0) - b.get(t, 0) for t in set(a) | set(b)
                 if a.get(t, 0) != b.get(t, 0)}
        g = groups.setdefault(tuple(sorted(delta)), {"files": [], "delta": {}})
        g["files"].append(f)
        for t, d in delta.items():
            g["delta"][t] = g["delta"].get(t, 0) + d
    return sorted(groups.items(), key=lambda kv: (-len(kv[1]["files"]), kv[0]))


def cmd_diff(args):
    with open(args.before, encoding="utf-8") as fh:
        b_payload = json.load(fh)
    with open(args.after, encoding="utf-8") as fh:
        a_payload = json.load(fh)
    kinds = {p.get("kind", "census") for p in (b_payload, a_payload)}
    if len(kinds) > 1:
        raise SystemExit("cannot diff a census against a skeleton run")
    if kinds == {"skeleton"}:
        return diff_skeletons(b_payload, a_payload, args.show)
    before, after = b_payload["files"], a_payload["files"]
    b_shapes, a_shapes = b_payload.get("shapes", {}), a_payload.get("shapes", {})

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
    recounted = sorted(f for f in common if before[f] != after[f])
    # Equal counts do not mean an equal tree: a body that swallows one more
    # line, or a node that moves to another parent, keeps every count.
    reshaped = sorted(f for f in common
                      if before[f] == after[f] and f in b_shapes and f in a_shapes
                      and b_shapes[f] != a_shapes[f])

    if not (changed_types or recounted or reshaped or added or removed):
        print("no change: the grammar change is inert on this file set.")
        return 0

    if changed_types:
        print(f"node types changed: {len(changed_types)}")
        for k, b, a in changed_types:
            print(f"  {k:40s} {b:7d} -> {a:7d}  ({a - b:+d})")

    def listing(title, names):
        print(f"  {title}: {len(names)}")
        for f in names[:args.show]:
            print(f"    {f}")
        if args.show and len(names) > args.show:
            print(f"    ... {len(names) - args.show} more")

    print(f"\nfiles present in both, parsing differently: "
          f"{len(recounted) + len(reshaped)}")
    groups = moved_type_groups(before, after, recounted)
    print(f"  node counts changed: {len(recounted)}, in {len(groups)} group(s) "
          f"by the types that moved")
    for types, g in groups:
        print(f"    {len(g['files'])} file(s): {describe_delta(g['delta'])}")
        for f in g["files"][:min(args.show, 3)]:
            print(f"      {f}")
        if args.show and len(g["files"]) > min(args.show, 3):
            print(f"      ... {len(g['files']) - min(args.show, 3)} more")
    listing("same counts, different shape (a span, parent or field moved)",
            reshaped)
    if not (b_shapes and a_shapes):
        print("  (a census without shapes predates them; only count changes "
              "are visible for it)")

    if added or removed:
        print(f"\nfile set also moved: +{len(added)} added, "
              f"-{len(removed)} removed (expected after an input sync; "
              f"no parser signal)")

    print("\nOnly the 'parsing differently' files are a blast radius. A fix "
          "aimed at one construct that moves unrelated files needs an "
          "explanation; after a sync, this list should normally be empty.")
    return 1 if (changed_types or recounted or reshaped) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--repo", required=True, help="grammar repository root")
        p.add_argument("--spec", required=True, help="invariant spec JSON")
        p.add_argument("--files", nargs="*", help="override the spec's globs")
        p.add_argument("--batch", type=int, default=60,
                       help="files per CLI invocation (default 60)")
        p.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                       help="processes to run at once (default: one per CPU)")
        p.add_argument("--grammar-repo",
                       help="the grammar repository whose parser to use, when "
                            "--repo holds files from somewhere else (normalized "
                            "output, an attached reproducer). Defaults to --repo.")

    p = sub.add_parser("provenance",
                       help="print the toolchain, commit and skill version for "
                            "the audit record")
    p.add_argument("--repo", required=True, help="grammar repository root")
    p.add_argument("--spec", help="invariant spec JSON, for its CLI command")
    p.add_argument("--tool", help="the declared reference parser, to record")
    p.set_defaults(func=cmd_provenance)

    p = sub.add_parser(
        "skeleton",
        help="compare the grammar against the language's reference parser")
    common(p)
    p.add_argument("--tool", help="the reference parser the user declared")
    p.add_argument("--out",
                   help="also save the run here, for `diff` against another")
    p.add_argument("--limit", type=int,
                   help="compare N files spread evenly across the set")
    p.add_argument("--show", type=int, default=10,
                   help="files to list per direction; 0 for summary lines only")
    p.set_defaults(func=cmd_skeleton)

    p = sub.add_parser("corpus", help="check the corpus against its own inputs")
    p.add_argument("--repo", required=True, help="grammar repository root")
    p.add_argument("--spec", required=True, help="invariant spec JSON")
    p.add_argument("--id", action="append", default=[])
    p.add_argument("--show", type=int, default=10,
                   help="cases to list; 0 for summary lines only")
    p.add_argument("--before", metavar="REV",
                   help="also sort the cases changed since this git revision "
                        "(e.g. HEAD, after `tree-sitter test --update`) by "
                        "what moved")
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser("probe", help="check structural invariants")
    common(p)
    p.add_argument("--id", action="append", default=[],
                   help="only run this invariant (repeatable)")
    p.add_argument("--show", type=int, default=5,
                   help="examples per mode; 0 for summary lines only")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("census", help="record a node census")
    common(p)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_census)

    p = sub.add_parser("diff", help="diff two censuses, or two skeleton runs")
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--show", type=int, default=20,
                   help="files to list per kind of change; 0 for counts only")
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
