---
name: tree-sitter-grammar-maintenance
description: Work on a tree-sitter grammar as a closed loop — compare against the language's own reference parser, locate the defect, fix it, verify, repeat — and hold every change against the architecture contract so a fix for one dialect cannot quietly narrow the general parsing path. Use it to find the root cause of a failing corpus or highlight test, to repair tests after a grammar or scanner edit, to audit for silent misparses that pass every gate, before accepting `tree-sitter test --update` output, when adding support for new syntax, after an upstream example sync, and when docs/ARCHITECTURE.md or docs/QUERIES.md may have drifted. Set up for tree-sitter-mlir; tree-sitter-tablegen and tree-sitter-pdll come under it through onboarding. Expect "why does this test fail", "this parses wrong", "I changed the grammar and tests broke", "扫一下解析有没有问题", "这个语法解析得不对", "加条规则支持这个方言". Not a general MLIR or compiler question answerer.
---

# Tree-sitter grammar maintenance

**A parse that reports no ERROR is not evidence that the tree is correct.**

A permissive fallback rule has no hard terminator. When it meets syntax it was not
told to stop at, it does not fail — it absorbs. The absorbed text still appears in
the tree, in the wrong place, under the wrong parent, with no ERROR and no MISSING.
Then someone runs `tree-sitter test --update`, the wrong shape is written into the
corpus as the *expected* result, and from that moment the defect is invisible to
every gate at once — including the one the project calls its only persistent source
of truth. It hides in the most ordinary syntax in the language, precisely because
ordinary syntax is what nobody re-reads.

The second half of the job follows from the first. Once a defect is found, the
pressure is to patch the grammar until the symptom goes away. That is how a
general-purpose parser rots into a pile of dialect-specific special cases. The
architecture document exists to stop exactly that, and it only works if it is
maintained as a contract rather than as prose that trails the code.

## Three ways in

**A test is failing, or you changed the grammar and tests broke.** Read the actual
tree before editing anything: the question is never "how do I make this green" but
"which of the two is wrong", answered per case, and guessing costs more than looking.
The repair order is in `references/tree-sitter-mechanics.md`; the patch goes through
Part 5.

**Nothing is failing and you want to know what is hiding.** Run the whole loop. This
is where silent misparses live, because by definition no gate is complaining.

## The loop

1. Load the contract and the audit record; check the toolchain; get the reference
   parser from the user or the record — never by searching (Part 0).
2. Record the baseline the project's own gates report (Part 0).
3. **Compare against the reference parser** — the strongest evidence, and the first
   thing to run for a language that has one (Part 3).
4. Check the corpus against its own inputs, and run the structural invariants over
   the example set — they cover the inputs the reference tool cannot reach (Part 3).
5. Triage every lead, one mode at a time, into a layer before proposing anything
   (Part 4).
6. Minimise the confirmed ones into hand-written corpus cases, fix, and verify
   (Part 5).
7. Check the contract documents for drift in both directions (Part 8).
8. Write the pass into the audit record, including what you decided *not* to act on
   and why (Part 7).

Then go round again: a fix changes what the next comparison shows, and the residue
after a fix is the next lead.

| Read | When |
| --- | --- |
| `references/mlir.md` | whenever you work in `tree-sitter-mlir` — its gates, layer table, principles as questions, lexical traps, reference-parser setup, two worked triages |
| `references/tree-sitter-mechanics.md` | before editing a grammar rule, and when repairing tests after one |
| `references/highlight-captures.md` | when the change touches queries or captures |
| `references/docs-contract.md` | Part 8 |
| `references/upstream-sync.md` | Part 6 |
| `references/onboarding.md` | a repository with no contract document |
| `references/boundaries.md` | when asked for something this skill refuses |
| `assets/audit-log-template.md` | Part 7 |

## What writes, and what needs a yes first

The probes read the parser repository and write nothing into it. Everything that
does write is here, so none of it happens as a side effect of a check:

| Action | Writes | Before doing it |
| --- | --- | --- |
| `tree-sitter generate` — freshness check, every grammar change | `src/` in the working tree | nothing; `git diff` shows it and `git checkout -- src/` undoes it |
| grammar, scanner, corpus and query edits (Part 5) | tracked files | the change is what the user asked for |
| `npm ci` — toolchain repair | `node_modules/`, over the network | **ask** |
| a tree-sitter release binary — toolchain repair | `node_modules/tree-sitter-cli/`, downloaded | **ask**, naming the URL |
| the audit record (Part 7) | one file in an ignored directory | confirm the directory is ignored |

