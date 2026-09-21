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
| `prec.dynamic(N, …)` + `conflicts` | runtime, GLR only | two complete parses are both valid and one must be chosen |

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
npx tree-sitter parse -d FILE                              # parse decision log
npx tree-sitter parse -D FILE                              # log.html with graphs
npx tree-sitter parse --open-log -D FILE                   # and open it
```

The fastest route to the real conflict is usually to **remove** the associativity
that is hiding it and read the unresolved-conflict error `generate` then prints: it
names the exact symbol sequence and the two interpretations, which is the thing you
were guessing at.

## Seeing what the tree actually contains

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
invisible.

Run one case by name:

```bash
npx tree-sitter test -i 'exact test name'
npx tree-sitter test --file-name 14-custom-assembly.txt
```

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
   diff. A mechanical direction check helps here: count node types before and after
   and confirm only the ones you intended moved. A change that touches exactly one
   node type is almost certainly the correction; a change that moves five is not.
5. **`tree-sitter test --update` is a bulk operation with no judgement in it.** It
   will happily record a defect as the expected result, and once it does, every gate
   agrees with the bug. Use it only after step 4, and read every hunk.

## When the parser disagrees with the language's own compiler

Prefer the real parser over a hand-written approximation of it. See
`references/mlir.md` for the MLIR setup; the general shape is: normalize the input
with the reference tool, parse the tool's output with the same grammar, and compare
skeletons. Both sides are then CSTs produced by the same parser, so the comparison
needs no mapping layer — and the reference side encodes the language's own answer
rather than your guess at it.

## Sources

Check these rather than trusting the summary above, which was written against one
version and will age:

- Grammar DSL — `prec`, `prec.dynamic`, `conflicts`, `token`:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/2-the-grammar-dsl.html>
- Writing the grammar — conflicts and the GLR rationale:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/3-writing-the-grammar.html>
- Writing tests — corpus format and attributes:
  <https://tree-sitter.github.io/tree-sitter/creating-parsers/5-writing-tests.html>
- The CLI's own help is the authority on flags, which move between releases:
  `npx tree-sitter parse --help`, `test --help`, `generate --help`, `fuzz --help`

Tree-sitter's documentation does not describe every behaviour that matters — the
interaction between `prec.right` on a `repeat` and a permissive body rule is not
written down anywhere, and was established here by experiment. Where this file
states something the docs do not, treat it as a finding reproduced in this
repository rather than as an upstream guarantee.
