#!/usr/bin/env python3
"""
Apply literal/regex replacements only inside translated Ren'Py text slots.

Replacement file format:
[
  {"old": "哈罗", "new": "海洛"},
  {"pattern": "([一-鿿])\\.\\{/i\\}", "new": "\\1。{/i}"}
]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path


QUOTED_SLOT_RE = re.compile(
    r"^(?P<prefix>\s*(?:(?:[A-Za-z_]\w*)\s+|new\s+)?)"
    r"(?P<quoted>\"(?:[^\"\\]|\\.)*\")"
    r"(?P<suffix>.*)$"
)


@dataclass(frozen=True)
class Replacement:
    old: str | None
    pattern: re.Pattern[str] | None
    new: str


def is_locked_line(line: str) -> bool:
    stripped = line.lstrip()
    return (
        stripped.startswith("#")
        or stripped.startswith("old ")
        or stripped.startswith("voice ")
        or stripped.startswith("translate ")
        or not stripped
    )


def parse_string(value: str) -> str:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, str):
        raise ValueError("quoted value is not a string")
    return parsed


def quote_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_replacements(path: Path) -> list[Replacement]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("replacement file must contain a JSON list")

    replacements: list[Replacement] = []
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"replacement #{index} is not an object")
        new = item.get("new")
        if not isinstance(new, str):
            raise ValueError(f"replacement #{index} is missing string field 'new'")

        old = item.get("old")
        pattern = item.get("pattern")
        if isinstance(old, str) and pattern is None:
            replacements.append(Replacement(old=old, pattern=None, new=new))
        elif isinstance(pattern, str) and old is None:
            replacements.append(Replacement(old=None, pattern=re.compile(pattern), new=new))
        else:
            raise ValueError(f"replacement #{index} must define exactly one of 'old' or 'pattern'")

    return replacements


def apply_to_text(text: str, replacements: list[Replacement]) -> tuple[str, int]:
    changes = 0
    for replacement in replacements:
        if replacement.old is not None:
            count = text.count(replacement.old)
            if count:
                text = text.replace(replacement.old, replacement.new)
                changes += count
        elif replacement.pattern is not None:
            text, count = replacement.pattern.subn(replacement.new, text)
            changes += count
    return text, changes


def process_file(path: Path, replacements: list[Replacement], dry_run: bool) -> int:
    lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    output: list[str] = []
    total_changes = 0

    for line in lines:
        newline = ""
        body = line
        if body.endswith("\r\n"):
            body = body[:-2]
            newline = "\r\n"
        elif body.endswith("\n"):
            body = body[:-1]
            newline = "\n"

        if is_locked_line(body):
            output.append(line)
            continue

        match = QUOTED_SLOT_RE.match(body)
        if not match:
            output.append(line)
            continue

        text = parse_string(match.group("quoted"))
        new_text, changes = apply_to_text(text, replacements)
        if changes:
            total_changes += changes
            body = f"{match.group('prefix')}{quote_string(new_text)}{match.group('suffix')}"

        output.append(body + newline)

    if total_changes and not dry_run:
        path.write_text("".join(output), encoding="utf-8")

    print(f"{path}: {total_changes} replacement(s){' (dry run)' if dry_run else ''}")
    return total_changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely apply replacements inside Ren'Py translated text slots.")
    parser.add_argument("replacement_json", help="JSON file with replacement objects.")
    parser.add_argument("files", nargs="+", help="Translation files to update.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = parser.parse_args()

    replacements = load_replacements(Path(args.replacement_json))
    total = 0
    for raw in args.files:
        total += process_file(Path(raw), replacements, args.dry_run)

    print(f"Total replacements: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
