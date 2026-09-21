# Maintaining `docs/` as a contract, in both directions


The documents under `docs/` are the instrument this whole method depends on. Treat
them as load-bearing, and audit them both ways.

**Forward — does the parser still honour what the document promises?** That is
Parts 2 through 6.

**Backward — does the document still describe the code?** Every factual claim in
the contract needs a command that confirms it. Run these whenever you touch the
relevant area, and whenever you are asked to check for drift:

| Claim in the document | Confirm with |
| --- | --- |
| Declared conflict count | `sed -n '/conflicts: (\$) =>/,/^  \],/p' grammar.js \| grep -cE '^\s*\[\$\.'` |
| Scanner token kinds and persistent state | `sed -n '/enum TokenType/,/};/p' src/scanner.c`, and check `serialize` |
| Public AST surface node names exist | grep each name in `src/node-types.json` |
| Query files and their status table | `ls queries/`, then compile each one |
| Capture vocabulary | compare the documented list against the captures in `queries/highlights.scm` |
| Dedicated dialect branches and their stated reasons | grep the named rules in `grammar.js` |
| Named gates and commands | compare against `package.json` scripts and the CI workflows |

Stale counts and dropped rationale are not cosmetic. The contract's authority comes
entirely from being accurate; once one table is known to be wrong, nobody checks
the rest against it, and the plumb line is gone.

**When a change alters the contract, update the document in the same change.** A
new node or field, a renamed field, a new conflict, a new scanner responsibility, a
new dedicated branch: each is a contract amendment and needs its reason recorded
next to it, not just its existence. Update `docs/QUERIES.md` too whenever node
names or capture choices move — it is the consumer-facing half of the same
contract.

**And hold the line from Part 1.** Updating a table to match reality is
maintenance. Editing a principle so a patch becomes acceptable is not maintenance,
and is not yours to do.

---

## Before you "fix" a documented claim

A claim that does not match the code is a finding. It is **not** automatically a
defect, and the repair is **not** automatically the obvious one. Separate three
cases before touching anything:

- **Stale** — a count or a name drifted as the code moved. Update the document.
  This is the common case and needs no discussion.
- **Intentional** — the entry records what the maintainer reserves or intends, not
  what the code currently emits. A standard capture listed in a vocabulary but not
  yet used is the archetype. Deleting it erases intent. Leave it, or raise it.
- **Ambiguous wording** — the list is accurate under one reading of the sentence
  above it and wrong under another. Then the sentence is the defect, not the list,
  and rewording is the smaller and more honest change.

When it is not clearly stale, say what you found and let the maintainer decide.
Deleting an entry and sharpening a sentence are different claims about intent, and
only one of them is yours to make.

## Do not manufacture work

If a pass turns up nothing, **the finding is that it turned up nothing** — write
that down and stop. The temptation is strongest at the end of an audit that has
found only one big problem you cannot finish: something small and completable looks
like a way to show progress. It is not. A change made to have made a change costs
the maintainer a review, puts churn in the history, and teaches them to distrust the
next finding, which may be real.

Every change needs a reason that would stand on its own if someone asked six months
later — a reader who is misled, a consumer that breaks, a claim that is false. "It
was inconsistent" is only a reason once you have established which of the three
cases above it is, and that the inconsistency actually costs someone something.

A pass whose honest output is "all gates green, three invariants clean, one known
defect still open, no new findings" is a complete pass and a useful record. Say it
plainly rather than padding it.
