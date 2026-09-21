# tree-sitter-mlir

The language layer for `SKILL.md`. Read `docs/ARCHITECTURE.md` in the parser
repository first — this file tells you how to *use* it, not what it says.

## Repository map

| Thing | Where |
| --- | --- |
| Contract | `docs/ARCHITECTURE.md` |
| Consumer contract | `docs/QUERIES.md` |
| Exact CST truth | `test/corpus/NN-topic.txt` |
| Query fixtures | `test/highlight/<layer>/*.mlir`, indexed by `test/highlight-fixtures.md` |
| Compatibility smoke | `examples/`, pinned by `examples/SOURCE.md` |
| Grammar / scanner | `grammar.js`, `src/scanner.c` |
| Roadmap and complexity budget | a development plan document, if the project keeps one — see below |

## Which document governs what

**`docs/ARCHITECTURE.md` is the contract.** It says what the parser promises about
tree shape: the public AST surface, the layer split, the six principles, the
declared conflicts, the scanner's responsibilities. It is the standard a finding is
judged against, it has no expiry, and its principles are not editable to fit a
patch. It is tracked, so everyone working on the repository has it.

**A development plan, if one exists, is the roadmap and the process.** It says how
work is chosen, what evidence a change owes, which gates block, what was
deliberately *not* built and why, and what the complexity budget is. Unlike the
contract it expires, and it may be a maintainer's local working document rather
than a tracked file — so look for it rather than assuming a path:

```bash
find . -maxdepth 3 -iname 'DEVELOPMENT[-_]PLAN.md' -not -path './node_modules/*'
```

If it turns up, read it before proposing any tooling or any change to the gates:
such documents usually record machinery the project already tried and removed, and
re-proposing it wastes the maintainer's time. If it does not turn up, work from the
contract alone and do not invent a process — ask the maintainer what the current
priorities are instead.

**So: adjudicate against the contract; work according to the plan.** When the two
seem to disagree about tree shape, the contract wins and the plan is stale. When
they disagree about process, the plan wins. If they genuinely conflict on substance,
that is a finding in itself — report it rather than quietly picking one.

Treat an untracked plan as the maintainer's own notes. Do not quote its contents
into a commit message, a PR description or anything else that leaves the machine;
cite the contract for that, or restate the reasoning in your own words.

## Gates

Exactly as the project defines them:

```bash
npm run test           # tree-sitter test: corpus + highlight fixtures
npm run test:examples  # tree-sitter parse --quiet --stat "examples/**/*.mlir"
npm run compile        # tree-sitter generate
npm run fuzz           # replays known seeds, then fuzzes the corpus
```

`examples/` is pinned to an LLVM commit recorded in `examples/SOURCE.md` and synced
only by `scripts/sync-examples.sh`, as an independent commit. Never edit files under
`examples/` to make something pass.

## The layer table, instantiated

`docs/ARCHITECTURE.md` states this as a three-row compatibility contract. Applied:

**Stable core — must fix.** Everything on the document's Public AST Surface list:
`operation` with its `lhs` / `rhs` / `location` fields, `op_result`, `value_use`,
`region`, `entry_block`, `block`, `block_label`, `successor`, `caret_id`,
`symbol_ref_id`, `func_operation` and its fields, `module_operation`,
`generic_operation`, the builtin type and attribute nodes, `trailing_location` and
the location family. A defect here is not negotiable — consult the list rather than
guessing which nodes count.

**Structurally unknown dialect syntax — judgement.** Unregistered dialects, custom
assembly bodies, open `dialect.op` namespaces, pretty dialect items. The promise is
principle 4 only: paired delimiters, high-value sigil references and *recoverable
outer boundaries*. So:

- Acceptable: a flat run of atoms inside a body; a coarse node where a precise one
  would be nicer; a local `ERROR` confined to one operation.
- Not acceptable: the body extending over the next operation, a block label, a
  region close, or the operation-level `loc(...)`.

The document says this directly — an `ERROR` inside one custom operation is
preferable to a clean-looking parse that absorbs later siblings. Quote that line
when someone proposes widening a fallback to remove an `ERROR`.

**Runtime dialect semantics — out of scope.** Registered assembly callbacks,
verifier rules, traits, interfaces, lowering. Record a limit; add no grammar.

