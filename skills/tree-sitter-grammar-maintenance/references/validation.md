# 验证案例

`docs/authoring.md` §5 要求的六类案例，针对 `tree-sitter-grammar-maintenance`。这是维护
材料，不是运行时指令，`SKILL.md` 不引用它。

验证分两层：

- **`scripts/test_probe.py`** —— `probe.py` 的确定性回归测试，只用标准库，不需要
  tree-sitter。夹具是从 tree-sitter 0.27.0 抓下来的真实 CLI 输出，被测的不变量直接读随 skill
  发布的 `assets/invariants/mlir.json`，不是副本。改 `probe.py` 或任何 spec 之后必须跑；CI 也
  会跑。见第 7 节。
- **下面的行为案例** —— 没有自动化的 model-eval harness。行为变更合入前，在一个真实的
  parser 仓库里把相关案例走一遍，记录读过的契约条款、落层结论、最终建议，以及动过 parser
  仓库的哪些文件。改动 Part 2 的硬规则、Part 4 的落层表、Part 9 的边界，或者
  「What writes」表时，至少重走第 1、2、4、6 节里受影响的案例。

## 1 · 典型触发

- **"帮我检查一下 tree-sitter-mlir 的解析有没有被 fallback 遮掩的问题"**
  → 先读 `docs/ARCHITECTURE.md` 和审计记录的当前状态块；用 `probe.py provenance` 核对 CLI
  与锁文件、记下 reference parser 的来源；确认 `src/` 能从 grammar 原样重新生成；跑现有 gate
  建立基线。然后按 skeleton → corpus → probe 的顺序跑。命中项按 mode 聚类，逐个 mode 落层
  之后才给结论，不直接提出 grammar 改动。
- **"这个 corpus case 的期望树对不对"**
  → 拿输入和期望树互相校验，不看它是否通过 `tree-sitter test`。通过本身不是证据。
- **"我改了 grammar，帮我看看有没有副作用"**
  → 改动前后各跑一次 `census`（写到 `mktemp -d` 的目录），`diff` 之后逐条说明每类计数变化
  和每个"计数相同、形状不同"的文件为什么应该变。只跑 `npm run test` 绿了就说没问题，属于
  未完成。
- **"某某方言的这个语法解析得很难看，加个规则支持一下"**
  → 落层。落在第二行且外层边界完好时，回答是"这是契约内的取舍，不改"，并说明理由；要改
  必须过 Part 5 的四个条件，包含未知 `test.*` dialect 的 fallback 回归用例。
- **"帮 tree-sitter-mlir 加上对 XXX 语法的支持"**
  → 这是**应该**触发的。通用路径与专用规则的取舍正是在这种请求里被决定的，也正是通用
  准绳被悄悄削弱的地方。先跑通用路径看它丢了什么，再决定是否需要专用规则。
- **"ARCHITECTURE.md 是不是过时了"**
  → 按 `references/docs-contract.md` 和 `references/mlir.md` 的核对表逐条跑命令，报告每条
  声明的实测值和检查日期；区分过时、有意保留和措辞含糊三种情况。
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
  → 不要凭空审计，也不要现场发明一套原则。走 `references/onboarding.md`，先和维护者一起把
  契约写出来，并说明在此之前只能做 ERROR/MISSING 和 corpus 自洽层面的检查。
- **没有 `assets/invariants/<language>.json`** —— 只有 `npm run test:examples` 的
  ERROR/MISSING 扫描可用；corpus 自洽检查也要 spec 里的一条 `corpus_invariants` 模式。
  说明覆盖面因此受限；要补 spec，走 onboarding 的第 6 步，先确认它在正确输入上不报，
  不要临时编造未经验证的不变量当作结论依据。
- **没有给 reference parser 路径** —— 用户本次说过就用；审计记录里有绝对路径就复用；否则
  问，并等待回答。**不搜索 `PATH`，不试常见名字**，不用 LLVM 的 `opt`。审计记录里只有目录、
  没有可执行文件路径时，照样要问。
- **用户只给了一段报错，没给输入** —— 先要最小输入，不要猜。

## 4 · 外部工具或数据源不可用

- **用户没有 reference parser** —— 其余检查照常进行。报告里写明对比没有运行、覆盖面因此
  缩小；不要把"没跑"说成"跑过没问题"。
- **声明的工具通不过自检**（比如给的是 `opt`）—— `skeleton` 以 2 退出。回去问用户要正确
  的工具，不换一个自己找的。
- **所有文件都被 reference parser 拒收** —— `skeleton` 打印 `NOTHING WAS COMPARED` 并以 2
  退出。这不是通过：放宽文件选择，或在报告里写明对比没有运行。
- **CLI 与锁文件版本不一致** —— `provenance` 以 1 退出并标出 MISMATCH。先问用户再跑
  `npm ci`（会联网改写 `node_modules`）。已经踩过的坑：npm 可能拦截 `tree-sitter-cli` 的
  install script，装出一个没有二进制的包，`npm ci` 不等于环境就绪。修完重跑 `provenance`；
  仍然跑不起来，补装 release 二进制之前再问一次，并说明下载地址。
