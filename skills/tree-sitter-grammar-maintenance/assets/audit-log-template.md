# Parser audit record

Local working note, kept in a directory the repository ignores — confirm with
`git check-ignore` before writing. It is not a repository asset and not a release
gate. Its only job is to stop the next pass from redoing work that was
already done, or re-arguing a trade-off that was already settled.

Two parts. **Current state** is rewritten at the end of every pass, and it is what
the next pass reads first. **Passes** are appended below it, one per pass, and never
rewritten; they are there when a number needs explaining. One row per decision —
never one row per input file. If a table starts growing a row per example, it has
turned into the ledger this project deliberately removed; cut it back.

Status values: `open` · `fixed in <commit>` · `accepted` (with the reason) ·
`out of scope` (with the layer that puts it there).

---

## Current state — as of pass <N>, <YYYY-MM-DD>

**Reference parser:** `<absolute path to the executable>` (<version>), or "none —
the user has no reference parser". The next pass reuses this path instead of asking;
a directory is not enough.

### Open

| # | Finding | Layer | Since | Next step |
| --- | --- | --- | --- | --- |
| 1 | <one line> | core | pass <N> | <what the next pass should do first> |

### Settled — do not re-argue

| # | Finding | Status | Why |
| --- | --- | --- | --- |
| 2 | <one line> | accepted | boundary intact; payload coarseness is within contract |
| 3 | <one line> | out of scope | runtime: needs a registered dialect's assembly callback |

An `accepted` or `out of scope` row without a reason is worthless — the next pass
will simply rediscover it and argue it again. The reason is the entire value.

### Coverage

| Evidence line | Last run | Result |
| --- | --- | --- |
| reference comparison (`skeleton`) | pass <N> | <compared> of <files> compared; <what fired> |
| corpus self-consistency (`corpus`) | pass <N> | clean / <n> cases, <m> missing |
| `probe <id>`, one row per invariant | pass <N> | clean / <n> hits in <k> mode(s) |
| highlight fixtures as their own line | never | not scanned — <why> |
| document drift, backward | pass <N> | <claims checked> |

Clean rows matter as much as hits: they let a later pass skip a check with
justification rather than by guess. A row that says *not scanned* is honest
coverage, not a gap to hide.

---

## Pass <N> — <YYYY-MM-DD>

Paste the output of
`python3 scripts/probe.py provenance --repo "$REPO" --spec "$SPEC" --tool "$TOOL"`,
then add the two lines it cannot measure:

- **Date:** <YYYY-MM-DD>
- **Branch / commit:** `<branch>` @ `<short sha>`
- **CLI version:** `<version>`, lock says `<version>`
- **Reference parser:** `<absolute path>` (<version>) / not declared
- **Skill:** `tree-sitter-grammar-maintenance` @ `<sha>`, content `<digest>` — the
  method changes between passes; this says which one produced these numbers
- **Generated parser:** regenerates identically / was stale, regenerated
- **Gates at baseline:** `npm run test` <result> · `npm run test:examples` <result>

### What ran

| Probe / check | Result |
| --- | --- |
| `skeleton` | <compared / declined>; <what fired> — or "not run: no reference parser" |
| `corpus <id>` | clean / N cases, M missing |
| `probe <id>` | clean / N hits in K mode(s) |
| … | … |

### Findings

| # | What | Layer | Status | Note |
| --- | --- | --- | --- | --- |
| 1 | <one line> | core / unknown-ext / dedicated / runtime | open | minimal repro at `<path>` |

### Document drift checked

| Claim | Verified | Result |
| --- | --- | --- |
| declared conflict count | yes/no | <n>, matches / corrected |
| scanner token kinds and state | yes/no | … |
| public AST surface names exist | yes/no | … |
| query files and status table | yes/no | … |

### Left for next time

- <what was deliberately not done, and why>
