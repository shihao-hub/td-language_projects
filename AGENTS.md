# AGENTS.md

<!-- 本文件须保持 <24000 字节：agy 规则文件硬上限，超出将被截尾 -->

> **全局基线继承**：通用交互、Windows 终端执行安全、文件操作防御、Token 经济等跨 Agent 规范已由 `GLOBAL.md` 统一注入；本文件仅声明本 Monorepo 专属架构、子仓契约与工程协作纪律。

## 一、仓库架构与多子仓模型

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **Git Submodules** 架构：

- 五个子目录（`go_projects`、`python_projects`、`rust_projects`、`typescript_projects`、`native_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 其中 `native_projects` 是**混合语言子仓**（C / C++ / Lua）：仓内同样是“一个子目录 = 一个项目”，具体语言由各项目自定；其余子仓仍按语言一一对应。
- 各语言子仓内部为 monorepo：**一个子目录 = 一个项目**，彼此独立、各自维护依赖与配置；新增项目直接建新子目录，不要在子项目内单独 `git init`。
- 已归档项目与通用文档集中放在**父仓库根目录**，统一收入 `projects/` 分层，按语言子仓名嵌套：
  - `.archived/projects/<lang>/`：归档停更的项目（如 `.archived/projects/go_projects/file-sync`、`.archived/projects/python_projects/lele`）；
  - `docs/projects/<lang>/`：各语言通用文档与项目文档，详见后文「归档与文档布局约定」。
- 编辑器配置（`.zed/settings.json`，入库随仓分发）与 AI 会话产物（`.zcode/`）统一集中在父仓库根目录，子仓内不再各自维护。
- 重要客体级资产「真身入本仓 + 链接到使用位置」：`.agents/skills` 是指向 `git@github.com:shihao-hub/td-agents-skills.git` 的子模块（skills 真身），并已用目录联接（junction）暴露为 `~/.agents/skills`（经链接与经本仓访问等价）；家目录被误删只会断链接、不再丢数据。
- 在本仓库下工作时，先确认目标所在位置（子仓内项目、根 `.archived/`、根 `docs/`），再进入对应目录执行构建、测试等操作。
- 不要试图从父仓库提交子模块内部改动：变更必须在子模块仓库内 commit + push。
- 父仓库层面可见的变更有：`.gitmodules`、子模块指针、README/AGENTS 等自有文件，以及根目录的 `.archived/` 与 `docs/`。

## 二、隔离性原则（重要）

- 各项目（无论子仓内还是 `.archived` 内）**基本无关联**：无共享代码/依赖或隐含约定，不要假设一个项目的改动需要另一个项目“配合”。
- 开发某个项目时，**只在该项目目录范围内工作**，不要想着顺带修改另一个项目的事情。
- 即使认为其他项目似乎也需要相应改动，也不要自行跨项目修改；先向用户说明情况，由用户决定是否另行处理。

## 三、Git 提交规范与范围隔离

- **Commit Message 格式**：
  - 子模块内（monorepo，一目录一项目）：`<project>:<type>: <subject>`，如 `taskmon:feat: 添加进程树过滤`；需更细范围用 `<project>:<type>(<scope>): <subject>`；
  - 父仓库（无项目维度）：`<type>: <subject>`，如 `docs: 更新仓库约定`；
  - type 限：`feat`（新功能）、`fix`（Bug 修复）、`docs`（文档）、`style`（格式）、`refactor`（重构）、`perf`（性能）、`test`（测试）、`chore`（构建/工具）、`ci`（CI/CD）、`revert`（回滚）；
  - Subject：中文描述，≤ 50 字符，不以句号结尾；祈使语气（添加、修复、优化、重构、移除、更新）；
  - Body：中文，每行 ≤ 72 字符，说明是什么和为什么，`-` 列表格式。
- **`**/plans/**` 与 `**/specs/**` 文件的独立提交规则（强约束）**：
  - **触发时机（必须单独 commit）**：
    1. **新建计划**：实施计划/需求设计一旦落盘，**必须立即单独提交**，严禁与随后的开发代码混在一起；
    2. **任务结束归档**：整组任务执行完成、勾选完最终状态后，**必须立即单独提交该文件的状态更新**，不得拖延到后续无关对话；
    3. **中间任务折叠**：连续执行 Task 1..N 期间，勾选类微改可折叠合并，在整批完成或停下等待确认时**一次性独立提交**。
  - **隔离纪律（单文件独占）**：严禁代码、配置或其他业务文件混入；每个不同的 plan/spec 文件互不干扰，禁止跨 plan 批量合并提交。
  - **自治权限**：Agent 可直接完成此类 commit，无需再次征得用户同意；只有遇到 Git 身份、权限、钩子、冲突或其他安全边界导致无法提交时，才向用户询问。
  - **Commit Message 规范**：标题使用规范类别（如 `docs(plans): ...`），Body 必须使用 `- ` 无序列表说明变动详情。
- **Git 提交范围隔离**：一次提交的文件只能属于同一范围——父仓库自身、某个子仓库根目录、或某个子仓库内的单个子项目；禁止跨范围混提（如多个子项目的改动混在一次提交，或子项目文件与子仓根目录文件混提）。

## 四、数据文件存放强约束（`%APPDATA%\language_projects`）

- 所有项目运行时产生的自有数据文件（JSON 数据库、SQLite db、索引/哈希缓存、锁文件、日志、会话存储、settings 等）**只允许放在 `%APPDATA%\language_projects\<项目名>\`**；取不到 `APPDATA` 时回退 `~/.language_projects/<项目名>/`；代码必须在写入前自动创建完整目录链（含 `language_projects` 一层）。
- **写路径禁止“跟随”外部文件所在目录推导**：不得因读取某外部程序/项目的文件（如凭据、数据库）就把自产文件（缓存/锁/临时文件等）落到其所在目录。
  - *【反面案例警戒】*：严禁将本项目的运行时缓存或锁文件写入宿主编辑器或外部凭据目录（如曾出现的将 token 缓存写进 Zed 凭据目录 `~/.gemini/antigravity-acp/`）。
- **例外项**：只读外部数据源（opencode.db、Zed db 等）仅指读取不受限，向其目录写入仍属违规；django-lab 的 `db.sqlite3` 保留项目根目录；zed-opencode-sessions 仓库内归档 db 为有意提交，保持现状。
- **构建形态隔离**：带 dev/prod 双构建形态的项目，数据目录还须按 dev/prod 子目录隔离（`%APPDATA%\language_projects\<项目名>\dev` 与 `...\prod`）。
- **飞书文档落盘位置**：lark-cli 创建的飞书文档默认放在用户的飞书「我的文档库」（创建时加 `--parent-position my_library`），不要落在云盘根目录；用户明确指定位置时以用户为准。

## 五、各语言子仓约定

### go_projects
- **定位**：以 CLI 工具为主；非 CLI 的服务端/SDK 及带 GUI 项目属例外（个位数，如 liteconf），收录须注明理由，详见父仓 README「子仓约定」。
- **CLI 工具开发标准**：统一遵循《[CLI 工具开发标准](docs/projects/go_projects/CLI 工具开发标准.md)》（跨语言适用）：新工具默认配套 MCP，CLI 默认人读并提供 `--json`，独立工具提供 `schema` 导出；适用例外与存量兼容迁移按标准执行。
  - *必须先完整阅读该标准再动手的场景*：① 新建任何 CLI/工具类项目（不限语言）；② 给已有项目新增 CLI / MCP 入口或 `schema` 导出；③ 需要豁免标准要求时；④ 重构/评审已有项目的 CLI 入口契约时。
- **默认图标**：产 exe 的项目默认带站标地鼠图标（用户明确指定其他图标或明确不要时除外）：复制 `docs\assets\projects\go_projects\go-default.ico` 到项目主包目录并生成 `.syso`，操作步骤遵循《[go exe 默认图标](docs/projects/go_projects/go exe 默认图标.md)》。
- **dev 与 release 隔离约束**：
  - **统一构建脚本**：构建统一由单一 `build.py` 完成（uv 单脚本，PEP 723 头即使无依赖也保留），不搞 ps1/bat 或 dev/prod 双脚本；脚本开头必须有用户可读使用说明，且每次变更同步更新；
  - **构建类型自动判定**：仅当 HEAD 严格命中 git tag 且工作区干净时才允许产 release，其余一律按 dev 处理（产物带 `-dev` 后缀，工作区不干净时版本号再带 `-dirty`）；版本号与 commit 经 `-ldflags` 注入；
  - **开发版（dev 构建）**：产物文件名必须显式包含 `-dev` 后缀（如 `<project>-dev.exe` 或 `<project>-gui-dev-windows-amd64.exe`），版本号附带 `-dev`（如 `vX.Y.Z-dev`）；
  - **正式版（release 构建）**：产物必须是标准正式名（如 `<project>.exe` 或 `<project>-gui-windows-amd64.exe`），严禁包含任何 dev 标识；
  - **数据目录隔离**：dev 与 prod 运行时数据目录必须分开（`%APPDATA%\language_projects\<项目名>\dev` 与 `...\<项目名>\prod`），开发调试严禁读写生产数据；
  - **单例互斥锁隔离**：带单实例互斥（mutex / SingleInstance UniqueID）的程序，dev 与 prod 必须使用不同 ID（dev 在 prod ID 基础上追加 `.dev` 后缀），防止开发调试实例与后台常驻生产实例互斥冲突；
  - **探测与快捷方式优先级**：任何快捷方式生成（`.lnk`）、开机自启动路径或外部进程查找器，**必须优先查找正式版 exe**，仅当正式版不存在时才允许回退查找开发版 exe，防止开发阶段与正式环境相互踩踏；
  - **开机自启动与注册表保护**：凡涉及向系统注册表（如 `HKCU\...\Run`）写入开机自启动路径的 GUI 程序，开发版必须强校验禁止写入（菜单项置灰并拒绝执行），并向用户明确提示该功能在 dev 版不生效；此类功能直接用 release 版本测试，仅正式版允许注册。
- **带 GUI / 独立品牌项目的图标规范**：
  - 普通 CLI 工具产 exe 默认使用地鼠图标；
  - **带 GUI / 托盘桌面壳项目属独立软件形态，禁止直接拿地鼠图标应付**：必须配套专属多分辨率矢量图标流水线（如 `scripts/render_icon.py`），产出 1024 高清图、16-256px 标准 `icon.ico`、托盘与窗口资源，经 `rsrc` 生成 `.syso`；
  - **GUI 窗口图标必须显式注入**：GUI 程序必须在主窗口初始化时显式绑定应用/窗口图标（如 Fyne 调用 `app.SetIcon` / `win.SetIcon`，Wails 绑定 `app.Icon`），严禁遗留 Windows 系统默认的白框线框图标。

### python_projects
- 产 exe 的项目默认带 Python 双蛇标志图标（用户明确指定其他图标或明确不要时除外）：以**绝对路径**引用 `docs\assets\projects\python_projects\python-default.ico`（Nuitka 构建期写入 PE 资源，无需复制进项目目录），操作步骤遵循《[python exe 默认图标](docs/projects/python_projects/python exe 默认图标.md)》。

### rust_projects
- 使用 rustup 管理的 `stable-x86_64-pc-windows-msvc` 工具链，链接器来自 VS Build Tools 2022。
- rustup/cargo 均已配置 rsproxy.cn 国内镜像（环境变量 `RUSTUP_DIST_SERVER` / `RUSTUP_UPDATE_ROOT` + `~/.cargo/config.toml`）。
- cargo 命令均在子项目目录下运行。

### typescript_projects
- 子仓根目录**不创建** `pnpm-workspace.yaml` 和根 `package.json`，子项目之间不做 workspace 关联。

### native_projects
- **混合语言子仓**：收录 C / C++ / Lua 项目（`native` 指原生代码生态；Lua 解释器为 C 实现，嵌入场景属原生生态圈内）。
- 构建主推 **CMake + CMakePresets.json + Ninja**，编译器默认 **MSVC**（VS Build Tools 2022），MSYS2 MinGW64 (gcc/g++) 备选；轻量项目可用 **xmake**。
- 测试用 **GoogleTest**（企业最常用；轻量项目可用 doctest），统一由 **CTest** 驱动：CMake 开 `enable_testing()` + `add_test()`，preset 里配 test 步骤。
- 质量工具随 **LLVM** 安装：**clang-format** + **clang-tidy**（静态分析）；LSP 用 **clangd**（Zed 白名单按项目开启），依赖 `CMAKE_EXPORT_COMPILE_COMMANDS=ON` 导出的 `compile_commands.json`。
- 包管理（vcpkg/conan）暂不引入，第一个需要第三方库（fmt/spdlog/gtest 等）的项目再上 vcpkg manifest；小依赖可先用 CMake FetchContent。
- Lua：嵌入宿主用 CMake 链接；纯 Lua 脚本项目无需构建系统；Lua 模块生态用 LuaRocks（按需装）。
- CI 用 **GitHub Actions**（windows-latest 自带 MSVC + CMake + Ninja）。
- 本机已装工具链：CMake 4.2、VS Build Tools 2022（含 VC 工具集）、MSYS2 MinGW64、xmake、Lua 5.1、LuaJIT、LLVM 22（clang/clangd/clang-format/clang-tidy）、Ninja 1.13。

## 六、仓库运维脚本约定（.scripts）

- 仓库运维脚本统一放 `.scripts/`（点前缀目录，与 `.archived`/`.zed` 同属仓库基础设施层）；项目自有脚本随各自子仓，不入该目录。
- 脚本语言**统一 Python**（PEP 723 + uv 单文件），**禁止新增 ps1/bat**：历史 ps1/bat 已全部迁移删除，双击入口一并放弃；typescript_projects 子仓内部脚本用 TS（Bun）。
- 例外：`docs/assets/projects/` 目录存放跨项目二进制资源（当前仅 go 默认图标），不属于脚本约束范围。
- **一个脚本只做一件事**：单一职责，禁止膨胀为万能工具脚本。
- Python 脚本**必须**带 PEP 723 内联元数据（`# /// script` 块）声明 `requires-python` 与 `dependencies`；无第三方依赖也要保留该块（形式统一），统一在仓库根用 `uv run .scripts/<脚本> <args>` 执行。
- **禁止**在仓库根或 `.scripts/` 内创建 `pyproject.toml`、`uv.lock`、`.venv`、`requirements.txt`；依赖一律走 PEP 723 + uv 全局缓存。

## 七、归档与文档布局约定（重要）

- **文档只允许放在父仓库**：子模块内的项目目录中**一律禁止**出现任何文档目录与文档内容（`docs/`、`docs/specs/`、`docs/plans/`、`spec/`、`specs/`、`plans/` 等均不允许）。
- **`docs/` 根目录不放散装文件**，各归其位：
  - `docs/projects/<lang>/`：项目镜像文档；
  - `docs/guides/`：AI 工作指南（GUIDE 系列）；
  - `docs/plans/`：**仅限父仓级/跨语言全局运维开发计划**（如全仓多子模块提交、跨项目工具链升级、MkDocs 根站点配置等全仓任务；单子项目计划**严禁**放此目录）；
  - `docs/repo/`：仓库自身文档与通用技术知识沉淀（git 子模块机制说明、与项目无关的技术介绍等）；
  - `docs/assets/projects/<lang>/`：跨项目二进制资源（如默认图标）；
  - `.archived/` 同理，跨项目内容收入 `.archived/projects/<lang>/` 分层。
- **例外且硬规则：`docs/index.md` 是站点入口页，禁止删除**（它是站点首页而非散装文件；mkdocs 的 `docs_dir` 根目录必须有它才能生成首页，删了产物无 `index.html`、根路径 404）。
- 所有**项目相关**文档（spec、plan、设计说明、项目知识沉淀等）统一放父仓库 `docs/projects/<lang>/` 下，按子模块内相对路径**镜像层级命名**，并去掉中间冗余的 `docs/` 一层：
  - 例：`go_projects/a/b.md` → `docs/projects/go_projects/a/b.md`；
  - 例：`typescript_projects/taskmon/docs/x.md` → `docs/projects/typescript_projects/taskmon/x.md`。
- 例外：子模块内全大写命名的文档（如 `README.md`、`SUBMODULES.md`）与子仓根级说明文件无需迁移，可原地保留。
- **方法论文档与 AI agent 工作指南**（跨项目、不归属单个子项目，如 `docs/projects/go_projects/CLI 工具开发标准.md`）：放 `docs/projects/<lang>/` 语言层目录，不镜像子仓路径；跨语言标准维护单一文件，其他语言引用同一标准；指南引用的项目实现/文档仍按 `docs/projects/<lang>/<项目>/` 存放。
- **父仓级 AI 工作指南（GUIDE 系列）**：当用户要求“把流程沉淀下来 / 写个操作手册 / 沉淀成 GUIDE”，或一次任务中出现可复用的多阶段工作流（分阶段执行、有人工确认点、有踩坑记录）值得沉淀时，按《[GUIDE 编写规范](docs/guides/README.md)》产出 `docs/guides/GUIDE-<中文主题>.md`（专有名词保留英文，如 `GUIDE-AOCI安装配置.md`）；GUIDE 仿 skill 规范编写但**不注册为 skill**，禁止放入任何 skills 目录。
- **通用技术知识文档**（与任何项目无关的知识介绍/沉淀，如协议介绍、技术调研）：放 `docs/repo/`；`docs/projects/<lang>/` 只收项目相关文档与语言层方法论文档，禁止把此类文档放语言层根目录或任何项目目录。
- 归档项目统一放 `.archived/projects/<lang>/<项目名>/`；语言通用文档放 `docs/projects/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。

- **AI 计划与规格落盘强制路由（防呆铁律，执行 sh-plan / sh-spec / kiro / specs 先决检查）**：
  - **子项目计划/规格归属**：任何针对具体子模块或工程（如 `python_projects/zedhub`、`go_projects/agyquota`、`typescript_projects/taskmon` 等）的功能开发、重构或缺陷修复，其 `plans/` 与 `specs/` **一律且必须**落盘在父仓 `docs/projects/<lang>/<subproject>/plans/` 与 `docs/projects/<lang>/<subproject>/specs/` 下，序号从 `01` 独立起编，严禁污染父仓根级目录。
  - **父仓级 `docs/plans/` 严格白名单**：仅用于全仓多语言批量构建、全局 Submodule 运维、根级站点冲突等纯父仓级任务。凡涉及具体代码工程改动的，一律不得将计划落盘在父仓根级 `docs/plans/`。
  - **编号自包含隔离**：子项目的计划编号（`01-xxx.md`）自成闭环，取号时只扫描该子项目自己的 `plans/` 目录，禁止参考或递增父仓 `docs/plans/` 下的全局编号。

## 八、新增语言子模块及子子模块规范

### 1. 新增语言子模块（一级子仓）
1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `branch = <默认分支>` 与 `ignore = all`，然后 commit；
4. **必须在新建子模块根目录配置规则继承指针**（详见下文）。

### 2. 子模块与子子模块的 Agent 规则继承指针（强约束）
为防止 Git Submodule 边界隔离导致 Agent 切入子仓/嵌套子仓时丢失父仓主规则，**所有一级子模块及更深层子子模块根目录必须配套添加规则继承指针文件**：

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

## 九、常用命令与 AOCI 认知

### 1. 常用命令
- 完整克隆：`git clone --recurse-submodules <URL>`
- 克隆后初始化并切换子模块到跟踪分支：`uv run .scripts/init-submodules.py`（初始化 + 按 `.gitmodules` 的 `branch` 字段切分支，解决子模块默认 detached HEAD）
- 初始化/补格子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`

### 2. AOCI Repository Cognition
本仓库已接入 AOCI 认知体系（MCP server：`aoci`）：
- **协同契约与触发纪律**：建立/恢复认知、收尾维护必维、纯读豁免及元数据独立提交等通用规范，已统一由 `GLOBAL.md` 托管；
- **协议与深层规范**：AOCI 通用协议及 F/R/A/S 规则手册已归集至 `~/.agents/rules/aoci.protocol.md`（按需查阅）。

## 十、仓库认知与上下文指针（Progressive Disclosure）

遵循 Matt Pocock 的渐进式披露原则，本文件作为仓库 Project Brief，深层技术规范按需触发加载：

- **CLI / MCP 开发契约**：涉及新建/重构 CLI 或 MCP 工具时，按需读取 `docs/projects/go_projects/CLI 工具开发标准.md`；
- **AI 沉淀工作流（GUIDE）**：当需把复杂流程沉淀为标准化作业指导时，按需读取 `docs/guides/README.md`；
- **AOCI 认知协议与规范**：需查阅 AOCI 架构协议或深层语法时，按需读取 `~/.agents/rules/aoci.protocol.md`；
- **子模块独立性与演进记录**：涉及子模块深度背景时，按需查阅各子仓根目录 `README.md` 与 `SUBMODULES.md`。
