---
name: tree-sitter-grammar-maintenance
description: Work on a tree-sitter grammar as a closed loop — compare against the language's own reference parser, locate the defect, fix it, verify, repeat — and hold every change against the architecture contract so a fix for one dialect cannot quietly narrow the general parsing path. Use it to find the root cause of a failing corpus or highlight test, to repair tests after a grammar or scanner edit, to audit for silent misparses that pass every gate, before accepting `tree-sitter test --update` output, when adding support for new syntax, after an upstream example sync, and when docs/ARCHITECTURE.md or docs/QUERIES.md may have drifted. Covers tree-sitter-mlir, tree-sitter-tablegen and tree-sitter-pdll. Expect "why does this test fail", "this parses wrong", "I changed the grammar and tests broke", "扫一下解析有没有问题", "这个语法解析得不对", "加条规则支持这个方言". Not a general MLIR or compiler question answerer.
---

# Tree-sitter grammar maintenance

**A parse that reports no ERROR is not evidence that the tree is correct.**

A permissive fallback rule has no hard terminator. When it meets syntax it was not
told to stop at, it does not fail — it absorbs. The absorbed text still appears in
the tree, in the wrong place, under the wrong parent, with no ERROR and no MISSING.
`tree-sitter parse --quiet --stat` reports 100% success. Then someone runs
`tree-sitter test --update`, the wrong shape is written into the corpus as the
*expected* result, and from that moment the defect is invisible to every gate at
once — including the one the project calls its only persistent source of truth.

That is the failure this skill exists to find. It is not exotic; it hides in the
most ordinary syntax in the language, precisely because ordinary syntax is what
nobody re-reads.

The second half of the job follows from the first. Once a defect is found, the
pressure is to patch the grammar until the symptom goes away. That is how a
general-purpose parser rots into a pile of dialect-specific special cases. The
architecture document exists to stop exactly that, and it only works if it is
maintained as a contract rather than as prose that trails the code.

## Three ways in

**A test is failing and you need the cause.** Go to Part 5's repair loop. Read the
actual tree before editing anything — the parser and the expectation are both
capable of being wrong, and guessing which costs more than looking.

**You changed the grammar and tests broke.** Same place. The question is never "how
do I make this green" but "which of these two is wrong", answered per case.

**Nothing is failing and you want to know what is hiding.** Run the full sweep
below. This is where silent misparses live, because by definition no gate is
complaining about them.

## The loop

Compare, locate, fix, verify, repeat. Each step is expanded below; do not skip
Part 0, because every later number is meaningless if the toolchain is not the one
CI builds.

1. Load the contract and the audit record; verify the toolchain; get the reference
   parser from the user or the record — never by searching (Part 0).
2. Record the baseline the project's own gates report (Part 0).
3. **Compare against the reference parser** — the strongest evidence, and the first
   thing to run for a language that has one (Part 3).
4. Check the corpus against its own inputs, and run the structural invariants over
   the example set — these cover the inputs the reference tool cannot reach (Part 3).
5. Triage every lead into a layer before proposing anything (Part 4).
6. Minimise the confirmed ones into hand-written corpus cases, fix, and verify
   (Part 5).
7. Check the contract documents for drift in both directions (Part 8).
8. Write the pass into the audit record, including what you decided *not* to act on
   and why (Part 7).

Then go round again: a fix changes what the next comparison shows, and the residue
after a fix is the next lead.

`references/highlight-captures.md` covers the query side: how to derive the standard
capture set from the toolchain instead of trusting a copied list, and why a query
improvement can be invisible in a rendered fixture.

`references/tree-sitter-mechanics.md` holds the mechanics that decide which grammar
edit can possibly work — the precedence and conflict rules, how to see anonymous
tokens, corpus test attributes, and the test-repair order. Read it before editing a
grammar rule, not after an edit mysteriously does nothing.

---

# Part 0 · Ground yourself before you measure anything

**Identify the repository and load its contract.**

| Repository | Contract document | Read this too |
| --- | --- | --- |
| `tree-sitter-mlir` | `docs/ARCHITECTURE.md` | `references/mlir.md` |
| `tree-sitter-tablegen` | — | `references/onboarding.md` |
| `tree-sitter-pdll` | — | `references/onboarding.md` |

