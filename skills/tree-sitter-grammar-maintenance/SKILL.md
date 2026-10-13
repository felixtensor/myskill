---
name: tree-sitter-grammar-maintenance
description: "Audit and repair existing tree-sitter grammars: investigate failing tests or silent misparses, review grammar/scanner changes and conflict decisions, and verify architecture or query contracts. Use for parser defects, test-update reviews, syntax additions, and upstream example syncs. Includes an MLIR profile; onboard other languages from their own contracts. Not for general compiler semantics or writing a grammar from scratch."
---

# Tree-sitter grammar maintenance

**A parse that reports no ERROR is not evidence that the tree is correct.**

A permissive fallback can absorb later constructs without reporting ERROR or
MISSING. Generated expectations can then teach the corpus to accept the defect.
Read expected trees against their inputs and the project's contract.

## Two ways in

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
| [MLIR profile](references/mlir.md) | whenever you work in `tree-sitter-mlir` — its gates, layer table, principles as questions, lexical traps, reference-parser setup, two worked triages |
| [Mechanics](references/tree-sitter-mechanics.md) | before editing a grammar rule or declaring a conflict, and when repairing tests after one |
| [Captures](references/highlight-captures.md) | when the change touches queries or captures |
| [Document contract](references/docs-contract.md) | Part 8 |
| [Upstream sync](references/upstream-sync.md) | Part 6 |
| [Onboarding](references/onboarding.md) | a repository with no contract document |
| [Boundaries](references/boundaries.md) | when asked for something this skill refuses |
| [Audit template](assets/audit-log-template.md) | Part 7 |

## What writes, and what needs a yes first

The probes read the parser repository and write nothing into it. Everything that
does write is here, so none of it happens as a side effect of a check:

| Action | Writes | Before doing it |
| --- | --- | --- |
| `tree-sitter generate` — freshness check, every grammar change | `src/` in the working tree | preserve existing `src/` changes; inspect the generated diff |
| grammar, scanner, corpus and query edits (Part 5) | tracked files | the change is what the user asked for |
| `npm ci` — toolchain repair | `node_modules/`, over the network | **ask** |
| a tree-sitter release binary — toolchain repair | `node_modules/tree-sitter-cli/`, downloaded | **ask**, naming the URL |
| the audit record (Part 7) | one file in an ignored directory | confirm the directory is ignored |

Committing and pushing are the user's call. Nothing here edits `examples/`, and
nothing here amends the contract's principles.

---

# Part 0 · Ground yourself before you measure anything

Read [audit setup](references/audit-workflow.md) before running probes. Identify
this checkout, read its contract and existing audit record, and establish toolchain
provenance and a baseline. Preserve existing generated-file edits before a
freshness check; failed generation can still rewrite `src/grammar.json`.

Use [MLIR](references/mlir.md) and `assets/invariants/mlir.json` only for an MLIR
repository. Other languages use their own contract, spec and gates; if these are
missing, follow [onboarding](references/onboarding.md) and state the coverage limit.

Reuse the reference executable declared in this session or the audit record.
Otherwise ask; do not search PATH for a plausible substitute. Without a reference
parser, continue the other checks and report that comparison did not run.

---

# Part 1 · What counts as evidence

A reference parser answers what syntax is legal, but its output may include
semantic expansion or printer-added structure. Compare only quantities the language
profile proves are preserved. When the tool prints syntax this grammar also parses,
compare both CSTs with the same parser; [MLIR](references/mlir.md) documents that
route. Otherwise define and validate a narrow mapping during onboarding.

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

Follow [probe commands and interpretation](references/audit-workflow.md).
For a full audit, run supported reference comparison, corpus self-consistency and
structural invariants. For a narrow failing test, start with its input and tree;
expand checks according to the patch's effects.

Group hits by structural mode and triage them against the contract. A candidate
is not a confirmed bug; skipped inputs and zero comparisons are coverage limits.
The language profile explains which counts survive normalization and which only
provide an upper bound. Do not transplant MLIR's count assumptions to another
language.

Every grammar change gets before/after census and a diff with an explanation for
each changed group. With a validated normalizer, also compare saved skeleton runs;
an AST-only reference tool uses its validated language-specific comparison instead.
Report any comparison this profile does not yet support.
Keep outputs in a temporary directory. Build and parse with this checkout's parser,
and isolate `TREE_SITTER_LIBDIR` for second-checkout test/fuzz runs.

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

**A pass that finds nothing is a finished pass.** Do not reach for a small change
to show progress: every change needs a reason that stands on its own — a reader
misled, a consumer broken, a claim that is false.

---

# Part 5 · From finding to patch

Read [repair and verification](references/patch-workflow.md) before changing the
parser. It preserves the required sequence: hand-written failing corpus case and
passing false-positive guards, a contract-supported repair, then applicable gates
and before/after comparisons.

Read [tree-sitter mechanics](references/tree-sitter-mechanics.md) for grammar,
scanner, precedence or conflict edits. Generated test updates are review drafts;
named-node equality cannot prove full-CST equality. Pin alternate construction
paths with `:cst` cases. Dedicated rules need the four conditions in the repair
reference, including a guard for unknown extension syntax.

Run fuzz for ambiguity-resolution changes, update affected queries and public AST
contracts, and report unresolved leads. Seek an independent review before shipping
a parser patch. A contract principle change remains a separate maintainer decision.

---

# Part 6 · Upstream example syncs

A sync is when new real-world syntax enters, so the audit is worth most then — and
is easiest to turn into per-file review. `references/upstream-sync.md` has the six
steps. Never edit `examples/` to make something pass: it is a pinned snapshot of
someone else's repository, and editing it destroys its value as evidence.

---

# Part 7 · Keep a local audit record

Keep it in the parser repository's main checkout but **outside version control**:
pick a directory the repository already ignores and confirm it
(`git check-ignore -v tmp/`); if nothing is ignored, ask the maintainer.
`assets/audit-log-template.md` gives the shape — a current state rewritten every
pass, reference parser path included, then one appended entry per pass with its
`provenance` lines and a status for each finding. Not allowed to write there? Put
the entry beside your work and say where, for the maintainer to merge.

**The reason attached to an `accepted` or `out of scope` row is the whole point**:
a status without one gets re-argued. One row per decision, never one per file — and
never a manifest, a coverage score or a release gate (Part 9).

---

# Part 8 · Keep `docs/` accurate, in both directions

Audit the contract documents both ways, since this whole method depends on them:
forward, does the parser still honour what they promise (Parts 3–6); backward, do
they still describe the code. `references/docs-contract.md` has the per-claim
commands, how to tell a stale claim from a deliberate one, and the amendment rule: a
new node, field, conflict, scanner responsibility or dedicated branch records its
*reason* beside it in the same commit.

Updating a table to match reality is maintenance. Editing a principle so a patch
becomes acceptable is not, and is not yours to do.

---

# Part 9 · Boundaries

No ledger or AST manifest, no per-file notarization of the examples, no resident
oracle or CST-to-IR mapping, no permanent tooling or baseline in the parser
repository, no principle amended to land a change, no grammar change without a
hand-written corpus case, no dedicated rule for coverage alone:
`references/boundaries.md` gives each its reason. An audit that keeps demanding
infrastructure is scoped wrong; narrow it to one construct, one invariant, one
reproducer.
