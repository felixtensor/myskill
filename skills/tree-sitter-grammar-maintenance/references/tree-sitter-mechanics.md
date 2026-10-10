# Tree-sitter mechanics that decide parser bugs

Only the mechanics that change what you do when hunting a misparse or repairing a
test after a grammar edit. Not a tutorial.

## Why a "correct-looking" rule still parses wrong

Four different mechanisms decide the shape of a tree, and they fire at different
times. Picking the wrong one wastes hours, because the change looks reasonable and
simply does nothing.

| Mechanism | When it acts | Use it for |
| --- | --- | --- |
| `token(prec(N, …))` | lexing | one token must win over another that matches the same text |
| `prec(N, …)` | parser generation | a static shift/reduce or reduce/reduce tie |
| `prec.left` / `prec.right` | parser generation | associativity; **also silently settles a repeat's continue-versus-stop** |
| `conflicts` | parser generation keeps both actions; the runtime forks | the right reading depends on more than one token of lookahead |
| `prec.dynamic(N, …)` | runtime, only inside a declared conflict | two complete readings both survive and one must be chosen |

### The rule that costs the most time

From the [grammar DSL reference][dsl]: `prec.dynamic`'s precedence "is applied at
*runtime* instead of at parser generation time", and it "is only necessary when
handling a conflict dynamically using the `conflicts` field in the grammar, and when
there is a genuine *ambiguity*".

[dsl]: https://tree-sitter.github.io/tree-sitter/creating-parsers/2-the-grammar-dsl.html

So:

- **`prec.dynamic` with no matching `conflicts` entry does nothing.** The alternative
  parse is never explored, because the static table already settled the decision.
  The grammar will still generate, tests will still run, and your change will have
  no effect at all. If a `prec.dynamic` edit changes nothing, this is why — check
  for the `conflicts` entry before assuming the number was too small.
- **Tree-sitter "compares the total dynamic precedence associated with each rule, and
  selects the one with the highest total."** *Total*, summed over the whole
  ambiguous subtree. A weight on a rule that appears the **same number of times** in
  both readings cancels out and cannot break the tie. Count the occurrences in each
  reading before trusting a weight; put the weight on something whose count actually
  differs between them.
- **`prec.right` on a `repeat` is a silent decision.** It resolves "continue the
  repeat or stop here" statically, always in favour of continuing. That is usually
  what you want and occasionally catastrophic: a permissive body rule will keep
  swallowing whatever follows. To let GLR weigh it instead, remove the associativity
  and declare the rule in `conflicts`, then supply dynamic precedences that
  distinguish the readings.
- **`generate` reporting "unnecessary conflicts" is information, not noise.** It
  means those rules are never in conflict in any state, so your theory about where
  the ambiguity lives is wrong. Re-derive it before trying another edit.

### Finding where the decision is actually made

```bash
npx tree-sitter generate --report-states-for-rule <rule>   # states for one rule
npx tree-sitter generate --report-states-for-rule -        # state count per rule
npx tree-sitter parse FILE -d                              # parse decision log
npx tree-sitter parse FILE -D                              # log.html with graphs
npx tree-sitter parse FILE --open-log -D                   # and open it
```

Put `-d` **after** the file. In CLI 0.26 and 0.27 it takes an optional value, so
`parse -d FILE` reads the file name as the debug mode and fails.

The fastest route to the real conflict is usually to **remove** the associativity
that is hiding it and read the unresolved-conflict error `generate` then prints: it
names the exact symbol sequence and the two interpretations, which is the thing you
were guessing at.

## Conflicts are a modelling decision

The [official guide][conflicts] puts it plainly: "Sometimes, conflicts are actually
desirable." When `generate` stops on an unresolved conflict it lists the resolutions
it accepts — a precedence, an associativity, or *add a conflict for these rules* —
and the third is not the lesser one. Real languages are locally ambiguous: MLIR
cannot tell `!foo` a type alias from a dialect namespace until it sees what follows.
Forcing such a construct through a static precedence picks a reading before the
evidence arrives. The pick is silent, and it is wrong on every input that needed the
other reading.

[conflicts]: https://tree-sitter.github.io/tree-sitter/creating-parsers/3-writing-the-grammar.html#using-conflicts

### What a declaration buys, and what it costs

A declared conflict tells the generator to keep every action in that state. At
runtime the parser forks and carries each reading forward. Each fork then meets one
of three fates:

