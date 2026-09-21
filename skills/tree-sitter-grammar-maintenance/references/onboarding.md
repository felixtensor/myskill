# Bringing a new grammar repository under this skill

A repository without a contract document cannot be audited; there is nothing to
audit against. Build the contract first, and build it from what the parser already
does, not from what it should ideally do — a contract that describes an aspiration
cannot tell you whether today's tree is wrong.

Applies to `tree-sitter-tablegen` and `tree-sitter-pdll`, neither of which has a
`docs/` directory yet. Both share `tree-sitter-mlir`'s toolchain and layout
(`npm run test`, `npm run test:examples`, `npm run compile`, `test/corpus/`, and
for pdll `test/highlight/`), so the mechanics transfer unchanged. Only the contract
and the invariants are language-specific.

## Five steps

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

**5 · Add an invariant spec** at `assets/invariants/<language>.json`. Start with one
or two, drawn from the layer split and from any defect the repository has already
hit. Before trusting an invariant's hits, confirm it is **quiet on known-good
input** — run it over the existing corpus inputs, which are presumed correct. An
invariant that fires on ordinary correct code trains you to skim its output, which
is worse than not having it.

## Then

Add the repository and its contract document to the table in `SKILL.md` Part 0, and
start an audit record in an ignored directory as described in Part 7.

Until a contract document exists, be explicit about what you can and cannot say: an
ERROR/MISSING sweep and a corpus self-consistency check both work without one, and
both are worth running. What you cannot do is adjudicate a finding — without a
layer split there is no basis for calling a coarse parse an accepted trade-off
rather than a defect. Say that rather than improvising a standard.
