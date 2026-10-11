# GLOBAL.md
<!-- Global AI Agent Rules & Engineering Invariants -->
<!-- Managed by language_projects repo. Synchronized across Codex, Claude Code, OpenCode, Pi, DSH, and Antigravity. -->

## 一、通用基线约束（跨项目与跨 Agent 通用规范）

### 1. 交互与语言规范
- **AI 回复语言**：所有 AI 对话回复必须使用中文。
- **设计文档语言**：所有 spec / plan 类设计文档（`requirements.md`、`design.md`、`tasks.md`、`plans/01-plan.md` 等）必须使用中文描述。
- **代码命名与注释**：代码注释推荐使用中文；变量名、函数名、类名等代码标识符一律使用英文。
- **专有名词保留**：专业术语（API、HTTP、TypeScript、React 等）、框架名称、命令行指令、文件路径保留英文原文。
- **任务完成交互**：代码修改完成后，向用户展示改动摘要，并给出可直接在 PowerShell 下执行的 git commit 命令建议（需包含必要的 `cd` 路径切换命令）。

### 2. Windows PowerShell 执行安全规范（通用条件约束）
当且仅当处于 Windows 宿主环境并调用 PowerShell 执行命令行时，所有 AI Agent（包括 Codex、Claude Code、OpenCode、Pi、DeepSeek Harness、Antigravity 等）**必须遵循以下跨 Agent 通用安全规范**：

1. **进程无状态与工作目录感知**：
   - Windows 下 Agent 命令行执行通常为**无状态的独立子进程**（各命令框架每次执行均拉起独立进程）；
   - 避免假设前一次命令的 `cd` 状态会持久保留到后续轮次；跨目录操作应优先依赖 Agent 工具自带的 `workdir` / `cwd` 参数，或在单次调用内完成路径切换与命令执行。
2. **版本感知与语句连接（pwsh 7 vs PowerShell 5.1）**：
   - **PowerShell 7+（`pwsh`）**：原生支持 `&&` 与 `||` 管道链，允许直接使用。
   - **Windows PowerShell 5.1（`powershell.exe`）**：
     - 不支持 `&&` / `||`（会抛出语句分隔符语法错误）；
     - 禁止盲目使用分号 `;` 串联前后强依赖的命令（防止前序失败导致后续命令在错误目录静默执行）；必须拆分为单步独立执行，或使用短路逻辑：
       ```powershell
       command1; if ($?) { command2 }
       ```
3. **文件 I/O 抽象与编码安全**：
   - **优先走 Agent 文件工具**：凡涉及源码或配置的查看与编辑，一律优先使用 Agent 宿主提供的专用文件读写工具（File System Tools），杜绝通过命令行终端回显或流重定向读写大文件。
   - **终端读取防御**：若必须通过终端读取文件，禁止裸调 `Get-Content`（5.1 默认按系统 ANSI/GBK 解析导致中文字符首轮乱码），显式带编码：
     ```powershell
     Get-Content -Encoding UTF8 "<filepath>"
     ```
   - **终端写入防御（防 UTF-8 BOM 破坏热加载与解析）**：严禁裸写 `>` 或 5.1 的 `Set-Content -Encoding UTF8`；**严禁使用 PowerShell 默认单例 `[System.Text.Encoding]::UTF8`**（其默认构造函数带有 UTF-8 BOM `EF BB BF`，会直接导致 Zed、Vite、Turbopack 等严格 JSON/TOML/Rust 解析器抛错并静默阻断配置热加载，甚至导致软件启动异常）。确需终端落盘无 BOM 纯正 UTF-8 时，必须显式传递 `$false`：
     ```powershell
     [System.IO.File]::WriteAllText("<filepath>", $content, [System.Text.UTF8Encoding]::new($false))
     ```
     或优先使用 Node.js（`fs.writeFileSync(file, text, 'utf8')`）/ Python 脚本落盘。
   - **控制台流编码保障**：调用外部 CLI（如 git/go/python）并需捕获中文输出时，显式统一当前会话编码流：
     ```powershell
     [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8
     ```
