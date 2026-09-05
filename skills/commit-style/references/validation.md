# 验证案例

`docs/authoring.md` §5 要求的六类案例，针对 `commit-style`。没有自动化 harness，这是
改这个 skill 之前手工走的清单：在一个真实仓库里触发，对照"期望"看输出。这是维护材料，
不是运行时指令，`SKILL.md` 不引用它。改动触发面
（frontmatter description）或 Part 2 的证据顺序时，1、2、3 三节必须重跑。

## 1 · 典型触发

- **Conventional 仓库，暂存了单文件修复，用户只说 "commit this"**
  → `fix(scope): …`，scope 取自日志里已有的，不自造；行宽符合仓库规定；无 attribution
  trailer。
- **"提交一下"，但什么都没暂存**
  → 先列出改动并问哪些属于这次提交，不自行 `git add -A`。
- **LLVM 风格仓库（日志里清一色 `[Component]`）**
  → bracket tag 从改动实际触及的组件推出，复用日志中已有的 tag，不造同义词。
- **"帮我把这几个 commit 的 message 统一一下"**
  → 走 reword 路径，先说明会动到哪几个 commit，且仅在未 push 时改写。
- **暂存的改动明显是两件事**
  → 给出拆分方案让用户选；既不擅自拆，也不闷头合成一个。

## 2 · 邻近请求（不应触发）

- "写一下这个 PR 的描述" —— PR 描述不是 commit message。
- "怎么撤销上一个 commit" / "rebase 怎么用" —— git 操作答疑。
- "生成这个版本的 release notes" —— 面向用户的发布说明。
- 边界，**应该**触发："我们仓库的 commit 规范是什么" —— 属于"如何措辞"。

## 3 · 缺少必要输入

- **不在 git 仓库里** → 直接说明，不假装读到了约定。
- **暂存区和工作区都干净** → 没有可提交的东西，不为了产出而产出。
- **全新仓库，只有一个 "Initial commit"** → 不发明仪式感：plain imperative，并明确告知
  未检测到约定，让用户自己定。
- **用户只说"感觉快了不少"，没有数字** → 消息里不得出现任何具体数字或百分比。

## 4 · 外部依赖不可用

- **`git config --get commit.template` 未配置时退出码是 1** —— 这是"没有配置"，不是
  失败，不要当错误上报或中断流程。
- **没有 CONTRIBUTING / AGENTS / commitlint 配置** → 落到第 2 级证据（日志）。
- **浅克隆，或日志只有一两条** → 日志给不出模式，落回文档规则或 plain imperative。
- **无网络** → 全流程不得需要联网。上游约定靠用户告知，不靠抓取。

## 5 · 重复运行

- 连续触发两次不得产生两个提交；已经提交过就走 amend/reword，且仅在未 push 时。
- 已经去掉的 trailer，重跑不得又加回来。
- Part 0 和 Part 2 的命令全部只读，重复执行安全。

## 6 · 输出格式与隐私

- 每一行不超过仓库规定的宽度（本仓库 80，含 body 与 footer）。
- 祈使语气，subject 末尾无句号，subject 与 body 之间有空行。
- 不给 agent 自己加 `Co-Authored-By`；仓库要求的 `Signed-off-by:` 照加。
- diff 里出现的 token、内网地址、客户名和个人信息，不得被抄进 commit message。
