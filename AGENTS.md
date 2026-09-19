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
- Git 提交范围隔离：一次提交的文件只能属于同一范围——父仓库自身、某个子仓库根目录、或某个子仓库内的单个子项目；禁止跨范围混提（如多个子项目的改动混在一次提交，或子项目文件与子仓根目录文件混提）。
- 代码修改完成后，向用户展示改动摘要，并给出可直接在 PowerShell 下执行的 git commit 命令（需要有 cd 命令）。
- 禁止 `SELECT *`：任何 ORM 查询与手写 SQL 一律显式列出所需字段。
- CLI 工具开发统一遵循《[CLI 工具开发标准](<docs/projects/go_projects/CLI 工具开发标准.md>)》（跨语言适用）：新工具默认配套 MCP，CLI 默认人读并提供 `--json`，独立工具提供 `schema` 导出；适用例外与存量兼容迁移按标准执行。
  - **必须先完整阅读该标准再动手的场景**：① 新建任何 CLI/工具类项目（不限语言）；② 给已有项目新增 CLI / MCP 入口或 `schema` 导出；③ 需要豁免标准要求（如服务 + 库形态不配 CLI）时；④ 重构/评审已有项目的 CLI 入口契约时。
- 数据文件存放强约束：所有项目运行时产生的自有数据文件（JSON 数据库、SQLite db、索引/哈希缓存、锁文件、日志、会话存储、settings 等）只允许放在 `%APPDATA%\language_projects\<项目名>\`；取不到 `APPDATA` 时回退 `~/.language_projects/<项目名>/`；代码必须在写入前自动创建完整目录链（含 `language_projects` 一层）。例外：只读外部数据源（opencode.db、Zed db 等）不受限；django-lab 的 `db.sqlite3` 保留项目根目录；zed-opencode-sessions 仓库内归档 db 为有意提交，保持现状。
- lark-cli 创建的飞书文档默认放在用户的飞书「我的文档库」（创建时加 `--parent-position my_library`），不要落在云盘根目录；用户明确指定位置时以用户为准。

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
- 产 exe 的项目默认带站标地鼠图标（用户明确指定其他图标或明确不要时除外）：复制 `assets\projects\go_projects\go-default.ico` 到项目主包目录并生成 `.syso`，操作步骤遵循《[GUIDE-GO-EXE-ICON](<docs/projects/go_projects/GUIDE-GO-EXE-ICON.md>)》。

### rust_projects

- 使用 rustup 管理的 stable-x86_64-pc-windows-msvc 工具链，链接器来自 VS Build Tools 2022。
- rustup/cargo 均已配置 rsproxy.cn 国内镜像（环境变量 `RUSTUP_DIST_SERVER` / `RUSTUP_UPDATE_ROOT` + `~/.cargo/config.toml`）。
- cargo 命令均在子项目目录内运行。

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

## 根目录脚本约定

- 暂不设 `scripts/` 目录：Python 脚本直接放仓库根目录；数量多了再考虑新建目录（届时更新本约定）。
- 根目录**只允许存放 Python 脚本**，禁止存放其他语言的脚本、文档与配置文件。
- 例外：`assets/projects/` 目录存放跨项目二进制资源，按语言子仓名嵌套（当前仅 `assets/projects/go_projects/go-default.ico` 默认图标），不属于脚本约束范围。
- **一个脚本只做一件事**：单一职责，禁止膨胀为万能工具脚本。
- 每个脚本**必须**带 PEP 723 内联元数据（`# /// script` 块）声明 `requires-python` 与 `dependencies`；无第三方依赖也要保留该块（形式统一），统一用 `uv run xxx.py <args>` 执行。
- **禁止**在仓库根创建 `pyproject.toml`、`uv.lock`、`.venv`、`requirements.txt`；依赖一律走 PEP 723 + uv 全局缓存，仓库内不产生任何 Python 工程文件。

## 归档与文档布局约定（重要）