Read the contract document before you read a single tree. It is not background
material; it is the specification you are about to audit against.

`references/mlir.md` is the language layer: which document governs what, the repo's
gates and layout, the layer table and six principles turned into questions you can
ask of a change, the commands that verify each documented claim, MLIR lexical facts
that trip up line-based analysis, how to use `mlir-opt`, and two worked triage
examples — one must-fix, one accepted trade-off. Read it whenever you are working
in `tree-sitter-mlir`, not only when stuck. A repository with no contract document
cannot be adjudicated at all — see `references/onboarding.md`.

**The reference parser is declared by the user, never discovered.** Do not search
`PATH`, do not try a list of likely names, do not take the first plausible binary.
`opt` is LLVM's IR optimiser and has nothing to do with MLIR; an arbitrary
`mlir-opt` build may not register the dialects this repository needs. Either would
produce a comparison that reads as authoritative while resting on a binary nobody
chose — and the whole value of this evidence line is that its provenance is known.

Resolve it in this order:

1. **The user said so in this session** — use that path.
2. **The audit record has it** — a previous pass recorded the path; reuse it.
3. **Otherwise ask, and wait.** Ask however the client allows: its question or
   option-picker mechanism where one exists, plain text otherwise. One line is
   enough — which opt tool to use and where it is; any MLIR-based project's build
   works (`mlir-opt`, `circt-opt`, `triton-opt`, `iree-opt` …); the version does not
   need to match the pinned examples.

Pass it with `--tool`. `probe.py` round-trips a trivial function through whatever it
is given and refuses anything that is not an MLIR opt tool, so a wrong answer fails
loudly instead of quietly. Record the working path in the audit record so the next
pass does not ask again.

**If the user has none**, continue with the remaining checks and **say in the report
that the reference comparison did not run and coverage is reduced**. That is a fine
outcome; presenting it as a complete audit is not.

Its version does **not** need to match the pinned examples, and you should not
check: a version difference surfaces as files the tool declines to process, which
is a coverage limit, not a parser signal.

**Read the audit record next** (Part 7). It tells you which invariants were already
clean, which findings are already open, and — most importantly — which findings
were examined and *deliberately accepted*. Re-litigating a settled trade-off is the
most common way this work gets repeated.

**Then establish that your toolchain is telling you the truth.** Measurements from
a parser that is not the one CI builds are worthless, and this check has already
caught a real drift:

```bash
npx tree-sitter --version
node -e "console.log(require('./package-lock.json').packages['node_modules/tree-sitter-cli'].version)"
```

If they disagree, run `npm ci` and say so in the report — then **check that the CLI
still runs**. `npm ci` is not the same as a working toolchain: npm may block the
`tree-sitter-cli` install script, leaving a package with no binary in it, and the
failure surfaces only when you try to parse. Rerun `npx tree-sitter --version`; if
it cannot spawn, fetch the matching release binary into
`node_modules/tree-sitter-cli/` yourself and record the version you ended up on.

Then confirm the committed parser matches the grammar source:

```bash
cp src/parser.c /tmp/parser.c.bak && npx tree-sitter generate && diff -q /tmp/parser.c.bak src/parser.c
```

A difference means the checked-in artifacts are stale; regenerate and rerun the
gates before attributing anything to the grammar.

**Record the baseline.** Run the repository's own gates and write down what they
say, unchanged:

```bash
npm run test
npm run test:examples
```

Expect them to be green. That is the point: the audit starts where the gates stop.

---

# Part 1 · What counts as evidence

There is no node-for-node oracle. A compiler's in-memory IR is what remains *after*
parsing, with the surface syntax already consumed by the dialect or front end, so it
has no correspondence with a CST. Mapping one onto the other means writing a second
interpreter that then needs verifying itself — a known dead end, and repositories
that tried it ended up with a ledger nobody could finish reviewing.

