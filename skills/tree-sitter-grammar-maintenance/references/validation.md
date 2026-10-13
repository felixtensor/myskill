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
  和每个"计数相同、形状不同"的文件为什么应该变。有 reference parser 时，再各存一次
  `skeleton --out` 并 `diff`：文件只能离 reference 更近；变远、新出现高于 reference、或
  reference 一侧变了，都要给出解释。corpus 有重新生成的用例时跑 `corpus --before HEAD`。
  改动让同一个节点多了一条生成路径（alias、外部 token、另一条规则）时，查有没有 `:cst`
  用例比对两条路径——具名节点相同不等于树相同。只跑 `npm run test` 绿了就说没问题，
  属于未完成。
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
- **"这里有歧义，加个 conflict 吧"**
  → 新增 conflict 不是禁区，但也不能直接加。先读 `generate` 报的冲突：符号序列、
  lookahead、各解读。再按 `references/tree-sitter-mechanics.md` 的阶梯逐级判断：
  歧义是语法自己造出来的，就重构；下一个 token 就能定，用静态 prec；要看更远的
  token，声明 conflict；两种读法都能走完，再加 `prec.dynamic`，并用 corpus 用例钉住
  胜出的读法；fuzz 不过或者要切边界，才进 lexer。加完跑
  `probe.py conflicts --only RULE --runtime --flip --static`，附上 accepted-conflict
  记录。阶梯指向的级别和用户要的不一样时，两个方案都量，交给用户选。三种偏差：只因为
  conflict 数会增加就拒绝；没有记录就加上；不说一声就按阶梯改掉用户要的做法。
- **"现有的 conflict 都有必要吗" / "ARCHITECTURE.md 里的 conflict 表对不对"**
  → 跑 `probe.py conflicts`。报 UNNECESSARY 的提出删除；文档写的原因与 `generate`
  报的符号序列逐条对照。加 `--flip`，把移动了示例、却没有 corpus 用例钉住的一侧
  当作线索落层：当前读法正确的补用例，读法有问题的按 Part 4 落层。加 `--static`，
  报 REPLACEABLE 的声明作为可以换成静态 prec 的线索提出。

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
  的工具，不换一个自己找的。审计记录里登记了另一个路径时也一样：问用户要不要改用它，
  不自己换过去。
- **同一个 grammar 有多个 checkout**（改动放在 worktree 里、对照组、并行的 agent）——
  `tree-sitter parse` 按扩展名在它知道的所有 grammar 里挑，包括 CLI 配置
  `parser-directories` 下的其他 checkout；在 worktree 里它用了主 checkout 的 grammar，
  加 `--grammar-path`、换独立的 `TREE_SITTER_LIBDIR` 都没用。`probe.py` 先
  `tree-sitter build` 出当前 checkout 的解析器、按 `src/` 内容缓存在临时目录，再用
  `parse --lib-path` 解析；手工解析也要这么做。之前的测量没出错，是因为先跑了
  `tree-sitter test`，它编译的是当前目录，后面的 `parse` 凭文件时间碰巧没有重编。
- **所有文件都被 reference parser 拒收** —— `skeleton` 打印 `NOTHING WAS COMPARED` 并以 2
  退出。这不是通过：放宽文件选择，或在报告里写明对比没有运行。
- **CLI 与锁文件版本不一致** —— `provenance` 以 1 退出并标出 MISMATCH。先问用户再跑
  `npm ci`（会联网改写 `node_modules`）。已经踩过的坑：npm 可能拦截 `tree-sitter-cli` 的
  install script，装出一个没有二进制的包，`npm ci` 不等于环境就绪。修完重跑 `provenance`；
  仍然跑不起来，补装 release 二进制之前再问一次，并说明下载地址。
- **CI 装的 CLI 与锁文件不一致** —— `provenance` 的「CLI in CI」一行标出 MISMATCH 并以 1
  退出。本地数字没问题，但 CI 的 fuzz 可能在正确的树上失败（旧 CLI 把 `:cst` 用例当
  S 表达式比）。写死的版本号即使一致也会提示「手工同步」：依赖机器人只升锁文件，不改
  workflow。改成从锁文件读版本是维护者的决定，报告里提出即可。
- **仓库没有 `package-lock.json`**（`tree-sitter-tablegen` 当前如此）—— `provenance` 会报告
  `package.json` 里声明的版本范围。写明实际测量用的版本，并说明 CI 取的是该范围内的最新版。
