# Repository guidance

## Purpose

This repository stores the owner's reusable personal workflows as portable Agent Skills. Keep the canonical source for every skill under `skills/<skill-name>/`.

## Skill layout

- Keep the `skills/` namespace flat. Do not nest one skill inside another.
- Record logical categories in `catalog.json`. A skill may belong to multiple categories; do not turn categories into directory nesting.
- Require `SKILL.md` in every skill directory.
- Match the frontmatter `name` to the directory name. Use lowercase letters, numbers, and hyphens only.
- Write a concrete `description` that states both what the skill does and when it should trigger.
- Keep the main instructions focused. Put detailed material in `references/`, deterministic helpers in `scripts/`, and output resources in `assets/`.
- Put client-specific metadata under `agents/`; do not make the core workflow depend on one agent unless the workflow truly requires it.

## Safety and portability

- Never commit credentials, tokens, private URLs, employee data, or generated reports containing confidential content.
- Use relative paths inside a skill. Do not hard-code a developer's home directory.
- Document external tools, network access, accounts, and permissions before relying on them.
- Prefer standard-library scripts when a small deterministic helper is needed.

## Changes

- Update `catalog.json` and the human-readable catalog in `skills/README.md` when adding, renaming, or removing a skill.
- Run `python scripts/validate_skills.py` before declaring a skill change complete.
- Keep repository-level tooling separate from scripts bundled inside an individual skill.
