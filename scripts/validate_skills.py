#!/usr/bin/env python3
"""Validate the repository's flat Agent Skills collection without dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_PATTERN = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)


def scalar(block: str, key: str) -> str | None:
    """Read a simple top-level YAML scalar used by required skill metadata."""
    pattern = re.compile(rf"^{re.escape(key)}:[ \t]*(.*)$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return None

    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def validate_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    relative_dir = skill_dir.relative_to(REPO_ROOT)
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.is_file():
        return [f"{relative_dir}: missing SKILL.md"], warnings

    nested_skill_files = [
        path
        for path in skill_dir.rglob("SKILL.md")
        if path.parent != skill_dir
    ]
    for nested in nested_skill_files:
        errors.append(
            f"{nested.relative_to(REPO_ROOT)}: nested skills are not allowed"
        )

    try:
        text = skill_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{skill_file.relative_to(REPO_ROOT)}: file must be UTF-8"], warnings

    frontmatter_match = FRONTMATTER_PATTERN.search(text)
    if not frontmatter_match:
        return [
            f"{skill_file.relative_to(REPO_ROOT)}: missing valid YAML frontmatter"
        ], warnings

    frontmatter = frontmatter_match.group(1)
    name = scalar(frontmatter, "name")
    description = scalar(frontmatter, "description")

    if not name:
        errors.append(f"{relative_dir}: frontmatter name is required")
    else:
        if len(name) > 64:
            errors.append(f"{relative_dir}: name must be at most 64 characters")
        if not NAME_PATTERN.fullmatch(name):
            errors.append(
                f"{relative_dir}: name must use lowercase letters, numbers, and single hyphens"
            )
        if name != skill_dir.name:
            errors.append(
                f"{relative_dir}: name '{name}' must match directory '{skill_dir.name}'"
            )

    if not description:
        errors.append(f"{relative_dir}: frontmatter description is required")
    elif len(description) > 1024:
        errors.append(f"{relative_dir}: description must be at most 1024 characters")

    body = text[frontmatter_match.end() :].strip()
    if not body:
        errors.append(f"{relative_dir}: SKILL.md must contain instructions")

    line_count = len(text.splitlines())
    if line_count > 500:
        warnings.append(
            f"{relative_dir}: SKILL.md has {line_count} lines; consider progressive disclosure"
        )

    return errors, warnings


def validate_catalog(skill_dirs: list[Path]) -> list[str]:
    errors: list[str] = []
    catalog_file = REPO_ROOT / "catalog.json"

    if not catalog_file.is_file():
        return ["catalog.json: file is required"]

    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"catalog.json: invalid UTF-8 JSON ({exc})"]

    if catalog.get("version") != 1:
        errors.append("catalog.json: version must be 1")

    categories = catalog.get("categories")
    entries = catalog.get("skills")
    if not isinstance(categories, dict):
        errors.append("catalog.json: categories must be an object")
        categories = {}
    if not isinstance(entries, dict):
        errors.append("catalog.json: skills must be an object")
        entries = {}

    for category_id, category in categories.items():
        if not NAME_PATTERN.fullmatch(category_id):
            errors.append(f"catalog.json: invalid category id '{category_id}'")
        if not isinstance(category, dict):
            errors.append(f"catalog.json: category '{category_id}' must be an object")
            continue
        if not isinstance(category.get("label"), str) or not category["label"].strip():
            errors.append(f"catalog.json: category '{category_id}' needs a label")
        if not isinstance(category.get("description"), str) or not category[
            "description"
        ].strip():
            errors.append(f"catalog.json: category '{category_id}' needs a description")

    directory_names = {path.name for path in skill_dirs}
    entry_names = set(entries)
    for missing in sorted(directory_names - entry_names):
        errors.append(f"catalog.json: missing entry for skill '{missing}'")
    for unknown in sorted(entry_names - directory_names):
        errors.append(f"catalog.json: entry '{unknown}' has no matching skill directory")

    for skill_name, entry in entries.items():
        if not isinstance(entry, dict):
            errors.append(f"catalog.json: skill '{skill_name}' must be an object")
            continue
        skill_categories = entry.get("categories")
        if not isinstance(skill_categories, list) or not skill_categories:
            errors.append(
                f"catalog.json: skill '{skill_name}' needs at least one category"
            )
            continue
        if len(skill_categories) != len(set(skill_categories)):
            errors.append(f"catalog.json: skill '{skill_name}' repeats a category")
        for category_id in skill_categories:
            if not isinstance(category_id, str) or category_id not in categories:
                errors.append(
                    f"catalog.json: skill '{skill_name}' uses unknown category '{category_id}'"
                )

    return errors


def main() -> int:
    if not SKILLS_ROOT.is_dir():
        print("ERROR: skills/ directory does not exist", file=sys.stderr)
        return 1

    skill_dirs = sorted(
        path
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )

    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(validate_catalog(skill_dirs))
    for skill_dir in skill_dirs:
        skill_errors, skill_warnings = validate_skill(skill_dir)
        errors.extend(skill_errors)
        warnings.extend(skill_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(
            f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s).",
            file=sys.stderr,
        )
        return 1

    print(f"Validation passed: {len(skill_dirs)} skill(s), {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
