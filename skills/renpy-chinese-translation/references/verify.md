# Final Verification

Run from the project root with `TOOLS` and `TERM_PROFILE` selected as in `SKILL.md`.
Use the actual source root; these examples use `game/`:

```bash
python3 "$TOOLS/translation_guard.py" <filepath> --root game --term-profile "$TERM_PROFILE" --warnings-as-errors
```

For a whole chapter directory:

```bash
python3 "$TOOLS/translation_guard.py" game/tl/schinese/chapter_2 --root game --term-profile "$TERM_PROFILE" --warnings-as-errors
```

Then verify Ren'Py can parse the translation tree:

```bash
"$RENPY_SDK/renpy.sh" . translate schinese --count
```

Acceptable final state for a completed translation:

- `comment_mismatch`: 0
- `old_changed`: 0
- `bad_dialogue_syntax`: 0
- `suffix_changed`: 0
- `tag_mismatch`: 0
- `interpolation_mismatch`: 0
- untranslated English: 0, unless manually justified for a proper noun or UI token
- every slot reviewed against the selected project glossary; `generic` does not
  automate that glossary check and is not a waiver of terminology review

If the guard reports structural errors, fix those before polishing translation quality.
