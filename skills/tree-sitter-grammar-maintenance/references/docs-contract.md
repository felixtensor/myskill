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
