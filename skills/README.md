# Skill catalog

可安装的 skills 放在此目录下，并保持单层结构：

```text
skills/
└── <skill-name>/
    └── SKILL.md
```

## Available skills

| Skill | 用途 | 分类 |
| --- | --- | --- |
| [`commit-style`](commit-style/) | 先读出仓库自己的提交约定，再照着写 commit message | `effective`、`work` |

下一个候选是“周报提交”工作流；在确定触发条件、输入来源、产出格式和提交动作后再创建目录。

## Categories

分类是 `catalog.json` 中的逻辑标签，不是子目录。当前预留：

| ID | 含义 |
| --- | --- |
| `work` | 工作交付、协作和例行事务 |
| `effective` | 提升个人效率、质量和决策一致性的工作流 |
| `note` | 笔记、知识整理和信息归档 |
| `linux` | Linux 环境、命令行和系统运维 |

一个 skill 可以归入多个分类。例如，一个自动整理工作记录的 skill 可以同时属于 `work`、`effective` 和 `note`。
