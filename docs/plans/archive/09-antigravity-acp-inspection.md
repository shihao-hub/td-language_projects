# 📋 Plan: Antigravity ACP 源码解包、子目录扫描探索与上游监控

**创建日期**：2026-09-23
**状态**：已完成
**关联文件**：
- [settings.json](file:///D:/Users/language_projects/.zed/settings.json)
- [.thirdparty](file:///D:/Users/language_projects/.thirdparty)
- [.scripts](file:///D:/Users/language_projects/.scripts)

---

## 1. 问题陈述与调研背景

### 1.1 `jiridanek/agy-acp` 等社区仓库为什么会出现？
- **官方初期缺位**：Google Antigravity（`agy` CLI）初期专注于自研独立终端交互，并未内置支持开放的 Agent Client Protocol（ACP）`stdio` 服务模式。
- **第三方桥接需求**：Zed、JetBrains（AI Chat）等现代 IDE 全面拥抱 ACP 标准协议，社区开发者（如 `jiridanek`、`shubzkothekar` 等）通过调用 Google 官方 `google-antigravity` SDK，外包封装了基于 JSON-RPC over stdio 的 ACP 桥接层。
- **官方后续整合**：Google 在发布 Antigravity 2.0 及 IDE Extensions 时，官方基于内部 codebase 构建了专用的 `agy_acp_server` 二进制发布物，并直接注册到官方 ACP Registry（`id: "antigravity-acp"`），替代了早期第三方的非官方桥接。

### 1.2 PyInstaller 解包现状
- 本地 `agy_acp_server.exe`（~430MB）使用 PyInstaller 打包，内置完整的 Python 3.10 运行时。
- 其业务源码位于 `google3/cloud/developer_experience/antigravity_extensions/acp_server/`，均为未混淆的纯 Python 源码（包含 `server.py`、`oauth/`、`ccpa_connection/` 等）。
- 运行时已解压至 `%TEMP%\_MEI*`，可直接复制核心树，避免解压全量 wheel 和 pyc/pyd 导致工作区膨胀。

### 1.3 工作区各子目录扫描摸底（实测数据）

当前各一级子目录的条目分布实测如下：

| 一级目录 | 总条目数 (Files+Dirs) | `.venv` 数量 | `node_modules` 数量 | `target` 数量 | 说明与现状 |
|---|---|---|---|---|---|
| `python_projects` | **73,800** | **11** | 0 | 0 | ⚠️ 最大条目来源；用户因需要索引/跳转明确保留 `.venv` |
| `.thirdparty` | **67,889** | 1 | 858 | 0 | ⚠️ 第三方依赖较深，需确保 node_modules 规则生效 |
| `typescript_projects` | **45,530** | 0 | 1,352 | 0 | node_modules 虽被排除，但源码结构依然有一定体量 |
| `.archived` | **3,475** | 1 | 0 | 0 | 归档项目，仍含 1 个 `.venv` |
| `rust_projects` | **2,745** | 0 | 0 | 2 | 编译产物已通过 `**/target` 排除 |
| `go_projects` | **329** | 0 | 0 | 0 | 极为轻量 |
| `docs` | **154** | 0 | 0 | 0 | 文档区，轻量 |
| 其他 (`.aoci` 等) | ~340 | 0 | 0 | 0 | 辅助与配置脚本 |

**扫描优化评估**：
- 当前 `.zed/settings.json` 已正确排除了 `**/node_modules` 和 `**/target`。
- 因为用户约束「`.venv 不能忽略`」，导致 `python_projects` 中的 11 个虚拟环境完全暴露在 Zed 的文件扫描器与 watcher 中，合计占用约 7.3 万条目。
- 建议保持核心项目 `.venv` 打开，而对于 `.archived` 或历史废弃目录做针对性排除（如 `**/.archived/**`），防止条目越界。

---

## 2. 需求与确认决策

- **源码提取范围**：用户确认选项 `1=a`，仅提取 `google3/...` 核心业务逻辑（ACP 服务端、OAuth、CCPA Onboarding 等纯 Python 源码）到 `.thirdparty/antigravity-acp-src/`。
- **扫描统计交付**：用户确认选项 `2=a`，直接在计划与总结报告中输出摸底数据与 `.zed/settings.json` 优化建议。
- **监控脚本模式**：用户确认选项 `3=a`，编写轻量脚本到 `.scripts/`，既可免 Token 校验 ACP Registry 最新版本，也可通过 GitHub Search API 查询上游新仓库。

---

## 3. 方案设计

### 3.1 核心源码提取方案
- 提取源：从 `%TEMP%\_MEI*` 中提取最新的 `google3/cloud/developer_experience/antigravity_extensions/acp_server`；
- 目标目录：`D:/Users/language_projects/.thirdparty/antigravity-acp-src/`；
- 过滤：排除 `__pycache__`、二进制扩展与无关证书 bundle，仅保留 `.py`、`.json`、协议定义和许可文件；
- 产出结构：直接可阅读的纯 Python 结构，清晰浏览 `server.py` (ACP 协议核心实现)、`oauth/`、`ccpa_connection/`。

### 3.2 上游检索脚本方案 (`check-agy-upstream.ps1`)
- 放置于 `D:/Users/language_projects/.scripts/check-agy-upstream.ps1`；
- 功能：
  1. 联网查询官方 ACP Registry JSON（`https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json`），提取 `antigravity-acp` 当前注册版本与下载 URL；
  2. 对比本地已安装版本（`%LOCALAPPDATA%\Zed\external_agents\registry\registry.json`），直接给出是否有新版本发布；
  3. 调用 GitHub API（`api.github.com/search/repositories?q=antigravity+acp` & `api.github.com/search/repositories?q=agy-acp`）检索活跃相关仓库列表（包含星标、最后更新时间、主页链接）。

---

## 4. 任务分解

- [x] **Task 1: 提取 Antigravity ACP 核心 Python 源码到 `.thirdparty`**
  - **文件**：`D:/Users/language_projects/.thirdparty/antigravity-acp-src/`
  - **实现**：定位有效 `_MEI*` 目录，将 `google3/cloud/developer_experience/antigravity_extensions/acp_server` 递归复制到目标路径，自动剔除缓存文件；在根目录生成 `README.md` 索引核心模块导读。
  - **验证**：`Test-Path "D:\Users\language_projects\.thirdparty\antigravity-acp-src\server.py"` 返回 `True`。
  - **Demo**：可在 Zed 侧栏 `.thirdparty/antigravity-acp-src/` 中直接点击阅读 `server.py`、`credential_manager.py` 与 `onboard.py`。

- [x] **Task 2: 评估与更新 `.zed/settings.json` 排除规则**
  - **文件**：[settings.json](file:///D:/Users/language_projects/.zed/settings.json)
  - **实现**：根据摸底数据，保持各开发项目的 `.venv` 不排除，但对 `.archived` 归档目录及新建的源码归档目录增加定向排除，确保 Zed 扫描条目稳定受控。
  - **验证**：检查 `.zed/settings.json` 语法合法且保留了 `.venv`。
  - **Demo**：Zed 不会因为 `.archived` 的虚拟环境和冗余条目产生额外的 watcher 压力。

- [x] **Task 3: 编写上游更新检测与 GitHub 仓库搜索脚本**
  - **文件**：`D:/Users/language_projects/.scripts/check-agy-upstream.ps1`
  - **实现**：编写 PowerShell 脚本，集成 ACP Registry 官方版本比对与 GitHub 关键词检索，带清晰的色彩输出与状态提示。
  - **验证**：运行 `powershell -ExecutionPolicy Bypass -File .scripts/check-agy-upstream.ps1`，成功输出本地版本 vs 官方最新版本以及 GitHub 仓库搜索列表。
  - **Demo**：命令行直接一键运行，直观看到当前是否有 `antigravity-acp` 更新。

---

**最后更新**：2026-09-23
**状态**：全部任务已完成