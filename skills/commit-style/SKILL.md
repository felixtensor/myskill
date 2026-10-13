---
name: commit-style
description: Draft or review repository-native commit messages, infer commit conventions, and create or rewrite commits only when requested. Use for commit wording, splitting, "commit this", "提交一下", or rewording specified history. Not for PR descriptions, release notes or general Git troubleshooting.
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

[Writing rationale and examples](references/craft.md) explains these rules with
worked examples. Read it when deciding how much context a message needs.

---

# Part 2 · Match the receiving repository

Read [repository style evidence](references/repository-style.md) before drafting.
Identify the receiving repository, then resolve each style dimension independently:
explicit rules first, comparable history second, and a plain imperative fallback
when neither supplies a stable signal. A rule about prefixes does not settle body
depth or physical wrapping.

Form an evidence-backed profile covering subject syntax, body threshold and order,
paragraph/list layout, hard wrapping, references and required trailers. Inspect the
actual stored lines. Follow documented rules when history disagrees, and report
uncertainty rather than inventing a convention.

---

# Part 3 · Execute and verify within the chosen boundary

**Attribution is the user's call, and the default is none.** Do not append a
`Co-Authored-By` trailer for yourself by default. An explicit user request can
set attribution; do not infer it from agent participation. When another human
wrote part of the change, establish their attribution with the user rather than
guessing their identity or adding a trailer automatically.

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
