# Bringing a new grammar repository under this skill

A repository without a contract document cannot be audited; there is nothing to
audit against. Build the contract first, and build it from what the parser already
does, not from what it should ideally do — a contract that describes an aspiration
cannot tell you whether today's tree is wrong.

Applies to `tree-sitter-tablegen` and `tree-sitter-pdll`, neither of which had a
`docs/` directory on 2026-09-24. Their toolchains are close to `tree-sitter-mlir`'s
but not the same, so check rather than assume:

- Both define `npm run test`, `test:examples` and `compile`; neither defines `fuzz`,
  so the fuzz gate in `SKILL.md` Part 5 has no command there yet.
- `tree-sitter-pdll` has `test/corpus/` and `test/highlight/`; `tree-sitter-tablegen`
  has `test/corpus/` only.
- `tree-sitter-tablegen` has no `package-lock.json`, so nothing pins the CLI: CI
  takes the newest release in the `package.json` range. `probe.py provenance` says so;
  record the version you actually measured with.

Re-derive these with `python3 scripts/probe.py provenance --repo "$REPO"` and the
`scripts` block of the repository's `package.json`.

## Six steps

**1 · Write down the public AST surface.** Read `src/node-types.json` and every
file in `queries/`. The nodes the queries already depend on are a de facto contract
whether or not anyone wrote it down — breaking one breaks a consumer today. List
them with their fields and parent relationships.

**2 · Write down the layer split.** For that language: what gets a precise CST,
what gets only boundary preservation, what is explicitly out of scope. The middle
layer is the one that does the work, so name the specific boundaries that must
survive — for MLIR those are the next sibling operation, a block label, a region
close and the operation-level `loc(...)`. Name the equivalents for the language at
hand; do not copy MLIR's list.

**3 · State the principles.** Few, specific, and tied to that language's own
extension mechanism. TableGen's `class`/`multiclass`/`defm` expansion and PDLL's
rewrite and constraint syntax pose different problems from MLIR's runtime dialect
registration, and deserve their own principles rather than a translated copy. Each
principle should be usable as a question asked of a proposed change.

**4 · Record what already exists and why.** Declared conflicts, scanner
responsibilities, dedicated branches, and the reason each one is there. This is
what later changes argue against. Reconstructing a rationale years later is much
harder than writing it down now, and an undocumented conflict is one nobody dares
remove.

**5 · Find the reference parser, and what survives its parse-and-print.** This is
the skill's strongest line of evidence, so settle it before writing any invariant —
invariants are for what it cannot reach. Both languages have one in the LLVM tree:

- **PDLL — `mlir-pdll`.** Its default output, `-x=ast`, is a dump of the parsed AST:
  closer to a CST than MLIR's in-memory IR, so declarations such as patterns,
  constraints and rewrites can be counted on both sides.
- **TableGen — `llvm-tblgen`.** With no backend selected it prints every class and
  def *after* `defm`, `multiclass` and `foreach` expansion, and `--dump-json` prints
  the same records as JSON. Expansion multiplies defs, so compare what it leaves
  alone — classes, or `def`s written outside any multiclass — not the record count.

Neither prints its own language back, so the MLIR move — parse the tool's output with
the same grammar — does not apply: the comparison needs a declared mapping from the
tool's node kinds to CST node types. Keep it to a few counts, write down what it
cannot see, and write the code in `probe.py` only once the contract exists and a
count has been shown to catch something. As for MLIR, the user declares the tool, the
spec carries a `self_check` it must pass, and its version is a coverage limit, not a
gate.

**6 · Add an invariant spec** at `assets/invariants/<language>.json`. Start with one
or two, drawn from the layer split and from any defect the repository has already
hit. Before trusting an invariant's hits, confirm it is **quiet on known-good
input** — run it over the existing corpus inputs, which are presumed correct. An
invariant that fires on ordinary correct code trains you to skim its output, which
is worse than not having it. Give each one a case in `scripts/test_probe.py`: an
input it must flag and a correct one it must leave alone, both from the real CLI.

## Then

Add the repository to the table in `SKILL.md` Part 0 — contract, spec, and a
`references/<language>.md` for its gates, layer table and lexical traps, in the
shape of `references/mlir.md` — and start an audit record in an ignored directory as
described in Part 7.

Until a contract document exists, be explicit about what you can and cannot say: an
ERROR/MISSING sweep and a corpus self-consistency check both work without one — the
latter needs only a `corpus_invariants` pattern in a spec — and both are worth
running. What you cannot do is adjudicate a finding: without a layer split there is
no basis for calling a coarse parse an accepted trade-off rather than a defect. Say
that rather than improvising a standard.