## The six principles, as tests

Each principle is a question to ask of a proposed change, not a slogan:

1. **Operation-first** — does the change preserve operation, region, block, result,
   operand, successor, symbol, envelope and trailing-location boundaries before
   classifying body syntax?
2. **Generic-anchored** — does it leave quoted generic form strict? Generic form
   must never acquire custom-assembly fallbacks; it is MLIR's stable compatibility
   path and the one form a reference compiler can normalize into.
3. **Dialect-open** — does it avoid enumerating the ecosystem? A dedicated branch
   needs a demonstrated structural or consumer benefit.
4. **Boundary-preserving** — can unknown content still not swallow the next
   construct? This is the one the `span_guard` invariant mechanizes.
5. **Consumer-driven** — does a new public node or field help a query, editor
   integration or downstream consumer? Matching the runtime parser's semantic
   detail is explicitly not a goal.
6. **Evidence-bounded** — is there a minimal reproducer, and is the test
   proportional to the maintenance cost of the new conflict, fallback, branch or
   scanner responsibility?

Existing dedicated branches exist for reasons the document records: `func.func`,
`llvm.func`, `module`, `builtin.module` for stable fields; `affine.for` and
`pdl_interp.record_match` because a body `loc(...)` would otherwise steal the
operation's trailing location. A new branch must clear the same bar.

## Verifying the document against the code

| Claim | Command | Value when last checked (2026-09-21) |
| --- | --- | --- |
| "The 11 conflicts listed in grammar.js" | `sed -n '/conflicts: (\$) =>/,/^  \],/p' grammar.js \| grep -cE '^\s*\[\$\.'` | 11 — accurate |
| "emits three token kinds", "no persistent state" | `sed -n '/enum TokenType/,/};/p' src/scanner.c`; read `serialize` | 3 tokens, `serialize` returns 0 — accurate |
| Public AST surface names are real | grep each name in `src/node-types.json` | — |
| Query status table in `QUERIES.md` | `ls queries/`; compile each | 6 files — accurate |
| Capture vocabulary in `QUERIES.md` | compare against captures in `queries/highlights.scm` | — |
| Gate commands | compare against `package.json` scripts and `.github/workflows/` | — |

Record the date you checked. A table that is right today and unverified for a year
is indistinguishable from a wrong one.

## MLIR lexical facts an agent gets wrong

- `//` starts a comment. **`#` and `!` do not** — they introduce attribute and type
  aliases. Never strip `#`-prefixed lines as comments.
- Whitespace, including newlines, is insignificant. `%x =` and its operation may sit
  on different lines, and a comment may sit between two operations. Both forms are
  ordinary MLIR and both have exposed real defects here.
- `^bb0` is a block label in one position and a successor reference in another. The
  external scanner exists for that distinction; a probe on line-initial labels is a
  direct regression guard for it.
- `x` is a dimension separator in `16x16` and a bare identifier elsewhere — the
  scanner's third token.
- `loc(...)` is an operation's trailing location in one position and body syntax in
  another. Two dedicated branches exist only because of this.
- Test files under `examples/` are FileCheck tests. `// CHECK:` lines contain
  MLIR-shaped text that is *not* parsed as MLIR. Any line-based probe must skip
  comment lines or it will drown in false positives.

## The reference parser is the primary evidence line

MLIR ships its own parser. Prefer it over any pattern you would write yourself: a
regex that guesses which lines bind SSA results is a crude re-implementation of the
thing sitting on disk, and it will be wrong in ways you cannot enumerate.

### Finding the tool

`mlir-opt` is required for this line of evidence, and it is the strongest one
available, so **never skip it silently**. If it is not on `PATH`, look in the usual
places and then *ask the user where it is* rather than falling back to weaker checks
without saying so:

```bash
command -v mlir-opt || ls ~/Projects/llvm-install/bin/mlir-opt /usr/local/bin/mlir-opt 2>/dev/null
```

Any build of `mlir-opt`, or a downstream project's own `*-opt`, works. **Do not
check its version against the `examples/SOURCE.md` anchor and do not refuse to run
because they differ.** A version difference shows up as files the tool rejects —
dialect syntax that moved between releases — which is a coverage limit, not a parser
signal and not a false hit. Report the version you used and move on.

