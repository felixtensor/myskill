# 跨 Agent 兼容性

## 唯一源码

所有 skills 都以开放的目录格式保存在 `skills/<skill-name>/`。不要在 `.agents/`、`.claude/` 等目录手工维护副本，否则内容很容易漂移。

`work`、`effective`、`note`、`linux` 等分类只登记在根目录 `catalog.json`。把分类做成 `skills/work/<skill-name>/` 之类的物理嵌套会破坏部分客户端和安装器的一层扫描，因此不采用。

核心 `SKILL.md` 保持客户端中立。只有界面展示、调用策略或工具声明等无法通用的内容，才放到 skill 自己的 `agents/` 目录。

## 默认安装目标

仓库自带的安装器目前内置两个目标：

| Agent | 个人范围 | 项目范围 |
| --- | --- | --- |
| Codex | `~/.agents/skills/` | `<project>/.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `<project>/.claude/skills/` |

其他支持 Agent Skills 的客户端使用 `--dest` 指定其当前文档要求的目录，避免在仓库中固化可能变化的路径。

示例：

```powershell
# 查看可安装列表
python scripts/install_skills.py --list

# 安装全部到个人 Codex
python scripts/install_skills.py --agent codex --scope user

# 安装指定 skill 到当前项目的 Claude Code
python scripts/install_skills.py --agent claude --scope project --skills weekly-report

# 安装到任意客户端目录
python scripts/install_skills.py --dest C:\path\to\skills --skills weekly-report
```

安装器使用复制而不是符号链接，以便在 Windows、macOS 和 Linux 上行为一致。替换已有 skill 必须显式使用 `--replace`；旧版本会移动到目标目录旁的 `.myskill-backups/`，便于恢复。

## 发布后的第三方安装方式

仓库推送到 GitHub 后，也可以使用支持 Agent Skills 仓库的第三方安装器。例如：

```text
npx skills add <github-owner>/myskill --list
npx skills add <github-owner>/myskill --skill <skill-name> -g
```

具体参数和目标 Agent 名称以该工具当时的文档为准。仓库内的 Python 安装器是无需 Node.js 的保底方式。

## 可移植性检查

- frontmatter 只依赖开放规范字段；客户端扩展放到专属文件。
- 路径使用相对路径和跨平台脚本接口。
- 外部命令、环境变量、账号和网络需求在 skill 中显式声明。
- 不假设某个 Agent 独有的工具名称；必须依赖时在触发描述和兼容性说明中写清楚。
- 每个 skill 可以单独复制、安装和版本化。
