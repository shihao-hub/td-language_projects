# AGENTS.md

## 强约束规则

- 所有 AI 回复必须使用中文。
- 所有 spec / plan 类设计文档（requirements.md、design.md、tasks.md、plans/01-plan.md 等）必须使用中文描述。
- 代码注释推荐使用中文；变量名、函数名、类名等代码标识符一律使用英文。
- 专业术语（API、HTTP、TypeScript、React 等）、框架名称、命令行指令、文件路径保留英文原文。
- Git Commit Message 格式：
  - 子模块内（monorepo，一目录一项目）：`<project>:<type>: <subject>`，如 `taskmon:feat: 添加进程树过滤`；需更细范围用 `<project>:<type>(<scope>): <subject>`；
  - 父仓库（无项目维度）：`<type>: <subject>`，如 `docs: 更新仓库约定`；
  - type 限：`feat`（新功能）、`fix`（Bug 修复）、`docs`（文档）、`style`（格式）、`refactor`（重构）、`perf`（性能）、`test`（测试）、`chore`（构建/工具）、`ci`（CI/CD）、`revert`（回滚）；
  - Subject：中文描述，≤ 50 字符，不以句号结尾；祈使语气（添加、修复、优化、重构、移除、更新）；
  - Body：中文，每行 ≤ 72 字符，说明是什么和为什么，`-` 列表格式。
- **`**/plans/**` 与 `**/specs/**` 文件的独立提交规则（强约束）**：
  - **触发时机（必须单独 commit）**：
    1. **新建计划**：实施计划/需求设计一旦落盘，**必须立即单独提交**，严禁与随后的开发代码混在一起；
    2. **任务结束归档**：整组任务执行完成、勾选完最终状态后，**必须立即单独提交该文件的状态更新**，不得拖延到后续无关对话；
    3. **中间任务折叠**：在连续执行 Task 1 到 Task N 期间，计划文件内微小的勾选改动可折叠合并，在整批任务完成或停下等待用户确认时**一次性独立提交**（无须每一个 Task 单独 commit 一次计划）。
  - **隔离纪律（单文件独占）**：
    - 严禁代码、配置或其他业务文件混入；
    - 每个不同的 plan/spec 文件互不干扰，禁止跨 plan 批量合并提交。
  - **自治权限**：Agent 可直接完成此类 commit，无需再次征得用户同意；只有遇到 Git 身份、权限、钩子、冲突或其他安全边界导致无法提交时，才向用户询问。
  - **Commit Message 规范**：标题使用规范类别（如 `docs(plans): ...`），Body 必须使用 `- ` 无序列表说明变动详情。
- Git 提交范围隔离：一次提交的文件只能属于同一范围——父仓库自身、某个子仓库根目录、或某个子仓库内的单个子项目；禁止跨范围混提（如多个子项目的改动混在一次提交，或子项目文件与子仓根目录文件混提）。
- 代码修改完成后，向用户展示改动摘要，并给出可直接在 PowerShell 下执行的 git commit 命令（需要有 cd 命令）。
- 禁止 `SELECT *`：任何 ORM 查询与手写 SQL 一律显式列出所需字段。
- CLI 工具开发统一遵循《[CLI 工具开发标准](<docs/projects/go_projects/CLI 工具开发标准.md>)》（跨语言适用）：新工具默认配套 MCP，CLI 默认人读并提供 `--json`，独立工具提供 `schema` 导出；适用例外与存量兼容迁移按标准执行。
  - **必须先完整阅读该标准再动手的场景**：① 新建任何 CLI/工具类项目（不限语言）；② 给已有项目新增 CLI / MCP 入口或 `schema` 导出；③ 需要豁免标准要求（如服务 + 库形态不配 CLI）时；④ 重构/评审已有项目的 CLI 入口契约时。