**But there is a skeleton oracle, and you should reach for it first.** Normalize the
input with the reference parser and parse *its output* with the same grammar. Both
sides are then CSTs from the same parser, the mapping is the identity, and the
reference side carries the language's own answer about the program's structure.
Compare the quantities that survive parse-and-print — how many results each
operation binds, how the structure nests. This is far better evidence than a pattern
you write yourself, which is only ever your guess at what the language's parser
knows. Part 3 has the mechanics; `references/mlir.md` has the MLIR setup.

**Where it does not reach, compare the tree against the contract.** The contract
states which constructs get a precise CST, which get only boundary preservation, and
which are explicitly out of scope. Every one of those statements is a testable claim.
Hand-written invariants are the second line of evidence, not the first — they exist
to cover the inputs the reference tool declines, which for MLIR is a real fraction:
pass pipelines, expected-error tests, and syntax from another compiler revision.

**The hard rule, and the reason this skill exists:**

> The principles in the contract document are not adjustable to accommodate a fix.
> If a change requires violating one, the change is wrong — find another one.
> Amending a principle is a separate, deliberate decision that belongs to the
> maintainer and gets its own review; it is never a side effect of making a test
> pass.

Hold this line even when the patch in front of you is small and the principle feels
abstract. The principles are what keeps a parser for an open, extensible IR from
degenerating into an unmaintainable pile of per-dialect special cases — which is
the whole reason the parser was written instead of hard-coding the ecosystem.

---

# Part 2 · Five lines of evidence, with distinct jobs

Do not treat these as one checklist. Each answers a different question, and
confusing them is how false confidence forms. They are listed in the order to reach
for them.

**1 · The reference parser — the language's own answer.** Where the language ships a
compiler that can re-print a program, this is the strongest evidence and the least
arguable: a disagreement is the grammar reading the program differently from the
implementation everyone else uses, with no judgement call left. It does not reach
every input — see Part 3 for what it declines — which is why the rest still matter.

**2 · `test/corpus` — the exact CST contract.** The only persistent AST truth, and
the only place a public node/field guarantee is actually written down. It is also
the only artifact that can record a defect as the expected result, so audit it
*first* and audit it *against its own inputs* (Part 3). Never trust it merely
because it passes; it passes by construction.

**3 · Highlight fixtures — the query contract.** They assert capture names at
source positions, so they test the query layer over the tree, not the tree.
A fixture can pass on a wrong tree whenever the capture lands on a node that
happens to carry the right type. Read them for what they do *not* pin down.

**4 · `examples/` — compatibility smoke only.** A blocking ERROR/MISSING gate
across real upstream input. It proves the parser does not choke; it proves nothing
about shape. Do not turn it into a per-file AST review, and do not let its green
status stand in for tree correctness.

**5 · Structural invariants — your own assertions, where nothing better reaches.**
Short, mechanical claims derived from the contract, run across the whole example
set. They catch absorption on inputs the reference tool declines, and they are the
only option for a language with no reference parser. Treat them as second-best:
an invariant is your guess at what the language's parser knows, so prefer the real
one wherever it reaches. They produce candidates, not verdicts.

---

# Part 3 · Run the probes

`scripts/probe.py` is standard-library Python and leaves nothing in the parser
repository. Invariants live in `assets/invariants/<language>.json`. Run the commands
below from the skill directory, with `REPO` set to the grammar repository:

```bash
REPO=~/Projects/tree-sitter-mlir     # wherever the checkout actually lives
```

Add `--show 0` to any run for just the per-invariant summary line, and `--show N`
to widen the per-file excerpts when a hit needs reading.

**Compare against the reference parser first, where one exists:**

```bash
python3 scripts/probe.py skeleton --repo "$REPO" --spec assets/invariants/mlir.json
python3 scripts/probe.py skeleton --repo "$REPO" --spec assets/invariants/mlir.json \
  --tool /path/to/mlir-opt --limit 80 --show 8
```

It normalizes each input with the reference tool, parses that output with the same
grammar, and compares skeletons. Read it as a **ranked lead generator, not a gate**:

- **grammar count above reference** — always a defect; the grammar invented
  structure the language's parser does not see. Open these first.
- **grammar count below reference, large gap** — strong signal, and the top of the
  list is where to look.
- **small gaps** — often a legitimate printing difference rather than a defect.
  `references/mlir.md` documents which ones, and why a green number here would be
  meaningless.

