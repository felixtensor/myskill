# Validation Cases

Walk these cases on a throwaway copy of a Ren'Py project before changing this skill. Never
validate against a user's working tree, and never commit game content into this repository.
An earlier walkthrough covered cases 1-6; its local import source is omitted for privacy.
The Ren'Py parser check could not be walked there because no SDK was installed.

## Harness

```text
project/
├── game/
│   ├── script.rpy                    # English source
│   └── tl/schinese/script.rpy        # translation under test
```

`translation_guard.py` resolves `# game/<path>:<line>` anchors against `--root`, and resolves
its file arguments against the current directory. Run it from the project root and pass the
`game/` directory as root:

```bash
python3 "$TOOLS/translation_guard.py" game/tl/schinese/script.rpy --root game
```

Passing `--root .` while the file lives under `game/tl/...` reports `ERROR missing_source` for
every anchor; that is a wrong invocation, not a broken translation.

## 1 · Structural safety

- **Clean file** → `Translation guard checked 1 file(s). Errors: 0  Warnings: 0`, exit 0.
- **Reference comment translated** → `ERROR comment_chinese` and `ERROR comment_mismatch`, exit 1.
- **Text tag dropped** (`{b}Come with me.{/b}` → bare text) → `ERROR tag_mismatch`, exit 1.
- **Interpolation dropped** (`[name]` missing) → `ERROR interpolation_mismatch`, exit 1.
- **`old` key translated** (Chinese inside `old "..."`) → `ERROR old_changed`, exit 1.
- **`new` left identical to `old`** → `ERROR untranslated_string`.
- **English left in a translated slot** → `ERROR english_left`, exit 1. Untranslated English is
  expected mid-workflow, but it is never an acceptable final state.
- **`--warnings-as-errors`** → a term warning (`haelo_wrong`, `elie_wrong`, `guardian_wrong`, …)
  also exits 1.

## 2 · Slot-safe writes

- **`translation_replace.py fixes.json <file> --dry-run`** → reports the replacement count and
  leaves the file byte-identical.
- **Apply the same batch** → only quoted translated slots change; reference comments, `old`
  keys, speaker prefixes, suffixes, tags and interpolation are untouched, and the guard returns
  to 0 errors.
- **`fix_terms.py`** → rewrites translated slots only; comments, `old` keys, `voice` lines and
  `translate` headers keep their text even when they contain a known mistranslation. Every
  matching `TERM_FIXES` pattern applies to the evolving line in one pass, the reported count
  matches the applied replacements, and a second run reports 0 fixes.
  `scripts/test_fix_terms.py` pins that behaviour and control-line immunity.

## 3 · Review batches

- **`translation_review_batch.py <file> --limit 80`** → ordered slots with file, line, kind,
  speaker, suffix, flags, original and current translation; read-only.
- **`--issues-only` / `--format jsonl`** → only flagged slots, as one JSON object per line.
- **`--offset`** → continues through the same ordering without skipping or repeating a slot.
- **Reviewing every slot** → each slot is either `PASS` or an exact replacement for the
  translated text only; comments, `old`, speaker, suffix, tags and interpolation stay fixed.

## 4 · Missing input and unavailable environment

- **Path does not exist** → `warning: path not found: ...` and `Translation guard checked 0
  file(s)` with exit 0. Do not read that as a pass; confirm the path before trusting the result.
- **Project-local `scripts/translation/` absent** → use this skill's bundled `scripts/` copies.
- **`deep-translator` missing or no network** → `translate_rpy.py` and `retry_translate.py`
  fail on import or request. The guard, the batch export, `fix_terms.py` and
  `translation_replace.py` still work offline. Do not report a machine-translation pass.
- **No Ren'Py SDK** → skip `translate <language> --count` and state plainly that parser
  verification was not run; a clean guard result is not a parser check.

## 5 · Adjacent requests (should not trigger)

- "把这份字幕或 JSON 翻成中文" — not Ren'Py `.rpy` translation slots.
- "帮我润色这段中文" with no `tl/<language>` tree — no translation-file contract to protect.
- Ren'Py programming, customization, or build errors — unrelated to translation slots.
- Boundary, **should** trigger but stay read-only: "review 一下这个 tl 文件" (guard and batch
  export only).

## 6 · Repeat runs and privacy

- **Re-running an applied batch** → `0 replacement(s)`; no duplicate edits.
- **Re-running the guard or the batch export** → no file changes.
- **Repository hygiene** → no credentials, no game content, no absolute home paths; only
  `RENPY_SDK` is referenced, as a runtime environment variable.

## Maintenance review

- **Review only** → inspect/export slots; do not translate, apply fixes or commit.
- **Different game glossary** → use its terms; do not run the bundled fixer unless
  its mappings fit. Select `--term-profile generic` on the bundled guard, keep
  `--warnings-as-errors`, and review every slot against the approved glossary.
  A clean generic result does not certify that glossary. A project-local guard
  must support the selected glossary; inspect its help before adapting commands.
  Skill-source maintenance is a separate scope from game edits.
- **Default baseline** → the approved baseline passes; replacing `羁绊状态` with
  `枢纽状态` still produces `nexus_wrong` and fails strict final verification.
- **Generic profile** → that same text passes when `枢纽状态` is approved by the
  other game's glossary. Tag/interpolation/comment/old/speaker/suffix/voice/block
  corruption still fails. English leftovers, ASCII punctuation and zero-width
  text still fail with `--warnings-as-errors`. Every guard invocation is read-only.
  `scripts/test_translation_guard.py` exercises these outcomes through the CLI.
- **Private dialogue and no external-service authorization** → keep translation
  offline; do not send it to the machine service just because the helper exists.
- **Translation requested, no commit requested** → return verified file edits;
  a second review does not authorize amending an earlier commit.

The entrypoint and references were walked before and after this maintenance change
against the structural, mode, path, unavailable-tool and privacy cases. This checks
instruction consistency only; no machine service, SDK or game runtime was exercised.

A temporary synthetic project also exercised the documented `--root game` command,
one-slot JSONL export, replacement dry-run, slot-only write and no-op second write.
The wrong `--root .` invocation produced `missing_source` as expected. This was an
offline helper smoke check; it does not validate Ren'Py parsing or translation quality.

An independent offline walkthrough then exported/reviewed three slots and applied
a slot-safe replacement batch using another approved glossary. It exposed the
baseline-only guard rejecting that glossary; the profile cases above cover the
correction. Review/dry-run preserved bytes, a repeat write made no replacements,
and 15 injected structural/text errors were rejected after correction. A simulated
project-local older guard without the profile flag was replaced by the bundled
guard according to the documented fallback. No external service, SDK,
game runtime or automatic skill-selection evaluation ran.
