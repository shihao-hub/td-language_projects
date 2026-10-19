# GLOBAL.md
<!-- Global AI Agent Rules & Engineering Invariants -->
<!-- Managed by language_projects repo. Synchronized across Codex, Claude Code, OpenCode, Pi, DSH, and Antigravity. -->

## 一、通用基线约束（跨项目与跨 Agent 通用规范）

### 1. 交互与语言规范
- **AI 回复语言**：所有 AI 对话回复必须使用中文。
- **AI 思维链语言（仅 DeepSeek 模型）**：当驱动当前 agent 的模型属于 DeepSeek 系列时（即系统提示人设段中的 `powered by <model> model` 处模型名以 `deepseek` 开头），内部推理（thinking / reasoning）与工具调用前的自我规划以简体中文为主体叙述，不因输入语言或英文技术文档而整段切换为英文；专有名词、技术术语、公式、代码标识符、文件路径、报错信息保留英文原文，并允许英文短语嵌入（术语锚定、自我校验）。非 DeepSeek 模型不受此条约束。
- **设计文档语言**：所有 spec / plan 类设计文档（`requirements.md`、`design.md`、`tasks.md`、`plans/01-plan.md` 等）必须使用中文描述。
- **代码命名与注释**：代码注释推荐使用中文；变量名、函数名、类名等代码标识符一律使用英文。
- **专有名词保留**：专业术语（API、HTTP、TypeScript、React 等）、框架名称、命令行指令、文件路径保留英文原文。
- **任务完成交互**：代码修改完成后，向用户展示改动摘要，并给出可直接在 PowerShell 下执行的 git commit 命令建议（需包含必要的 `cd` 路径切换命令）。

### 2. Windows 终端执行安全规范（通用条件约束）
当且仅当处于 Windows 宿主环境并通过终端执行命令行时（PowerShell 5.1 / pwsh 7，或 Git Bash 等 POSIX shell），所有 AI Agent（包括 Codex、Claude Code、OpenCode、Pi、DeepSeek Harness、Antigravity 等）**必须遵循以下跨 Agent 通用安全规范**；分条自带适用范围标注，未标注者视为对 PowerShell 与 Git Bash 均适用：

1. **进程无状态与工作目录感知**：
   - Windows 下 Agent 命令行执行通常为**无状态的独立子进程**（各命令框架每次执行均拉起独立进程）；
   - 避免假设前一次命令的 `cd` 状态会持久保留到后续轮次；跨目录操作应优先依赖 Agent 工具自带的 `workdir` / `cwd` 参数，或在单次调用内完成路径切换与命令执行。
2. **版本感知与语句连接（仅 PowerShell 适用；pwsh 7 vs PowerShell 5.1）**：
   - **PowerShell 7+（`pwsh`）**：原生支持 `&&` 与 `||` 管道链，允许直接使用。
   - **Windows PowerShell 5.1（`powershell.exe`）**：
     - 不支持 `&&` / `||`（会抛出语句分隔符语法错误）；
     - 禁止盲目使用分号 `;` 串联前后强依赖的命令（防止前序失败导致后续命令在错误目录静默执行）；必须拆分为单步独立执行，或使用短路逻辑：
       ```powershell
       command1; if ($?) { command2 }
       ```
