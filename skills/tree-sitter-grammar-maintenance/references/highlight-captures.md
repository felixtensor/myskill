# Highlight captures

**This file deliberately does not reproduce the standard capture list.** A copied
list is correct on the day it is written and quietly wrong afterwards: the set grows
between tree-sitter releases, and a reader who trusts the copy will "fix" a query to
match a vocabulary that has moved on. Derive the list from the toolchain you are
actually running, and link to the source rather than transcribing it.

That principle applies beyond this file — see the note at the end.

## The authority is executable

```bash
npx tree-sitter highlight --check FIXTURE
```

`--check` compares every capture in the shipped queries against the standard set
**compiled into the CLI you are running**, so it cannot drift from your toolchain.
It prints, for example:

```
Warning: Non-standard highlight captures detected:
* totally.bogus.capture
```

Read the output against the project's own documentation before acting on it. A
warning means "not in the standard set", not "wrong": a grammar may deliberately use
a non-standard capture where the standard vocabulary has no good fit, and
`tree-sitter-mlir` does exactly that for `@variable.special` (SSA values) and
`@label` (block labels), recorded in `docs/QUERIES.md`. Those two warnings are
expected. A *new* name in that output is the signal.

Captures whose name starts with `_` are treated as private and are not reported.

## Where the list actually lives

Pin the URL to the version you are running rather than to whatever is current:

```bash
npx tree-sitter --version        # -> tree-sitter 0.27.0
```

- `STANDARD_CAPTURE_NAMES`, the set `--check` enforces:
  <https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/crates/highlight/src/highlight.rs>
- The default CLI theme, which decides what each capture looks like in
  `tree-sitter highlight`:
  <https://github.com/tree-sitter/tree-sitter/blob/v0.27.0/crates/cli/src/highlight.rs>
- Query-file roles — highlights, locals, injections:
  <https://tree-sitter.github.io/tree-sitter/3-syntax-highlighting.html>

Swap `v0.27.0` for your version. Reading the source for five seconds beats trusting
a table someone transcribed at an unknown version.

## What does not age, and is worth knowing

**Two captures can share a theme channel.** The default CLI theme maps several
distinct captures onto the same colour and weight, so a query change that is a
genuine semantic improvement can be *invisible* in the terminal, and conversely a
distinction that looks fine in the query file may not reach the reader.

Observed at v0.26.10: `@constant.builtin` and `@number` were both bold brown, and
`@constructor.builtin` had no style of its own and fell back to `@constructor`.
Those specific pairs may have changed since — that is the point of this file, so
check rather than quote them. The theme is one `match` block in
`crates/cli/src/highlight.rs`, linked above; read it at your version.

The consequence for this skill: **do not claim a highlighting improvement on the
strength of the query diff alone.** Render the fixture and look, or say plainly that
the change is semantic and that its visible effect depends on the consumer's theme.
The CLI theme is one consumer among many, and editors ship their own.

**Fixtures assert capture names, not colours.** `test/highlight/**` pins which
capture lands on which source position. That is the right contract to test — it is
what a downstream theme binds to — but it means a fixture can pass while the
rendered result is unreadable, and it means a fixture cannot tell you whether a
capture is the *semantically* right choice. That judgement belongs in
`docs/QUERIES.md`, next to the reasoning.

## The general rule

Prefer a link and a derivation command over a transcribed fact, for anything owned
upstream: capture vocabularies, CLI flags, default themes, ABI versions, node names
belonging to another project. Transcribe only what you cannot derive, and when you
must, record the version it was true at and the command that re-derives it — as the
verification table in `references/mlir.md` does.

A reference that says "go look, here" stays correct. A reference that says "here is
the answer" starts decaying the moment it is written, and its decay is silent.