Committing and pushing are the user's call. Nothing here edits `examples/`, and
nothing here amends the contract's principles.

---

# Part 0 · Ground yourself before you measure anything

**Identify the repository and load its contract.**

| Repository | Contract document | Invariant spec | Language layer |
| --- | --- | --- | --- |
| `tree-sitter-mlir` | `docs/ARCHITECTURE.md` | `assets/invariants/mlir.json` | `references/mlir.md` |
| `tree-sitter-tablegen` | — | — | `references/onboarding.md` |
| `tree-sitter-pdll` | — | — | `references/onboarding.md` |

Read the contract document before you read a single tree. It is not background
material; it is the specification you are about to audit against. A repository with
no contract document cannot be adjudicated at all — see `references/onboarding.md`.

**Read the audit record next** (Part 7). Its current-state block says which findings
are open, which were examined and *deliberately accepted*, which invariants were
clean, and which reference parser the last pass used. Re-litigating a settled
trade-off is the most common way this work gets repeated.

**The reference parser is declared by the user, never discovered.** Do not search
`PATH`, do not try a list of likely names, do not take the first plausible binary. A
comparison against a tool nobody chose reads as authoritative while resting on
nothing — and the whole value of this evidence line is that its provenance is known.
Resolve it in this order:

1. **The user named it in this session** — use that path.
2. **The audit record holds an absolute path** — reuse it.
3. **Otherwise ask, and wait.** Ask however the client allows: its question or
   option-picker mechanism where one exists, plain text otherwise. One line is
   enough; the spec's `tool_hint` says what kind of tool serves.

`probe.py` runs the spec's self-check on whatever it is given and refuses a tool that
fails it, so a wrong answer fails loudly instead of quietly. **If the user has none**,
continue with the remaining checks and **say in the report that the reference
comparison did not run and coverage is reduced**. That is a fine outcome; presenting
it as a complete audit is not.

**Check the toolchain, and record what produced the numbers.** From the skill
directory:

```bash
REPO=/path/to/tree-sitter-mlir          # wherever the checkout actually lives
SPEC=assets/invariants/mlir.json
TOOL=/path/declared/by/the/user         # leave --tool off if there is none
python3 scripts/probe.py provenance --repo "$REPO" --spec "$SPEC" --tool "$TOOL"
```

It prints the lines the audit record needs — branch and commit, the CLI version
against the lock file, the reference parser's absolute path and version, the skill
version — and exits 1 when the CLI in `node_modules` is not the one the lock pins.
Measurements from a parser that is not the one CI builds are worthless, and this
check has already caught a real drift. A repository with no lock file is reported as
such: CI then takes the newest CLI in the declared range, so name the version you
measured with.

On a mismatch, **ask before repairing** with `npm ci`, and rerun `provenance` after:
npm may block the `tree-sitter-cli` install script and leave a package with no binary
in it. The remaining repair is then the matching release binary in
`node_modules/tree-sitter-cli/` — a download, so ask again.

**Then confirm the committed parser matches the grammar source:**

```bash
(cd "$REPO" && npx tree-sitter generate && git status --short -- src/)
```

It prints nothing when the checked-in parser is current. The check covers every
generated file, including `src/node-types.json`, where the public AST surface is
checked, and files a newer CLI adds. Any output means the checked-in artifacts are
stale: measure on the regenerated parser, and say in the report that `src/` now
differs from the commit.

**Record the baseline.** Run the repository's own gates and write down what they
say, unchanged:

```bash
npm run test
npm run test:examples
```

Expect them to be green. That is the point: the audit starts where the gates stop.

---

# Part 1 · What counts as evidence

There is no node-for-node oracle: a compiler's in-memory IR is what remains *after*
parsing, so it has no correspondence with a CST, and mapping one onto the other means
writing a second interpreter that then needs verifying itself — a known dead end,
which left repositories that tried it with a ledger nobody could finish reviewing.
**But there is a skeleton oracle.** Normalize the input with the reference parser and
parse *its output* with the same grammar: both sides are then CSTs from the same
parser, the mapping is the identity, and the reference side carries the language's
own answer about the program's structure.