| Fate | What happens | Cost |
| --- | --- | --- |
| **Local ambiguity** | later tokens kill every fork but one, so one complete parse exists | parse time and table states; nobody has to choose |
| **Genuine ambiguity** | two forks complete the same span and merge; the runtime keeps one | a choice — and someone has to have made it |
| **Version cap** | more than six forks are alive; the least promising are dropped, mostly without a log line | the right reading can vanish with no ERROR |

The runtime keeps one reading of a genuine ambiguity by these rules, in order
(`ts_parser__select_tree` in [`lib/src/parser.c`][parser.c]):

1. the lower error cost;
2. then the higher total dynamic precedence;
3. then a structural comparison of the two subtrees: symbol, then child count,
   then each child in turn. The symbols compare by the numbers the generator
   assigns, and those move when rules are reordered. When everything compares
   equal, the log says `select_existing` and the reading reached first is kept.
   The comparison ignores aliases and field names, so the two can still differ
   there.

The third rule is not a decision anybody wrote down. In tree-sitter-tablegen,
`foreach i = 1 in` has two complete readings, `range_piece` and `_simple_value`,
and no dynamic precedence: it parses as `integer_literal`. Move the `range_piece`
rule above `_simple_value` in the grammar, change nothing else, and it parses as
`range_piece`. **A refactor that only reorders rules changes trees.**

The cap is `MAX_VERSION_COUNT`, 6, in the same file. Most drops happen when the
stack is condensed, which logs only a generic `condense` line. The one specific line,
`aborting reduce with too many versions`, appears for some reduce-time drops and not
others. So a log without it is not evidence that nothing was dropped. A conflict that
forks once for each element of a list is the shape that reaches the cap.

[parser.c]: https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/lib/src/parser.c

### Choosing a resolution

Read the conflict first. `generate`'s error names the symbol sequence, the lookahead
and each interpretation; `probe.py conflicts` prints the same for a declaration
already in place. Then take the first rung that holds:

1. **The grammar invented the ambiguity.** Two rules describe the same text and
   give a consumer no structure it could use. Merge them, or hide one — the guide's
   "Structuring Rules Well". This removes the conflict instead of managing it.
2. **One reading is right whenever this lookahead token appears.** Use a static
   `prec` or associativity, as `generate` offers. It is the cheapest rung — no fork,
   no runtime cost — and the final one: the table never revisits it. Check the
   readings it rules out against real input before trusting it:
   `probe.py conflicts --static` tries each resolution `generate` offers in place
   of a declaration and lists what moves. `prec.right` on a repeat is this rung
   taken by accident.
3. **The right reading depends on tokens further ahead.** Declare the conflict.
   If the forks are local, that is all it needs: later tokens decide.
4. **Both readings can complete.** Declare the conflict *and* say which reading
   wins: a `prec.dynamic` on a rule that appears in one reading and not the other,
   and corpus cases that pin the winner. The defect is a genuine ambiguity left to
   symbol order, not the conflict itself. If both readings give the same tree,
   no corpus case can pin either: you are on rung 1.
5. **The weighted choice fails fuzz, or has to end a construct at a boundary.**
   Decide it in the lexer — the next section. The docs present external scanners
   as the tool for what lexical rules, parsing and dynamic precedence cannot
   handle. This is the last rung, not the first.

**When the ladder and the request disagree.** A user who asks for a conflict may be
on rung 1, and one who asks for a precedence may be on rung 4. The request is
theirs; the ladder is evidence. Measure both — the rung asked for and the rung the
ladder points to, with `--static`, `--flip` and a census — and let the user choose.
Doing either one silently is the wrong outcome.

### When a full parse is right and an incremental one is not

A `prec.dynamic` decision is made between two complete readings. Incremental
re-parse reuses subtrees and does not reliably make it again, so a weighting that
fixes every whole-file test can still fail fuzz. When it does, stop tuning the
weight and move the decision into the lexer, where nothing is left to weigh:

- Emit an external token the permissive rule cannot consume. The scanner's
  `valid_symbols` include tokens that are only valid after a reduction, so returning
  one forces the reduction the static table would have skipped.
