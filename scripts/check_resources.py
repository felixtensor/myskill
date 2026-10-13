#!/usr/bin/env python3
"""Check local Markdown links and high-confidence privacy markers, offline.

Git supplies tracked and non-ignored working files; history and ignored artifacts
are excluded. Diagnostics contain only repository paths, line numbers and rules.
This is a focused heuristic, not a guarantee that content is safe to publish.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".env",
    ".pem", ".key", ".ini", ".cfg", ".conf", ".sh", ".ps1", ".csv", ".tsv",
}
PRIVACY_RULES = {
    "absolute-home-path": re.compile(
        r"/(?:Users|home)/[\w.-]+/|[A-Za-z]:[\\/]Users[\\/][\w.-]+[\\/]"
    ),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b"),
    "literal-credential": re.compile(
        r"\b(?:api[_-]?key|app[_-]?secret|password|access[_-]?token)\b"
        r"[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_+/=-]{16,}[\"']", re.I
    ),
    "signed-or-authenticated-url": re.compile(
        r"https?://[^\s<>\"')]*(?:[?&](?:access_token|api_key|token|"
        r"x-amz-signature|x-goog-signature|signature)=|[^/\s]+:[^/\s]+@)[^\s<>\"')]+", re.I
    ),
}
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
EXAMPLE_DOMAINS = {"example.com", "example.org", "example.net", "example.invalid"}
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+[^)\n]+)?\s*\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", re.M)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


def privacy_findings(path: str, text: str) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for rule, pattern in PRIVACY_RULES.items():
            if pattern.search(line):
                findings.append(Finding(path, number, rule))
        for match in EMAIL.finditer(line):
            domain = match.group(1).lower()
            if not any(domain == allowed or domain.endswith("." + allowed)
                       for allowed in EXAMPLE_DOMAINS):
                findings.append(Finding(path, number, "non-example-email"))
                break
    return findings


def markdown_prose(text: str, *, strip_inline_code: bool = True) -> str:
    """Blank fenced code and inline code while preserving diagnostic line numbers."""
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
            lines.append("\n" if line.endswith("\n") else "")
        elif marker:
            fence = marker.group(1)
            lines.append("\n" if line.endswith("\n") else "")
        else:
            # Backticks in a link label are harmless; code containing fake links is not prose.
            lines.append(re.sub(r"(`+)([^`\n]*?)\1", lambda m: " " * len(m.group()), line)
                         if strip_inline_code else line)
    return "".join(lines)


def heading_anchors(text: str) -> set[str]:
    anchors = set()
    counts: dict[str, int] = {}
    for line in markdown_prose(text, strip_inline_code=False).splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        title = match.group(1).lower()
        slug = "".join(c for c in title if c.isalnum() or c in " _-").replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def link_findings(root: Path, file: Path, text: str) -> list[Finding]:
    prose = markdown_prose(text)
    findings = []
    label = file.relative_to(root).as_posix()
    for pattern in (INLINE_LINK, REFERENCE_LINK):
        for match in pattern.finditer(prose):
            target = match.group(1).strip("<>")
            number = prose.count("\n", 0, match.start()) + 1
            # External sources are preserved; this checker never performs network requests.
            if target.startswith("//"):
                continue
            if re.match(r"^[A-Za-z]:[\\/]", target):
                findings.append(Finding(label, number, "absolute-local-link"))
                continue
            url = urlsplit(target)
            if url.scheme:
                if url.scheme == "file":
                    findings.append(Finding(label, number, "nonportable-file-link"))
                continue
            if url.path.startswith("/"):
                findings.append(Finding(label, number, "absolute-local-link"))
                continue
            resolved = (file.parent / unquote(url.path)).resolve() if url.path else file.resolve()
            if not resolved.is_relative_to(root):
                findings.append(Finding(label, number, "link-outside-repository"))
            elif not resolved.exists():
                findings.append(Finding(label, number, "missing-local-link"))
            elif url.fragment and resolved.suffix == ".md" and resolved.is_file():
                anchors = heading_anchors(resolved.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in anchors:
                    findings.append(Finding(label, number, "missing-local-anchor"))
    return findings


def repository_files(root: Path) -> list[Path]:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if Path(top.stdout.decode("utf-8").strip()).resolve() != root:
        raise ValueError("--root must be the Git worktree root")
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return sorted({root / name.decode("utf-8") for name in result.stdout.split(b"\0") if name})


def check_repository(root: Path) -> list[Finding]:
    root = root.resolve()
    findings = []
    for file in repository_files(root):
        if not file.exists():  # Tracked files deleted in the working tree.
            continue
        label = file.relative_to(root).as_posix()
        if not file.resolve().is_relative_to(root):
            findings.append(Finding(label, 1, "file-outside-repository"))
            continue
        if not file.is_file():
            continue
        if file.suffix.lower() not in TEXT_SUFFIXES and not file.name.startswith(".env"):
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(Finding(label, 1, "non-utf8-resource"))
            continue
        findings.extend(privacy_findings(label, text))
        if file.suffix == ".md":
            findings.extend(link_findings(root, file, text))
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        validation = skill.parent / "references/validation.md"
        if not validation.is_file() or not validation.read_text(encoding="utf-8").strip():
            findings.append(Finding(skill.parent.relative_to(root).as_posix(), 1,
                                    "missing-validation-cases"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        findings = check_repository(args.root)
    except (OSError, subprocess.CalledProcessError, ValueError):
        print("Resource check could not read a Git working tree.", file=sys.stderr)
        return 2
    for finding in findings:
        print(f"ERROR: {finding}", file=sys.stderr)
    print(f"Resource check: {len(findings)} finding(s).")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
