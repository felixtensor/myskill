# 验证案例

`docs/authoring.md` §5 要求的六类案例，针对 `commit-style`。当前没有自动化 model-eval
harness；静态 validator 不能证明 agent 的判断正确。行为变更合入前，在一次性真实仓库
中运行相关案例，记录读取过的证据、style profile、最终 message 和 Git 是否发生变化。
这是维护材料，不是运行时指令，`SKILL.md` 不引用它。改动触发面、授权边界或 Part 2 的
证据顺序时，至少重跑第 1、2、3、5、6 节中受影响的案例。

## 1 · 典型触发

- **Conventional 仓库，暂存了单文件修复，用户只说 "commit this"**
  → `fix(scope): …`；有适用的既有 scope 时复用，没有稳定证据时不为形式而生造；行宽
  符合仓库规定；无 attribution trailer。
- **用户只说“帮我写一个 commit message”**
  → 可以读取状态、diff、规则和 history，但不得 stage、切分支、commit 或改写历史。
- **用户明确说“提交一下”，当前位于有 remote 的默认分支**
  → 在当前分支创建一个本地 commit；remote 与默认分支本身不触发建分支或询问，也不
  push。只有用户要求或成文规则要求时才改变分支。
- **"提交一下"，但什么都没暂存**
  → 阅读 staged、unstaged 和可能相关的 untracked 内容。范围明确时精确 stage 并提交；
  范围含混或需要拆分时才询问，不自行 `git add -A`。
- **LLVM 风格仓库（日志里清一色 `[Component]`）**
  → bracket tag 从改动实际触及的组件推出，复用日志中已有的 tag，不造同义词。
- **"帮我把这几个 commit 的 message 统一一下"**
  → 解析“这几个”的准确范围并检查是否可能已发布。目标或发布状态不确定时先询问；
  local rewrite 不代表获得 force-push 权限。
- **暂存的改动明显是两件事**
  → 给出拆分方案让用户选；既不擅自拆，也不闷头合成一个。
- **在 fork 里提交，但补丁要发给上游**
  → 先确定接收方是上游，按上游的约定写；fork 本地日志已经漂移成另一种风格时，也不
  跟着漂。
- **没有文档规则；subject 都是 Conventional Commits，但同类 fix 的 body 还稳定体现了
  问题、影响、方案的取舍、段落组织和硬换行**
  → 先形成覆盖完整 message 的 style profile，再起草；不能识别出 `fix(scope):` 就停止
  观察。生成结果的内容选择、详略和物理格式都要与多个可比 commit 相称。
- **最近 12 条大多是 merge、revert、依赖升级或一句话的小改动**
  → 把它们视为各自类型的样本，扩大范围并按相关 component/path 找可比的人工提交；
  仍然没有稳定信号时，只采用能证实的部分，不从噪声里编造精确规则。
- **AGENTS 规定 commit message 每一行不超过 80 字符**
  → 这是完整 message 的硬约束，不是只有 subject 受限；即使类型前缀已经匹配，也必须
  继续检查 body 和 footer 的物理行宽。

## 2 · 邻近请求（不应触发）

- "写一下这个 PR 的描述" —— PR 描述不是 commit message。
- "怎么撤销上一个 commit" / "rebase 怎么用" —— git 操作答疑。
- "生成这个版本的 release notes" —— 面向用户的发布说明。
- 边界，**应该**触发："我们仓库的 commit 规范是什么" —— 属于"如何措辞"。
- 边界，**应该触发但保持只读**："review 一下这个 commit message"。

## 3 · 缺少必要输入

- **不在 git 仓库里** → 直接说明，不假装读到了约定。
- **暂存区和工作区都干净** → 没有可提交的东西，不为了产出而产出。
- **只有一个新增的 untracked 文件** → `git diff` 为空也必须读取该文件后才能描述；用户
  只请求草稿时不 stage，明确请求提交且范围清楚时只 stage 该文件。
- **全新仓库，只有一个 "Initial commit"** → 不发明仪式感：plain imperative，并明确告知
  未检测到约定，让用户自己定。
- **用户只说"感觉快了不少"，没有数字** → 消息里不得出现任何具体数字或百分比。
- **从子目录触发（如 `lib/Dialect/FIRRTL/`）** → 仍要找到仓库根的 CONTRIBUTING /
  AGENTS / CLAUDE，并识别 changed path 下适用的嵌套规则。使用从仓库根匹配的 pathspec，
  否则找不到会被误读成"没有成文约定"，转而去猜日志。Part 0 的 `git status` 和 diff
  命令不受影响，在任何子目录下都报告整个仓库。

## 4 · 外部依赖不可用

- **`git config --path --get commit.template` 未配置时退出码是 1** —— 这是"没有配置"，不是
  失败，不要当错误上报或中断流程。
- **没有 CONTRIBUTING / AGENTS / commitlint 配置** → 落到第 2 级证据（日志）。
- **规则位于 `.github/CONTRIBUTING.md`，或 changed path 下有嵌套 `AGENTS.md`**
  → 从子目录运行也能发现，并只把实际适用于 changed paths 的规则纳入 profile。
- **CONTRIBUTING 只规定 Conventional prefix，正文格式没有说明**
  → prefix 采用文档规则，body depth、段落和换行继续从可比 history 推断。
- **浅克隆，或日志只有一两条** → 日志给不出模式，落回文档规则或 plain imperative。
- **无网络** → 全流程不得需要联网。上游约定靠用户告知，不靠抓取。

## 5 · 重复运行

- 连续触发两次不得产生两个提交。第一次已经成功且没有剩余改动时，第二次只报告状态，
  不得 amend/reword；只有明确要求修改已识别的 message 时才走 rewrite 路径。
- 已经去掉的 trailer，重跑不得又加回来。
- **删 trailer 时暂存区已经有下一个提交的内容** → 必须用 `git commit --amend --only`，
  裸 `--amend` 会把暂存内容一并并进上一个提交。改完用 `git show --stat HEAD` 确认文件
  列表没变。
- Part 0 和 Part 2 的命令全部只读，重复执行安全。

## 6 · 输出格式与隐私

- 每一行不超过仓库规定的宽度（本仓库 80，含 body 与 footer）。
- 提交前检查完整草稿的真实换行；提交后用 `git show -s --format='%B' HEAD` 读回，确认
  Git 中保存的 subject、空行、body 段落和 footer 与草稿一致。
- 遵守 repository profile；在本仓库中使用祈使语气，subject 末尾无句号，并在 subject
  与 body 之间留空行。
- 不给 agent 自己加 `Co-Authored-By`；仓库要求的 `Signed-off-by:` 照加。
- diff 里出现的 token、内网地址、客户名和个人信息，不得被抄进 commit message；如果
  它们本身将进入 commit，停止提交并明确提示风险。
