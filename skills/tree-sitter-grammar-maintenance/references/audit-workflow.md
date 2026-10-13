# Audit setup and probes

Read this for an audit or before measuring a grammar change. Commands run from
the skill directory; `REPO` is the target checkout and `SPEC` is its validated
language spec. Python helpers use the standard library. Parsing requires the
project's tree-sitter CLI and build toolchain; reference comparison also requires
the declared reference executable. Downloads and environment repair require host
permissions. Measurements and private audit records stay outside this skill.

# Part 0 · Ground yourself before you measure anything

**Identify the repository and load its contract.** Use the selected language profile
for the contract path and invariant spec. For MLIR, use `docs/ARCHITECTURE.md` and
`assets/invariants/mlir.json`; for another language, follow onboarding rather than
borrowing MLIR's nodes, boundaries or normalizer.

Read the contract document before you read a single tree. It is not background
material; it is the specification you are about to audit against. A repository with
no contract document cannot be adjudicated at all — see `references/onboarding.md`.

**Read the audit record next** (Part 7). Its current-state block says which findings
are open, which were examined and *deliberately accepted*, which invariants were
clean, and which reference parser the last pass used. Re-litigating a settled
trade-off is the most common way this work gets repeated.

**The reference parser is declared by the user, never discovered.** Do not search
`PATH` or try likely names: a comparison against a tool nobody chose reads as
authoritative while resting on nothing. Take, in order, the path the user gave in
this session; the absolute path in the audit record; otherwise ask — with the
client's question mechanism where there is one — and wait. The spec's `tool_hint`
says what kind of tool serves, and `probe.py` refuses one that fails the spec's
self-check, so a wrong answer fails loudly. When the user's tool fails it and the
record names another, ask before switching. **If the user has none**, run the other
checks and **say in the report that the reference comparison did not run and
coverage is reduced** — a fine outcome, as long as it is not presented as complete.

**Check the toolchain, and record what produced the numbers.** From the skill
directory:

```bash
REPO=/path/to/parser-repository          # wherever the checkout actually lives
SPEC=/path/to/validated-invariant-spec
TOOL=/path/declared/by/the/user         # leave --tool off if there is none
python3 scripts/probe.py provenance --repo "$REPO" --spec "$SPEC" --tool "$TOOL"
```

It prints the audit record's provenance lines — commit, the CLI against the lock
file and against what the CI workflows pin, the reference parser's absolute path and
version, the skill version — and exits 1 when either CLI differs from the lock:
numbers from a parser CI would not build are worthless, and each check has caught a
real drift. Without a lock file, CI takes the newest CLI in the declared range, so
name the version you measured with.

On a mismatch, **ask before repairing** with `npm ci`, then rerun `provenance`: npm
may block the CLI's install script and leave no binary. The remaining repair, the
matching release binary in `node_modules/tree-sitter-cli/`, is a download: ask
again.

**Then confirm the committed parser matches the grammar source:**

```bash
(cd "$REPO" && npx tree-sitter generate && git status --short -- src/)
```

It prints nothing when the checked-in parser is current, and covers every generated
file — `src/node-types.json`, where the public AST surface is checked, and anything
a newer CLI adds. Any output means stale artifacts: measure on the regenerated
parser and say so. If `generate` fails, it has still rewritten `src/grammar.json`
(preserve the original `src/` diff before restoring generated files), and
`tree-sitter test` keeps passing on the old parser: report that the working tree
does not generate, and measure the committed one in an isolated checkout.

**Record the baseline.** Run the repository's own gates and write down what they
say, unchanged:

