# Parser audit record

Local working note, kept in a directory the repository ignores — confirm with
`git check-ignore` before writing. It is not a repository asset and not a release
gate. Its only job is to stop the next pass from redoing work that was
already done, or re-arguing a trade-off that was already settled.

Keep it short enough to read in full before starting a pass. One row per decision —
never one row per input file. If it starts growing a row per example, it has turned
into the ledger this project deliberately removed; cut it back.

Status values: `open` · `fixed in <commit>` · `accepted` (with the reason) ·
`out of scope` (with the layer that puts it there).

---

## Pass <N> — <YYYY-MM-DD>

- **Branch / commit:** `<branch>` @ `<short sha>`
- **CLI version:** `<npx tree-sitter --version>`, lock says `<locked version>`
- **Generated parser:** regenerates identically / was stale, regenerated
- **Reference parser:** not used / `<absolute path>` `<version>` — record the
  path so the next pass does not have to ask for it again
- **Gates at baseline:** `npm run test` <result> · `npm run test:examples` <result>

### Probes run

| Probe / invariant | Result |
| --- | --- |
| `corpus <id>` | clean / N cases, M missing |
| `probe <id>` | clean / N hits |
| … | … |

Invariants that came back **clean** matter as much as the hits — they are what a
later pass can skip with justification rather than by guess.

### Findings

| # | What | Layer | Status | Note |
| --- | --- | --- | --- | --- |
| 1 | <one line> | core / unknown-ext / dedicated / runtime | open | minimal repro at `<path>` |
| 2 | <one line> | unknown-ext | accepted | boundary intact; payload coarseness is within contract |
| 3 | <one line> | runtime | out of scope | needs a registered dialect's assembly callback |

An `accepted` or `out of scope` row without a reason is worthless — the next pass
will simply rediscover it and argue it again. The reason is the entire value.

### Document drift checked

| Claim | Verified | Result |
| --- | --- | --- |
| declared conflict count | yes/no | <n>, matches / corrected |
| scanner token kinds and state | yes/no | … |
| public AST surface names exist | yes/no | … |
| query files and status table | yes/no | … |

### Left for next time

- <what was deliberately not done, and why>
