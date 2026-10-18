# 各语言子仓约定（自根 AGENTS.md §五 迁出 · 按需引用）

> **触发**：进入任一语言子仓/子项目动工前必读对应语言章节。本文件不在规则自动加载目录（`.agents/rules/`）内，由根 `AGENTS.md` 触发器指引按需读取。

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

### java_projects
- **定位**：Java 21 + Spring Boot 3 的**企业级 JVM 服务端**方向（子仓 `td-java_projects`，父 POM 多模块）；CLI / GUI / 系统底层不归 Java（Go / Rust 已优于 Java，论证见 `docs/repo/Java 与 python-go-rust 子仓对比分析.md`）。
- **构建**：用 `cmd /c` 显式注入 `JAVA_HOME` 并调用 `mvn.cmd`，以锁定 JDK 21；三个服务端口固定 8080 / 8081 / 8082（模块与接口表见子仓 `README.md`）。
- **规则继承指针**：子仓根 `AGENTS.md` / `CLAUDE.md` 分别指向 `../AGENTS.md` 与单行 `@../AGENTS.md`。