3. **文件 I/O 抽象与编码安全（防 BOM 绝对红线）**：
   - **优先走 Agent 文件工具（全终端适用）**：凡涉及源码或配置的查看与编辑，一律优先使用 Agent 宿主提供的专用文件读写工具（File System Tools），杜绝通过命令行终端回显或流重定向读写大文件。
   - 以下编码防御细则**仅针对 PowerShell**（Git Bash 等 POSIX shell 不适用）：
     - **终端读取防御**：若必须通过终端读取文件，禁止裸调 `Get-Content`（5.1 默认按系统 ANSI/GBK 解析导致中文字符首轮乱码），显式带编码：
       ```powershell
       Get-Content -Encoding UTF8 "<filepath>"
       ```
     - **终端写入防御（零容忍 BOM 污染）**：
       - **全面封杀原生重定向与落盘 cmdlet**：严禁在 PowerShell 终端使用任何 `>`、`>>`、`Out-File`、`Set-Content`、`Add-Content` 落盘代码或配置（5.1 下默认强制带 BOM，无论参数为何一律禁止）；
       - **终端落盘唯一合规路径**：首选单文件 Python 脚本（`uv run`，默认纯正无 BOM UTF-8）；确需 PowerShell 单行写入时，**严禁裸用 `[System.Text.Encoding]::UTF8`**，必须显式传递 `$false`：
         ```powershell
         [System.IO.File]::WriteAllText("<filepath>", $content, [System.Text.UTF8Encoding]::new($false))
         ```
     - **严格配置写后必检（Post-Write Invariant）**：
       凡创建或修改 Zed、VSCode、Vite、Cargo、Rust 等 JSON/JSONC/TOML/YAML 严格格式配置文件，**落盘后必须显式自检**：
       1. 检查文件头 3 字节，确保绝不含 `EF BB BF`（BOM）；
       2. 执行语法解析器校验，确保无尾逗号（trailing comma）等语法硬伤；
       未通过自检严禁直接宣布完成交付。
     - **控制台流编码保障**：调用外部 CLI（如 git/go/python）并需捕获中文输出时，显式统一当前会话编码流（控制台流编码与 BOM 无关，不受上一条限制）：
       ```powershell
       [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8
       ```
4. **命令原子化与跨平台兜底（全终端适用）**：
   - 终端仅执行确定性的单条原生命令；禁止将 Linux 专有写法盲目移植到非 POSIX 环境（如 PowerShell 下带 Linux 参数的 `curl`、`export`、`rm -rf`）。
   - 凡涉及复杂文本流提取（正则、awk/sed）或多步骤依赖任务，**严禁在终端拼接复杂脆弱的管道**：
     - **首选**：编写单文件 Python 脚本，以 `uv run` 驱动；
     - **备选（PowerShell 下调起 Git Bash）**：若需直接利用 POSIX 工具链，动态定位并校验 Git Bash 后再执行，严禁硬编码盘符：
       ```powershell
       $bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
       if (-not $bash) { $git = (Get-Command git -ErrorAction SilentlyContinue).Source; if ($git) { $root = Split-Path (Split-Path $git -Parent) -Parent; foreach ($rel in 'bin\bash.exe', 'usr\bin\bash.exe', '..\usr\bin\bash.exe') { $c = Join-Path $root $rel; if (Test-Path $c) { $bash = $c; break } } } }
       if (-not ($bash -and (Test-Path $bash))) { throw '未找到 Git Bash，改用 uv run Python 单文件脚本' }
       & $bash -c '<unix-command>'
       ```