4. **命令原子化与跨平台兜底**：
   - 终端仅执行确定性的单条原生命令，禁止混用 Linux 专有别名（如带 Linux 参数的 `curl`、`cat`、`grep`、`export`、`rm -rf`）。
   - 凡涉及复杂文本流提取（正则、awk/sed）或多步骤依赖任务，**严禁在终端拼接复杂脆弱的管道**：
     - **首选**：编写单文件 Python 脚本，以 `uv run` 驱动；
     - **备选（Git Bash）**：若需直接利用 POSIX 工具链，动态定位 Git Bash 执行，严禁硬编码盘符：
       ```powershell
       $bash = (Get-Command git -ErrorAction SilentlyContinue).Source -replace '\\cmd\\git\.exe$','\bin\bash.exe'; & $bash -c '<unix-command>'
       ```

### 3. 文件操作安全与命令防御（强约束）
- **写前必读（防盲目覆写）**：当用户给出目标文件路径时，必须先探测该文件是否存在及当前职责（禁止未查看即直接 `Overwrite=True` 覆写），尤其总控索引/草稿文件需按规范追加条目，严禁冲掉已有内容；
- **删前必核（防误删历史资产）**：删除任何疑似“临时/多余”文件前，严禁凭短期记忆臆断，必须通过 `git status` / `git log` 严格核实身世；已入库文件绝不可擅自清理；
- **文件名非法字符防御（防嵌套子目录）**：创建文档或代码文件时，文件名内部严禁包含 `/`、`\` 等路径分隔符（如 `(Python/TS)` 会被系统判定为多层子目录），所有分割一律用短横线 `-` 或下划线 `_`。

### 4. 资源清理与 Token 经济
- **测试资源用后即清**：chrome-devtools 等工具打开的浏览器测试页、临时起的开发服务、后台子进程，验证完成后必须立即关闭或终止，不得遗留；确需保留时必须向用户说明并获得明确同意。
  - *chrome-devtools 浏览器收尾*：其专属 Chrome 的最后一个 `about:blank` 标签页 MCP 关不掉（属启动初始页，非残留错误），收尾标准为不残留任何窗口与后台进程，需按 user-data-dir 过滤整组终止：
    ```powershell
    Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*chrome-devtools-mcp\chrome-profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    ```
- **数据密集型任务必须“脚本化”（Token 经济强约束）**：凡跨目录搜索、批量文件遍历、会话历史/日志/数据库检索、结果筛选去重统计等任务，一律先写单文件脚本（`uv run` Python 或单条 `rg`）在代码层完成筛选、去重、统计、汇总，只把摘要结论带回对话；**严禁**使用多轮工具调用把原始内容（搜索结果、文件正文、目录清单）逐批灌入模型上下文。此类任务不使用 max / 高思考档模型。

### 5. 通用编码质量与后端防线
- **禁止 `SELECT *`**：任何 ORM 查询与手写 SQL 一律显式列出所需字段。
- **任务标记规范**：代码或文档注释中的 `sh-ai-todo`，若已完成请标记为 `sh-ai-todo[o]`。
- **PostgreSQL 规范**：数据库表尽量避免使用 JSONB；若业务必要使用，须在方案中说明理由，并在应用层或约束上限制字段最大容量。
- **Python (FastAPI + SQLAlchemy + Celery) 架构防线**：
  - **连接池保护**：严格避免数据库连接被长时间运行的后台任务或外部 I/O 阻塞持有，长任务应在执行前释放会话或采用短生命周期连接；
  - **ORM 变更审查**：SQLAlchemy 的 `BaseModel` 首次创建、增减字段或修改关联关系时，任务完成后需明确提示人工审阅，重点核查 N+1 查询风险与隐式级联操作（cascade）；
  - **异步任务分层**：Celery 应聚焦毫秒/秒级轻量异步任务；对于高吞吐、强流式或长耗时计算任务，应解耦至专用消息管道（如 Kafka）或独立 Worker 执行，避免阻塞 Celery 任务队列及持有数据库连接。

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
