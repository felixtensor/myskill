# Final Verification

Use the project-local guard when available:

```bash
python3 scripts/translation/translation_guard.py <filepath> --warnings-as-errors
```

For a whole chapter directory:

```bash
python3 scripts/translation/translation_guard.py tl/schinese/chapter_2 --warnings-as-errors
```

Then verify Ren'Py can parse the translation tree:

```bash
"$RENPY_SDK/renpy.sh" . translate schinese --count
```

Acceptable final state for the file being committed:

- `comment_mismatch`: 0
- `old_changed`: 0
- `bad_dialogue_syntax`: 0
- `suffix_changed`: 0
- `tag_mismatch`: 0
- `interpolation_mismatch`: 0
- untranslated English: 0, unless manually justified for a proper noun or UI token

If the guard reports structural errors, fix those before polishing translation quality.