Files the tool declines are not a parser signal. Pass pipelines, expected-error
tests and syntax from a different compiler revision all land there; say how many
were skipped rather than reporting a percentage as if it covered everything.

**Corpus self-consistency — needs no parser at all:**

```bash
python3 scripts/probe.py corpus --repo "$REPO" --spec assets/invariants/mlir.json
```

It compares each corpus case's input against that case's own expected tree. A case
whose expected tree contradicts its input was accepted from `--update` without
being read.

**Structural invariants over the example set:**

```bash
python3 scripts/probe.py probe --repo "$REPO" --spec assets/invariants/mlir.json
python3 scripts/probe.py probe --repo "$REPO" --spec assets/invariants/mlir.json --id op-result-binding --show 10
```

Three invariant kinds are available, and each maps onto a contract statement:

- `line_produces` — a source line of a given shape must start a node of a given
  type. This is how a lost or re-attributed binding is detected.
- `no_node` — ERROR / MISSING must not appear, with locations.
- `span_guard` — a node must not extend across a line that unambiguously starts the
  next sibling construct. This is boundary preservation in machine-checkable form.

Keep invariants few, narrow and high-precision. An invariant that fires on ordinary
correct code is worse than no invariant, because it trains you to skim the output.

**Strip comments before any text-level scan**, whether of sources or of query
files. Prose mentioning `@function` or a `%x` is not a capture or a binding, and a
scan that counts it will hand you a confident list of findings that are entirely
punctuation. The spec's `skip_line` does this for source files; a one-off check you
write inline has to do it itself. When a check reports several odd-looking hits at
once, suspect the check before the parser.

**Blast radius, around any grammar change:**

```bash
python3 scripts/probe.py census --repo "$REPO" --spec assets/invariants/mlir.json --out /tmp/before.json
# ... make the grammar change, then ...
python3 scripts/probe.py census --repo "$REPO" --spec assets/invariants/mlir.json --out /tmp/after.json
python3 scripts/probe.py diff /tmp/before.json /tmp/after.json
```

Run this on every grammar change without exception. A fix aimed at one construct
that moves the tree of unrelated files has done something you did not intend, and
you need to know that before review, not after. This is the cheapest available
guard against a dialect-specific fix quietly damaging the general path.

A census is a scratch measurement for one change. Write it to a temporary path,
never into the repository — a committed baseline is the persistent snapshot the
project has already decided not to maintain.

**The reference parser also answers one question the skeleton check does not:**
whether an input is legal at all.

```bash
mlir-opt --verify-diagnostics FILE
```

Run it before blaming the grammar for failing on something, and before building a
corpus case out of syntax you wrote by hand — a case whose input the language itself
rejects is not evidence of anything. Record the command and the tool version
wherever you cite its output.

---

# Part 4 · Triage: what must be fixed, what is a legitimate trade-off, what is out of scope

**A probe hit is a candidate, not a bug.** Before proposing any change, place the
finding in the contract's layer table. The layer decides the answer; your intuition
about how wrong the tree looks does not.

| Category | What the contract promises | Verdict | Evidence it takes |
| --- | --- | --- | --- |
| **Stable core** — operations, regions, blocks, results, operands, successors, symbols, the type/attribute envelope, trailing locations, and anything on the public AST surface | A precise CST | **Must fix.** Not negotiable, not deferrable, regardless of how narrow the trigger looks. | Hand-written corpus S-expression |
| **Structurally unknown extension syntax** — unregistered dialects, custom assembly, open namespaces | Only that outer boundaries survive | **Judgement.** A coarse, flat or locally erroneous parse of the payload is an accepted trade-off. Swallowing the following sibling construct, a block label, a region close or an operation-level location is not. | Small boundary corpus + examples smoke |
| **Narrow dedicated parsing** — a rule for one specific construct | Nothing in advance; this is the escape hatch, not a layer | **Only when all four conditions in Part 5 hold.** Nominal coverage of one more dialect is never a reason. | Real sample, minimal corpus, written rationale |
| **Runtime semantics** — registered assembly callbacks, verifiers, traits, interfaces, lowering | Nothing | **Out of scope.** Record it as a known limit at most. Do not add grammar for it. | A recorded limitation |

