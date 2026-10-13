#!/usr/bin/env python3
"""
Export Ren'Py translation slots as ordered review batches.

This is read-only. It gives an LLM a bounded list of source/translation pairs
to review one by one, with file and line numbers for exact patching.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


TRANSLATE_RE = re.compile(r"^\s*translate\s+\w+\s+([A-Za-z0-9_.]+|strings):\s*$")
OLD_RE = re.compile(r"^\s*old\s+(\"(?:[^\"\\]|\\.)*\")\s*$")
NEW_RE = re.compile(r"^\s*new\s+(\"(?:[^\"\\]|\\.)*\")\s*$")
DIALOGUE_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?:(?P<who>[A-Za-z_]\w*)\s+)?"
    r"(?P<quoted>\"(?:[^\"\\]|\\.)*\")"
    r"(?P<suffix>.*)$"
)
ENGLISH_RE = re.compile(r"[A-Za-z]{3,}")
CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
TAG_RE = re.compile(r"\{[^}]*\}")
INTERPOLATION_RE = re.compile(r"\[[^\]]+\]")
ALLOWED_ENGLISH_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"https?://\S+",
        r"\b[a-z_]+(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b",
        r"\b[A-Za-z0-9_./-]+\.(?:txt|rpy|rpym|png|jpg|jpeg|webp|ogg|mp3|wav)\b",
        r"(?<![A-Za-z0-9_])(?:Shift|Alt|Ctrl|Tab|Esc|Escape)(?:\+[A-Za-z])?(?![A-Za-z0-9_])",
        r"(?<![A-Za-z0-9_])(?:Ren'?Py|MIT|GNU|LGPL|GL2|ANGLE2|GLES2|BBCode|BBcode|Markdown)(?![A-Za-z0-9_])",
        r"(?<![A-Za-z0-9_])(?:Discord|Steam|App Store|Lovense|DejaVu Sans|Opendyslexic)(?![A-Za-z0-9_])",
        r"(?<![A-Za-z0-9_])(?:Heartskip Games|Heartskip|HeartSkip|BLits)(?![A-Za-z0-9_])",
    ]
]


@dataclass
class Slot:
    index: int
    kind: str
    file: str
    line: int
    speaker: str
    original: str
    translation: str
    suffix: str
    flags: list[str]


def parse_string(value: str) -> str:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, str):
        raise ValueError("quoted value did not parse as str")
    return parsed


def parse_dialogue(line: str) -> tuple[str, str, str] | None:
    match = DIALOGUE_RE.match(line)
    if not match:
        return None
    return (
        match.group("who") or "",
        parse_string(match.group("quoted")),
        (match.group("suffix") or "").strip(),
    )


def strip_reference_comment(line: str) -> str:
    text = line.lstrip()[1:]
    if text.startswith(" "):
        text = text[1:]
    return text.rstrip()


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.rpy")))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(raw)
    return sorted(dict.fromkeys(files))


def flags_for(original: str, translation: str) -> list[str]:
    flags: list[str] = []
    clean = scrub_review_text(translation)
    original_clean = scrub_review_text(original)

    if translation == original and ENGLISH_RE.search(original_clean):
        flags.append("untranslated")
    elif ENGLISH_RE.search(clean):
        flags.append("english-left")

    if not CHINESE_RE.search(clean) and ENGLISH_RE.search(original_clean):
        flags.append("no-chinese")

    if TAG_RE.findall(original) != TAG_RE.findall(translation):
        flags.append("tag-mismatch")

    if INTERPOLATION_RE.findall(original) != INTERPOLATION_RE.findall(translation):
        flags.append("interpolation-mismatch")

    return flags


def scrub_review_text(text: str) -> str:
    text = TAG_RE.sub("", text)
    text = INTERPOLATION_RE.sub("", text)
    for pattern in ALLOWED_ENGLISH_PATTERNS:
        text = pattern.sub("", text)
    return text


def slots_from_file(path: Path) -> list[Slot]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    slots: list[Slot] = []
    index = 0

    while index < len(lines):
        match = TRANSLATE_RE.match(lines[index])
        if not match:
            index += 1
            continue

        if match.group(1) == "strings":
            index += 1
            old_text = None
            while index < len(lines) and not TRANSLATE_RE.match(lines[index]):
                old_match = OLD_RE.match(lines[index])
                if old_match:
                    old_text = parse_string(old_match.group(1))
                    index += 1
                    continue

                new_match = NEW_RE.match(lines[index])
                if new_match and old_text is not None:
                    new_text = parse_string(new_match.group(1))
                    slots.append(
                        Slot(
                            index=0,
                            kind="string",
                            file=str(path),
                            line=index + 1,
                            speaker="",
                            original=old_text,
                            translation=new_text,
                            suffix="",
                            flags=flags_for(old_text, new_text),
                        )
                    )
                    old_text = None

                index += 1
            continue

        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1

        comments: list[tuple[int, str]] = []
        while index < len(lines) and lines[index].lstrip().startswith("#"):
            comments.append((index + 1, strip_reference_comment(lines[index])))
            index += 1

        code: list[tuple[int, str]] = []
        while index < len(lines) and lines[index].strip() and not TRANSLATE_RE.match(lines[index]):
            if not lines[index].lstrip().startswith("#"):
                code.append((index + 1, lines[index].rstrip()))
            index += 1

        for (_, original_line), (code_line, translated_line) in zip(comments, code):
            if original_line.strip().startswith("voice "):
                continue

            original = parse_dialogue(original_line)
            translated = parse_dialogue(translated_line)
            if original is None or translated is None:
                continue

            original_speaker, original_text, original_suffix = original
            translated_speaker, translated_text, translated_suffix = translated
            speaker = translated_speaker or original_speaker
            suffix = translated_suffix or original_suffix

            slots.append(
                Slot(
                    index=0,
                    kind="dialogue",
                    file=str(path),
                    line=code_line,
                    speaker=speaker,
                    original=original_text,
                    translation=translated_text,
                    suffix=suffix,
                    flags=flags_for(original_text, translated_text),
                )
            )

    return slots


def print_markdown(slots: list[Slot]) -> None:
    print("# Translation Review Batch")
    print()
    print("Review every slot in order. For each slot, decide PASS or propose an exact replacement for the translated text only.")
    print("Do not change reference comments, old strings, speaker names, suffixes, tags, or interpolation.")
    print()

    for slot in slots:
        flags = ", ".join(slot.flags) if slot.flags else "none"
        speaker = slot.speaker or "narrator/string"
        print(f"## Slot {slot.index}")
        print(f"- location: `{slot.file}:{slot.line}`")
        print(f"- kind: `{slot.kind}`")
        print(f"- speaker: `{speaker}`")
        print(f"- suffix: `{slot.suffix}`")
        print(f"- flags: `{flags}`")
        print()
        print("Original:")
        print(f"> {slot.original}")
        print()
        print("Current translation:")
        print(f"> {slot.translation}")
        print()


def print_jsonl(slots: list[Slot]) -> None:
    for slot in slots:
        print(json.dumps(asdict(slot), ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ordered Ren'Py translation review slots.")
    parser.add_argument("paths", nargs="+", help="Translation files or directories.")
    parser.add_argument("--offset", type=int, default=0, help="Zero-based slot offset.")
    parser.add_argument("--limit", type=int, default=80, help="Maximum slots to print.")
    parser.add_argument("--issues-only", action="store_true", help="Only include slots with automatic flags.")
    parser.add_argument("--format", choices=("markdown", "jsonl"), default="markdown")
    args = parser.parse_args()

    all_slots: list[Slot] = []
    for path in collect_files(args.paths):
        all_slots.extend(slots_from_file(path))

    if args.issues_only:
        all_slots = [slot for slot in all_slots if slot.flags]

    for number, slot in enumerate(all_slots, 1):
        slot.index = number

    selected = all_slots[args.offset : args.offset + args.limit]

    if args.format == "jsonl":
        print_jsonl(selected)
    else:
        print_markdown(selected)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
