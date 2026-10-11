# 02-VSCode 按项目软关闭多语言 LSP 实施计划

## 概述

**问题陈述**：本机 VS Code 全局全开所有语言 LSP，打开 `language_projects` 根目录时 Go/Rust/Python/C++ 等语言服务器同时扫描，常驻内存高。需要像 Zed 白名单一样，在只做某一语言时让其他语言 LSP 静默，且切换项目自动生效。

**需求**（已确认）：
- 范围：仅 VS Code 侧（1=a），不动 Zed 配置。
- 粒度：软关闭（2=a），扩展保留，只关语言服务器与自动构建检查，不做 Profile 硬隔离。
- 交付：单文件落盘计划（3=a），交由其他 AI 执行。

**背景**：
- 全局设置 `%APPDATA%\Code\User\settings.json` 无按语言开关；仓库 `d:\Users\language_projects\.vscode\` 下仅有 `tasks.json`，无 `settings.json`。
- 已装语言扩展：`ms-python.python` + Pylance、`golang.go`、`rust-lang.rust-analyzer`、`ms-vscode.cpptools` + cmake-tools、`sumneko.lua`；`redhat.java` 缺失。
- VS Code 无全局 `enable_language_server` 总开关，LSP 随扩展激活；按项目开关靠工作区 `settings.json` 覆盖。

**方案**：
- 不在根 `.vscode/settings.json` 做统一关闭（原因见下）。
- 采用“全局保持全开 + 各项目目录下放 `.vscode/settings.json` 覆盖关闭不需要的语言”；根目录仅保留通用编辑器设置。
- 关于“放在主目录 `.vscode` 里不行吗”：行，但达不到你要的效果。根 `settings.json` 作用域是整个工作区，用它只能一刀切全关/全开，无法区分“当前做 Go 还是做 Python”；打开根目录时所有子项目同时被扫描，五个语言的开关会互相打架。真想要“打开哪个项目、哪个 LSP 才跑”，设置必须下沉到各项目目录（或改用多根工作区 `.code-workspace` + 按文件夹设置）。

## 任务分解

- [ ] Task 1: 盘点各目标项目目录与语言归属
  - 文件：仅读取，不新建（`go_projects/`、`python_projects/`、`rust_projects`、`java_projects/`、`native_projects/` 下各项目目录清单）
  - 实现：列出要下放设置的项目目录清单；确认 Java 项目是否需先补装 `redhat.java`
  - 验证：`code --list-extensions` 确认语言扩展现状，与预期清单一致
  - Demo：能说出每个设置文件要放到哪几个目录

- [ ] Task 2: 编写五类语言的 settings.json 模板
  - 文件：`docs/projects/repo/vscode-lsp-soft-toggle-templates.md`（模板集中放父仓文档，不进子模块；仅模板，不直接下发）
  - 实现：按 Go-only / Rust-only / Python-only / Java-only / Cpp-only 五类写模板；核心键：`go.useLanguageServer`、`python.languageServer`、`rust-analyzer.checkOnSave`、`java.autobuild.enabled`、`C_Cpp.intelliSenseEngine`、`cmake.configureOnOpen`；注释写中文
  - 验证：JSON 语法校验通过（`python -m json.tool` 对每份模板无报错，去掉注释后）
  - Demo：能展示任意一类模板全文

- [ ] Task 3: 下放设置到各项目并验证隔离效果
  - 文件：各目标项目下的 `.vscode/settings.json`（同一改动模式跨多文件计为一项，逐文件列清单）
  - 实现：按 Task 1 清单复制对应模板；Java 项目若缺 `redhat.java` 则先 `code --install-extension redhat.java`；不动全局设置与 `.zed/` 配置
  - 验证：分别单开一个 Go 项目与一个 Python 项目，从 Output 面板确认非常驻语言的语言服务器未启动
  - Demo：打开 Go 项目只见 gopls，打开 Python 项目只见 Pylance

## 关键决策

- 软关闭而非 Profile 硬隔离：切换成本最低，交由其他 AI 可一次性批量执行。
- 设置下沉而非根统一关：根统一关无法按项目区分语言，违背“当前做什么、什么才跑”的目标。
- Java 需补扩展：本机缺 `redhat.java`，`settings.json` 残留旧键不生效。

---
**最后更新：** 2026-10-10
**作者：** AI & User
**版本：** v1.1（纠正落盘位置至 docs/plans/）
