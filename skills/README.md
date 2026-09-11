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
| [`commit-style`](commit-style/) | 从成文规则与 history 逐维读出完整 commit message 风格，再据此撰写 | `effective`、`work` |
| [`feishu-weekly-report`](feishu-weekly-report/) | 结合仓库及飞书、Notion、本地和在线文档，在实际审批页面填写与反复 review；按页面能力保存草稿，由用户提交；技能说明为英文 | `work`、`effective` |

## Categories

分类是 `catalog.json` 中的逻辑标签，不是子目录。当前预留：

| ID | 含义 |
| --- | --- |
| `work` | 工作交付、协作和例行事务 |
| `effective` | 提升个人效率、质量和决策一致性的工作流 |
| `note` | 笔记、知识整理和信息归档 |
| `linux` | Linux 环境、命令行和系统运维 |

一个 skill 可以归入多个分类。例如，一个自动整理工作记录的 skill 可以同时属于 `work`、`effective` 和 `note`。
