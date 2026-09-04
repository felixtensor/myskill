#!/usr/bin/env python3
"""Install selected skills into Codex, Claude Code, or a custom directory."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"


def available_skills() -> dict[str, Path]:
    return {
        path.name: path
        for path in sorted(SKILLS_ROOT.iterdir())
        if path.is_dir() and not path.name.startswith(".") and (path / "SKILL.md").is_file()
    }


def destination_for(agent: str, scope: str) -> Path:
    if scope == "user":
        base = Path.home()
    else:
        base = Path.cwd()

    if agent == "codex":
        return base / ".agents" / "skills"
    if agent == "claude":
        return base / ".claude" / "skills"
    raise ValueError(f"Unsupported agent: {agent}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy this repository's Agent Skills into an agent skills directory."
    )
    parser.add_argument("--list", action="store_true", help="list available skills and exit")
    parser.add_argument("--agent", choices=("codex", "claude"), help="known agent target")
    parser.add_argument(
        "--scope",
        choices=("user", "project"),
        default="user",
        help="installation scope for --agent (default: user)",
    )
    parser.add_argument("--dest", type=Path, help="custom destination directory")
    parser.add_argument(
        "--skills",
        nargs="+",
        metavar="NAME",
        help="skill names to install (default: all)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace existing targets after preserving them in .myskill-backups",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skills = available_skills()

    if args.list:
        if skills:
            for name in skills:
                print(name)
        else:
            print("No skills found.")
        return 0

    if bool(args.agent) == bool(args.dest):
        print("ERROR: specify exactly one of --agent or --dest", file=sys.stderr)
        return 2

    selected_names = args.skills or list(skills)
    unknown = sorted(set(selected_names) - set(skills))
    if unknown:
        print(f"ERROR: unknown skill(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not selected_names:
        print("ERROR: no skills are available to install", file=sys.stderr)
        return 2

    destination = (
        args.dest.expanduser().resolve()
        if args.dest
        else destination_for(args.agent, args.scope).resolve()
    )

    existing = [name for name in selected_names if (destination / name).exists()]
    if existing and not args.replace:
        print(
            "ERROR: target already exists for "
            + ", ".join(existing)
            + "; use --replace to preserve and replace it",
            file=sys.stderr,
        )
        return 2

    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = destination.parent / ".myskill-backups" / timestamp

    for name in selected_names:
        source = skills[name]
        target = destination / name
        backup: Path | None = None

        if target.exists():
            backup = backup_root / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            target.replace(backup)

        try:
            shutil.copytree(source, target, symlinks=True)
        except Exception:
            if target.exists():
                shutil.rmtree(target)
            if backup is not None and backup.exists():
                backup.replace(target)
            raise

        print(f"Installed {name} -> {target}")
        if backup is not None:
            print(f"Preserved previous version -> {backup}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
