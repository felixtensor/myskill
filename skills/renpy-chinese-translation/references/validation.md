# Validation Cases

Walk these cases on a throwaway copy of a Ren'Py project before changing this skill. Never
validate against a user's working tree, and never commit game content into this repository.
Cases 1-6 were walked on 2026-10-13 against the copy imported from the local cc-switch store.
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
python3 scripts/translation_guard.py game/tl/schinese/script.rpy --root game
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
- **`fix_terms.py`** → rewrites translated slots only; comments and `old` lines keep their text
  even when they contain a known mistranslation.
- **Known defect in the imported copy (2026-10-13).** When several `TERM_FIXES` patterns match
  the same line, only the last matching pattern is persisted and the printed count also counts
  the discarded matches. A line containing Haelo/Elie/Guardians/escort mistakes needed four runs
  to converge (`陪侍` → `守护者` → `艾利` → `海洛`). Re-run until the report says 0 fixes and
  re-check with the guard, or fix the loop before trusting a single pass.

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