Five lines of evidence follow, each with its own job. Do not treat them as one
checklist — confusing them is how false confidence forms. In the order to reach for
them:

1. **The reference parser** — the language's own answer, and the least arguable: a
   disagreement is the grammar reading the program differently from the
   implementation everyone else uses. It does not reach every input (Part 3).
2. **`test/corpus`** — the exact CST contract, and the only artifact that can record
   a defect as the expected result. Audit it *against its own inputs*; it passes by
   construction, so its passing proves nothing.
3. **Highlight fixtures** — the query contract. They assert capture names at source
   positions, so a fixture can pass on a wrong tree whenever the capture lands on a
   node of the right type. Read them for what they do *not* pin down.
4. **`examples/`** — compatibility smoke only. It proves the parser does not choke
   and nothing about shape; do not turn it into a per-file AST review.
5. **Structural invariants** — your own assertions, for inputs the reference tool
   declines or a language without one. Each is your guess at what the language's
   parser knows, so they produce candidates, not verdicts.

Where the reference does not reach, compare the tree against the contract. It states
which constructs get a precise CST, which get only boundary preservation, and which
are out of scope; every one of those statements is a testable claim.

---

# Part 2 · The rule that is not negotiable

> The principles in the contract document are not adjustable to accommodate a fix.
> If a change requires violating one, the change is wrong — find another one.
> Amending a principle is a separate, deliberate decision that belongs to the
> maintainer and gets its own review; it is never a side effect of making a test
> pass.

Hold this line even when the patch in front of you is small and the principle feels
abstract. The principles are what keeps a parser for an open, extensible language
from degenerating into an unmaintainable pile of per-dialect special cases — which is
the whole reason the parser was written instead of hard-coding the ecosystem.

---

# Part 3 · Run the probes

`scripts/probe.py` is standard-library Python and writes nothing into the parser
repository. Run it from the skill directory with `REPO`, `SPEC` and `TOOL` set as in
Part 0. Every command that prints detail takes `--show N` to widen it, and
`--show 0` for summary lines only; the ones that parse use every core, and
`--jobs N` limits them.

**Compare against the reference parser first, where one exists:**

```bash
python3 scripts/probe.py skeleton --repo "$REPO" --spec "$SPEC" --tool "$TOOL"
python3 scripts/probe.py skeleton --repo "$REPO" --spec "$SPEC" --tool "$TOOL" --limit 80
```

`--limit N` compares N files spread evenly across the set. The command normalizes
each input with the reference tool, parses that output with the same grammar, and
compares quantities the printer preserves — for MLIR, the results each file binds
(counted so that `%0:2` is two, because the printer regroups `%a, %b`), and the
operation, region and block counts. Read it as a **ranked lead generator, not a
gate**:

- **grammar above the reference** — always a defect, on any quantity: the grammar
  invented structure the language's parser does not see. Open these first.
- **grammar below the reference, large gap** — a strong signal on a `ranked`
  quantity, and the top of the list is where to look. On a `ceiling` quantity the
  reference is expected to count more, for the reason the spec states — which is
  also where a swallowed operation hides, so leave those to the invariants.
- **small gaps** — often a legitimate printing difference rather than a defect. The
  language layer documents which ones, and why a green number here would be
  meaningless.

Files the tool declines — pass pipelines, expected-error tests, syntax from another
compiler revision — are a coverage limit, not a parser signal: say how many were
skipped. A run that compared nothing exits 2; never report it as clean.

**Corpus self-consistency — needs no parser at all:**

```bash
python3 scripts/probe.py corpus --repo "$REPO" --spec "$SPEC"
```

It compares each corpus case's input against that case's own expected tree. A case
whose expected tree contradicts its input was accepted from `--update` without
being read.

**Structural invariants over the example set:**

```bash
python3 scripts/probe.py probe --repo "$REPO" --spec "$SPEC"
python3 scripts/probe.py probe --repo "$REPO" --spec "$SPEC" --id op-result-binding --show 10
```

Hits are grouped by **mode** — what a hit looks like structurally, such as
`value_use in custom_operation` for a binding a body swallowed — with examples drawn
from different files. Ten thousand hits in one mode are one finding: triage modes,
not files. Three invariant kinds are available, and each maps onto a contract
statement:

- `line_produces` — a source line of a given shape must start a node of a given
  type. This is how a lost or re-attributed binding is detected.