- **文档只允许放在父仓库**：子模块内的项目目录中**一律禁止**出现任何文档目录与文档内容（`docs/`、`docs/specs/`、`docs/plans/`、`spec/`、`specs/`、`plans/` 等均不允许）。
- **`docs/` 根目录不放散装文件**，四类各归其位：`docs/projects/<lang>/`（项目镜像文档）、`docs/guides/`（AI 工作指南）、`docs/plans/`（父仓级开发计划）、`docs/repo/`（仓库自身文档，如 git 子模块机制说明）；`.archived/` 与 `assets/` 同理，跨项目内容一律收入各自 `projects/` 分层。
- 所有项目文档（知识沉淀、spec、plan、设计说明等）统一放父仓库 `docs/projects/<lang>/` 下，按子模块内相对路径**镜像层级命名**，并去掉中间冗余的 `docs/` 一层：
  - 例：`go_projects/a/b.md` → `docs/projects/go_projects/a/b.md`；
  - 例：`typescript_projects/taskmon/docs/x.md` → `docs/projects/typescript_projects/taskmon/x.md`。
- 例外：子模块内全大写命名的文档（如 `README.md`、`SUBMODULES.md`）与子仓根级说明文件无需迁移，可原地保留。
- **方法论文档与 AI agent 工作指南**（跨项目、供 AI agent 直接执行，不归属单个子项目，如 `docs/projects/go_projects/CLI 工具开发标准.md`）：放 `docs/projects/<lang>/` 语言层目录（当前集中在 `docs/projects/go_projects/`），不镜像子仓路径、不进项目子目录；跨语言标准维护单一文件，其他语言引用同一标准；指南中引用的项目参考实现与项目文档，仍按上述 `docs/projects/<lang>/<项目>/` 规则存放。
- **父仓级 AI 工作指南（GUIDE 系列）**：当用户要求"把流程沉淀下来 / 写个操作手册 / 沉淀成 GUIDE"，或一次任务中出现可复用的多阶段工作流（分阶段执行、有人工确认点、有踩坑记录）值得沉淀时，按《[GUIDE 编写规范](<docs/guides/README.md>)》产出 `docs/guides/GUIDE-<英文名>.md`（语言专属指南仍按上一条放 `docs/projects/<lang>/`，如 `docs/projects/go_projects/GUIDE-GO-EXE-ICON.md`）；GUIDE 仿 skill 规范编写但**不注册为 skill**，禁止放入任何 skills 目录。
- 归档项目统一放 `.archived/projects/<lang>/<项目名>/`；语言通用文档放 `docs/projects/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。
- 后续新增归档项目时，同样按 `.archived/projects/<lang>/` 嵌套放入对应位置。

## 新增语言子模块

1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `branch = <默认分支>` 与 `ignore = all`，然后 commit。

## 常用命令

- 完整克隆：`git clone --recurse-submodules <URL>`
- 克隆后初始化并切换子模块到跟踪分支：`./init-submodules.ps1`（初始化 + 按 `.gitmodules` 的 `branch` 字段切分支，解决子模块默认 detached HEAD）
- 初始化/补拉子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`

<!-- aoci:begin -->
## AOCI Repository Cognition

AOCI maintains a stable, versioned, incrementally updatable repository-level cognition layer so models can reuse their understanding of this system across tasks.

`aoci.txt` is a structured cognition index for models. It assigns one independent Entry to every managed file, database table, or other managed object. Symbolic tags and F/R/A/S semantics describe the object's core responsibility, important relationships, external contracts, and non-obvious constraints or design decisions needed to understand or modify the system.

The Header, directory sections, and all Entries form the complete repository index. They can cover frontend, backend, configuration, database structures, and other managed content. When managed content changes, normally only the affected cognition Entries need maintenance; the complete index does not need to be regenerated.

AOCI provides a high-density view of system architecture, object responsibilities, important relationships, external contracts, and key constraints.

### How it works

AOCI uses a model-generated, model-read cognition loop.