The second row is the line you are really being asked to draw, and it is testable
rather than a matter of taste: **structure inside the payload is negotiable; the
payload's boundary is not.** Anything on the public AST surface is stable core by
definition — check the list rather than assuming a node is peripheral. Record every
verdict in the audit record, including the ones you decide *not* to act on.
`references/mlir.md` works two examples end to end, one must-fix and one accepted.

**A pass that finds nothing is a finished pass.** Do not reach for a small
completable change to show progress — a fix made to have made a fix costs a review,
adds churn, and spends the credibility the next real finding will need. Every change
needs a reason that stands on its own: a reader misled, a consumer broken, a claim
that is false. "It was inconsistent" only becomes a reason once you have shown the
inconsistency costs someone something, and that it is not deliberate.

---

# Part 5 · From finding to patch

**Take one topic at a time.** One grammar or scanner theme per change, and if it
does not resolve within a couple of working sessions, split it rather than growing
it. An audit that turns into a rewrite has stopped being an audit, and a large
change forfeits the one review mechanism this project relies on: a corpus diff a
person can actually read.

**Write the minimal reproducer first, and write it as a corpus case.** Shrink the
real input until one construct remains. Write the expected tree *by hand*, from the
contract. Confirm it fails. Only then open the grammar.

Never do this in the other order. Generating the tree first and reading it second
is precisely how the defect got into the corpus to begin with.

**`tree-sitter test --update` output is a draft, never a result.** Read every line
of the diff it produces. If the diff is too large to read, the change is too large
to land. A hunk you do not understand is a hunk you have not verified.

**Put the fix through the principles before you put it through the tests.** State,
in the commit message or PR, which principle justifies it.

**A dedicated rule for one construct needs all four of these**, not three:

1. A specific issue, an upstream failure, or a downstream consumer that is blocked.
2. A minimal input that reproduces what the general path loses.
3. A readable corpus case for the new structure — **plus a corpus case proving the
   generic fallback for an unknown dialect still works.** Use an unregistered
   `test.*` operation shaped like the one you specialised. This is the guard that
   stops a dialect fix from quietly narrowing the general path, and it is the
   single most important test in a dedicated-branch change.
4. New conflicts, recursion, scanner responsibility and parser size proportional to
   the benefit.

When no principle supports the change, stop and take it to the maintainer as a
contract question — do not weaken the contract to fit the patch.

**Then run the gates the change actually touches.** Do not force every change
through the same list; do not skip a gate that applies.

```bash
npx tree-sitter generate       # must exit 0; declared conflict count must not silently grow
npm run test                   # corpus + highlight fixtures
npm run test:examples          # ERROR/MISSING smoke over pinned examples
npm run fuzz                   # scanner, generated-parser, corpus or fuzz-runner changes

# compile every shipped query against one real file, not just highlights
for q in queries/*.scm; do npx tree-sitter query "$q" "$SAMPLE" --quiet || echo "FAILED: $q"; done
```

Then, from the skill directory, with `$REPO` pointing at the grammar repository:

```bash
python3 scripts/probe.py probe --repo "$REPO" --spec assets/invariants/mlir.json
python3 scripts/probe.py diff /tmp/before.json /tmp/after.json
```

Compile **every** shipped query, not just `highlights.scm` — node-name drift breaks
`locals`, `tags`, `folds` and `indents` silently, and those have no fixtures.

**Never skip fuzz on a change that touches ambiguity resolution.** A precedence or
conflict change can be correct on a full parse and still be wrong under editing:
incremental re-parse reuses cached subtrees, and a decision that depended on
weighing two complete readings does not reliably get re-made. The corpus, the
examples and the queries all parse whole files, so none of them can see this. An
editor re-parsing on every keystroke is the primary consumer, so a tree that is
only correct on a full parse is not a fix — it is a fix that has not been tested
yet. If fuzz reports a failure, confirm whether your change caused it by stashing
and replaying the same seed before you spend time on the parse itself.

If the change added a conflict, a recursive rule, a scanner token or a dedicated
branch, record the before and after size of `src/parser.c` and say what the growth
bought. Ordinary changes do not need this.

