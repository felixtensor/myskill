# The craft, at length

`SKILL.md` carries these rules in summary; this file is the reasoning and the worked
examples behind them. Read it when a change has earned a body and you are not sure
what belongs in one.

Distilled from the projects that take this seriously — Git's own `SubmittingPatches`,
the Linux kernel's submission docs, LLVM, PostgreSQL — which converged on
substantially the same advice from very different codebases.

## Write for the archaeologist

The reader you are writing for is not reviewing your PR today. It is someone six
months from now who ran `git blame` on one confusing line and is trying to work out
why it exists. That person **already has the diff**. What they lack is everything
that was in your head and nowhere in the code.

This single reframe decides most of what follows. It is why "what changed" is filler
and "why it had to change" is the message.

## Problem first, then the fix

When the repository does not establish another order, a strong default is:

> What was wrong → why that mattered → what this change does about it.

Not `Add null check to getUser`. That names the patch, not the problem.

```
Take the user id explicitly in getUser

getUser read the id off the ambient session, which held until anonymous
checkout shipped. Anonymous carts have no session user, so the lookup
now takes the null branch and 500s on a page every visitor can reach.

Pass the id in, so the caller decides what identity means in its own
context rather than inheriting whatever the session happened to hold.
```

Note what the body does not do: it never says "changed the signature and updated
three call sites." The diff says that.

## Record the roads not taken

The highest-value sentence in many good commits can be the one explaining a rejected
alternative — when that alternative was actually considered and the reasoning would
otherwise evaporate.

> A null guard inside getUser would have been smaller, but it hides the same
> confusion at the other two call sites instead of resolving it.

Six months later this is what stops someone from "simplifying" your fix back into
the bug.

## One logical change per commit

The message can only be as clear as the commit. A useful heuristic: if the subject
needs an "and" to be accurate, the commit probably wants splitting. Unrelated
cleanups riding along make the real change harder to find, revert, and bisect.

## Calibrate depth to consequence

Good practice is not "always write three paragraphs" — it is spending words in
proportion to what a future reader will need.

- A typo fix, a version bump, a formatting pass: **subject only.** A body here is noise.
- An ordinary feature or a clear bug fix: **subject plus a short why.**
- A subtle fix, a behaviour change, a performance claim, anything surprising:
  **the full treatment** — problem, reasoning, alternatives, boundaries.

Over-explaining a trivial change trains readers to skip your messages, which costs
you exactly when a message finally matters.

## State user-visible impact

If behaviour changes, say so plainly, and say for whom. Anyone triaging a regression
or writing release notes is scanning for exactly this.

## Evidence: only what you actually have

Cite figures that were measured, with enough context to read them — configuration,
sample size, spread. If the effect was described impressionistically ("感觉快了不少"),
keep it impressionistic. **An invented number is worse than no number**, because it
reads as authoritative and nobody re-derives it.

Same for mechanism: if you know *that* something happened but not *why*, write that
the cause is not established rather than supplying a plausible-sounding explanation.

Negative and inconclusive results are worth committing. A recorded wrong prediction
is evidence of method; quietly dropping it is how a log stops being trustworthy.

## Stand on its own

Reference the issue or discussion, but do not depend on it. Trackers get migrated and
links rot; the commit message is in the repository forever. A reader with no network
access should still understand the change.