### Why comparing against it works at all

MLIR has no AST. What `mlir-opt` builds is the in-memory Operation graph, which is
what remains *after* parsing: the dialect's assembly callback has already consumed
the surface syntax, so there is no node-for-node correspondence with a CST and no
honest way to diff them directly. Writing the mapping would mean building a second
interpreter that then needs verifying itself.

The move that avoids all of that:

> Normalize the input to generic form with `mlir-opt`, then parse **its output** with
> the same tree-sitter grammar. Both sides are now CSTs from the same parser, so the
> mapping is the identity — and the reference side carries MLIR's own answer about
> the program's structure.

This is sound here specifically because the grammar parses generic form precisely
(principle 2, verified clean across hundreds of normalized files). Generic form is
the fixed point: no custom assembly, no dialect callbacks, just the core syntax the
contract commits to.

### The invocation

```bash
mlir-opt --allow-unregistered-dialect --mlir-print-op-generic --split-input-file FILE
```

Measured over 150 checked-in examples:

| Options | Files accepted |
| --- | --- |
| generic form alone | 99 / 150 |
| **`+ --split-input-file`** | **126 / 150** |
| `+ --no-implicit-module` | 52 / 150 — **do not use**, most files need the implicit module |
| `+ --mlir-print-debuginfo` | 126 / 150, same coverage, and emits `loc(...)` |

`--split-input-file` is the single biggest win: the upstream tests are full of
`// -----` chunks, and without it every one of those files is simply unavailable.
`--mlir-print-debuginfo` costs nothing and turns on a second comparison axis for the
location family, which is on the Public AST Surface.

The files the tool still rejects are pass pipelines, `expected-error` tests and
syntax from a different LLVM revision. Those are outside this check by nature, which
is exactly why the broad ERROR/MISSING sweep over all 617 examples still earns its
place — the two lines of evidence cover different halves.

```bash
python3 scripts/probe.py skeleton --repo "$REPO" --spec assets/invariants/mlir.json
python3 scripts/probe.py skeleton --repo "$REPO" --spec assets/invariants/mlir.json \
  --tool ~/Projects/llvm-install/bin/mlir-opt --limit 60
```

### What is comparable, and what is not

| Quantity | Comparable? |
| --- | --- |
| `op_result` count | **Yes, as a ranked signal** — the strongest one available |
| `operation`, `region`, `block` counts | No — the implicit module wrapper and materialized entry-block labels move them; informational only |
| attributes | No — the printer adds dialect defaults, e.g. `overflowFlags = #arith.overflow<none>` |
| names, ordering of operands | No — the printer renumbers everything |

**The `op_result` caveat, learned the hard way.** Result counts are *not* exactly
equal under parse-and-print. MLIR lets an operation's results go unnamed, and the
printer then invents a name for them:

```mlir
affine.load %m[%i] : memref<?xf32>        // source binds nothing
%0 = "affine.load"(%arg0, %arg1) ...      // mlir-opt names the result
```

So the reference side can legitimately hold more. Read the comparison as a **ranked
report**, not a pass/fail gate:

- **grammar count > reference count** — always a defect. The grammar has invented a
  binding that MLIR does not see. Triage these first; there should be none.
- **grammar count < reference count, large gap** — strong bug signal. A block whose
  operations each lose their binding produces exactly this shape.
- **grammar count < reference count, gap of one or two** — most often the unnamed
  result above. Confirm before reporting it as a defect.

Do not turn this into a pass/fail CI gate. It is a ranked lead generator whose top
entries are worth opening, and the caveat above means a green number would be
meaningless anyway.

### Two other uses

```bash
mlir-opt --verify-diagnostics FILE        # is this input legal MLIR at all?
```

Use it before blaming the grammar for failing on something, and before adding a
corpus case built from syntax you wrote by hand — a case whose input MLIR itself
rejects is not evidence of anything. Record the exact command and the tool version
wherever you cite its output.

## Worked triage: an accepted trade-off

Take this one first, because the instinct to "fix" a coarse parse is stronger than
the instinct to fix a real defect, and acting on it is how the general path gets
narrowed. Verified legal by `mlir-opt --verify-diagnostics`:

```mlir
%0 = amdgpu.mfma 16x16x16 %a * %a + %c { abid = 0 : i32 } blgp = none : vector<4xf16>, …
```

