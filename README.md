# myskill

`myskill` 是我的个人 Agent Skills 仓库，用来沉淀高频、可复用、可验证的工作流。

这个仓库优先服务个人工作方式，同时尽量遵循开放的 Agent Skills 格式，让同一份 skill 可以被 Codex、Claude Code，以及其他兼容 `SKILL.md` 的 Agent 使用。

## 设计原则

- 一个 skill 只解决一个边界清晰的问题。
- `skills/<skill-name>/` 是唯一源码目录，不维护多份 Agent 专属副本。
- 物理目录保持扁平，使用 `catalog.json` 做 `work`、`effective`、`note`、`linux` 等逻辑分类；一个 skill 可以属于多个分类。
- 每个 skill 至少包含一个带 YAML frontmatter 的 `SKILL.md`。
- 优先用清晰指令表达流程；只有在需要确定性或重复执行时才添加脚本。
- 大段背景资料、模板和可执行代码按需放入 `references/`、`assets/` 和 `scripts/`。
- 个人配置与凭据不进入版本库；skill 应显式说明所需输入和权限。
- 每次新增或修改 skill 后都运行本地校验。

## 仓库结构

```text
myskill/
├── skills/                    # 可安装的 skills；保持扁平
│   └── <skill-name>/
│       ├── SKILL.md           # 必需：元数据与工作流指令
│       ├── agents/            # 可选：特定客户端的展示/依赖元数据
│       ├── scripts/           # 可选：确定性辅助脚本
│       ├── references/        # 可选：按需读取的参考资料
│       └── assets/            # 可选：模板、图像、静态资源
├── catalog.json               # 逻辑分类与 skill 索引
├── docs/                      # 仓库级设计与维护说明
├── scripts/                   # 仓库级安装、校验工具
└── .github/workflows/         # 持续校验
```

## 使用

列出当前仓库中的 skills：

```powershell
python scripts/install_skills.py --list
```

安装到个人 Codex：

```powershell
python scripts/install_skills.py --agent codex --scope user
```

安装到当前项目的 Claude Code：

```powershell
python scripts/install_skills.py --agent claude --scope project
```

其他 Agent 可以指定其 skills 目录：

```powershell
python scripts/install_skills.py --dest C:\path\to\agent\skills
```

只安装某几个 skills 时追加 `--skills name-a name-b`。目标已存在时安装器默认停止；明确使用 `--replace` 才会替换，并把旧版本保存在目标目录旁的 `.myskill-backups/` 中。

## 开发

新增 skill 前先阅读 [创作约定](docs/authoring.md)，并在 `catalog.json` 中登记分类。修改后运行：

```powershell
python scripts/validate_skills.py
```

跨 Agent 的目录与安装方式见 [兼容性说明](docs/compatibility.md)。

## Roadmap

- [ ] 设计并实现第一个 skill：周报提交工作流（名称、输入、数据源、输出和提交边界待讨论）

## 参考项目

初始化结构主要借鉴了以下项目中的成熟做法：

- [OpenAI Skills](https://github.com/openai/skills)：Codex skill 的官方实现与元数据约定。
- [Anthropic Skills](https://github.com/anthropics/skills)：自包含 skill、渐进式披露和资源分层。
- [sensein/agent_skills](https://github.com/sensein/agent_skills)：扁平 skill 集合与跨 Agent 安装脚本。
- [obra/superpowers](https://github.com/obra/superpowers)：将个人方法论拆成可组合工作流，并针对多个 Agent 分发。
- [Agent Skills 规范](https://agentskills.io/specification)：`SKILL.md` 的开放格式与校验约束。

## License

暂未选择开源许可证。公开发布前再根据复用范围决定。
