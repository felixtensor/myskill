# Contributing

## Skill changes

新增或修改 skill 时，遵循 [Skill 创作约定](docs/authoring.md)，更新 `catalog.json` 和 `skills/README.md`，然后运行：

```powershell
python scripts/validate_skills.py
```

## Commit messages

提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```text
<type>[optional scope][!]: <description>

[optional body]

[optional footer]
```

规则：

- 每一行不超过 80 个字符，包括正文和 footer。
- description 简洁、使用祈使语气、末尾不加句号。
- 常用 type 包括 `feat`、`fix`、`docs`、`refactor`、`test`、`ci`、`build` 和 `chore`。
- 有破坏性变更时，在 type/scope 后加 `!`，并使用 `BREAKING CHANGE:` footer 解释影响。
- 正文说明原因、背景和重要取舍，不重复 diff 中显而易见的内容。

示例：

```text
feat(weekly-report): add draft generation workflow
docs: explain cross-agent installation
fix(installer): preserve existing skill before replacement
```