- **`npx` 无法联网** —— 用仓库内已安装的 CLI，不要静默换版本。`probe.py` 本来就优先直接调用
  `node_modules/.bin/tree-sitter`，只有找不到时才退回 npx。
- **在 Windows 上运行** —— CLI 和工具都通过 `shutil.which` 查找，能找到 npm 装的 `.cmd` 包装；
  工具输出一律按 UTF-8 解码，不走系统代码页。测试里的假工具在 Windows 上是 `.cmd` 包装加 Python
  脚本，CI 在 Linux 和 Windows 上都跑。
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
  `--limit` 取的是均匀分布的确定子集，两次运行比较的是同一批文件；`--jobs` 并行时，结果和
  顺序都与 `--jobs 1` 完全相同。
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
- parser 仓库也可能含有私有源码、计划或路径。对外报告只使用获准公开的证据，
  不把本地审计记录或未入库计划抄进 commit 或 PR。

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
| 不绑定结果的 generic 操作被 custom body 吞掉时仍然报告；region 里面的同类行不报 | 整个操作从树里消失：绑定检查只看 `%x =` 行，skeleton 的 operation 上限又把"数得少"当作预期，没有任何检查报出来 |
| corpus 检查按绑定的名字计数（`%a, %b` 算两个、`%x:2` 算一个），与期望树里的节点数精确比较 | 一行绑定多个名字，会掩盖同一用例里别处丢掉的绑定——`memref.extract_strided_metadata` 就是这样漏掉的 |
| `%b = %y)` 这种操作数赋值不算绑定行 | 换行的 `iter_args`、`gpu.launch` 表头产生假命中 |
| 命中按 mode 聚类，示例先覆盖不同文件 | 一个缺陷的上万条命中被当成上万个问题 |
| 多进程解析与单进程的结果、顺序完全相同；迭代版 `walk` 与递归版顺序一致 | 并行后命中顺序或计数悄悄变了，前后两次运行没法比 |
| 优先直接调用仓库的 `node_modules/.bin/tree-sitter`，找不到才退回 npx；spec 指定的 `cli` 优先 | 每批解析都多花 0.3 秒启动 npm |
| 工具输出按 UTF-8 解码；skill 摘要不受 CRLF 检出影响 | Windows 上带非 ASCII 字符串属性的文件解码出错；同一个提交在两个平台上摘要不同 |
| 两次 skeleton 运行的 `diff` 标出变远、新高于 reference 和 reference 一侧变动的文件；census 与 skeleton 的结果不能互相 `diff` | 修复是否真的让文件更接近 reference，只能靠肉眼比较总数；generic 路径被改动也没人发现 |
| `probe`、`census` 走完整命令：有命中时退出码为 1、命中归在正确的不变量和 mode 下、`--show 0` 只留汇总行；census 输出带 `kind` 和 `shapes`，能直接 `diff` | 这四处植入的 bug，之前的测试一个都没发现：有命中却报干净、命中归错不变量、漏掉第一个文件之后的命中、census 悄悄退化成只比计数 |
| census 在计数相同、形状不同时仍然报告 | span 或父节点变了的改动被报告成 inert |
| `--limit` 均匀抽样；声明的工具必须通过 spec 的自检；没声明时拒绝运行；一个文件都没比较时以 2 退出 | 只抽到少数几个目录；在一个没人选过的二进制上得出看似权威的数字；什么都没比较却报告通过 |
| `provenance` 标出 CLI 与锁文件不一致，没有锁文件时说明版本范围 | 在 CI 不会构建的 parser 上测量 |
| `provenance` 读 `.github` 下 workflow 和 composite action 的 CLI 输入：写死且不一致报 MISMATCH，写死但一致提示手工同步，运行时计算的指出在哪一行 | CI 固定 0.26.12、锁文件是 0.27.0，持续了两次版本升级；CI 的 fuzz 在一个正确的 `:cst` 用例上失败才暴露 |
| census `diff` 按「哪些类型变了」给文件分组 | 482 个变动文件里只有一个少了 region，淹没在平铺列表里；两个 agent 各自手写了按类型归因的脚本 |
| `corpus --before REV` 按内部节点类型给变动用例分组，输入或叶子顺序变了的单独标出；比叶子顺序而不是前序 | 44 个重新生成的用例只能靠手写脚本核对，第一版脚本按前序比较，把每个正确用例都标成违规 |
| 每个 checkout 用自己 `src/` 编出的解析器：`build` 一次、按内容缓存、`parse --lib-path` | 在 worktree 里量合并后的 main，结果和修复前一模一样——量的是主 checkout 的旧解析器 |
| `:cst` 用例按 CST 行格式计数；`--before` 对比时单独标出 | `:cst` 用例被当成 S 表达式数，报成少了一个绑定 |
| 绑定行正则排除 `=` 后接数字、`max`、`min` 的行 | 换行的 `affine.for` 下界 `%i = max …` 被当成绑定，main 上专门钉这个形状的用例被报成缺陷 |
| `conflicts` 逐个去掉声明，在临时目录里从 `grammar.json` 重新 generate，报出符号序列、lookahead、各解读和 `generate` 接受的静态解法；去掉后仍能 generate 的报 UNNECESSARY，以 1 退出 | 文档里的冲突计数靠 `sed` 匹配 `conflicts: ($) =>`，tree-sitter-tablegen 写的是 `conflicts: $ =>`，数出 0 个，实际有 2 个；「每个 conflict 都必不可少」这类声明也没有任何检查 |
| `generate` 非零退出、摘要里又没有错误时拒绝继续 | CLI 一崩溃，每个声明都被报成多余 |
| `--runtime` 把 `-d` 放在文件名之后，按 `new_parse` 把每次选择归到文件，再按决定方式分组 | `parse -d FILE` 在 0.26 和 0.27 里会把文件名当成 debug 模式直接报错，mechanics 原来写的正是这个顺序 |
| `--flip` 偏向一侧后只有示例变化时报 UNPINNED，以 1 退出；有 corpus 用例跟着变化时报 pinned | tree-sitter-tablegen 的 `foreach i = 1 in` 由符号顺序决定，调换两条规则的位置树就变，原有检查都发现不了 |
| 仓库里没有可用的 CLI 时以 2 退出 | 什么都没测，却报告干净 |
| 一个样例、一个 corpus 用例都没解析到时以 2 退出 | `--flip` 对每一侧都报没有移动、以 0 退出，读起来像所有 conflict 都是局部的 |
| 先 generate 未修改的 grammar，生成不了就以 2 退出 | 换了 CLI 版本后基线本身就生成不了，每个声明都被同一个无关的冲突「解释」 |
| 「钉住」按 `tree-sitter test` 的方式比较：不比 range，期望树没有字段就不比字段，`:error` 用例不算 | 只挪了 span、或者只挪了 `:error` 用例的翻转被报成已被 corpus 钉住，其实测试照样通过 |
| 输出只用 ASCII | 中日韩 Windows 上重定向输出时，`•` 在本地代码页里编码失败，第一个冲突就崩溃 |
| `--static` 对每个必要的声明，把 `generate` 给出的每种静态解法换上去，报能否生成、哪些输入变化，不能生成的给出下一个冲突；只给线索，不影响退出码 | 第二轮走查要回答「能不能换成静态 prec」时只能自己写脚本 import `probe.py`；`--flip` 把权重加在规则上，回答不了 |
| 不认识的生成错误照常报告；`src/` 里的子目录整个复制；相对路径的 `--cli` 按启动目录解析 | traceback 以 1 退出被当成发现；`src/scanner/` 目录让复制崩溃；生成在临时目录里跑，相对路径指向别处 |