- `no_node` — ERROR / MISSING must not appear, with locations. A MISSING token is
  usually anonymous and absent from the printed tree; the probe takes it from the
  CLI's per-file error line instead.
- `span_guard` — a node must not extend across a line that unambiguously starts the
  next sibling construct. This is boundary preservation in machine-checkable form.
  With `check_after_last`, a node holding a region is checked after the region
  closes; exempting such nodes outright hid bodies that ran on past their region.

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
T=$(mktemp -d)
python3 scripts/probe.py census --repo "$REPO" --spec "$SPEC" --out "$T/before.json"
# ... make the grammar change, then ...
python3 scripts/probe.py census --repo "$REPO" --spec "$SPEC" --out "$T/after.json"
python3 scripts/probe.py diff "$T/before.json" "$T/after.json"
```

Run this on every grammar change without exception. `diff` lists the files that now
parse differently: node counts changed, or same counts with a different shape — a
span, parent or field that moved, which counts alone never show. A fix aimed at one
construct that moves unrelated files needs an explanation before review; this is the
cheapest guard against a dialect-specific fix quietly damaging the general path.

A census is a scratch measurement for one change. Write it to a temporary path,
never into the repository — a committed baseline is the persistent snapshot the
project has already decided not to maintain.

**The reference parser also answers one question the skeleton check does not:**
whether an input is legal at all. The language layer has the command. Ask it before
blaming the grammar for failing on something, and before building a corpus case out
of syntax you wrote by hand — a case whose input the language itself rejects is not
evidence of anything. Record the command and the tool version wherever you cite its
output.

---

# Part 4 · Triage: what must be fixed, what is a legitimate trade-off, what is out of scope

**A probe hit is a candidate, not a bug.** Before proposing any change, place the
finding in the contract's layer table. The layer decides the answer; your intuition
about how wrong the tree looks does not.

| Category | What the contract promises | Verdict | Evidence it takes |
| --- | --- | --- | --- |
| **Stable core** — everything on the contract's public AST surface | A precise CST | **Must fix.** Not negotiable, not deferrable, regardless of how narrow the trigger looks. | Hand-written corpus S-expression |
| **Structurally unknown extension syntax** — what the language lets users define and a static grammar cannot know | Only that outer boundaries survive | **Judgement.** A coarse, flat or locally erroneous parse of the payload is an accepted trade-off. Swallowing the following sibling construct, or a boundary the contract names, is not. | Small boundary corpus + examples smoke |
| **Narrow dedicated parsing** — a rule for one specific construct | Nothing in advance; this is the escape hatch, not a layer | **Only when all four conditions in Part 5 hold.** Nominal coverage of one more dialect is never a reason. | Real sample, minimal corpus, written rationale |
| **Runtime semantics** — what the language's implementation decides after parsing | Nothing | **Out of scope.** Record it as a known limit at most. Do not add grammar for it. | A recorded limitation |

The second row is the line you are really being asked to draw, and it is testable
rather than a matter of taste: **structure inside the payload is negotiable; the
payload's boundary is not.** Anything on the public AST surface is stable core by
definition — check the list rather than assuming a node is peripheral. The language
layer names the surface and the boundaries for its language, and works two examples
end to end, one must-fix and one accepted. Record every verdict in the audit record,
including the ones you decide *not* to act on.

**A pass that finds nothing is a finished pass.** Do not reach for a small
completable change to show progress — a fix made to have made a fix costs a review,
adds churn, and spends the credibility the next real finding will need. Every change
needs a reason that stands on its own: a reader misled, a consumer broken, a claim
that is false.

---

# Part 5 · From finding to patch

**Take one topic at a time.** One grammar or scanner theme per change, and if it
does not resolve within a couple of working sessions, split it rather than growing
it. An audit that turns into a rewrite has stopped being an audit, and a large
change forfeits the one review mechanism this project relies on: a corpus diff a
person can actually read.

**Write the minimal reproducer first, and write it as a corpus case.** Shrink the
real input until one construct remains. Write the expected tree *by hand*, from the
contract. Confirm it fails. Only then open the grammar. Never do this in the other
order: generating the tree first and reading it second is precisely how the defect
got into the corpus to begin with.

**`tree-sitter test --update` output is a draft, never a result.** Read every line
of the diff it produces. If the diff is too large to read, the change is too large
to land. A hunk you do not understand is a hunk you have not verified.

**Put the fix through the principles before you put it through the tests.** State,
in the commit message or PR, which principle justifies it.
`references/tree-sitter-mechanics.md` holds the precedence and conflict mechanics
that decide which grammar edit can possibly work; read it before the edit, not after
one mysteriously does nothing.

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
repository's own; the shape is:

```bash
npx tree-sitter generate       # must exit 0; declared conflict count must not silently grow
npm run test                   # corpus + highlight fixtures
npm run test:examples          # ERROR/MISSING smoke over pinned examples
npm run fuzz                   # where it exists: scanner, generated-parser, corpus or fuzz-runner changes

