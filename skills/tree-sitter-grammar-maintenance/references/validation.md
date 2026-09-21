# 验证案例

`docs/authoring.md` §5 要求的六类案例，针对 `tree-sitter-grammar-maintenance`。没有自动化
model-eval harness；`scripts/validate_skills.py` 只检查结构，不能证明 agent 的判断正确。
行为变更合入前，在一个真实的 parser 仓库里走相关案例，记录读过的契约条款、落层结论、
最终建议，以及是否动过 parser 仓库的文件。这是维护材料，不是运行时指令，`SKILL.md`
不引用它。改动 Part 1 的硬规则、Part 4 的落层表或 Part 8 的边界时，至少重跑第 1、2、
4、6 节中受影响的案例。

## 1 · 典型触发

- **"帮我检查一下 tree-sitter-mlir 的解析有没有被 fallback 遮掩的问题"**
  → 先读 `docs/ARCHITECTURE.md`，核对 CLI 版本与 `src/parser.c` 新鲜度，跑一遍现有 gate
  建立基线，再按 corpus → invariants 的顺序跑探针。命中项逐条落层后才给结论，不直接
  提出 grammar 改动。
- **"这个 corpus case 的期望树对不对"**
  → 拿输入和期望树互相校验，不看它是否通过 `tree-sitter test`。通过本身不是证据。
- **"我改了 grammar，帮我看看有没有副作用"**
  → 改动前后各跑一次 `census`，`diff` 之后说明每一类被移动的节点为什么应该移动。
  只跑 `npm run test` 绿了就说没问题，属于未完成。
- **"某某方言的这个语法解析得很难看，加个规则支持一下"**
  → 落层。落 Layer 2 且外层边界完好时，回答是"这是契约内的取舍，不改"，并说明理由；
  要改必须过 Part 5 的四个条件，包含未知 `test.*` dialect 的 fallback 回归用例。
- **"帮 tree-sitter-mlir 加上对 XXX 语法的支持"**
  → 这是**应该**触发的。通用路径与专用规则的取舍正是在这种请求里被决定的，也正是通用
  准绳被悄悄削弱的地方。先跑通用路径看它丢了什么，再决定是否需要专用规则。
- **"ARCHITECTURE.md 是不是过时了"**
  → 按 `references/mlir.md` 的核对表逐条跑命令，报告每条声明的实测值和检查日期。
- **`tree-sitter test --update` 之后的 diff 很大**
  → 不批量接受。diff 大到读不完，说明改动太大，应当拆小。

## 2 · 容易误触发的相邻请求

不应进入本 skill 的完整流程：

- **"MLIR 的 affine.for 语义是什么"** —— 语言问题，直接回答，不跑探针。
- **"帮我给一门新语言写 tree-sitter grammar"** —— 从零创作不在范围内；只有在需要为它
  建立契约时才走 `references/onboarding.md`。
- **"帮我写 commit message"** —— 交给 `commit-style`。
- **"CI 挂了"** —— 先看是不是构建、依赖或 workflow 问题；确认是解析结果不对之后再进入
  本 skill。
- **任何非 tree-sitter 的 parser 仓库** —— 方法不适用，明确说明。

## 3 · 缺少必要输入

- **没有说是哪个仓库** —— 从当前工作目录推断；推断不出就问，不要默认 `tree-sitter-mlir`。
- **仓库没有契约文档**（`tree-sitter-tablegen`、`tree-sitter-pdll` 当前如此）
  → 不要凭空审计，也不要现场发明一套原则。走 Part 7，先和维护者一起把契约写出来，
  并说明在此之前只能做 ERROR/MISSING 层面的检查。
- **没有 `assets/invariants/<language>.json`** —— 只跑 `no_node` 和 corpus 自洽检查，
  并说明覆盖面因此受限；不要临时编造未经验证的不变量当作结论依据。
- **用户只给了一段报错，没给输入** —— 先要最小输入，不要猜。

## 4 · 外部工具或数据源不可用

- **`mlir-opt` 未安装** —— 整套审计照常进行。在报告里写明未使用 reference compiler，
  不要把"没跑"说成"跑过没问题"。装了就用，但只用 §"Reference compiler" 允许的两种用法。
- **`npm ci` 之后 CLI 反而不可用** —— 已经踩过：npm 可能拦截 `tree-sitter-cli` 的
  install script，装出一个没有二进制的包。`npm ci` 不等于环境就绪，必须紧接着核对
  `npx tree-sitter --version` 真的能跑；不能跑就补装二进制，并在记录里写明最终版本。
- **`node_modules` 里的 CLI 版本与 `package-lock.json` 不一致** —— 先 `npm ci`；无法
  安装时，明确记录实际使用的版本，并说明结论受此限制。
- **`npx` 无法联网** —— 用仓库内已安装的 CLI，不要静默换版本。
- **`src/parser.c` 与 `grammar.js` 不一致** —— 先重新生成并重跑 gate，再归因；不要
  在 stale artifact 上下结论。
- **探针输出的 tree 数与输入文件数对不上** —— 脚本会直接报错退出。减小 `--batch` 或
  检查 CLI 版本，不要忽略这个错误继续统计。

## 5 · 重复运行是否安全

- 全部探针命令只读 parser 仓库，不写入；`census` 只写 `--out` 指定的路径，默认放在
  临时目录。重复运行安全。
- 同一仓库状态下重复运行必须给出相同结论。结论飘动说明不变量本身不稳定，应先修探针。
- 已经确认并修复过的问题再次运行时，应当报告为已解决，不重复开同样的建议。
- 本 skill 自身不创建分支、不提交、不推送、不修改 parser 仓库的任何文件；产出是最小
  复现、落层结论和改动建议。实际改动由用户决定是否执行。

## 6 · 输出与边界

- **命中必须区分"候选"和"已确认"。** 探针输出是候选；只有给出最小复现并完成落层之后
  才能称为缺陷。
- **报告必须写明每个结论的证据来源**：哪条契约条款、哪个探针、哪个最小输入。
- **不得为了让结论好看而修改 `examples/`、corpus 期望树或契约文档。** 期望树只能在
  grammar 修好之后重新生成并人工阅读。
- **不得修改契约文档中的原则条款。** 表格数据过时可以更新；原则要改，必须作为独立
  决定交给维护者。
- **不得在 parser 仓库留下任何工具、报告或台账文件。**
- **不得提议重建已被审计淘汰的机制**（ledger、manifest、attestation、常驻 oracle、
  逐文件 AST 公证）。被问到时说明它们为什么被淘汰，并给出有边界的替代方案。
- 本 skill 不涉及凭据、私有数据或外部写操作；报告中引用的都是公开仓库内容。
