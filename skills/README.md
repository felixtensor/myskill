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
| [`commit-style`](commit-style/) | 按需读取仓库规则与 history，逐维识别 commit message 风格；起草与提交授权分开 | `effective`、`work` |
| [`feishu-weekly-report`](feishu-weekly-report/) | 按实际表单映射字段、按需读取工作来源，在审批页面填写与 review；保存草稿与提交分开，由用户提交；技能说明为英文 | `work`、`effective` |
| [`renpy-chinese-translation`](renpy-chinese-translation/) | 区分只读审查与翻译修改，按项目术语保护 `.rpy` 译文槽位；机器初译按需授权，slot 审查与结构验证收口；技能说明为英文 | `work`、`effective` |
| [`tree-sitter-grammar-maintenance`](tree-sitter-grammar-maintenance/) | 通用审计与修复流程按需加载，以语言契约判定取舍；附 MLIR 配置和其他语言接入指导；技能说明为英文 | `effective`、`work` |

## Categories

分类是 `catalog.json` 中的逻辑标签，不是子目录。当前预留：

| ID | 含义 |
| --- | --- |
| `work` | 工作交付、协作和例行事务 |
| `effective` | 提升个人效率、质量和决策一致性的工作流 |
| `note` | 笔记、知识整理和信息归档 |
| `linux` | Linux 环境、命令行和系统运维 |

一个 skill 可以归入多个分类。例如，一个自动整理工作记录的 skill 可以同时属于 `work`、`effective` 和 `note`。