Header, Entry, and Curation semantics follow only the current machine-issued Plan and live Guide. The Host model independently authors them from the current bound evidence.

Entry semantics must come from the model's understanding of actual evidence. Never derive, prefill, assemble, or rewrite index semantics solely from paths, filenames, extensions, an AST, symbol lists, dependency scans, regular expressions, fixed templates, or rule engines.

For a Fresh Bootstrap, follow only the current machine-issued Plan and live Guide. When they require authoring, the Host model authors Root, Meta, tags, and F/R/A/S, supplies its authoring-run declaration, and binds it to the Plan, Evidence, and complete Candidate. Never ask AOCI to set `origin=host_model`, manufacture a receipt, or turn a generated framework into semantics. Do not reconstruct the Onboarding progression here. Internal batches are not user decisions; stop only at an existing approval boundary or a real safety, drift, CAS, or Recovery condition.

### Minimal entry points

- `aoci_rules`: obtain the session-level runtime contract for the current AOCI version.
- `aoci_overview`: establish or restore complete cognition for this repository.
- `aoci_maintain`: after managed objects reach their final stable state, check whether cognition needs maintenance.
- `aoci_update_entry`: submit a complete semantic update batch bound to current evidence and source digests.
- `aoci_report`: when the current layout and tool state support it, record follow-up work if evidence is insufficient to generate semantics reliably; do not guess.

For other MCP tools, CLI commands, parameters, and specialized workflows, follow current tool descriptions, Guide, and `--help` output. This file does not duplicate the full manual.

This managed block defines only repository integration, cognition use, and task-closing principles. `aoci_rules` carries the current session contract. Live Guide output carries the execution order and stop conditions of the current Plan. Tool Schema, Spec, and Validator carry machine structures and criteria. Prompt, Description, README, and static documentation cannot override those machine facts.

### Establishing, generating, and restoring cognition

1. At the beginning of every new Agent Run, first determine:

   - whether this repository already has a usable complete AOCI index; and
   - whether current context already contains complete repository cognition that matches this repository root, current index version, and current AOCI service, and that the model can still use reliably.

