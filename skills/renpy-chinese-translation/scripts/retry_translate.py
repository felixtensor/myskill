#!/usr/bin/env python3
"""Retry translation for lines that still contain English text."""
import re
import sys
import time
from deep_translator import GoogleTranslator

PROTECTED_PATTERN = re.compile(r'(\{[^}]*\}|\[[^\]]+\])')

QUOTED_LINE = re.compile(
    r'^(\s*)([a-zA-Z_]\w*\s+)?("(?:[^"\\]|\\.)*")(\s+nointeract)?((?:\s+with\s+\w+)*)(\s*)$'
)

SKIP_PATTERNS = [
    re.compile(r'^\s*voice\s+"', re.IGNORECASE),
    re.compile(r'^\s*old\s+"', re.IGNORECASE),
    re.compile(r'^\s*#'),
    re.compile(r'^\s*$'),
]

HAS_ENGLISH = re.compile(r'[A-Za-z]{3,}')  # 3+ consecutive English letters
HAS_CHINESE = re.compile(r'[\u3400-\u9fff]')


def translate_text(text):
    if not text or not text.strip():
        return text

    protected = []

    def replace_protected(m):
        idx = len(protected)
        protected.append(m.group(0))
        return f'ZXQ{idx}QXZ'

    clean = PROTECTED_PATTERN.sub(replace_protected, text)

    try:
        translated = GoogleTranslator(source='en', target='zh-CN').translate(clean)
        if not translated:
            return text
        for i, tag in enumerate(protected):
            placeholder = f'ZXQ{i}QXZ'
            if placeholder not in translated:
                print(f"  Protected token lost: {text[:80]}...", file=sys.stderr)
                return None
            translated = translated.replace(placeholder, tag)
        return translated
    except Exception as e:
        print(f"  FAILED: {text[:80]}... -> {e}", file=sys.stderr)
        time.sleep(1)
        return None  # signal failure


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    translated_count = 0
    failed_count = 0
    output_lines = []

    for line in lines:
        stripped = line.strip()
        skip = False
        for pat in SKIP_PATTERNS:
            if pat.match(line):
                skip = True
                break
        if skip:
            output_lines.append(line)
            continue

        m = QUOTED_LINE.match(line)
        if not m:
            output_lines.append(line)
            continue

        indent = m.group(1) or ''
        char_prefix = m.group(2) or ''
        quoted_text = m.group(3)
        suffix = m.group(4) or ''
        with_clause = m.group(5) or ''
        inner_text = quoted_text[1:-1]

        # Only retry untouched English lines. Mixed Chinese/English needs manual
        # review or terminology fixes, not another machine translation pass.
        if not HAS_ENGLISH.search(inner_text) or HAS_CHINESE.search(inner_text):
            output_lines.append(line)
            continue

        # Translate
        translated_text = translate_text(inner_text)
        if translated_text is None:
            failed_count += 1
            output_lines.append(line)
            continue

        if char_prefix:
            result = f'{indent}{char_prefix} "{translated_text}"'
        else:
            result = f'{indent}"{translated_text}"'
        if suffix:
            result += f' {suffix}'
        if with_clause:
            result += f' {with_clause}'
        result += '\n'

        if result != line:
            translated_count += 1
            if translated_count % 10 == 0:
                time.sleep(0.3)

        output_lines.append(result)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    print(f"Translated: {translated_count}, Failed: {failed_count}")
    return translated_count, failed_count


def main():
    filepath = sys.argv[1]
    t, f = process_file(filepath)
    print(f"Done. {t} lines translated, {f} failures.")
    sys.exit(0 if f == 0 else 1)


if __name__ == '__main__':
    main()
