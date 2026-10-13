#!/usr/bin/env python3
"""
Ren'Py translation script: translates untranslated English dialogue/narration
in .rpy translation files to Chinese using deep-translator (Google Translate backend).

Usage: python translate_rpy.py <path_to_rpy_file> [more_files...]
Output: overwrites the file with translations applied.

Preserves: voice directives, {i}...{/i}, {font=...}...{/font}, character prefixes,
nointeract tags, comment lines, and all other Ren'Py markup.
"""

import re
import sys
import time
from deep_translator import GoogleTranslator

# Lines that should NOT be translated (returned as-is)
SKIP_PATTERNS = [
    re.compile(r'^\s*voice\s+"', re.IGNORECASE),
    re.compile(r'^\s*old\s+"', re.IGNORECASE),  # NEVER translate old (reference) lines
    re.compile(r'^\s*translate\s+', re.IGNORECASE),
    re.compile(r'^\s*#'),
    re.compile(r'^\s*$'),
]

# Lines that are just punctuation/ellipsis - no translation needed
PUNCTUATION_ONLY = re.compile(
    r'^[""](\.{2,3}|…|!|\?|\.|,|;|:|\s|-)*[""]$'
)

# Match a quoted string line: optional_char_prefix "text" optional_nointeract optional_with
QUOTED_LINE = re.compile(
    r'^(\s*)([a-zA-Z_]\w*\s+)?("(?:[^"\\]|\\.)*")(\s+nointeract)?((?:\s+with\s+\w+)*)(\s*)$'
)

# Ren'Py markup tags and interpolation placeholders must survive translation.
PROTECTED_PATTERN = re.compile(r'(\{[^}]*\}|\[[^\]]+\])')
HAS_CHINESE = re.compile(r'[\u3400-\u9fff]')
HAS_ENGLISH = re.compile(r'[A-Za-z]{2,}')


def extract_text_and_prefix(line):
    """Parse a translation line. Returns (char_prefix, inner_text, suffix, indent, with_clause)
    or (None, None, None, None, None) for non-translatable lines."""
    stripped = line.strip()
    if not stripped:
        return None, None, None, None, None

    for pat in SKIP_PATTERNS:
        if pat.match(line):
            return None, None, None, None, None

    m = QUOTED_LINE.match(line)
    if not m:
        return None, None, None, None, None

    indent = m.group(1) or ''
    char_prefix = m.group(2) or ''
    quoted_text = m.group(3)
    suffix = m.group(4) or ''
    with_clause = m.group(5) or ''

    inner_text = quoted_text[1:-1]  # strip outer quotes

    if PUNCTUATION_ONLY.match(quoted_text):
        return None, None, None, None, None
    if HAS_CHINESE.search(inner_text):
        return None, None, None, None, None
    if not HAS_ENGLISH.search(inner_text):
        return None, None, None, None, None

    return char_prefix.strip(), inner_text, suffix.strip(), indent, with_clause.strip()


def translate_text(text):
    """Translate while preserving Ren'Py tags/interpolation by using placeholders."""
    if not text or not text.strip():
        return text

    protected = []
    placeholder_map = {}

    def replace_protected(m):
        idx = len(protected)
        placeholder = f'ZXQ{idx}QXZ'
        protected.append(m.group(0))
        placeholder_map[placeholder] = m.group(0)
        return placeholder

    clean = PROTECTED_PATTERN.sub(replace_protected, text)

    if not protected:
        try:
            translated = GoogleTranslator(source='en', target='zh-CN').translate(clean)
            return translated if translated else text
        except Exception as e:
            print(f"  Translation error: {e}", file=sys.stderr)
            time.sleep(2)
            return text

    try:
        translated = GoogleTranslator(source='en', target='zh-CN').translate(clean)

        if not translated:
            return text

        missing = [placeholder for placeholder in placeholder_map if placeholder not in translated]
        if missing:
            print(
                f"  Protected token lost, keeping original: {text[:80]}...",
                file=sys.stderr,
            )
            return text

        for placeholder, tag in placeholder_map.items():
            translated = translated.replace(placeholder, tag)

        return translated
    except Exception as e:
        print(f"  Translation error: {e}", file=sys.stderr)
        time.sleep(2)
        return text


def process_line(line):
    """Process one line: translate if needed, otherwise return as-is."""
    char_prefix, inner_text, suffix, indent, with_clause = extract_text_and_prefix(line)

    if char_prefix is None:
        return line

    translated_text = translate_text(inner_text)

    if char_prefix:
        result = f'{indent}{char_prefix} "{translated_text}"'
    else:
        result = f'{indent}"{translated_text}"'

    if suffix:
        result += f' {suffix}'
    if with_clause:
        result += f' {with_clause}'

    return result + '\n'


def process_file(filepath):
    """Translate all dialogue/narration in a .rpy file."""
    print(f"Processing: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    translated_count = 0
    output_lines = []

    for i, line in enumerate(lines):
        new_line = process_line(line)

        if new_line != line:
            translated_count += 1
            if translated_count % 100 == 0:
                print(f"  Translated {translated_count} lines so far...")
            # Small delay every 10 translations to avoid rate limiting
            if translated_count % 10 == 0:
                time.sleep(0.3)

        output_lines.append(new_line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    print(f"  Done! Translated: {translated_count} lines")
    return translated_count


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_rpy_file> [more_files...]")
        sys.exit(1)

    total = 0
    for filepath in sys.argv[1:]:
        total += process_file(filepath)

    print(f"\nTotal lines translated across all files: {total}")


if __name__ == '__main__':
    main()