- 数据文件存放强约束：所有项目运行时产生的自有数据文件（JSON 数据库、SQLite db、索引/哈希缓存、锁文件、日志、会话存储、settings 等）只允许放在 `%APPDATA%\language_projects\<项目名>\`；取不到 `APPDATA` 时回退 `~/.language_projects/<项目名>/`；代码必须在写入前自动创建完整目录链（含 `language_projects` 一层）。**写路径禁止“跟随”外部文件所在目录推导**：不得因读取某外部程序/项目的文件（如凭据、数据库）就把自产文件（缓存/锁/临时文件等）落到其所在目录，历史违规案例：agyquota 曾把 token 缓存写进 Zed 凭据目录 `~/.gemini/antigravity-acp/`。例外：只读外部数据源（opencode.db、Zed db 等）仅指读取不受限，向其目录写入仍属违规；django-lab 的 `db.sqlite3` 保留项目根目录；zed-opencode-sessions 仓库内归档 db 为有意提交，保持现状。
- lark-cli 创建的飞书文档默认放在用户的飞书「我的文档库」（创建时加 `--parent-position my_library`），不要落在云盘根目录；用户明确指定位置时以用户为准。
- 测试资源用后即清：chrome-devtools 等工具打开的浏览器测试页、临时起的服务、后台进程，验证完成立即关闭或终止，不得遗留；chrome-devtools 浏览器任务收尾时，其专属 Chrome 的最后一个 about:blank 标签页 MCP 关不掉（属启动初始页，非残留错误），收尾标准为不残留任何窗口与后台进程，需按 user-data-dir 过滤整组终止：`Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*chrome-devtools-mcp\chrome-profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`；确需保留时必须向用户说明并获得同意。
- 注释中的 `sh-ai-todo` 如果完成了请标记为 `sh-ai-todo[o]`

### Windows PowerShell 执行安全规范（通用条件约束）

当且仅当处于 Windows 宿主环境并调用 PowerShell 执行命令行时，所有 AI Agent（包括 Codex、DeepSeek Harness、Antigravity 等）**必须遵循以下跨 Agent 通用安全规范**：

1. **进程无状态与工作目录感知**：
   - Windows 下 Agent 命令执行通常为**无状态的独立子进程**（如 DeepSeek Harness 等框架每次命令均拉起独立进程）；
   - 避免假设前一次命令的 `cd` 状态会持久保留到后续轮次；跨目录操作应优先依赖 Agent 工具自带的 `workdir` / `cwd` 参数，或在单次调用内完成路径切换与执行。
2. **版本感知与语句连接（pwsh 7 vs PowerShell 5.1）**：
   - **PowerShell 7+（`pwsh`，如 Codex 命中 7 或 DeepSeek Harness 运行时）**：
     - 原生支持 `&&` 与 `||` 管道链，允许自由使用。
   - **Windows PowerShell 5.1（`powershell.exe`，系统内置默认）**：
     - 不支持 `&&` / `||`（抛出语句分隔符语法错误）；
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
   - **终端写入防御**：严禁裸写 `>` 或 5.1 的 `Set-Content -Encoding UTF8`（会强行注入 UTF-8 BOM `EF BB BF`，破坏下游 JSON/编译解析）。确需终端落盘无 BOM 纯正 UTF-8 时：
     ```powershell
     [System.IO.File]::WriteAllText("<filepath>", $content, [System.Text.UTF8Encoding]::new($false))
     ```
   - **控制台流编码保障**：调用外部 CLI（如 git/go/python）并需捕获中文输出时，显式统一当前会话编码流：
     ```powershell
     [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8
     ```
4. **命令原子化与跨平台兜底（契合父仓规范）**：
   - 终端仅执行确定性的单条原生命令，禁止混用 Linux 专有别名（如带 Linux 参数的 `curl`、`cat`、`grep`、`export`、`rm -rf`）。
   - 凡涉及复杂文本流提取（正则、awk/sed）或多步骤依赖任务，**严禁在终端拼接复杂脆弱的管道**：
     - **首选（仓库正统）**：按本仓规范编写单文件 Python 脚本，以 `uv run` 驱动；
     - **备选（Git Bash）**：若需直接利用 POSIX 工具链，动态定位 Git Bash 执行，严禁硬编码盘符：
       ```powershell
       $bash = (Get-Command git -ErrorAction SilentlyContinue).Source -replace '\\cmd\\git\.exe$','\bin\bash.exe'; & $bash -c '<unix-command>'
       ```

### 开发约束（手工编写）

- pg 数据库表尽量避免使用 JSONB，如果一定要使用请说明原因，而且该字段要设置最大容量
- 在 python 项目的 fastapi + sqlalchemy + celery 框架中：
  - 要考虑如何避免一个数据库连接被某个长任务长期持有
  - sqlalchemy 的 BaseModel 类首次创建、增减字段、修改字段时，在任务完成后，需要人工参与审阅，避免出现 N+1、隐式级联操作等问题，所以记得任务完成后提示
  - celery 应该只负责轻任务，重任务可以给 kafka（待定）

## 仓库结构说明

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **git submodules** 结构：

- 五个子目录（`go_projects`、`python_projects`、`rust_projects`、`typescript_projects`、`native_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 其中 `native_projects` 是**混合语言子仓**（C / C++ / Lua）：仓内同样是"一个子目录 = 一个项目"，具体语言由各项目自定；其余子仓仍按语言一一对应。
- 各语言子仓内部为 monorepo：**一个子目录 = 一个项目**，每个子目录都是一个独立项目，彼此互不依赖归属关系，各自维护自己的依赖与配置；新增项目时直接建新的子目录，不要在子项目内单独 `git init`。
- 已归档项目与通用文档集中放在**父仓库根目录**，统一收入 `projects/` 分层，按语言子仓名嵌套（由各子仓迁移而来）：
  - `.archived/projects/<lang>/`：归档停更的项目（如 `.archived/projects/go_projects/file-sync`、`.archived/projects/python_projects/lele`）；
  - `docs/projects/<lang>/`：各语言通用文档与项目文档（如 `docs/projects/go_projects/clictl/clictl 使用指南.md`、`docs/projects/python_projects/tech_learning_room/`），详见下方「归档与文档布局约定」。
- 编辑器配置同样集中在父仓库根目录 `.zed/settings.json`（入库，随仓库分发），子仓内不再各自维护。
- AI 会话产物（`.zcode/`）同样集中在父仓库根目录，子仓内不再各自维护。
- 在本仓库下工作时，先确认目标所在位置（子仓内项目、根 `.archived/`、根 `docs/`），再进入对应目录执行构建、测试等操作。
- 不要试图从父仓库提交子模块内部的改动：子模块内的变更必须在子模块自己的仓库里 commit + push。
- 父仓库层面可见的变更有：`.gitmodules`、子模块指针、README/AGENTS 等自有文件，以及根目录的 `.archived/` 与 `docs/`。

## 隔离性原则（重要）

- 各项目（无论在子仓内还是 `.archived` 内）之间**基本上无任何关联**：没有共享代码、共享依赖或隐含约定，不要假设对一个项目的改动需要另一个项目"配合"。
- 开发某个项目时，**只在该项目目录范围内工作**，不要想着顺带修改另一个项目的事情。
- 即使认为其他项目似乎也需要相应改动，也不要自行跨项目修改；先向用户说明情况，由用户决定是否另行处理。

## 各语言子仓约定

### go_projects

- 定位：以 CLI 工具为主；非 CLI 的服务端/SDK 及带 GUI 项目属例外（个位数，如 liteconf），收录须注明理由，详见父仓 README「子仓约定」。
- 曾计划采用 git submodules 管理子项目，后因维护成本退回 monorepo；背景与操作方案见子仓内 `SUBMODULES.md`。
- 产 exe 的项目默认带站标地鼠图标（用户明确指定其他图标或明确不要时除外）：复制 `docs\assets\projects\go_projects\go-default.ico` 到项目主包目录并生成 `.syso`，操作步骤遵循《[go exe 默认图标](<docs/projects/go_projects/go exe 默认图标.md>)》。
- 产 exe / GUI 项目的 dev 与 release 产物命名隔离约束：
  - **开发版（dev 构建）**：产物文件名必须显式包含 `-dev` 后缀（如 `<project>-dev.exe` 或 `<project>-gui-dev-windows-amd64.exe`），版本号附带 `-dev`（如 `vX.Y.Z-dev`）；
  - **正式版（release 构建）**：产物必须是标准的正式名（如 `<project>.exe` 或 `<project>-gui-windows-amd64.exe`），严禁包含任何 dev 标识；
  - **探测与快捷方式优先级**：任何快捷方式生成（`.lnk`）、开机自启动路径或外部进程查找器，**必须优先查找正式版 exe**，仅当正式版不存在时才允许回退查找开发版 exe，防止开发阶段与正式环境相互踩踏；
  - **开机自启动与注册表保护**：凡涉及向系统注册表（如 `HKCU\...\Run`）写入开机自启路径的 GUI 程序，开发版必须强校验禁止写入（菜单项置灰并拒绝执行），仅正式版（HEAD 严格命中 Git Tag 且工作区干净）允许注册。
- 带 GUI / 独立品牌项目的图标规范：
  - 普通 CLI 工具产 exe 默认使用地鼠图标；
  - **带 GUI / 托盘桌面壳的项目属独立软件形态，禁止直接拿地鼠图标应付**：必须配套专属的现代多分辨率矢量图标流水线（如 `scripts/render_icon.py`），生成 1024x1024 高清图、16-256px 多尺寸标准 `icon.ico`、托盘与窗口资源，并通过 `rsrc` 生成 `.syso`；
  - **GUI 窗口图标必须显式注入**：GUI 程序必须在主窗口初始化时显式绑定应用/窗口图标（如 Fyne 调用 `app.SetIcon` / `win.SetIcon`，Wails 绑定 `app.Icon`），严禁遗留 Windows 系统默认的白框线框图标。

### python_projects

- 产 exe 的项目默认带 Python 双蛇标志图标（用户明确指定其他图标或明确不要时除外）：以**绝对路径**引用 `docs\assets\projects\python_projects\python-default.ico`（Nuitka 构建期写入 PE 资源，无需复制进项目目录），操作步骤遵循《[python exe 默认图标](<docs/projects/python_projects/python exe 默认图标.md>)》。

### rust_projects

- 使用 rustup 管理的 stable-x86_64-pc-windows-msvc 工具链，链接器来自 VS Build Tools 2022。
- rustup/cargo 均已配置 rsproxy.cn 国内镜像（环境变量 `RUSTUP_DIST_SERVER` / `RUSTUP_UPDATE_ROOT` + `~/.cargo/config.toml`）。
- cargo 命令均在子项目目录下运行。

### typescript_projects

- 子仓根目录**不创建** `pnpm-workspace.yaml` 和根 `package.json`，子项目之间不做 workspace 关联。

### native_projects

- **混合语言子仓**：收录 C / C++ / Lua 项目（`native` 指原生代码生态；Lua 解释器为 C 实现，嵌入场景属原生生态圈内），仓内一个子目录 = 一个项目，语言由各项目自定。
- 构建主推 **CMake + CMakePresets.json + Ninja**，编译器默认 **MSVC**（VS Build Tools 2022），MSYS2 MinGW64 (gcc/g++) 备选；轻量项目可用 **xmake**。
- 测试用 **GoogleTest**（企业最常用；轻量项目可用 doctest），统一由 **CTest** 驱动：CMake 开 `enable_testing()` + `add_test()`，preset 里配 test 步骤。
- 质量工具随 **LLVM** 安装：**clang-format**（格式化）+ **clang-tidy**（静态分析/现代 C++ 检查）；LSP 用 **clangd**（Zed 白名单按项目开启），依赖 `CMAKE_EXPORT_COMPILE_COMMANDS=ON` 导出的 `compile_commands.json`。
- 包管理（vcpkg/conan）暂不引入，第一个需要第三方库（fmt/spdlog/gtest 等）的项目再上 vcpkg manifest；小依赖可先用 CMake FetchContent。
- Lua：嵌入宿主用 CMake 链接；纯 Lua 脚本项目无需构建系统；Lua 模块生态用 LuaRocks（按需装）。
- CI 用 **GitHub Actions**（windows-latest 自带 MSVC + CMake + Ninja）。
- 本机已装：CMake 4.2、VS Build Tools 2022（含 VC 工具集）、MSYS2 MinGW64、xmake、Lua 5.1、LuaJIT、LLVM 22（clang/clangd/clang-format/clang-tidy）、Ninja 1.13。
- 本机已装：CMake 4.2、VS Build Tools 2022（含 VC 工具集）、MSYS2 MinGW64、xmake、Lua 5.1、LuaJIT。

## 仓库脚本约定（.scripts）

- 仓库运维脚本统一放 `.scripts/`（点前缀目录，与 `.archived`/`.zed` 同属仓库基础设施层，不占根目录可见位置）；项目自有脚本随各自子仓，不入该目录。脚本语言**统一 Python**（PEP 723 + uv 单文件），**禁止新增 ps1/bat**：历史 ps1/bat 已全部迁移删除（迁移记录见 `docs/plans/26-script-migration-py-ts.md`），双击入口一并放弃；typescript_projects 子仓内部脚本用 TS（Bun）。
- 例外：`docs/assets/projects/` 目录存放跨项目二进制资源，按语言子仓名嵌套（当前仅 `docs/assets/projects/go_projects/go-default.ico` 默认图标），不属于脚本约束范围。
- **一个脚本只做一件事**：单一职责，禁止膨胀为万能工具脚本。
- Python 脚本**必须**带 PEP 723 内联元数据（`# /// script` 块）声明 `requires-python` 与 `dependencies`；无第三方依赖也要保留该块（形式统一），统一在仓库根用 `uv run .scripts/<脚本> <args>` 执行。
- **禁止**在仓库根或 `.scripts/` 内创建 `pyproject.toml`、`uv.lock`、`.venv`、`requirements.txt`；依赖一律走 PEP 723 + uv 全局缓存，仓库内不产生任何 Python 工程文件。

## 归档与文档布局约定（重要）

- **文档只允许放在父仓库**：子模块内的项目目录中**一律禁止**出现任何文档目录与文档内容（`docs/`、`docs/specs/`、`docs/plans/`、`spec/`、`specs/`、`plans/` 等均不允许）。
- **`docs/` 根目录不放散装文件**，各类各归其位：`docs/projects/<lang>/`（项目镜像文档）、`docs/guides/`（AI 工作指南）、`docs/plans/`（父仓级开发计划）、`docs/repo/`（仓库自身文档与通用技术知识沉淀：git 子模块机制说明、与项目无关的技术介绍等）、`docs/assets/projects/<lang>/`（跨项目二进制资源，如默认图标）；`.archived/` 同理，跨项目内容收入 `.archived/projects/<lang>/` 分层。
- **例外且硬规则：`docs/index.md` 是文档站点入口页，禁止删除**（mkdocs 的 `docs_dir` 根目录必须有 `index.md` 才能生成首页，它不属于“散装文件”而是站点首页本身）；删了会导致构建产物无 `index.html`、站点根路径 404。站点用法见仓库根 `README.md` 的「文档站点」一节。
- 所有**项目相关**文档（spec、plan、设计说明、项目知识沉淀等）统一放父仓库 `docs/projects/<lang>/` 下，按子模块内相对路径**镜像层级命名**，并去掉中间冗余的 `docs/` 一层：
  - 例：`go_projects/a/b.md` → `docs/projects/go_projects/a/b.md`；
  - 例：`typescript_projects/taskmon/docs/x.md` → `docs/projects/typescript_projects/taskmon/x.md`。
- 例外：子模块内全大写命名的文档（如 `README.md`、`SUBMODULES.md`）与子仓根级说明文件无需迁移，可原地保留。
- **方法论文档与 AI agent 工作指南**（跨项目、供 AI agent 直接执行，不归属单个子项目，如 `docs/projects/go_projects/CLI 工具开发标准.md`）：放 `docs/projects/<lang>/` 语言层目录（当前集中在 `docs/projects/go_projects/`），不镜像子仓路径、不进项目子目录；跨语言标准维护单一文件，其他语言引用同一标准；指南中引用的项目参考实现与项目文档，仍按上述 `docs/projects/<lang>/<项目>/` 规则存放。
- **父仓级 AI 工作指南（GUIDE 系列）**：当用户要求"把流程沉淀下来 / 写个操作手册 / 沉淀成 GUIDE"，或一次任务中出现可复用的多阶段工作流（分阶段执行、有人工确认点、有踩坑记录）值得沉淀时，按《[GUIDE 编写规范](<docs/guides/README.md>)》产出 `docs/guides/GUIDE-<中文主题>.md`（专有名词保留英文，如 `GUIDE-AOCI安装配置.md`；语言层方法论文档按上一条放 `docs/projects/<lang>/`，不加 GUIDE 前缀，如 `docs/projects/go_projects/go exe 默认图标.md`）；GUIDE 仿 skill 规范编写但**不注册为 skill**，禁止放入任何 skills 目录。
- **通用技术知识文档**（与任何项目无关的知识介绍/沉淀，如协议介绍、技术调研）：放 `docs/repo/`；`docs/projects/<lang>/` 只收项目相关文档与语言层方法论文档，禁止把此类文档放语言层根目录或任何项目目录。
- 归档项目统一放 `.archived/projects/<lang>/<项目名>/`；语言通用文档放 `docs/projects/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。
- 后续新增归档项目时，同样按 `.archived/projects/<lang>/` 嵌套放入对应位置。

## 新增语言子模块及子子模块规范

### 1. 新增语言子模块（一级子仓）
1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `branch = <默认分支>` 与 `ignore = all`，然后 commit；
4. **必须在新建子模块根目录配置规则继承指针**（详见下文）。

### 2. 子模块与子子模块的 Agent 规则继承指针（强约束）
为了防止 Git Submodule 边界隔离导致 Agent（如 Antigravity、Claude Code、Codex）在切入子仓或嵌套子仓时丢失父仓主规则，**所有一级子模块及更深层级的子子模块根目录下，必须配套添加规则继承指针文件**：

1. **`CLAUDE.md`**：保持单行引用（利用 Claude Code 原生 `@import` 机制自动内联）：
   - 一级子模块（如 `go_projects/CLAUDE.md`）：
     ```markdown
     @../AGENTS.md
     ```
   - 二级子子模块（如 `go_projects/glmquotawatch-gui/CLAUDE.md`）：
     ```markdown
     @../../AGENTS.md
     ```
2. **`AGENTS.md`**：声明最高优先级的继承行动指令，指引所有 Agent 工具启动时优先读取顶层主规范：
   - 一级子模块（如 `go_projects/AGENTS.md`）：
     ```markdown
     # Agent Context Pointer

     > **CRITICAL**: This repository is a submodule (`<submodule_name>`) of the parent project.
     > All base conventions, Git commit rules, and environment guidelines are inherited from:
     > `file://../AGENTS.md`

     **ACTION REQUIRED**: Before executing any code changes or git commands, you MUST read and follow the root conventions in `../AGENTS.md`.
     ```
   - 二级子子模块（如 `go_projects/glmquotawatch-gui/AGENTS.md`）：
     ```markdown
     # Agent Context Pointer

     > **CRITICAL**: This repository is a nested submodule (`<path/submodule_name>`) of the parent project.
     > All base conventions, Git commit rules, and environment guidelines are inherited from:
     > `file://../../AGENTS.md`

     **ACTION REQUIRED**: Before executing any code changes or git commands, you MUST read and follow the root conventions in `../../AGENTS.md`.
     ```
3. **提交与推送规范**：
   - 指针文件必须在对应子模块/子子模块**自己的 Git 仓库中**先行 `git commit` 并 `git push`；
   - 随后在父级仓库中更新对应的 submodule 指针并提交推送。

## 常用命令

- 完整克隆：`git clone --recurse-submodules <URL>`
- 克隆后初始化并切换子模块到跟踪分支：`uv run .scripts/init-submodules.py`（初始化 + 按 `.gitmodules` 的 `branch` 字段切分支，解决子模块默认 detached HEAD）
- 初始化/补格子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`

## AOCI Repository Cognition

AOCI 是仓库级认知索引工具（以 MCP server 形式接入）：通过 aoci.txt / aoci.code.txt / .aoci/ 等索引与数据，让 AI 会话跨任务复用对本仓库的结构化认知（架构、对象职责、关系、外部契约、关键约束）。

完整集成说明与工作流原文存于根目录 aoci.repository.cognition.md，**按需读取，不随会话默认加载**（原文较长，为省上下文从本文件迁出）。满足以下触发条件之一时，**必须先读该文件**再按其中工作流调用 aoci_* 工具：

1. **建立/恢复认知**：新会话接手复杂或跨模块任务，需要仓库全景（先 `aoci_overview`）；本会话上下文经历过压缩后继续 AOCI 相关工作。
2. **收尾维护（最易遗漏）**：本会话改动过任何 AOCI 纳管文件（父仓文档、.scripts/ 脚本、根级配置等）且已到最终稳定状态——调用**一次** `aoci_maintain` 对齐索引；不得边改边逐文件调用，也不得跳过。
3. **纯读/小改动豁免**：未改动任何纳管文件的只读任务与日常小改动，无需加载该文件，也无需维护调用。

AOCI 托管资产（aoci*.txt 与 .aoci/）在收尾维护后产生的变更，提交时与业务代码分开成笔。