tree-sitter CLI 升级后，先在新版本下重抓夹具里的 parse 输出，再跑这组测试：输出格式的
变化应该先在这里暴露，而不是在一次审计里悄悄出错。

## 8 · 行为验证的范围与维护结论

过去的独立走查验证过审计、方言取舍、工具自检失败和修复副作用案例；后续的
conflict 走查显式指定了 skill，因此只能作为行为证据，不能作为自动触发证据。
逐次耗时、工具调用数、项目身份、分支和 issue 记录不作为技能规则保留。

保留的回归重点：

- 工具先按用户声明或审计记录选择，再做自检，不在自检失败后悄悄换工具。
- 具名节点相同不证明完整 CST 相同；替代构造路径要用 `:cst` 对照。
- 两种隐藏规则给出相同树时，先检查是否应重构，而不是默认保留 conflict。
- 增量解析和全文件解析是不同证据；对照 checkout 必须隔离构建缓存。
- 审计记录无法写入主 checkout 时，保存在允许的位置并说明待合并的记录。

本次维护前后按第 1–6 节逐项核对了入口及迁移后的参考文件。测量命令、落层依据、
四个专用规则条件和授权边界均可沿入口找到；其他语言不会借用 MLIR 的 spec 或 gate。
这是指令走查，没有执行真实 parser 审计，也没有重跑独立 agent 触发测试。