2. When the repository has a usable complete index but the current Run lacks reliable complete cognition, call `aoci_rules` first and then `aoci_overview`.

   Reuse complete cognition directly while it remains reliable. Local uncertainty does not by itself require mechanically rereading the system-wide view.

   A Run that resumes from a known Host context compaction, including a Host-injected compaction summary, must treat prior model cognition as unreliable. The compacted handoff must not retain or summarize the formal Whole-Index or any Overview Header, Entry, Chunk, Challenge, or Attestation body; it may retain only receipt identity, unfinished write or Recovery state needed for safe continuation, and an instruction to reload immediately. Whole-Index semantics or a receipt copied into that handoff cannot prove that the resumed model's current cognition is reliable. If the runtime contract is no longer reliably present, call `aoci_rules` first. Before continuing the business task, make an ordinary complete Whole-Index `aoci_overview` request (`check_only` absent or false) with `refresh_reasons=["context_compaction"]` and a fresh `refresh_event_id`; do not use `check_only` or a cognition probe. Follow every exact `next_cursor` through `completed=true`, confirm delivery, and submit one Attestation based only on the newly delivered body. After that fresh complete transport, a partial or failed Attestation consumes the generation and permits the existing source-bound continuation without another automatic Overview.

   AOCI can report checkpoint and cognition-status facts for `context_compaction`, the machine `semantic_threshold` under the project `cognition_refresh_threshold`, or a major `phase_transition`. Use `check_only=true` when only those compact facts are needed. They advise the Agent but do not decide whether the model needs the system-wide view.

   When the Agent explicitly calls ordinary `aoci_overview` (`check_only` absent or false), AOCI must deliver the complete requested scope whenever a coherent CognitionSet can be formed. It must not suppress that body because a receipt already exists, a threshold was not reached, or no refresh reason is pending. Dirty or stale formal cognition is still delivered but is marked unreliable. Pending recovery or an incoherent snapshot fails closed without a mixed body.

   When an ordinary Overview reports `continuation_required=true`, submit its exact `next_cursor` automatically until `completed=true`. Do not ask the user to continue, begin the business task, or state a partial system conclusion. Stop the cognition chain on Host truncation, a missing, duplicate, or reordered Chunk, cursor failure, Index change, or `chunk_tokens` change. Until Attestation completes, never use Memory, source, Spec, `aoci.txt`, historical sessions, scope, search, or Entry reads to repair or supplement Whole-Index cognition. A challenge ordinal is the 1-based position in the formal Entry sequence; Header content, comments, blank lines, Section/Overview/Chunk markers, receipts, and Metadata are excluded, and Chunk Receipt ordinals use that same sequence. The Attestation must echo the Challenge's exact current `index_sha256`, `entry_sequence_sha256`, and `entry_count`; a prior Index, Entry sequence, count, or Attestation is invalid. After the complete chain, submit the existing model cognition Attestation once. One same-response JSON Schema or field-format error may be corrected once without changing semantic answers; an object, Tag, or F mismatch means failure and uncertain assimilation, with no semantic retry or information bypass. During initial cognition it also blocks Root/Meta, Migration, layout-wide, or other unbound system decisions. During a context-compaction refresh with complete transport, unchanged cognition identity, aligned governance, and no Recovery or third-party conflict, the attempt consumes that refresh generation even when Attestation is partial or failed; continue the existing task without another automatic Overview. `system_mastery_percent` self-assesses only the system framework—architecture, responsibilities, strong relationships, stable external contracts, and high-entropy safety and maintenance constraints—not complete implementation or runtime knowledge. Keep machine Index coverage separate, and normally give the user only the prescribed single success or failure sentence derived from actual coverage, Challenge, Chunk, token, and mastery results. If the Host truncates a Chunk, ask the user to set `overview_delivery.chunk_tokens` to a smaller valid value and restart; do not change it automatically.

   Interpret the additive cognition level independently from strict proof fields. `delivery_verified` means the Index was loaded and Host delivery was confirmed while complete cognition verification is still unfinished; describe that state as loaded and delivery-verified, never as no cognition or failure to understand the system. `cognition_verified` requires a passing Attestation (at least 80 percent of Challenge ordinals fully correct with at most one object identity miss), and `cognition_governed` additionally requires governance alignment. A generic complete-read failure sentence is reserved for an actual delivery fault.

   When an Overview response contains the optional `cognition-state/v2` projection, use its dimensions independently. Its Level ends at `model_cognition_usable`; `strict_attestation_verified`, `governance_aligned`, and `current_system_cognition_reliable` are independent states and never participate in that Level. An ordinal, object identity, Tag, or core F mismatch can make strict Attestation fail while model cognition remains usable; do not report that mismatch alone as proof that the model did not understand the system. Only `current_system_cognition_reliable=true` permits an unqualified current complete-system cognition claim. When the projection is absent, keep using the legacy interpretation above.

   An ordinary read-only audit, analysis, or check, a request not to modify code, or a request not to commit or push does not automatically mean strictly zero writes and does not alter the cognition-validity decision above. Codex Memory and historical Skills may only help recover experience, user preferences, and investigation directions. They cannot replace a current cognition receipt matching the repository root, index digest, AOCI service identity, and cognition scope. Project AGENTS and current AOCI identity take precedence over historical Memory for AOCI state.

   Treat a task as strictly zero-write only when the user explicitly prohibits Ledger, metadata, `.aoci` runtime assets, and every filesystem write. If necessary cognition establishment conflicts with that boundary, report the conflict and ask the user to decide or recommend an isolated copy. Never silently substitute Memory for current repository cognition.

