# AGENTS.md

<!-- 本文件须保持 <24000 字节：agy 规则文件硬上限，超出将被截尾 -->

> **全局基线继承**：通用交互、Windows 终端执行安全、文件操作防御、Token 经济等跨 Agent 规范已由 `GLOBAL.md` 统一注入；本文件仅声明本 Monorepo 专属架构、子仓契约与工程协作纪律。

## 一、仓库架构与多子仓模型

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **Git Submodules** 架构：

- 语言子仓（`go_projects`、`java_projects`、`python_projects`、`rust_projects`、`typescript_projects`、`native_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 其中 `native_projects` 是**混合语言子仓**（C / C++ / Lua）：仓内同样是“一个子目录 = 一个项目”，具体语言由各项目自定；其余子仓仍按语言一一对应。
- **`native_projects` 当前为本地注销态**（属有意暂停，非缺陷）：远端 `td-native-projects` 正常（main 有内容），本地仅保留 gitlink（`git submodule status` 显示 `-` 前缀、未检出）；恢复执行 `git submodule update --init native_projects`，注销/恢复机制与踩坑见 `docs/repo/Git 子模块临时注销（native、rust）.md`。**不得把「声明了但本地无目录」当作架构缺陷重新上报。**
- 各语言子仓内部为 monorepo：**一个子目录 = 一个项目**，彼此独立、各自维护依赖与配置；新增项目直接建新子目录，不要在子项目内单独 `git init`。
- 已归档项目与通用文档集中放在**父仓库根目录**，统一收入 `projects/` 分层，按语言子仓名嵌套：
  - `.archived/projects/<lang>/`：归档停更的项目（如 `.archived/projects/go_projects/file-sync`、`.archived/projects/python_projects/lele`）；
  - `docs/projects/<lang>/`：各语言通用文档与项目文档，详见 `~/.agents/references/language_projects/docs-and-plans-layout.md`。
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

## 五、各语言子仓约定（按需引用）

各语言子仓的定位、构建/数据隔离、图标与工具链约定已迁至 **`~/.agents/references/language_projects/lang-conventions.md`**——**进入任一语言子仓/子项目动工前必读对应语言章节**（go 的 CLI 标准与 dev/release 隔离、python 图标、rust 工具链、ts 约定、native 工具链、java 服务端）。

## 六、仓库运维脚本约定（.scripts）

统一 Python + PEP 723、禁 ps1/bat、单一职责、禁工程文件等约定详见 **`~/.agents/references/language_projects/scripts-convention.md`**——**新建/修改 `.scripts` 脚本前必读**。

## 七、归档与文档布局约定（重要）

文档只放父仓、`docs/` 分区归位、`docs/index.md` 禁删、plans/specs 落盘强制路由等铁律详见 **`~/.agents/references/language_projects/docs-and-plans-layout.md`**——**创建任何文档/计划/规格前必读**。

## 八、新增语言子模块及规则软链规范

独立仓创建、`.gitmodules` 配置、各级 AGENTS/CLAUDE 软链拓扑与一键同步脚本详见 **`~/.agents/references/language_projects/submodule-pointer-spec.md`**——**新增子模块/子项目或调整规则软链前必读**。

## 九、常用命令与 AOCI 认知

### 1. 常用命令

子模块/仓库运维命令速查（克隆初始化、指针提交等）见 **`~/.agents/references/language_projects/repo-commands.md`**。

### 2. AOCI Repository Cognition
本仓库已接入 AOCI 认知体系（MCP server：`aoci`）：
- **协同契约与触发纪律**：建立/恢复认知、收尾维护必维、纯读豁免及元数据独立提交等通用规范，已统一由 `GLOBAL.md` 托管；
- **协议与深层规范**：AOCI 通用协议及 F/R/A/S 规则手册已归集至 `~/.agents/references/aoci.protocol.md`（按需查阅）。

## 十、仓库认知与上下文指针（Progressive Disclosure）

遵循 Matt Pocock 的渐进式披露原则，本文件作为仓库 Project Brief，深层技术规范按需触发加载：

- **CLI / MCP 开发契约**：涉及新建/重构 CLI 或 MCP 工具时，按需读取 `docs/projects/go_projects/CLI 工具开发标准.md`；
- **AI 沉淀工作流（GUIDE）**：当需把复杂流程沉淀为标准化作业指导时，按需读取 `docs/guides/README.md`；
- **AOCI 认知协议与规范**：需查阅 AOCI 架构协议或深层语法时，按需读取 `~/.agents/references/aoci.protocol.md`；
- **子模块独立性与演进记录**：涉及子模块深度背景时，按需查阅各子仓根目录 `README.md` 与 `SUBMODULES.md`。
- **按需引用库（references）**：低频操作规范收录于 `.agents/references/`（家目录 `~/.agents/references/` 等价）；**本仓专有规则归入其 `language_projects/` 子目录，跨项目件（如 `aoci.protocol.md`）置顶层**；各章节触发器（§五~§九）为**强制前置阅读**，执行对应任务前先读取。
