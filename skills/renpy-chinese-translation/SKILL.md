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
  (`GoogleTranslator`) and network access to Google Translate; use the existing
  interpreter or environment that provides it. No particular environment name is required.
- `translation_guard.py` can additionally run Ren'Py's own parser check when an
  SDK is available; point `RENPY_SDK` at that SDK directory.
- Writing translated slots in `.rpy` files is the only write this skill
  performs. The guard, the review-batch export, and
  `translation_replace.py --dry-run` are read-only.

## Choose the mode and tool directory

A review request uses the guard and batch export read-only. A translation or
revision request permits edits to translated slots; it does not by itself authorize
Git commits or history rewrites. Skip machine translation when the user requests
review, when slots are already translated, or when no external service is authorized.

Run from the Ren'Py project root. Set `TOOLS` to the existing project-local
`scripts/translation/` directory, or to this skill's installed `scripts/` directory.
Do not copy helpers into the target repository merely to run them. For paths under
`game/tl/`, pass `--root game`; other layouts need their actual source root.
Confirm the target exists and that the guard checked at least one file.

Read [project terminology](references/term-table.md) before applying term fixes.
The bundled term table and `fix_terms.py` patterns are a project-specific baseline,
not a universal glossary for every game. Prefer the target project's glossary and
validated local fixer. If the bundled mappings do not fit, review terms in context
and apply slot-safe replacements instead of forcing those mappings.

## Translation and revision workflow

1. Preflight the target file:

   ```bash
   python3 "$TOOLS/translation_guard.py" <filepath> --root game --max-examples 20
   ```

   Resolve structural errors first: comment mismatches, `old_changed`, bad dialogue syntax, suffix/tag/interpolation mismatches. Untranslated English is expected before initial translation.

2. If an initial machine pass is needed and authorized, use an interpreter with
   `deep-translator`. This sends dialogue text to Google Translate; private or
   unreleased game content requires the user's authorization for that service.

   ```bash
   python3 "$TOOLS/translate_rpy.py" <filepath>
   ```

   Otherwise prepare slot translations offline and continue slot review.

3. Apply deterministic terms only when the selected fixer matches the project glossary:

   ```bash
   python3 "$TOOLS/fix_terms.py" <filepath>
   ```

4. Run the gate again:

   ```bash
   python3 "$TOOLS/translation_guard.py" <filepath> --root game --max-examples 20
   ```

5. Do LLM slot-by-slot review. Do not rely on free-form whole-file browsing. Export bounded batches:

   ```bash
   python3 "$TOOLS/translation_review_batch.py" <filepath> --offset 0 --limit 80
   ```

   Review every slot in order. For each slot, produce `PASS` or an exact replacement for translated text only. Do not change comments, `old`, speaker, suffix, tags, or interpolation. Process flagged slots first with `--issues-only`, then review all slots in batches of about 50-100.

   If a deterministic pattern misses a stable correction or damages valid text,
   update the project-local fixer when helper maintenance is in scope and rerun
   its tests and the guard. Otherwise apply a slot-safe fix for this task and
   propose helper maintenance separately; do not edit an installed skill copy.

   Check:

   - Term table violations: see `references/term-table.md`.
   - Project names and stable mistranslations established by the selected glossary.
   - Ambiguous words like `灰色`, `本质`, and `审判` require source-context review rather than blind replacement.
   - Character voice, idioms, sexual/violent wording, raw English leftovers, smart quotes, escaped quotes, placeholders, zero-width spaces, and unnatural Chinese phrasing.

6. Apply batch fixes through slot-safe replacement:

   ```bash
   python3 "$TOOLS/translation_replace.py" fixes.json <filepath> --dry-run
   python3 "$TOOLS/translation_replace.py" fixes.json <filepath>
   python3 "$TOOLS/translation_guard.py" <filepath> --root game --max-examples 20
   ```

7. Final verification:

   ```bash
   python3 "$TOOLS/translation_guard.py" <filepath> --root game --warnings-as-errors
   "$RENPY_SDK/renpy.sh" . translate schinese --count
   ```

8. Inspect the final diff and report the files changed, slot-review coverage, guard
   outcome, and whether SDK/runtime checks ran. Follow [final verification](references/verify.md).
   Commit only if requested, using the receiving repository's convention. Amend
   history only when the user identifies and authorizes that target; reviewing a
   file a second time is not permission to rewrite its earlier commit.

## Runtime Feedback

Manual single-person line review is not the primary quality gate. Use an authorized machine service for an initial pass when needed, LLM slot review for textual quality, guard/Ren'Py parsing for structural safety, and packaged runtime testing for later context/UI/pacing feedback patches.
