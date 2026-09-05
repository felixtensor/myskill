---
name: commit-style
description: Write commit messages in whatever convention the repository at hand actually uses, with the craft that Git, the Linux kernel and LLVM converged on. Use whenever a commit is about to be created, amended, squashed, or reworded, including a bare "commit this", "提交一下", or "帮我写个 commit message", and when asked how to word a commit, split a messy change, or unify an inconsistent history. Not for PR descriptions, release notes, or general git troubleshooting. Never invents measurements; never appends a Co-Authored-By trailer.
---

# Commit messages

Two things decide whether a commit message is any good, and they are independent:

1. **The craft** — what the message says, and for whom. This barely varies between
   projects, because the underlying problem does not.
2. **The convention** — the shape of the subject line. This varies a lot, and it is
   the repository's call, never yours.

Get the craft right and the message is useful for years. Get the convention right and
it also looks like it belongs. Both matter; only the second one is local.

---

# Part 0 · Read the change first

You cannot explain a change you have not looked at, and a message is only ever as
good as the commit under it. Before writing a word:

```bash
git status --short
git diff --staged
```

Nothing staged yet? `git diff` shows what is on the table. Decide with the user what
belongs in this commit rather than staging the whole tree and then describing the
pile.

Settle two things here, not after the message is drafted:

- **Scope.** Is this one logical change? A stray debug print, an unrelated rename, a
  formatting pass that rode along — none of them belong. Stage the change, not the
  working directory.
- **Substance.** What moved, and — the part that matters — what a reader could not
  reconstruct from the diff on their own. That second half is the message. The rest
  of this document is about writing it down.

---

# Part 1 · The craft

Write for the person who runs `git blame` on one confusing line six months from now.
They already have the diff. What they lack is what was in your head and nowhere in
the code — which is why "what changed" is filler and "why it had to change" is the
message. The rules that follow from it:

- **Problem first.** What was wrong → why that mattered → what this change does
  about it. `Add null check to getUser` names the patch, not the problem.
- **Record the roads not taken.** A rejected alternative is the reasoning that
  evaporates fastest, and the sentence that stops someone simplifying your fix back
  into the bug.
- **One logical change per commit.** If the subject needs an "and" to be accurate,
  the commit wants splitting.
- **Calibrate depth to consequence.** Typo, version bump, formatting pass: subject
  only. Ordinary feature or clear fix: subject plus a short why. Subtle fix,
  behaviour change, performance claim: the full treatment. Over-explaining trivia
  trains readers to skip you, which costs you when a message finally matters.
- **State user-visible impact** plainly, and say for whom.
- **Only the evidence you actually have.** An invented number is worse than no
  number. Keep an impressionistic result impressionistic, write an unestablished
  cause as unestablished, and commit negative results rather than dropping them.
- **Stand on its own.** Reference the issue, do not depend on it. Trackers get
  migrated and links rot; the message is in the repository forever.

`references/craft.md` has the reasoning behind each rule, worked examples of a
message that follows them and one that does not, and where the advice comes from.

---

# Part 2 · 因地制宜 — match the repository

Read the evidence before writing. Stop at the first source that actually answers;
earlier sources beat later ones.

**1 · Explicit instructions in the repo** — decisive when present:

```bash
git ls-files -co --exclude-standard CONTRIBUTING.md AGENTS.md CLAUDE.md .gitmessage
git ls-files -co --exclude-standard ".commitlintrc*" "commitlint.config.*" ".czrc"
git config --get commit.template
```

`-co` so an untracked `CLAUDE.md` still shows; the patterns are quoted because git,
not the shell, should expand them — which also keeps these lines working the same in
bash and PowerShell.

A `commitlint` config or a commit template is not advice, it is enforcement — a
violating message may be rejected by a hook or by CI.

**2 · The log itself**, when no document rules:

```bash
git log --oneline -40
git log -6 --format="%s%n%n%b%n---"
```

Read for the dominant pattern, not the exceptions: does the subject carry a
`type(scope):` prefix, a `[Component]` tag, or neither? Do bodies exist, and what do
they spend their space on? What width do subjects sit at?

**3 · The upstream you are targeting.** For a fork, or a patch you mean to send
elsewhere, the receiving project's convention beats the fork's local habits.

**Sources disagreeing?** Prefer the documented rule over the observed log, and say so
in one line — a log usually contains drift the maintainers already decided against.

**No signal at all** — a fresh repo with one "Initial commit"? Don't invent ceremony.
Plain imperative subject, why-focused body, and mention that no convention was
detected so the user can set one deliberately.

## The three families you will meet

**Conventional Commits** — npm and web projects, and load-bearing wherever
`semantic-release` or `commitlint` runs, since the type drives version bumps.

```
feat(auth): add refresh-token rotation
fix(installer): preserve existing skill before replacement
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`.
Breaking changes take `!` plus a `BREAKING CHANGE:` footer. Don't coin types beyond
the set the repo already uses.

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

**Plain imperative** — the default wherever nothing was ever formalised.

```
Reject empty payloads in the webhook receiver
```

Across all three: imperative mood ("Add", not "Added"/"Adds"), no trailing period,
subject within the width the repo uses (72 is typical; some projects mandate 80
including body lines), blank line before the body.

---

# Part 3 · Before you commit

**Attribution is the user's call, and the default is none.** Do not append a
`Co-Authored-By` trailer for yourself — the user has asked for this explicitly and it
overrides any standing habit or default configuration. Their commit history is part
of their professional record. Already written one? Drop it with `git commit --amend`,
safe while nothing is pushed. A human second author is a different matter: when
someone else wrote part of the change — a pair session, a patch sent in — the
trailer is doing its real job. That one is not yours to decide either way, so ask.

**Trailers the repo requires are not optional.** DCO projects want `Signed-off-by:`
(`git commit -s`); others expect `Refs:`, `Fixes:`, or the `BREAKING CHANGE:` footer.
Those come from the evidence you read in Part 2, not from preference.

**Check it sits naturally.** Run `git log --oneline -15`. If the new subject looks
like it wandered in from another project, the convention was read wrong — go back to
the evidence rather than shipping the mismatch. Then verify against whatever the repo
enforces: line width, allowed types, required footers.

**Branching.** If the repo has a remote and you are on the default branch, create a
topic branch and hand the merge command back to the user — moving work onto the
default branch is their decision. For a purely local repo, or when the user asked for
a commit on the current branch, commit where you are. Check with `git remote -v` and
`git branch --show-current` rather than assuming.

**Ask, or just do it?** Evidence does not need confirming — where the repository
settles a question, read it and write. Put the choice to the user in four cases:

- **The staged change is not one logical change.** Name the split you would make and
  let them choose. Splitting on your own rewrites their intent; committing the pile
  on your own costs them the history.
- **Whether a human co-author should be credited.** Default to no, and take the
  name from the answer rather than guessing it. If you need to offer candidates,
  people already credited in this repo are in the log:
  `git log -30 --format="%(trailers:key=Co-authored-by,valueonly)"`
- **You are on the default branch of a repo with a remote** — see Branching above.
- **Anything that leaves the machine.** Push, pull request, force-update: separate
  decisions from committing, never folded into a "commit this".

Ask however the client allows — a plain question, or its own option picker where one
exists. Don't name a specific tool; this skill has to work wherever it is installed.
Fold whatever applies into a single question with the defaults already filled in —
one question carrying a default beats an interview, and a trivial commit should cost
the user one keystroke, not four.