# compile every shipped query against one real file, not just highlights
for q in queries/*.scm; do npx tree-sitter query "$q" "$SAMPLE" --quiet || echo "FAILED: $q"; done
```

Then rerun the probes from Part 3 and diff the census; with a reference parser,
also `diff` a `skeleton --out` run from before against one from after. A file may
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
replaying the same seed before you spend time on the parse itself.

If the change added a conflict, a recursive rule, a scanner token or a dedicated
branch, record the before and after size of `src/parser.c` and say what the growth
bought. Ordinary changes do not need this.

**Record a public AST change where consumers will look.** A new, renamed or removed
node or field goes in the changelog, called out as a breaking AST change when it is
one, with the affected queries updated in the same change.

**Report faithfully.** Say which leads still fire and why they are acceptable. A fix
that resolves one class and leaves a related one open is a fine outcome; a fix
described as complete when it isn't will be trusted later by someone who shouldn't.

---

# Part 6 · Upstream example syncs

A sync is when new real-world syntax enters the repository, so it is the moment the
audit is worth the most — and also the moment it is easiest to turn into per-file
review. `references/upstream-sync.md` has the six steps. Never edit files under
`examples/` to make something pass: they are a pinned snapshot of someone else's
repository, and editing them destroys the only reason they are evidence.

---

# Part 7 · Keep a local audit record

Keep it in the parser repository but **outside version control**, so it stays a
local working note rather than a repository asset or a release gate. Pick a
directory the repository already ignores and confirm it before writing
(`git check-ignore -v tmp/`); if nothing is ignored, ask the maintainer where such
notes belong rather than committing one. Use `assets/audit-log-template.md`.

It has two parts. The **current state** at the top is rewritten every pass: open
findings, accepted trade-offs with their reasons, invariants that came back clean,
what has not been covered yet, and the reference parser's absolute path. Below it,
one entry per pass is appended and never rewritten: the `provenance` lines, what ran
and what did not, and one line per finding with a status — `open`,
`fixed in <commit>`, `accepted`, or `out of scope`. The next pass reads the current
state; the history is there when a number needs explaining.

**The reason attached to an `accepted` or `out of scope` row is the whole point** —
a status with no reason gets rediscovered and re-argued. And the record must never
become a per-file classification, a tree manifest, hashes, a coverage score or a
release gate: those were built once and removed, because they reduced no judgement
and made ordinary fixes wait on a data platform. One row per decision.

---

# Part 8 · Keep `docs/` accurate, in both directions

The contract documents are the instrument this whole method depends on, so audit
them both ways: forward, does the parser still honour what the document promises
(Parts 3–6); backward, does the document still describe the code.
`references/docs-contract.md` has the per-claim verification commands, how to tell a
stale claim from a deliberate one, and the rule for amendments: a new node, field,
conflict, scanner responsibility or dedicated branch is a contract change and needs
its *reason* recorded beside it in the same commit.

Updating a table to match reality is maintenance. Editing a principle so a patch
becomes acceptable is not, and is not yours to do.

---

# Part 9 · Boundaries

No persistent review ledger or AST manifest; no per-file AST notarization of the
example set; no resident reference-compiler oracle or CST-to-IR mapping layer; no
permanent tooling, report or baseline inside the parser repository; no amendment to
the contract's principles to make a change land; no grammar change without a
hand-written, human-read corpus case; no dedicated rule justified by dialect coverage
alone. `references/boundaries.md` says why each was rejected, so that a refusal
comes with a reason and a bounded alternative rather than a flat no.

If an audit keeps demanding more infrastructure to reach a conclusion, the audit is
scoped wrong. Narrow it to one construct, one invariant, one reproducer.
