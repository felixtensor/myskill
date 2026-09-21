# myskill

这是我的个人 Agent Skills 仓库，收集我日常反复使用的工作流。

## Skills

- [`commit-style`](skills/commit-style/) — 从成文规则与 history 逐维读出完整 commit
  message 风格，再据此撰写
- [`feishu-weekly-report`](skills/feishu-weekly-report/) — 汇总仓库与文档中的本周工作，在真实审批页面填写和反复 review，保留草稿能力，最终由用户提交（英文技能说明）
- [`tree-sitter-grammar-maintenance`](skills/tree-sitter-grammar-maintenance/) — 拿 mlir-opt 等官方 parser 当参照，对比、定位、修复、验证成闭环，并把架构文档维护成判定取舍的准绳（英文技能说明）

完整列表和分类在 [skills/README.md](skills/README.md)。

## 常用命令

```powershell
python scripts/install_skills.py --list
python scripts/validate_skills.py
```

## 文档

- [编写 skill](docs/authoring.md)
- [安装到不同 Agent](docs/compatibility.md)
- [提交约定](CONTRIBUTING.md)