### 3. 文件操作安全与命令防御（强约束）
- **写前必读（防盲目覆写）**：当用户给出目标文件路径时，必须先探测该文件是否存在及当前职责（禁止未查看即直接 `Overwrite=True` 覆写），尤其总控索引/草稿文件需按规范追加条目，严禁冲掉已有内容；
- **删前必核（防误删历史资产）**：删除任何疑似“临时/多余”文件前，严禁凭短期记忆臆断，必须通过 `git status` / `git log` 严格核实身世；已入库文件绝不可擅自清理；
- **文件名非法字符防御（防嵌套子目录）**：创建文档或代码文件时，文件名内部严禁包含 `/`、`\` 等路径分隔符（如 `(Python/TS)` 会被系统判定为多层子目录），所有分割一律用短横线 `-` 或下划线 `_`；
- **工作区防污染（禁止根目录散落探针）**：严禁在项目根目录下平铺创建与项目本身无关的临时排查脚本、逆向探针、解密测试或中间转储文件。

### 4. 资源清理与 Token 经济
- **测试资源用后即清**：chrome-devtools 等工具打开的浏览器测试页、临时起的开发服务、后台子进程，验证完成后必须立即关闭或终止，不得遗留；确需保留时必须向用户说明并获得明确同意。
  - *chrome-devtools 浏览器收尾*：其专属 Chrome 的最后一个 `about:blank` 标签页 MCP 关不掉（属启动初始页，非残留错误），收尾标准为不残留任何窗口与后台进程，需按 user-data-dir 过滤整组终止：
    ```powershell
    Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*chrome-devtools-mcp\chrome-profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    ```
- **数据密集型任务必须“脚本化”（Token 经济强约束）**：凡跨目录搜索、批量文件遍历、会话历史/日志/数据库检索、结果筛选去重统计等任务，一律先在代码层完成筛选、去重、统计、汇总（首选 `uv run` Python 单文件脚本；若终端确装有 `rg` 等流式搜索命令，亦可用单条命令等价完成；**严禁在仓根裸跑 `grep -r` 全递归**——大仓/monorepo 含子模块与构建大树（`node_modules`、`target` 等）时必然长时间卡死，检索须限定路径范围或改用 Agent 内置快速检索工具），只把摘要结论带回对话；**严禁**使用多轮工具调用把原始内容（搜索结果、文件正文、目录清单）逐批灌入模型上下文——**原因：上下文窗口是 AI 最稀缺资源，模型心算汇总易出错，代码层汇总确定、可复核、可重跑**。此类任务不使用 max / 高思考档模型。
- **临时探索脚本治理（Scratchpad Hygiene / 防随地落盘与文件膨胀）**：
  - **隔离落位（禁止根目录随地落盘）**：逆向分析、排查探针、解密提取等一次性/探索性脚本与转储文件，**严禁平铺散落在项目根目录或业务源码目录**；必须放入不参与版本管理的隔离区——首选系统临时目录（Windows `%TEMP%`、POSIX `/tmp`）；如放项目内，则仅限**已确认被忽略规则覆盖**的临时目录（如 `.scratch/`、`temp/`，使用前先核实其确被忽略，未覆盖则先补豁免或改用系统临时目录）；
  - **单文件就地复用（防步骤级文件泛滥）**：多步分析或探针验证时，一律在同一个脚本（如 `scratch/probe.py`）内就地修改覆盖迭代，**严禁每排查一个步骤/符号就新建一个文件**（杜绝 `find_1.py`、`inspect_2.py` 式文件垃圾堆）；
  - **闭环清理与沉淀边界**：排查验证结束后，一次性探索脚本与中间产物原则上必须随手清理，确保 `git status` 工作区干净；若脚本确属具备长期工程复用价值的工具，须重构规范后归入项目标准脚本目录（如 `scripts/`）并向用户明确说明。

### 5. 通用编码质量与后端防线
- **禁止 `SELECT *`**：任何 ORM 查询与手写 SQL 一律显式列出所需字段。
- **任务标记规范**：代码或文档注释中的 `sh-ai-todo`，若已完成请标记为 `sh-ai-todo[o]`。
- **PostgreSQL 规范**：数据库表尽量避免使用 JSONB；若业务必要使用，须在方案中说明理由，并在应用层或约束上限制字段最大容量。
- **凭证与密钥防线**：密钥 / 令牌 / 密码严禁写入代码、日志、提交内容或终端回显；读取外部凭据文件时保持只读，禁止将自产缓存 / 锁 / 临时文件落盘到任何外部程序或凭据所在目录。
- **Python (FastAPI + SQLAlchemy + Celery) 架构防线**：
  - **连接池保护**：严格避免数据库连接被长时间运行的后台任务或外部 I/O 阻塞持有，长任务应在执行前释放会话或采用短生命周期连接；
  - **ORM 变更审查**：SQLAlchemy 的 `BaseModel` 首次创建、增减字段或修改关联关系时，任务完成后需明确提示人工审阅，重点核查 N+1 查询风险与隐式级联操作（cascade）；
  - **异步任务分层**：Celery 应聚焦毫秒/秒级轻量异步任务；对于高吞吐、强流式或长耗时计算任务，应解耦至专用消息管道（如 Kafka）或独立 Worker 执行，避免阻塞 Celery 任务队列及持有数据库连接。

### 6. Python 模块结构规范（统一骨架）
单文件 Python 模块的元素按固定顺序组织；常量 / 开关集中置顶（打开即见），类与函数随后：

```text
PEP 723 内联元数据块（uv 单文件脚本）
module docstring
from __future__ imports（如有）
__all__ / 模块级 dunder（如有）
imports（stdlib → 第三方 → 本地，组间空行）
模块常量 / 开关（无依赖者集中置顶，打开即见）
类型别名 / 异常类
类定义 → 函数定义 → main() → __main__ guard
```

- **硬约束**：任何元素必须"先用先定义"（类体、默认参数、装饰器在定义时求值）；依赖其他定义才能构造的模块级常量（如引用处理类实例的注册表）不得机械上移；
- **开关 / 配置类纯字面量常量一律置顶**，不得散落在使用处；模块顶层不写可执行语句，引导性副作用（如控制台编码设置）收编为函数，在 `main()` 开头调用。

### 7. AOCI 仓库级认知协同规范（自适应条件约束）
当且仅当当前工作区/环境满足以下条件之一时（检测到 `aoci.txt`、根目录存在 AOCI 索引文件、或当前会话接入了 `aoci_*` 系列 MCP 工具），所有 Agent 必须遵循以下协同契约：
- **动态契约优先**：建立或恢复认知时，优先通过调用 `aoci_rules` 获取动态运行时契约，再通过 `aoci_overview` 建立系统全景；深层语法与协议手册位于 `~/.agents/references/aoci.protocol.md`（按需查阅，日常不全量注入上下文）。
- **按需加载（防上下文膨胀）**：未改动索引资产的纯读任务与日常局部小改动，严格豁免 AOCI 操作，杜绝无意义消耗上下文。
- **收尾必维（防漏维护）**：会话内一旦修改过 AOCI 纳管文件（架构配置、核心脚本、规范文档等），且已达到最终稳定状态后，任务收尾前必须且仅调用**一次** `aoci_maintain` 对齐索引；严禁边改边频繁调用，亦不可遗漏。
- **元数据提交隔离**：AOCI 维护产出的元数据文件变更（`aoci*.txt` 与 `.aoci/`）必须与业务代码拆分独立提交。

### 8. 子任务委托路由（只读外包优先）

**能力门禁（不满足即整节跳过）**：仅当**本会话工具列表中确实存在 `mcp__agy__research`** 时才适用本节；不具备时**一律不得委托**——不要读配置文件或探测 `agy` 可执行文件去"凑"能力，不要自建替代通道（如直接调 agy CLI），不要凭猜测调用 `mcp__agy__*`；直接改用 subagent 或自行执行，并**静默降级**（不报错、不声明"缺少 agy"、不写进结论）。挂载情况因 Agent 与 profile 而异且会变，一律以**本会话工具列表**为准，本文件不维护"谁已配置"清单。

**判定（已具备桥接时）**：接到任务先跑下表；命中「委托」列即把活派给 `mcp__agy__research`（agy 只读调研桥），不要自己逐步探索：

| 判据 | 委托 agy | 自己做 |
| :--- | :--- | :--- |
| 是否只读 | 调研 / 审计 / 诊断（不改文件） | 任何写入、编辑、提交、有副作用的命令 |
| 取证量 | 预计需 ≥10 次工具调用才能定论 | 1–2 次调用即可得 |
| 预期耗时 | ≥2 分钟的宽面任务（**通道选择见下**） | 秒级事实查询 |
| 交互性 | 一次问清、无需边看边判断 | 需多轮试探与即时决策 |

- **宽度换时间**：一条 prompt 只装一个板块，写明产出格式与范围，禁止"顺便看看"式开放提问；宽任务拆 2–3 个**并行**委托（agy 约 5.5s/回合，60 回合 ≈ 10 分钟，拆并行取最慢者）；
- **回读必抽验**：agy 产出当证据而非事实，关键数字与定性判断须抽样复核（实测出现过计数错误与定性偏差）；
- **红线**：桥接为只读沙箱（`--sandbox --mode plan`），任何需要写盘的任务一律不得委托。
- **通道选择（硬约束）**：预期 < 3 分钟走同步工具 `mcp__agy__research`；预计 ≥ 3 分钟的宽面调研 / 全仓审计**禁止**走同步工具调用（客户端工具超时会在自设上限处掐断，而服务端会继续跑并留下孤儿进程），必须改走后端作业——宿主后台作业（`pwsh` 带 `run_in_background`），或桥接器的作业句柄工具（本会话若已提供 `research_submit` / `research_status` / `research_result` / `research_cancel` 则优先用它）；统一封装入口：`node D:\Users\dsh-local-plugins\agy-bridge\bin\agy-run.mjs`。
- **已知走不通、不要重复设计**：MCP `notifications/progress` 心跳（本版 DSH 不传 `onprogress`，SDK 因此不挂 `progressToken`，进度通知根本到不了模型）；MCP Tasks（工具声明 `execution.taskSupport: "required"` 会被 DSH 拒绝注册）。

## 二、通用 Agent 工程工作流与思维模型（Matt Pocock 实践体系）

本章规范沉淀自 Matt Pocock（AI Hero、`mattpocock/skills`）的 AI 协同编码工程学，适用于任何 Agent 在任何项目中的日常交互。

### 1. 终结“负向规则膨胀循环”（Break the Negative Rule Bloat Loop）
- **核心反模式**：模型偶发犯错 ➔ 人工在规则文件中补一条“禁止做 X / 必须做 Y”的特例条目 ➔ 规则无限膨胀为数千 Token 的垃圾场 ➔ 模型注意力机制被稀释、指令遵循能力断崖式下降。
- **修正铁律**：
  - **删除优于解释**：规则只写最核心的约束，默认行动是删除冗余文字，而非长篇说教；
  - **不变式（Invariants）优于补丁（Patches）**：只沉淀能经历大重构依然成立的底层不变式；偶发的具体逻辑 Bug 属于测试用例范畴，严禁随意升级为全局系统提示词。

### 2. 区分运行框架行为与领域知识（Harness Behavior vs. Domain Docs）
- **职责边界**：
  - `GLOBAL.md` / `AGENTS.md` 只定义 **Harness 行为契约**（Agent 如何思考、如何规划、如何与工具和人类交互）；
  - 具体的业务架构、API 契约、领域模型定义为 **Source Material（源资产）**，必须保存在独立的领域文档（如 `docs/`、`CONTEXT.md`、ADR 架构决策记录），只在相关任务时按需读取。

### 3. Plan Mode 规划纪律与阻塞问题暴露
在进入复杂编码前，实施计划必须满足以下纪律：
- **致密表达（Concision First）**：计划书极度压缩，去除客套与语法修饰，以短句和列表呈现，让人类审阅者能在 10 秒内把握全貌；
- **强制暴露未决问题（Unresolved Questions Block）**：
  每个 Plan 的结尾**必须且强制**附带未决问题清单。在人类确认之前，严禁擅自假定答案并开始编码：
  ```markdown
  ### 未决问题与阻塞确认清单
  - [ ] 问题 1：...
  - [ ] 问题 2：...
  ```

### 4. 消除会话冗余与信息污染（Anti-Bloat）
- **禁止复述可探测事实**：禁止向用户复述 `package.json` 中的 scripts、目录结构、已安装依赖或代码库中一目了然的技术事实；
- **只提供差异（Diff-Oriented）**：会话交互只汇报思考决策点、潜在风险与变更摘要，不把工具输出的大段原始日志灌回对话。

### 5. 跨 Harness 兼容原则（Cross-Harness Parity）
- 不同的 Agent 运行时依赖不同的配置文件入口（Codex/AGY/Pi/DSH 依赖 `AGENTS.md`，Claude Code 依赖 `CLAUDE.md`）；
- 必须通过软链接（`ln -s` / Windows Junction / 自动化分发工具）保持多端统一，杜绝在不同工具的配置中分散维护不同版本的提示词。
