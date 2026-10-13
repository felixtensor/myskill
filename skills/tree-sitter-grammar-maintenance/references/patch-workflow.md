# Repair and verification

Read this before editing grammar, scanner, corpus or queries. Use the language
profile for project-specific gates and the mechanics reference for conflict,
precedence and incremental-parsing decisions.

# Part 5 · From finding to patch

**Take one topic at a time.** One grammar or scanner theme per change; if it does
not resolve within a couple of working sessions, split it. A large change forfeits
the one review mechanism this project relies on: a corpus diff a person can read.

**Write the minimal reproducer first, and write it as a corpus case.** Shrink the
real input until one construct remains. Write the expected tree *by hand*, from the
contract. Confirm it fails. Only then open the grammar. Never do this in the other
order: generating the tree first and reading it second is precisely how the defect
got into the corpus to begin with. Write the false-positive guards at the same time:
inputs that look like the defect and parse correctly today. The direct hits must
fail before the change and the guards must pass before it; a guard checked only
against the fixed parser pins nothing.

**`tree-sitter test --update` output is a draft, never a result.** Read every line
of the diff it produces; if it is too large to read, the change is too large to
land. Before reading, run `probe.py corpus --before HEAD`: it groups the changed
cases by the node types that moved and flags any whose input or leaf order moved —
read those first.

**Named nodes are not the whole tree.** Corpus trees, census, skeleton and probes
all compare named nodes, so none of them sees an anonymous token appear or vanish.
When a change builds an existing node a second way — an alias, an external token,
another rule — pin both paths against each other with a `:cst` corpus case;
`references/tree-sitter-mechanics.md` has the scanner pattern that keeps them equal.

**Put the fix through the principles before you put it through the tests.** State,
in the commit message or PR, which principle justifies it.
`references/tree-sitter-mechanics.md` holds the precedence and conflict mechanics
that decide which grammar edit can possibly work; read it before the edit, not after
one mysteriously does nothing.

**A conflict is a modelling decision, not a defeat.** Languages are locally
ambiguous, and tree-sitter is GLR so a grammar can say so. Refuse a conflict without
its record, or one that leaves a genuine ambiguity to rule order. The mechanics file
has the ladder and the record; after any conflict or weight change,
`probe.py conflicts --runtime --flip` measures what it decides.

**A dedicated rule for one construct needs all four of these**, not three:

1. A specific issue, an upstream failure, or a downstream consumer that is blocked.
2. A minimal input that reproduces what the general path loses.
3. A readable corpus case for the new structure — **plus a corpus case proving the
   generic fallback for unknown extension syntax still works**, shaped like the
   construct you specialised (for MLIR, an unregistered `test.*` operation). This is
   the guard that stops a dialect fix from quietly narrowing the general path, and it
   is the single most important test in a dedicated-branch change.
4. New conflicts, recursion, scanner responsibility and parser size proportional to
   the benefit.

When no principle supports the change, stop and take it to the maintainer as a
contract question — do not weaken the contract to fit the patch.

**Then run the gates the change actually touches.** Do not force every change
through the same list; do not skip a gate that applies. The language layer lists the
repository's own; the following are MLIR command examples, not required script
names for other languages:

```bash
npx tree-sitter generate       # must exit 0; a newly declared conflict carries its record
npm run test                   # corpus + highlight fixtures
npm run test:examples          # ERROR/MISSING smoke over pinned examples
npm run fuzz                   # where it exists: scanner, generated-parser, corpus or fuzz-runner changes

# compile every shipped query against one real file, not just highlights
for q in queries/*.scm; do npx tree-sitter query "$q" "$SAMPLE" --quiet || echo "FAILED: $q"; done
```

Then rerun the supported probes from Part 3 and diff the census. When the profile
has a validated normalizer, also `diff` a `skeleton --out` run from before against
one from after. An AST-only reference tool instead uses its validated
language-specific comparison; do not require `skeleton` merely because a reference
executable exists. State which comparison has not been implemented. A file may
only move closer to the reference: moving further, landing above it, or a moved
reference side (the generic path, your control) needs an explanation. Compile
**every** shipped query, not just `highlights.scm` — node-name drift breaks
`locals`, `tags`, `folds` and `indents` silently, and those have no fixtures.

**Never skip fuzz on a change that touches ambiguity resolution.** A precedence or
conflict change can be correct on a full parse and wrong under editing: incremental
re-parse reuses cached subtrees, and a decision that weighed two complete readings
does not reliably get re-made. Corpus, examples and queries all parse whole files, so
none of them can see this — and an editor re-parsing on every keystroke is the
primary consumer. If fuzz fails, confirm your change caused it by stashing and
replaying the same seed before you spend time on the parse itself. A pass counts only
if fuzz could have failed here; `references/tree-sitter-mechanics.md` says how to
read a failure line and how to run the control.

If the change added a conflict, a recursive rule, a scanner token or a dedicated
branch, record `src/parser.c` size, `STATE_COUNT` and parse throughput before and
after, and what the growth bought.

**Record a public AST change where consumers will look.** A new, renamed or removed
node or field goes in the changelog, called out as a breaking AST change when it is
one, with the affected queries updated in the same change. A change to where a
construct ends also updates the contract's account of that boundary, residue
included — `references/docs-contract.md`.

**Report faithfully.** Say which leads still fire and why they are acceptable. A fix
that resolves one class and leaves a related one open is a fine outcome; a fix
described as complete when it isn't will be trusted later by someone who shouldn't.

**Have it reviewed cold.** Before it goes out, hand the change to a reviewer with
this skill and none of your context — a fresh agent will do — and ask what else it
moved. Record what the review actually checked; do not infer coverage from the
reviewer being independent.