Use the commands declared by the project, not assumed npm script names.
The [MLIR profile](mlir.md#gates) gives its commands.

A silent-misparse audit starts where passing gates stop. If a gate already fails,
record that failure and keep it distinct from new findings.

---

# Part 3 · Run the probes

`scripts/probe.py` is standard-library Python and writes nothing into the parser
repository. Run it from the skill directory with `REPO`, `SPEC` and `TOOL` set as in
Part 0. `--show N` widens what a command prints and `--show 0` leaves summary lines;
the commands that parse use every core, and `--jobs N` limits them.

**Compare against the reference parser first, where one exists:**

`skeleton` requires a validated normalizer that prints syntax this grammar parses.
MLIR supplies that profile. A reference tool that only dumps an AST or expanded
records needs the mapping described in [onboarding](onboarding.md); its mere
availability does not make this command applicable.

```bash
python3 scripts/probe.py skeleton --repo "$REPO" --spec "$SPEC" --tool "$TOOL"
python3 scripts/probe.py skeleton --repo "$REPO" --spec "$SPEC" --tool "$TOOL" --limit 80
```

`--limit N` compares N files spread evenly across the set. The command normalizes
each input with the reference tool, parses that output with the same grammar, and
compares quantities the printer preserves — for MLIR, the results each file binds
(`%0:2` counts two, because the printer regroups `%a, %b`), and the operation,
region and block counts. Read it as a **ranked lead generator, not a gate**:

- **grammar above the reference** — always a defect, on any quantity: the grammar
  invented structure the language's parser does not see. Open these first.
- **grammar below the reference, large gap** — a strong signal on a `ranked`
  quantity, and the top of the list is where to look. On a `ceiling` quantity the
  reference is expected to count more, for the reason the spec states — which is
  also where a swallowed operation hides, so leave those to the invariants.
- **small gaps** — often a legitimate printing difference; the language layer
  documents which, and why a green number here would be meaningless.

Files the tool declines are a coverage limit, not a parser signal: say how many were
skipped. A run that compared nothing exits 2; never report it as clean.

**Corpus self-consistency — needs no parser at all:**

```bash
python3 scripts/probe.py corpus --repo "$REPO" --spec "$SPEC"
```

It compares each case's input with its own expected tree; a case that contradicts
its input was accepted from `--update` without being read.

**Structural invariants over the example set:**

```bash
python3 scripts/probe.py probe --repo "$REPO" --spec "$SPEC"
python3 scripts/probe.py probe --repo "$REPO" --spec "$SPEC" --show 10
```

Hits are grouped by **mode** — what a hit looks like structurally, such as
`value_use in custom_operation` for a binding a body swallowed. Ten thousand hits in
one mode are one finding: triage modes, not files. Each invariant kind mechanizes a
contract statement:

- `line_produces` — a source line of a given shape must start a node of a given
  type; a lost or re-attributed binding fails it.
- `no_node` — no ERROR or MISSING. A MISSING token is anonymous, so it comes from
  the CLI's error line, which names only a file's *first* error: fix it and rerun.
- `span_guard` — a node must not cross a line that unambiguously starts the next
  sibling; with `check_after_last`, also after the node's own region closes.

Keep invariants few, narrow and high-precision. An invariant that fires on ordinary
correct code is worse than no invariant, because it trains you to skim the output.

**What each declared conflict decides.** A flip that moves examples but would fail no
corpus test, and a declaration `--static` calls REPLACEABLE, are both leads.

```bash
python3 scripts/probe.py conflicts --repo "$REPO" --spec "$SPEC" --runtime --flip --static
```

**Strip comments before any text-level scan**, of sources or query files: prose
mentioning a capture or binding is not code. Use the language's actual comment
syntax; the spec's `skip_line` handles configured source comment lines. A one-off
check must handle comments itself, and several odd hits at once point at the check
before the parser.

**Blast radius, around any grammar change:**

```bash
T=$(mktemp -d)
python3 scripts/probe.py census --repo "$REPO" --spec "$SPEC" --out "$T/before.json"
# ... make the grammar change, then ...
python3 scripts/probe.py census --repo "$REPO" --spec "$SPEC" --out "$T/after.json"
python3 scripts/probe.py diff "$T/before.json" "$T/after.json"
```

Run this on every grammar change without exception. `diff` lists the files that now
parse differently: node counts changed — grouped by the types that moved, so one odd
file cannot hide among four hundred expected ones — or same counts with a moved
span, parent or field. Every group needs an explanation, and every kind of real
input the change moved owes a corpus case: the cheapest guard against a dialect fix
quietly damaging the general path.

**Parse by hand with this checkout's parser:** `tree-sitter build -o LIB`, then
`parse --lib-path LIB --lang-name NAME`; a plain `parse` picks a grammar by
extension, and in a worktree it used the main checkout's. In any second checkout,
set `TREE_SITTER_LIBDIR=$(mktemp -d)` before `tree-sitter test` or fuzz: their cache
is keyed by grammar name, so one checkout's build serves another. A census goes to a
temporary path, never into the repository (Part 9).

**The reference parser also answers one question the skeleton check does not:**
whether an input is legal at all. The language layer has the command. Ask it before
blaming the grammar for failing on something, and before building a corpus case out
of syntax you wrote by hand — a case whose input the language itself rejects is not
evidence of anything. Record the command and the tool version wherever you cite its
output.
