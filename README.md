# myskill

这是一个可移植的 Agent Skills 工作流仓库。

## Skills

- [`commit-style`](skills/commit-style/) — 按需读取仓库规则与 history，逐维识别 commit
  message 风格；起草与提交授权分开
- [`feishu-weekly-report`](skills/feishu-weekly-report/) — 汇总仓库与文档中的本周工作，在真实审批页面填写和反复 review，保留草稿能力，最终由用户提交（英文技能说明）
- [`renpy-chinese-translation`](skills/renpy-chinese-translation/) — 区分只读审查与翻译修改，按项目术语保护 `.rpy` 译文槽位；机器初译按需授权（英文技能说明）
- [`tree-sitter-grammar-maintenance`](skills/tree-sitter-grammar-maintenance/) — 通用审计与修复流程按需加载，以语言契约判定取舍；附 MLIR 配置和其他语言接入指导（英文技能说明）

完整列表和分类在 [skills/README.md](skills/README.md)。

## 常用命令

```powershell
python scripts/install_skills.py --list
python scripts/validate_skills.py
python scripts/check_resources.py
python scripts/test_check_resources.py
```

## 文档

- [编写 skill](docs/authoring.md)
- [安装到不同 Agent](docs/compatibility.md)
- [提交约定](CONTRIBUTING.md)