**Record a public AST change where consumers will look.** A new, renamed or removed
node or field goes in the changelog, called out as a breaking AST change when it is
one, with the affected queries updated in the same change. A change with no AST
surface movement needs none of this.

**Report faithfully.** Say which leads still fire and why they are acceptable. A fix
that resolves one class and leaves a related one open is a fine outcome; a fix
described as complete when it isn't will be trusted later by someone who shouldn't.

---

# Part 6 · Upstream example syncs

A sync is when new real-world syntax enters the repository, so it is the moment the
audit is worth the most — and also the moment it is easiest to turn into per-file
review. `references/upstream-sync.md` has the six steps: keep the sync its own
commit, census before and after so a new input is not mistaken for a regression,
cluster failures by mode rather than by file, read only the new ones, minimise
confirmed bugs into corpus cases, and leave expected-diagnostic files alone.

Never edit files under `examples/` to make something pass. They are a pinned
snapshot of someone else's repository; editing them destroys the only reason they
are evidence.

---

# Part 7 · Keep a local audit record

Keep it in the parser repository but **outside version control**, so it stays a
local working note rather than a repository asset or a release gate. Pick a
directory the repository already ignores and confirm it before writing:

```bash
git check-ignore -v tmp/ scratch/ .local/ 2>/dev/null   # whichever the repo has
```

If nothing is ignored, ask the maintainer where such notes belong rather than
committing one. Use `assets/audit-log-template.md` rather than inventing a shape
each time; a record the next pass cannot skim is a record nobody reads.

One entry per pass: date, branch and commit, CLI version, which probes and gates
ran, and one line per finding with a status — `open`, `fixed in <commit>`,
`accepted`, or `out of scope`. Record the invariants that came back **clean** too;
that is what lets a later pass skip them with justification rather than by guess.

**The reason attached to an `accepted` or `out of scope` row is the whole point.** A
status with no reason will be rediscovered and re-argued, which is the exact waste
this record exists to prevent.

**What it must not become.** Not a per-file classification of the example set, not a
tree manifest, not hashes, not a coverage score, and never a release gate. Those
were built once in this project's history and deliberately removed: they did not
reduce the judgement a maintainer had to apply, and they made ordinary fixes wait on
a data platform. If it is growing a row per input file, cut it back to one row per
decision.

---

# Part 8 · Keep `docs/` accurate, in both directions

The contract documents are the instrument this whole method depends on, so they are
load-bearing and audited both ways: forward, does the parser still honour what the
document promises (Parts 2–6); backward, does the document still describe the code.

`references/docs-contract.md` has the per-claim verification commands — conflict
counts, scanner tokens and state, public AST surface names, query files, capture
vocabulary, dedicated branches, gate commands — and the rule for amendments: a new
node, field, conflict, scanner responsibility or dedicated branch is a contract
change and needs its *reason* recorded beside it in the same commit.

Stale counts and dropped rationale are not cosmetic. The contract's authority comes
entirely from being accurate; once one table is known to be wrong, nobody checks the
rest against it, and the plumb line is gone.

**And hold the line from Part 1.** Updating a table to match reality is maintenance.
Editing a principle so a patch becomes acceptable is not, and is not yours to do.

---

# Part 9 · Boundaries

Some things are deliberately out of scope, and being asked for them is common enough
that the answer should be ready. No persistent review ledger, AST manifest or
classification registry; no per-file AST notarization of the example set; no
resident reference-compiler oracle and no CST-to-IR mapping layer; no permanent
tooling, report or baseline left inside the parser repository; no amendment to the
contract's principles to make a change land; no grammar change without a
hand-written, human-read corpus case; and no dedicated rule justified by dialect
coverage alone.

`references/boundaries.md` says why each one was rejected — several were built once
in this project's history and removed — so that a refusal comes with a reason and a
bounded alternative rather than a flat no.

If an audit keeps demanding more infrastructure to reach a conclusion, the audit is
scoped wrong. Narrow it to one construct, one invariant, one reproducer.

To bring a repository without a contract document under this skill, see
`references/onboarding.md`.