The parser produces `custom_op_name`, a structured `custom_body_dim_list` for
`16x16x16`, three flat `value_use` nodes, and a parsed `dictionary_attribute`. The
`*` and `+` are dropped as anonymous tokens. Nothing in the tree expresses that this
is a multiply-accumulate, or which operand is which — semantically, the payload
structure is meaningless.

**Verdict: accepted, do not change.** `amdgpu.mfma`'s assembly is defined by a
runtime dialect callback, so it sits in the structurally-unknown row, where the only
promise is that outer boundaries survive. They do: the operation spans exactly its
own line, the result binding is intact, every operand and type is individually
recoverable, and the following operation is a proper sibling. A query that wants the
operands can have them; a query that wants to know this is an FMA was never going to
get that from a static parser.

Adding a dedicated `amdgpu.mfma` branch here would fail all four conditions in
`SKILL.md` Part 5 at once: no blocked consumer, nothing structural lost, no
reproducer of a loss, and real conflict and maintenance cost for nominal coverage.
Principle 3 exists to stop exactly this, and principle 5 says the parser is not
trying to match the runtime parser's semantic detail.

Record it as `accepted` in the audit record **with that reasoning**, or the next
pass will rediscover the ugly tree and re-argue it.

## Worked triage: a must-fix

Kept because the reasoning is the lesson, not because the defect is current.
Confirmed 2026-09-21 on tree-sitter-mlir `dev/recheck-rules`, first on CLI 0.26.12
and again on 0.27.0 after repairing a lock/`node_modules` mismatch, with
`src/parser.c` verified to regenerate identically from `grammar.js`.

Input — ordinary MLIR, no unregistered dialect, no custom assembly:

```mlir
func.func @f(%arg0 : i32) -> i32 {
  %cst0 = arith.constant 0 : i32
  %res = arith.addi %cst0, %arg0 : i32
  return %res : i32
}
```

The first operation's `custom_operation` extends to `[2, 8]`, taking `%res` in as a
`value_use` operand and consuming the `=`. The second operation begins at the
operation name and carries **no `lhs` field at all**: the result binding is gone,
and `%res` is recorded as an operand of the operation above it.

Triage:

1. **Layer?** `op_result` and `operation.lhs` are both on the Public AST Surface.
   Stable core. Must fix. No judgement call available.
2. **Which principle?** 1 and 4. The operation boundary was not preserved, and the
   custom body absorbed the following operation's result binding.
3. **Is it a dialect problem?** No — `arith.constant` is not special here. Any
   region-less custom operation followed by a result-binding operation reproduces
   it. So the fix belongs on the general path; a dialect branch would be the wrong
   shape of answer and would violate principle 3.
4. **Where is it not?** All four invariants are clean across 220 real examples
   normalised by `mlir-opt --mlir-print-op-generic`. Principle 2 holds — the strict
   generic path is correct — so the defect is confined to the custom-assembly path.
   That negative result is what makes the fix bounded: it names where to look and
   gives a control case that must not move.
5. **Why was it invisible?** All four gates were green. `test:examples` only checks
   ERROR/MISSING, and there are none. `tree-sitter test` was green because the
   corpus records the defective shape as the *expected* tree — 43 of 88 corpus
   cases with SSA bindings, 178 `op_result` nodes short of their own inputs. The
   contract had been overwritten by the bug it was supposed to catch.

Detection, for reference. The first two need no reference compiler; the third is
what localised it:

```bash
python3 scripts/probe.py corpus --repo "$REPO" --spec assets/invariants/mlir.json
python3 scripts/probe.py probe  --repo "$REPO" --spec assets/invariants/mlir.json
# normalise a batch, then audit the normalised files using the repo's parser
mlir-opt --allow-unregistered-dialect --mlir-print-op-generic "$f" > "$OUT/$(basename $f)"
python3 scripts/probe.py probe --repo "$OUT" --grammar-repo "$REPO" \
  --spec assets/invariants/mlir.json --files '*.mlir'
```

The lesson to carry: the defect lived in the most ordinary syntax in the language,
the corpus had been taught to expect it, and every gate agreed. Audit the boring
constructs first, and never accept a generated expected tree you have not read.