- **仓库没有 `package-lock.json`**（`tree-sitter-tablegen` 当前如此）—— `provenance` 会报告
  `package.json` 里声明的版本范围。写明实际测量用的版本，并说明 CI 取的是该范围内的最新版。
- **`npx` 无法联网** —— 用仓库内已安装的 CLI，不要静默换版本。
- **`src/` 与 `grammar.js` 不一致** —— 在重新生成的 parser 上测量，报告里说明 `src/` 已经
  偏离提交；不要在过时的产物上下结论。
- **`probe.py` 报 parse 输出对不上、有无法识别的行，或同一文件出现两棵树** —— 以 2 退出是
  故意的：CLI 的输出格式变了。先在新版本下重抓 `test_probe.py` 的夹具，不要绕过这个错误
  继续统计。

## 5 · 重复运行是否安全

- `skeleton`、`corpus`、`probe`、`provenance` 只读 parser 仓库；`census` 只写 `--out` 指定的
  路径，放在临时目录。重复运行安全。
- 会写入的动作只有 `SKILL.md`「What writes, and what needs a yes first」表里列出的那些；
  `npm ci` 和下载二进制每次都要先问。
- 同一仓库状态下重复运行必须给出相同结论。结论飘动说明不变量本身不稳定，应先修探针。
  `--limit` 取的是均匀分布的确定子集，两次运行比较的是同一批文件。
- 已经确认并修复过的问题再次运行时，应当报告为已解决，不重复开同样的建议。
- 本 skill 不提交、不推送；是否提交由用户决定。

## 6 · 输出与边界

- **命中必须区分"候选"和"已确认"。** 探针输出是候选；只有给出最小复现并完成落层之后
  才能称为缺陷。同一个 mode 下的大量命中是一个候选，不是很多个。
- **报告必须写明每个结论的证据来源**：哪条契约条款、哪个探针、哪个最小输入，以及
  `provenance` 打出的工具链和 reference parser。
- **报告必须写明覆盖面**：哪些证据线跑了、哪些没跑、reference parser 拒收了多少文件。
- **不得为了让结论好看而修改 `examples/`、corpus 期望树或契约文档。** 期望树只能在
  grammar 修好之后重新生成并人工阅读。
- **不得修改契约文档中的原则条款。** 表格数据过时可以更新；原则要改，必须作为独立
  决定交给维护者。
- **不得在 parser 仓库留下任何工具、报告或基线文件**；审计记录只放在被忽略的目录里，
  顶部是每轮重写的当前状态，下面按轮追加。
- **不得提议重建已被审计淘汰的机制**（ledger、manifest、attestation、常驻 oracle、
  逐文件 AST 公证）。被问到时说明它们为什么被淘汰，并给出有边界的替代方案。
- 本 skill 不涉及凭据、私有数据或外部写操作；报告中引用的都是公开仓库内容。未入库的
  开发计划只作为维护者的本地笔记，内容不引用进 commit 或 PR。

## 7 · `probe.py` 的确定性回归

```bash
python3 scripts/test_probe.py
```

每一条测试都对应一次真实踩过的错误，删测试之前先确认那个错误不会再出现：

| 测试覆盖的行为 | 出错时的后果 |
| --- | --- |
| 有解析错误的文件，树保持完整，第一个错误从 CLI 的摘要行补回 | 整棵树被一个 `MISSING` 节点替换，文件里每个绑定都成了假命中，census 只剩 `{'MISSING': 1}` |
| 摘要行对不上文件、出现无法识别的行、一段输出里有两棵树时拒绝继续 | 静默地把错误归到别的文件，或者丢掉一棵树 |
| 引号里的括号仍然是 token | 树的嵌套被打乱 |
| `%0:2` 按两个结果计数 | generic form 把 `%a, %b` 合成一组，按节点数计数会误报"grammar 比 reference 多" |
| `ceiling` 只标记 grammar 多于 reference 的方向 | 两个方向都当噪声时，grammar 凭空生成的 region 被放过 |
| 带 region 的节点在 region 关闭之后仍然检查 | 整个节点被豁免，吞掉后续绑定的 body 看不见 |
| `%b = %y)` 这种操作数赋值不算绑定行 | 换行的 `iter_args`、`gpu.launch` 表头产生假命中 |
| 命中按 mode 聚类，示例先覆盖不同文件 | 一个缺陷的上万条命中被当成上万个问题 |
| census 在计数相同、形状不同时仍然报告 | span 或父节点变了的改动被报告成 inert |
| `--limit` 均匀抽样；声明的工具必须通过 spec 的自检；没声明时拒绝运行；一个文件都没比较时以 2 退出 | 只抽到少数几个目录；在一个没人选过的二进制上得出看似权威的数字；什么都没比较却报告通过 |
| `provenance` 标出 CLI 与锁文件不一致，没有锁文件时说明版本范围 | 在 CI 不会构建的 parser 上测量 |

tree-sitter CLI 升级后，先在新版本下重抓夹具里的 parse 输出，再跑这组测试：输出格式的
变化应该先在这里暴露，而不是在一次审计里悄悄出错。
