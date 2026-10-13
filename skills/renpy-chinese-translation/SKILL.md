---
name: renpy-chinese-translation
description: Use when translating or reviewing Ren'Py .rpy translation files from English to Chinese, especially schinese tl files with dialogue blocks, old/new string tables, terminology consistency requirements, or risk of corrupting Ren'Py-generated reference comments.
---

# Ren'Py Chinese Translation Workflow

## Core Rule

Only translated text slots may change. Reference/control material must remain byte-for-byte safe:

- `# ...` reference comments must match the source line from `game/...`.
- `old "..."` string keys must remain the original English.
- `voice ...`, speaker prefixes, `nointeract`, `with ...`, `{...}` tags, and `[...]` interpolation must be preserved.
- Batch fixes must operate on parsed translated slots, never by blind whole-file replacement.

## Tooling

Prefer project-local tools from `scripts/translation/` when present. Otherwise use this skill's bundled `scripts/` copies.

- `translation_guard.py`: read-only gate for comments, `old`, block shape, suffixes, tags, interpolation, English leftovers, and known term mistakes.
- `translate_rpy.py`: GoogleTranslator initial pass for untranslated English dialogue slots.
- `fix_terms.py`: deterministic terminology and stable mistranslation normalization.
- `translation_review_batch.py`: exports bounded source/translation slot batches for LLM review.
- `translation_replace.py`: applies JSON literal/regex replacements only inside translated text slots.
- `retry_translate.py`: retries untouched English-only slots.

## Requirements

- Python 3.10 or newer. Every helper uses the standard library only, except
  the two machine-translation scripts.
- `translate_rpy.py` and `retry_translate.py` need `deep-translator`
  (`GoogleTranslator`) and network access to Google Translate; run them with an
  interpreter that provides it, for example `conda run -n translator`.
- `translation_guard.py` can additionally run Ren'Py's own parser check when an
  SDK is available; point `RENPY_SDK` at that SDK directory.
- Writing translated slots in `.rpy` files is the only write this skill
  performs. The guard, the review-batch export, and
  `translation_replace.py --dry-run` are read-only.

## Required Workflow

1. Preflight the target file:

   ```bash
   python3 scripts/translation/translation_guard.py <filepath> --max-examples 20
   ```

   Resolve structural errors first: comment mismatches, `old_changed`, bad dialogue syntax, suffix/tag/interpolation mismatches. Untranslated English is expected before initial translation.

2. Machine translate:

   ```bash
   conda run -n translator python3 scripts/translation/translate_rpy.py <filepath>
   ```

3. Apply deterministic terms:

   ```bash
   python3 scripts/translation/fix_terms.py <filepath>
   ```

4. Run the gate again:

   ```bash
   python3 scripts/translation/translation_guard.py <filepath> --max-examples 20
   ```

5. Do LLM slot-by-slot review. Do not rely on free-form whole-file browsing. Export bounded batches:

   ```bash
   python3 scripts/translation/translation_review_batch.py <filepath> --offset 0 --limit 80
   ```

   Review every slot in order. For each slot, produce `PASS` or an exact replacement for translated text only. Do not change comments, `old`, speaker, suffix, tags, or interpolation. Process flagged slots first with `--issues-only`, then review all slots in batches of about 50-100.

   If review finds a term/name/stable mistranslation that `fix_terms.py` failed to cover and it is safe to normalize automatically, add or narrow the relevant `fix_terms.py` pattern in the same fix. If an existing pattern over-replaces and damages a valid translation, update that pattern and rerun the guard on the target file before committing.

   Check:

   - Term table violations: see `references/term-table.md`.
   - Names: `Haelo` 海洛, `Horne` 霍恩, `Grey` 格雷, `Elie` 艾利, `Gerrard` 杰拉德.
   - Stable Chinese mistranslations: `埃利`, `哈罗/哈喽`, `格瑞`, `枢纽状态`, `监护人`, `伴游/陪护` must be normalized.
   - Ambiguous words like `灰色`, `本质`, and `审判` require source-context review rather than blind replacement.
   - Character voice, idioms, sexual/violent wording, raw English leftovers, smart quotes, escaped quotes, placeholders, zero-width spaces, and unnatural Chinese phrasing.

6. Apply batch fixes through slot-safe replacement:

   ```bash
   python3 scripts/translation/translation_replace.py fixes.json <filepath> --dry-run
   python3 scripts/translation/translation_replace.py fixes.json <filepath>
   python3 scripts/translation/translation_guard.py <filepath> --max-examples 20
   ```

7. Final verification:

   ```bash
   python3 scripts/translation/translation_guard.py <filepath> --warnings-as-errors
   "$RENPY_SDK/renpy.sh" . translate schinese --count
   ```

8. Commit focused files only:

   ```bash
   git add <filepath>
   git commit -m "Translate <path> to Chinese"
   ```

   For one dialogue file, keep the translation task in one commit when practical. If a second review finds missed issues and that file's translation commit is still `HEAD`, amend the fix into that commit after checking `git show --stat --oneline HEAD`. If work has moved on and `HEAD` belongs to another file/task, make a separate patch commit for the earlier file. Do not amend fixes for one file into another file's translation commit.

## Runtime Feedback

Manual single-person line review is not the primary quality gate. Use GoogleTranslator for initial translation, LLM slot review for textual quality, guard/Ren'Py parsing for structural safety, and packaged runtime testing for later context/UI/pacing feedback patches.