- **Consume only the sigil.** Take the first character (`%`, `"`), `mark_end`, then
  read on for the evidence without consuming it; tree-sitter re-lexes the token when
  an edit lands inside the range it looked at. Alias the token to the anonymous
  token it stands for, and let the grammar parse the rest with the rule the ordinary
  path uses, which stays the other alternative:

  ```js
  _op_result_value: ($) => seq(alias($._op_result_sigil, "%"), $._suffix_id),
  op_result: ($) => seq(choice(alias($._op_result_value, $.value_use), $.value_use), …),
  ```

- **Never alias a whole external token to a named node.** An alias renames what it
  wraps, and an external token is a terminal, so the node comes out a leaf without
  the anonymous children the ordinary path gives it. Named nodes stay equal, so no
  corpus tree, census or probe notices. A token that swallows the whole name also
  shuts out every spelling the scanner does not reimplement — escaped names, first
  time round.
- Pin the two paths against each other with a `:cst` corpus case that reaches the
  same node once through each; it compares anonymous tokens too.
- Make the evidence narrow — position, the whole shape, what must follow — and give
  each branch of it a direct-hit case, plus false-positive guards shaped like the
  commonest real continuation lines. Then measure the envelope on real input: for
  every line where the token fires, the line before should end a complete
  construct. Write down what is still absorbed and what is now cut
  (`references/docs-contract.md`); "never" is a claim the next reviewer will break.

