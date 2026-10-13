# Repository style evidence

Read before drafting a message or answering a question about repository convention.
This is read-only discovery; Git is the only required external tool. No network is
required. Use repository instructions for mandatory syntax and history for dimensions
those instructions leave unanswered.

# Part 2 · 因地制宜 — match the repository

**First: whose repository is this going into?** Usually the one you are standing in.
For a fork, or a patch you mean to send elsewhere, it is the receiving project, and
its convention beats the fork's local habits — so read the evidence there. Settle
this before reading anything, because it decides which repository the rest of this
section is even about.

Then apply the following evidence order to each style dimension. Stop at the first
source that answers that particular question; earlier sources beat later ones. A
document that settles prefixes but says nothing about body depth or layout does not
make the log irrelevant for those unanswered dimensions.

**1 · Explicit instructions in the repo** — decisive when present:

```bash
git rev-parse --show-toplevel
git ls-files -co --exclude-standard ":(top,glob)**/CONTRIBUTING*"
git ls-files -co --exclude-standard ":(top,glob)**/AGENTS.md" ":(top,glob)**/CLAUDE.md"
git ls-files -co --exclude-standard ":(top,glob)**/.gitmessage" ":(top,glob)**/.czrc"
git ls-files -co --exclude-standard ":(top,glob)**/.commitlintrc*" ":(top,glob)**/commitlint.config.*"
git config --path --get commit.template
```

Listing these files is only discovery. Open the relevant files and read their commit
instructions in context. Do not stop after finding a prefix rule: line length and
wrapping requirements often live in a general writing or commits section rather
than under a heading named "commit style". For nested instruction files, determine
which ones apply to the changed paths and read them in root-to-leaf order. Follow
relevant links from contribution docs and inspect project configuration they point
to; no filename list is exhaustive.

`-co` includes tracked and untracked candidates. The `top` magic anchors discovery at
the repository root from any working directory, while `glob` and `**/` include root
and nested locations. The quotes hand the pathspecs to Git rather than the shell. A
missing commit template exits with status 1 and simply means that source supplied no
rule.

A `commitlint` config may be enforcement: a violating message can be rejected by a
hook or CI. A commit template is strong evidence of expected structure, but it does
not enforce that structure by itself; inspect its placeholders and comments.

**2 · The log itself**, for every dimension left unanswered above:

```bash
git --no-pager log -40 --format="%h %s"
git --no-pager log -12 --format="%h%n%B%n---"
```

These are starting samples, not a quota. Expand the range when it contains too few
substantive messages, and inspect history for the component or paths being changed
when that gives a better comparison. Separate ordinary feature and fix messages from
generated merge text and special-purpose reverts, dependency bumps, or squash
metadata; those may have their own shapes without defining ordinary commits.

Do not draft after recognizing one familiar marker. First form a short,
evidence-backed profile of the dominant style across the whole message:

- **Subject grammar and vocabulary.** Prefix or tag, recurring scopes or component
  names, capitalization, mood, punctuation, and width. Distinguish text authors
  write from issue numbers or suffixes added later by a merge workflow.
- **Body threshold and content.** Which changes get a body? For comparable changes,
  how much context is normal, what information is selected, and does the prose move
  through problem, consequence, approach, trade-off, or validation in a recurring
  order? A run of trivial subject-only commits says little about a subtle fix.
- **Structure and physical layout.** Blank lines, semantic paragraphs, lists,
  indentation, hard wrapping, references, and trailers. Inspect raw line lengths.
  When prose repeatedly continues on the next physical line near the same column,
  hard wrapping is part of the convention; preserve paragraph breaks and reflow the
  new message accordingly. Do not mistake terminal soft wrapping for stored
  newlines, or infer an exact limit merely because all observed lines are short. If
  width matters, use an available local tool to measure stored lines rather than
  judging the rendered output by eye.

A prefix alone is not a style profile. Prefer an explicit rule for each dimension;
otherwise require several comparable examples before calling a pattern local style.
When evidence is sparse or inconsistent, follow only the stable signals and use the
craft rules for the rest instead of inventing precision.

**Sources disagreeing?** Prefer the documented rule over the observed log, and say so
in one line — a log usually contains drift the maintainers already decided against.
Fork against upstream is not a tie either: the receiving project decides. A fork
whose log has drifted into another convention is still sending patches to a
maintainer who has never read that log.

**No signal at all** — a fresh repo with one "Initial commit"? Don't invent ceremony.
Use the fallback below, calibrate body depth from Part 1, and tell the user no local
convention was detected so they can set one deliberately.

## Common subject shapes, not a taxonomy

**Conventional Commits** — load-bearing wherever release tooling or commitlint uses
the type to drive validation or versioning.

```
feat(auth): add refresh-token rotation
fix(installer): preserve existing skill before replacement
```

Common types include `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`,
and `chore`. Use the types and scopes allowed by repository configuration or
established history; do not assume this example list is its schema. Breaking changes
take `!` plus a `BREAKING CHANGE:` footer when the repository follows the standard.

**LLVM-style bracket tags** — LLVM, MLIR, Triton, IREE and neighbours. The bracket
tag is the overwhelming norm across these logs and a Conventional prefix is
essentially absent. Read the log for the tags actually in use rather than trusting a
proportion quoted here, which would be stale by the time you needed it.

```
[Coalesce] Widen vectorization when index and value layouts disagree
```

Derive the tag from what the change touches, preferring the most specific accurate
one — a pass or component name beats a broad subsystem. Reuse tags already in the log
rather than coining synonyms. Reverts and cross-cutting changes skip the tag.

**Other local forms** — subsystem prefixes, ticket identifiers, multiple bracket
tags, sentence-style subjects, and other stable patterns are equally valid when the
repository evidence supports them. Do not force them into one of the examples above.

**Plain imperative fallback** — use only where nothing was formalised or observed.

```
Reject empty payloads in the webhook receiver
```

When the repository is silent, use an imperative subject, no trailing period, and a
blank line before the body. Keep the subject concise and wrap body prose for
readability without claiming an exact local limit. Any observed or documented width
takes precedence and must appear as real physical newlines, not visual editor wraps.
