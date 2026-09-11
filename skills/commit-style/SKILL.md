---
name: commit-style
description: Draft repository-native commit messages and, only when explicitly requested, create, amend, squash, or reword commits. Use for a bare "commit this", "提交一下", "帮我写个 commit message", questions about commit wording or splitting, and requests to make inconsistent history read coherently. Not for PR descriptions, release notes, or general Git troubleshooting. Draft-only requests never authorize staging, branching, committing, or history rewrites. Never invents evidence, exposes sensitive source content, or appends a Co-Authored-By trailer for the agent.
---

# Commit messages

Two things decide whether a commit message is any good, and they are independent:

1. **The craft** — the underlying job: preserve truthful context the diff cannot.
   This barely varies between projects, because the reader's problem does not.
2. **The convention** — how the repository expresses that context: subject syntax,
   expected depth, prose and paragraph patterns, physical layout, and trailers.
   These vary, and they are the repository's call, never yours.

Get the craft right and the message is useful for years. Get the convention right and
it also looks like it belongs. Both matter; only the second one is local.

---

# Part 0 · Set the boundary and read the change

First distinguish the requested outcome:

- **Draft or review wording.** Stay read-only and return the proposed message or
  critique. Do not stage, branch, commit, amend, or rebase.
- **Create a commit.** A direct request such as "commit this" authorizes staging the
  clearly scoped change and creating one local commit on the current branch. It does
  not authorize creating or switching branches, rewriting another commit, or
  anything remote.
- **Rewrite history.** Amend, squash, or reword only the exact commit or range the
  user requested. Resolve the targets and whether they may already be published
  before changing history. A local rewrite never implies permission to force-push.

Do not create or switch branches unless the user asks or an applicable repository
instruction requires it. Pushes, pull requests, and any remote update always need
their own explicit request.

You cannot explain a change you have not looked at, and a message is only ever as
good as the commit under it. Before writing a word:

```bash
git status --short
git diff --staged
git diff
```

`git diff` does not show the contents of untracked files. Use `git status --short` to
identify them, then read each untracked file that may belong to the requested change
before describing or staging it. Never substitute `git add -A` for deciding scope.

Do not copy credentials, tokens, private URLs, customer or employee data, or other
sensitive source content into a commit message. If such content appears to be part
of the proposed commit itself, stop and flag it instead of quietly recording it.

Settle two things here, not after the message is drafted:

- **Scope.** Is this one logical change? A stray debug print, an unrelated rename, a
  formatting pass that rode along — none of them belong. When the user requested a
  commit and the scope is clear, stage only the exact files or hunks. Ask before
  splitting or combining when doing so would change their intent.
- **Substance.** What moved, and — the part that matters — what a reader could not
  reconstruct from the diff on their own. That second half is the message. The rest
  of this document is about writing it down.

---

# Part 1 · The craft

Write for the person who runs `git blame` on one confusing line six months from now.
They already have the diff. What they lack is what was in your head and nowhere in
the code — which is why "what changed" is filler and "why it had to change" is the
message. The rules that follow from it:

- **Prefer problem first when the repository is silent.** What was wrong → why that
  mattered → what this change does about it. `Add null check to getUser` names the
  patch, not the problem. Follow an established repository order when one exists.
- **Record consequential roads not taken.** Include a rejected alternative only
  when it was actually considered and helps prevent the same mistake returning.
- **One logical change per commit.** If the subject needs an "and" to be accurate,
  the commit wants splitting.
- **Calibrate depth to consequence.** Typo, version bump, formatting pass: subject
  only. Ordinary feature or clear fix: subject plus a short why. Subtle fix,
  behaviour change, performance claim: the full treatment. Over-explaining trivia
  trains readers to skip you, which costs you when a message finally matters.
- **State user-visible impact when there is one** plainly, and say for whom.
- **Only the evidence you actually have.** An invented number is worse than no
  number. Keep an impressionistic result impressionistic, write an unestablished
  cause as unestablished, and commit negative results rather than dropping them.