tree-sitter-mlir: a custom body absorbed the next operation's `%x =` binding.
`prec.dynamic` with a declared conflict fixed every full parse and failed the fuzz
seed. An external token for a line-start `%x … = <operation name>` passed it (#74)
— as a leaf `value_use` without its `%`. The follow-up building the same boundary
for unbound generic operations (#75) caught that, and fixed both with the sigil
pattern above and one `:cst` case.

### Measuring what a conflict decides

```bash
python3 scripts/probe.py conflicts --repo "$REPO" --spec "$SPEC"
python3 scripts/probe.py conflicts --repo "$REPO" --spec "$SPEC" --runtime --flip
python3 scripts/probe.py conflicts --repo "$REPO" --spec "$SPEC" --only RULE --flip
python3 scripts/probe.py conflicts --repo "$REPO" --spec "$SPEC" --static
```

With no flags it explains each declaration: the conflict `generate` reports without
it, with its symbol sequence, lookahead, interpretations and the static resolutions
`generate` would accept. A declaration the grammar generates without is
unnecessary, and the command exits 1. It reads `src/grammar.json` and generates
into a temporary directory, so no JavaScript runs and the repository is untouched.
The spec is optional; without one, inputs default to `examples/` by the file types
in `tree-sitter.json`, and `--cli` names a binary when the repository has none.

- **`--runtime`** parses the examples and every corpus input with `-d`, and counts
  the choices the runtime made between complete readings, by what decided them:
  dynamic precedence, symbol order, or stack order (readings equal by symbol). It
  also counts the version-cap line, as a lower bound. Rows are named after the
  node being reduced where the readings merged — usually a parent of the
  conflict's rules, not one of them. The count covers the whole grammar even
  with `--only`, because a log line does not name the declaration behind it. It
  is a lower bound: when two equivalent readings link the same stack nodes,
  `stack_node_add_link` in `lib/src/stack.c` keeps one and logs nothing.
- **`--flip`** favours each side of each conflict in turn with a large dynamic
  precedence, rebuilds, and lists the inputs whose named nodes move, and whether
  a corpus case would then fail — compared as `tree-sitter test` compares, so a
  span-only move or an `:error` case pins nothing. A side that moves nothing is
  local on these inputs *or* genuine with readings that differ only in hidden
  nodes and anonymous tokens; `--runtime` tells which. A side that moves only
  examples is a choice the runtime makes on real input that nothing pins — a
  lead, and exit 1. Favouring a
  rule weights every ambiguity it takes part in, so a rule in two declarations is
  flipped once and reported under the first. Read one moved file before
  attributing it to a conflict. `:skip` cases do not count as pinning.
- **`--static`** removes each needed declaration in turn and puts each static
  resolution `generate` offered in its place — `prec` on one side, or `prec.left`
  / `prec.right` — then reports whether the grammar generates and which inputs
  move. `REPLACEABLE` means no named node moves on these inputs: rung 2 holds
  there. A variant that moves inputs can still be the fix, when every move goes to
  the right reading. It reports leads, never a finding.

They measure only the inputs given. A conflict that is quiet on every one of them
can still be genuine: turn the symbol sequence into an input and parse it with `-d`.
tablegen's `'foreach' identifier '=' integer_literal • 'in'` became
`foreach i = 1 in def A;`, which no example or corpus case contained.

Watch for one text read two ways. When the same spelling parses as different nodes
depending on what follows it, a genuine ambiguity is being settled by stack order,
and no tool here will name it: the merge happens in `stack_node_add_link`, which
logs nothing. In tree-sitter-mlir, `test.op !foo<i32>` alone is a `dialect_type`;
with another operation after it, a `type_alias` — and one corpus case recorded both
as expected. Parse the construct alone and with a sibling after it.

### Recording an accepted conflict

Real ambiguity is not a reason to refuse a conflict, and a conflict is not exempt
from evidence. This record makes a new declaration an ordinary, reviewable change.
Put a short form in the contract's conflict table and the whole of it in the commit
or PR:

| Field | Where it comes from |
| --- | --- |
| The rules, and the conflict `generate` reports without the declaration | `probe.py conflicts --only RULE` |
| Its fate — local or genuine — and on which inputs | `--runtime`, `--flip`, and an input built from the symbol sequence |
| For a genuine one: the `prec.dynamic` that decides it, and the corpus cases that pin the winner | the grammar, `test/corpus` |
| The rungs above it, and why each failed — with a number where there is one | the attempt itself. tree-sitter-mlir's `array` and `tensor` rows are the model: token precedence was tried and grew the parser without improving the tree |
| Cost: `src/parser.c` size, `STATE_COUNT`, parse throughput, before and after | `SKILL.md` Part 5 |
| Fuzz, for a genuine one | the repository's fuzz gate |

A declaration with this record is a modelling decision. One without it is what a
reviewer is right to refuse, and it will be the one nobody dares remove later.

## Seeing what the tree actually contains

**Parse with this checkout's parser.** `tree-sitter parse` picks a grammar by file
extension among all it knows, other checkouts in its config included: in a worktree
it parsed with the main checkout's grammar despite `--grammar-path` and its own
`TREE_SITTER_LIBDIR`. `probe.py` builds and loads the checkout's own; by hand, run
`tree-sitter build -o LIB`, then `parse --lib-path LIB --lang-name NAME`.
`tree-sitter test` and fuzz do compile the current directory, but into a cache
keyed by grammar name, and they rebuild only when `src/` is newer than the cached
library. A second checkout's build can therefore serve the first. Give every
checkout other than the main one its own `TREE_SITTER_LIBDIR=$(mktemp -d)`.

The default S-expression shows **named nodes only**. Anonymous tokens — the `=`, the
`,`, the punctuation a loose fallback absorbed — are invisible. When a span looks too
long but the children look right, the absorbed material is anonymous:

```bash
npx tree-sitter parse --cst FILE        # includes anonymous tokens
npx tree-sitter parse -x FILE           # XML
npx tree-sitter parse --no-ranges FILE  # compact, good for diffing two trees
```

Node **ranges are the real evidence of a boundary bug**. A node whose span crosses
into the next construct's line has absorbed it, whatever its children look like.
Read `[row, col]` before concluding a tree is fine.

## Corpus test attributes

Header attributes, one per line under the test name:

| Attribute | Use |
| --- | --- |
| `:error` | assert the parse contains an ERROR, with no expected tree — the right way to pin recovery behaviour |
| `:skip` | disable, for a known-failing case you are not fixing now |
| `:fail-fast` | stop the run at this failure |
| `:platform(macos)` | restrict by OS |
| `:language(name)` | multi-parser repositories |
| `:cst` | expect a full CST including anonymous tokens |

`:cst` is worth reaching for when the defect is about *what got absorbed* rather than
about named structure — it makes the swallowed punctuation assertable instead of
invisible — and whenever two paths must build the same node. `tree-sitter fuzz`
compares a `:cst` case as a CST only since tree-sitter `543734d2` (in 0.27.0, not in
0.26.12); an older CLI compares it as an S-expression and fails a correct tree, so
check what CI pins (`probe.py provenance`).

Run one case by name:

```bash
npx tree-sitter test -i 'a regex, not a literal name'
npx tree-sitter test --file-name 14-custom-assembly.txt
```

`-i` matches names by **regular expression**, so `.` and `(` in a test name are
metacharacters. Anchor or escape when a name would otherwise match several cases.

## Repairing tests after a grammar change

This is the common loop, and the order matters.

1. **Run the narrow test first** (`-i`), not the whole suite. A single readable
   failure beats fifty.
2. **Read the actual tree before editing anything** — `tree-sitter parse` on a file
   holding just that test's input, with ranges. Decide whether the parser or your
   expectation is wrong. Both happen; assuming it is always the parser leads to
   grammar churn, and assuming it is always the expectation is how a defect gets
   written into the corpus as truth.
3. **If the expectation was wrong, fix that one case by hand** and say why it was
   wrong. Do not reach for `--update`.
4. **If the parser is wrong**, fix the grammar, then regenerate and read the whole
   diff. A mechanical direction check helps here: take a `probe.py census` before
   and after, and confirm with `diff` that only the node types you intended moved.
   A change that touches exactly one node type is almost certainly the correction;
   a change that moves five is not — unless `diff`'s groups explain each one: files
   are grouped by the set of types that moved in them, and a small group that moved
   something unexpected is the lead. `diff` also lists files whose shape moved while
   every count stayed put — read those too.
5. **`tree-sitter test --update` is a bulk operation with no judgement in it.** It
   will happily record a defect as the expected result, and once it does, every gate
   agrees with the bug. Use it only after step 4, and read every hunk.

### Checking a large corpus diff by its shape

```bash
python3 scripts/probe.py corpus --repo "$REPO" --spec "$SPEC" --before HEAD
```

After `--update`, this compares every case with its committed version: cases whose
input and leaf order held are grouped by the inner node types that moved, and any
case whose input or leaves moved is flagged to read first. The `corpus` check itself
runs too, and should come back clean. For the result-binding fix it printed one
group — 44 cases, `op_result +180` — which is what a correction looks like.

It compares leaf order, not preorder. When a node moves to a neighbouring parent — a
`value_use` leaving the end of one body to become the next operation's
`op_result` — its preorder position changes even though the fix is right, so a
preorder check flags every correct case; the first hand-written version of this
check did exactly that. The command does not replace reading the hunks; it tells you
which kind of hunk you are about to read.

## Reading a fuzz result

`tree-sitter fuzz` has two failure lines, and they mean different things:

| Line | Meaning |
| --- | --- |
| `Incorrect initial parse for …` | A full parse disagrees with the corpus: a stale expected tree, or a `:cst` case under a CLI without `543734d2` (0.26.12 lacks it). Not an editing problem |
| `Incorrect parse for … - seed N` | An edit re-parsed differently from a fresh parse — the incremental failure fuzz exists to find |

A pass is evidence only if fuzz could have failed on this machine and corpus. When a
change replaces an approach fuzz rejected, run that approach as a control: put it
back in a scratch checkout, regenerate its corpus with `--update` so it cannot fail
for the first reason, replay the recorded seed, and see it fail. Then replay the same
seed against the change.

## When the parser disagrees with the language's own compiler

Prefer the real parser over a hand-written approximation of it. `SKILL.md` Part 1
has the method and `references/mlir.md` the MLIR setup.

## Sources

Check these rather than trusting the summary above, which was written against one
version and will age:

- Grammar DSL — `prec`, `prec.dynamic`, `conflicts`, `token`:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/2-the-grammar-dsl.html>
- Writing the grammar — conflicts and the GLR rationale:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/3-writing-the-grammar.html>
- Writing tests — corpus format and attributes:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/5-writing-tests.html>
- External scanners — when to reach for one, and the error-recovery call with every
  token valid:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/4-external-scanners.html>
- How the runtime chooses between complete readings, and the version cap —
  `ts_parser__select_tree`, `ts_parser__condense_stack`, `MAX_VERSION_COUNT`; the
  docs do not describe either:
  <https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/lib/src/parser.c>
- The CLI's own help is the authority on flags, which move between releases:
  `npx tree-sitter parse --help`, `test --help`, `generate --help`, `fuzz --help`

Tree-sitter's documentation does not describe every behaviour that matters — the
interaction between `prec.right` on a `repeat` and a permissive body rule is not
written down anywhere, and neither is the symbol-order tie-break; both were
established here by experiment. Where this file states something the docs do not,
treat it as a finding reproduced in this repository rather than as an upstream
guarantee.