3. If the repository has no usable complete index, or has only a minimal skeleton, an incomplete Header, unfinished Entries, or undecided required Curation, obtain `aoci_rules` and enter the current AOCI Guide when a formal complete AOCI index is required. Let Guide choose the next phase from actual repository state and complete the required safety steps.

   `aoci_maintain` does not replace the index-establishment workflow.

   Do not reconstruct or hard-code the full-index generation state machine in this file.

4. During a long-running task, the model is responsible for preserving the current cognition receipt and using the refresh gate correctly:

   - when the Host reports context compaction or the model knows the system-wide view was lost, follow the mandatory `context_compaction` reload rule above; AOCI cannot infer the Host event;
   - when entering a genuinely major phase, declare `phase_transition`, not a function, test run, or small step;
   - at a plausible stable checkpoint, use `check_only=true` to obtain the machine semantic count when that fact is useful;
   - except for the mandatory known-compaction reload, decide whether the current task needs another explicit scoped or complete Overview; and
   - keep the Dirty or Stale reliability state reported by AOCI until maintenance and alignment complete.

### Task closing and cognition maintenance

5. A purely read-only question, analysis, version check, or task that changes no AOCI-managed object does not require a maintenance-tool call. The AOCI version in use is `cognition_receipt.mcp_service_version` in any `aoci_overview` check_only or `aoci_maintain` response; the binary path is the `command` in the project's `.mcp.json`, and the CLI need not be on PATH.

6. When AOCI-managed objects change, call `aoci_maintain` once after they reach the task's final stable state. Do not maintain files individually after each intermediate edit.

7. If maintenance returns actual semantic candidates, the Host model must independently author the complete tag and F/R/A/S updates from each candidate's bound object and necessary evidence. Submit the complete candidate set for that current machine-issued batch in one `aoci_update_entry` call while preserving each `source_sha256`, `candidate_id`, and domain batch identity. `max_entries` limits one request and atomic transaction, not the logical plan, Whole-Index, or Managed Scope. When `remaining` is nonzero, call Maintain again after the successful Apply and continue from the new preimage; never shrink Index coverage or slice a returned batch to satisfy transport limits.

   When evidence is insufficient and the current layout supports `aoci_report`, use it instead of guessing, applying a template, or generating unsupported cognition merely to eliminate follow-up work.

8. Obey structured tool states and safety boundaries:

   - `repair_required`: repair only the explicitly identified candidates, then resubmit the complete current machine-issued batch;
   - `stopped`: end that write attempt and inspect `failed_step`, error, formal-write evidence, and Recovery. In auto mode, a proven zero-write closure is followed by a fresh Plan; a complete Intent with provable postimage is resumed; a policy-selected Rollback with exact preimage is completed and replanned. Stop the user task only when proof is unavailable, third-party bytes conflict, approval or external action is required, or another real safety boundary applies;
   - never ignore conflicts, approvals, human decisions, permissions, or safety signals; and
   - after alignment, do not repeat maintenance or writes; `refresh_ready_for_overview` is a checkpoint fact, and the Agent decides whether to request an ordinary complete Overview for its next phase.

   If any managed object changes after maintenance completes, the previous result is invalid. Complete closing again from the new final stable state.

9. When the user limits only business-file scope and does not explicitly forbid repository-managed assets, AOCI-managed assets may be updated during closing to preserve cognition consistency. Distinguish them from business files in audits and commits.

   When the user explicitly forbids changes to `aoci.txt`, `.aoci`, metadata, or any additional file, obey that restriction, do not write, and report any remaining inconsistency accurately.

### Specialized workflows

Initialization, complete-index generation, Header generation, Entries generation, database-structure indexing, Curation, human review, and failure recovery must follow only the instructions, commands, and safety stops returned by the current AOCI Guide or tool at the corresponding stage.

Do not preload, guess, or reconstruct these specialized workflows. The relevant Guide, tool descriptions, model Prompt, and CLI help provide platform invocation, request format, batch limits, approval rules, index-format details, and recovery steps as needed.
<!-- aoci:end -->