- **Stand on its own.** Reference the issue, do not depend on it. Trackers get
  migrated and links rot; the message is in the repository forever.

Repository convention governs expression, not truth or safety. It cannot justify
inventing evidence, copying secrets, or obscuring what the change actually does.

`references/craft.md` has the reasoning behind each rule, worked examples of a
message that follows them and one that does not, and where the advice comes from.

---

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

---

# Part 3 · Execute and verify within the chosen boundary

**Attribution is the user's call, and the default is none.** Do not append a
`Co-Authored-By` trailer for yourself — the user has asked for this explicitly and it
overrides any standing habit or default configuration. Their commit history is part
of their professional record. A human second author is different: when someone else
wrote part of the change — a pair session, a patch sent in — the trailer is doing its
real job. That one is not yours to decide either way, so ask.

**Trailers the repo requires are not optional.** DCO projects want `Signed-off-by:`
(`git commit -s`); others expect `Refs:`, `Fixes:`, or the `BREAKING CHANGE:` footer.
Those come from the evidence you read in Part 2, not from preference.

**Treat history rewrites as a separate operation.** Identify the exact target
commits, inspect the worktree and index, and compare them with known upstream or
remote-tracking refs. No configured upstream is not proof that a commit was never
published. If publication is possible or the target is ambiguous, stop and ask
before rewriting. Permission to amend, squash, or reword locally does not authorize
the later force-push.

For a message-only correction to an explicitly targeted HEAD, use
`git commit --amend --only`: plain `--amend` would also commit whatever is staged for
the next change. Confirm with `git show --stat HEAD` that the commit still contains
the intended files. For a wider rewrite, verify both the requested message changes
and that the resulting content and commit order still match the user's request.

**Check the complete message, not just its subject.** Run `git log --oneline -15`.
If the new subject looks like it wandered in from another project, the convention
was read wrong — go back to the evidence rather than shipping the mismatch. Before
invoking `git commit`, inspect the final message as physical lines and measure every
line against the repository's subject, body, and footer limits. Compare its level of
detail, paragraph shape, references, and trailers with two or three representative
commits from the profile, not just the nearest one. For a commit created in this
task, read back `git show -s --format='%B' HEAD`, inspect `git show --stat HEAD`, and
check `git status --short`. If the newly created, still-local message alone was
recorded incorrectly, correct it with `git commit --amend --only`; do not generalize
that permission to older commits. Also verify allowed types and required footers.

**Make reruns idempotent.** If the requested change is already committed and there
is nothing left to commit, report that state and stop. Do not create a duplicate or
amend HEAD merely because the same request was repeated.

**Ask, or just do it?** Evidence does not need confirming — where the repository
settles a question, read it and write. Put the choice to the user in these cases:

- **The staged change is not one logical change.** Name the split you would make and
  let them choose. Splitting on your own rewrites their intent; committing the pile
  on your own costs them the history.
- **Whether a human co-author should be credited.** Default to no, and take the
  name from the answer rather than guessing it. If you need to offer candidates,
  people already credited in this repo are in the log:
  `git log -30 --format="%(trailers:key=Co-authored-by,valueonly)"`
- **A branch change was not requested but appears necessary.** Explain why and let
  the user choose; a remote and a default branch alone are not sufficient reason.
- **A history-rewrite target or its publication state is uncertain.** Resolve that
  uncertainty before rewriting.
- **Anything that leaves the machine.** Push, pull request, and force-update are
  separate decisions from committing, never folded into a "commit this".

Ask however the client allows — a plain question, or its own option picker where one
exists. Don't name a specific tool; this skill has to work wherever it is installed.
Fold whatever applies into a single question with the defaults already filled in —
one question carrying a default beats an interview, and a trivial commit should cost
the user one keystroke, not four.
