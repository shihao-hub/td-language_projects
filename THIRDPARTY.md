# .thirdparty 第三方项目与参考库归档清单

> **目录定位**：根目录下的 `.thirdparty/` 已被 `.gitignore` 忽略，不随本仓库提交。
> 本文档专门用于**登记 `.thirdparty/` 目录中的全部外部组件、Git 远端仓库地址、检出分支与提交版本，以及本地定制改动与恢复指南**，方便在更换机器、目录清理或重置后快速完整恢复。

---

## 一、速查盘点总表

当前 `.thirdparty/` 下共包含 **20** 个条目（17 个 Git 上游仓库，3 个非 Git 归档/工具目录）：

| 组件名称 | 类型 | 远端仓库地址 (HTTPS / SSH) | 跟踪分支 / 标签 | 基线 Commit | 本地定制 / 特殊说明 |
|---|:---:|---|---|:---:|---|
| [`Antigravity-Hans`](#1-antigravity-hans) | Git | `https://github.com/yuexps/Antigravity-Hans.git`<br>`git@github.com:yuexps/Antigravity-Hans.git` | `feat/fyne-gui` (基于 `v0.4.4`) | `6655319` | 包含 3 个本地提交（Fyne GUI 构建流水线支持） |
| [`antigravity-acp-src`](#2-antigravity-acp-src) | 源码提取 | 非 Git 仓库（提取自官方二进制） | N/A | N/A | Google Antigravity ACP 核心源码（解包自 `v_1.1.1`） |
| [`claude-code-transcripts`](#3-claude-code-transcripts) | Git | `https://github.com/simonw/claude-code-transcripts.git` | `main` | `316fd09` | Simon Willison 开源的 Claude Code 会话记录工具 |
| [`ClaudeScope`](#4-claudescope) | Git | `https://github.com/Liuziyu77/ClaudeScope.git` | `main` | `d690945` | Claude Code 会话执行轨迹与思维链可视化 UI |
| [`codex`](#5-codex) | Git | `https://github.com/openai/codex.git` | `main` | `4fd5745` | OpenAI 官方开源本地终端编程 Agent CLI |
| [`commerce-agents`](#6-commerce-agents) | Git | `https://github.com/anthropics/commerce-agents.git` | `main` | `fd4d592` | Anthropic 官方开源 Claude 商业/电商 Agent 范式 |
| [`ContextMenuManager`](#7-contextmenumanager) | Git | `https://github.com/BluePointLilac/ContextMenuManager.git` | `master` | `5550715` | Windows 纯粹右键菜单管理程序（C# / .NET） |
| [`deepseek-harness`](#8-deepseek-harness) | Git | `https://github.com/deepseek-ai/deepseek-harness.git` | `master` (标签 `dsh-v0.2.0-rc.1`) | `4878cda` | DeepSeek 官方开源评测框架与 Harness 工具 |
| [`dive-into-llms`](#9-dive-into-llms) | Git | `https://github.com/Lordog/dive-into-llms.git` | `main` | `f84c042` | 《动手学大模型》系列编程实践教程与学习资料库 |
| [`docs`](#10-docs) | 文档 | 非 Git 仓库（本地调研文档） | N/A | N/A | 包含 `cli_debugging_guide.md`（终端调试实战指南） |
| [`FerretDB`](#11-ferretdb) | Git | `https://github.com/FerretDB/FerretDB.git` | `main` | `799235d` | Go 实现的开源 MongoDB 替代方案（转译 PG/SQLite） |
| [`mini-swe-agent`](#12-mini-swe-agent) | Git | `https://github.com/SWE-agent/mini-swe-agent.git` | `main` | `db3dce9` | 领先上游 3 个提交（补充中文 README、文档与中英注释） |
| [`minimax-code`](#13-minimax-code) | Git | `https://github.com/MiniMax-AI/minimax-code.git` | `main` | `8b55164` | MiniMax 官方开源代码编程助手与 Agent CLI |
| [`nanocode`](#14-nanocode) | Git | `https://github.com/1rgs/nanocode.git` | `master` | `b009d3d` | 包含本地修改（`nanocode.py` 定制多模型扩展与测试） |
| [`nanocode-acl-recovery`](#15-nanocode-acl-recovery) | 脚本备份 | 非 Git 仓库（Windows 运维产物） | N/A | N/A | nanocode 目录 Windows ACL 权限备份与恢复脚本 |
| [`opencode`](#16-opencode) | Git | `https://github.com/anomalyco/opencode.git` | `dev` | `ad6c72c` | 开源终端 AI 编程助手系统（TS/Node.js 实现） |
| [`pi-mono`](#17-pi-mono) | Git | `https://github.com/badlogic/pi-mono.git` | `main` | `6160683` | Mario Zechner 开源的 pi 智能体与工具生态 Monorepo |
| [`QwenPaw`](#18-qwenpaw) | Git | `https://github.com/agentscope-ai/QwenPaw.git` | `main` (标签 `v2.2.1-beta.1`) | `a403b24` | 基于 AgentScope 与 Qwen 的智能体个人助手框架 |
| [`screenshot-to-code`](#19-screenshot-to-code) | Git | `https://github.com/abi/screenshot-to-code.git`<br>`git@github.com:abi/screenshot-to-code.git` | `local-glm` (本地定制分支) | `32d3fec` | 包含本地提交 `feat: 支持用 GLM 驱动本应用` 及适配代码 |
| [`ZCode`](#20-zcode) | Git | `https://github.com/zai-org/ZCode.git` | `main` (标签 `v3.14.3`) | `29628c9` | 智谱 AI (ZAI) 开源的代码生成与开发提效工具套件 |

---

## 二、各组件详细信息与恢复指南

### 1. Antigravity-Hans
- **定位**：Google Antigravity 与 Antigravity IDE 的中文汉化工具及 GUI 构建流水线。
- **远端地址**：
  - HTTPS: `https://github.com/yuexps/Antigravity-Hans.git`
  - SSH: `git@github.com:yuexps/Antigravity-Hans.git`
- **检出分支**：`feat/fyne-gui`（基于标签 `v0.4.4`）
- **基准提交**：`665531947ca3e414b56343514f2898bd245101cd`
- **本地改动说明**：本地分支包含 3 个定制提交：
  1. `3ad3d28 Antigravity-Hans:feat: 移除 GUI IDE 按钮并引入专属矢量图标流水线`
  2. `7070668 Antigravity-Hans:chore: build-gui 支持 --dev 显式编译开发版`
  3. `6655319 Antigravity-Hans:docs: 完善 build-gui.py 头部注释与产物命名用法说明`
- **恢复命令**：
  ```bash
  git clone https://github.com/yuexps/Antigravity-Hans.git .thirdparty/Antigravity-Hans
  cd .thirdparty/Antigravity-Hans
  # 若远端已同步 feat/fyne-gui 分支则直接切换；否则基于 v0.4.4 创建分支
  git switch feat/fyne-gui 2>/dev/null || git switch -c feat/fyne-gui v0.4.4
  ```

---

### 2. antigravity-acp-src
- **定位**：Google 官方 Antigravity ACP (Agent Client Protocol) Server 核心源码归档。
- **来源机制**：非 Git 仓库。由官方发布的 `agy_acp_server.exe` (PyInstaller 打包) 逆向提取得出，对应版本 `antigravity-acp v_1.1.1`。
- **关键文件**：
  - `server.py`：核心 JSON-RPC 路由与 ACP 方法实现（initialize, authenticate, session/prompt 等）。
  - `tools.py`：向 IDE 暴露的工具定义与调用转发。
  - `oauth/`：本地 OAuth 环回服务与凭据文件读写。
  - `ccpa_connection/`：CloudCode PA 与订阅 Tier 确认。
- **关联文档**：完整架构拓扑、时序与证据链见本仓库 `docs/repo/antigravity-acp-architecture-research.md`。

---

### 3. claude-code-transcripts
- **定位**：Simon Willison 开源的用于处理与查看 Anthropic Claude Code 历史会话 transcripts 的工具。
- **远端地址**：`https://github.com/simonw/claude-code-transcripts.git`
- **检出分支**：`main`（Commit: `316fd093aca3c9c0ad8aa70092711aee3adacc6e`）
- **恢复命令**：
  ```bash
  git clone https://github.com/simonw/claude-code-transcripts.git .thirdparty/claude-code-transcripts
  ```

---

### 4. ClaudeScope
- **定位**：Claude Code 会话执行轨迹与思维链可视化 UI 工具。
- **远端地址**：`https://github.com/Liuziyu77/ClaudeScope.git`
- **检出分支**：`main`（Commit: `d690945160b1e2ee66b5eaf709b1a052474883ff`）
- **恢复命令**：
  ```bash
  git clone https://github.com/Liuziyu77/ClaudeScope.git .thirdparty/ClaudeScope
  ```

---

### 5. codex
- **定位**：OpenAI 官方开源的本地终端智能编程 Agent CLI 工具（Codex CLI）。
- **远端地址**：`https://github.com/openai/codex.git`
- **检出分支**：`main`（Commit: `4fd5745e8486d655a0c7e7d762741465b986130b`）
- **恢复命令**：
  ```bash
  git clone https://github.com/openai/codex.git .thirdparty/codex
  ```

---

### 6. commerce-agents
- **定位**：Anthropic 官方开源的 Claude 商业/电商场景智能体示例工程与多步决策工作流。
- **远端地址**：`https://github.com/anthropics/commerce-agents.git`
- **检出分支**：`main`（Commit: `fd4d59224ab96b43c6dc6888207c67b3bd5a24cf`）
- **恢复命令**：
  ```bash
  git clone https://github.com/anthropics/commerce-agents.git .thirdparty/commerce-agents
  ```

---

### 7. ContextMenuManager
- **定位**：Windows 平台纯粹、高效的右键菜单配置管理工具（开源 .NET/C#）。
- **远端地址**：`https://github.com/BluePointLilac/ContextMenuManager.git`
- **检出分支**：`master`（Commit: `55507155dd8e49c7ab4606da97f2af192d590dfe`）
- **恢复命令**：
  ```bash
  git clone https://github.com/BluePointLilac/ContextMenuManager.git .thirdparty/ContextMenuManager
  ```

---

### 8. deepseek-harness
- **定位**：DeepSeek 官方开源的评估基准与测试 Harness 工具。
- **远端地址**：`https://github.com/deepseek-ai/deepseek-harness.git`
- **检出分支**：`master`（标签：`dsh-v0.2.0-rc.1`，Commit: `4878cdabd87d4041bdaff61d04c966883b9fd07a`）
- **恢复命令**：
  ```bash
  git clone https://github.com/deepseek-ai/deepseek-harness.git .thirdparty/deepseek-harness
  cd .thirdparty/deepseek-harness
  git checkout dsh-v0.2.0-rc.1
  ```

---

### 9. dive-into-llms
- **定位**：《动手学大模型》系列实战编程教程，含主流大模型从预训练、微调到部署的技术指南。
- **远端地址**：`https://github.com/Lordog/dive-into-llms.git`
- **检出分支**：`main`（Commit: `f84c04268794ef94f8949808bbc14ab8636763a0`）
- **恢复命令**：
  ```bash
  git clone https://github.com/Lordog/dive-into-llms.git .thirdparty/dive-into-llms
  ```

---

### 10. docs
- **定位**：存放单篇深度调研与工程实战参考文档。
- **说明**：非 Git 仓库。目前包含 `cli_debugging_guide.md`（终端调试 CLI Debug 系统性研究与实战指南，覆盖 GDB、LLDB、pdb、Delve、Node.js 调试器及 Linux 内核诊断 strace/core dump 等）。

---

### 11. FerretDB
- **定位**：真正的开源 MongoDB 替代方案（Go 实现），将 MongoDB 协议通信映射为 PostgreSQL / SQLite 查询。
- **远端地址**：`https://github.com/FerretDB/FerretDB.git`
- **检出分支**：`main`（Commit: `799235dab9e350655e72e65a0b24d849f7d68143`）
- **恢复命令**：
  ```bash
  git clone https://github.com/FerretDB/FerretDB.git .thirdparty/FerretDB
  ```

---

### 12. mini-swe-agent
- **定位**：SWE-agent 团队推出的轻量级开源软件工程 Agent（Minimal AI Software Engineering Agent）。
- **远端地址**：`https://github.com/SWE-agent/mini-swe-agent.git`
- **检出分支**：`main`（Commit: `db3dce937c32f920fc5e45e1cfdc4a731d7e188d`）
- **本地改动说明**：本地领先官方 `origin/main` 3 个提交，完成全套中文本土化：
  1. `7e81662a docs: 添加中文 README 文档`
  2. `c922a736 docs: 补充根目录下其他文档的中文版本`
  3. `db3dce93 docs: src/minisweagent 注释与文档字符串增加中英双语对照`
- **恢复命令**：
  ```bash
  git clone https://github.com/SWE-agent/mini-swe-agent.git .thirdparty/mini-swe-agent
  ```

---

### 13. minimax-code
- **定位**：MiniMax 官方开源的代码编程助手与智能体 CLI 工具。
- **远端地址**：`https://github.com/MiniMax-AI/minimax-code.git`
- **检出分支**：`main`（Commit: `8b5516443305d25e550faa5406aef870c029b144`）
- **恢复命令**：
  ```bash
  git clone https://github.com/MiniMax-AI/minimax-code.git .thirdparty/minimax-code
  ```

---

### 14. nanocode
- **定位**：极简（百行级）命令行 AI 编程 Agent 原型实现。
- **远端地址**：`https://github.com/1rgs/nanocode.git`
- **检出分支**：`master`（Commit: `b009d3dbedf14795a5c10804a5455386563f4b5b`）
- **本地改动说明**：本地对 `nanocode.py` 进行了多项功能扩充（支持接入本地及国内模型、命令行增强），并保留 `replica_nanocode.py`、`demo.py`、`.env` 等本地运行套件。
- **恢复命令**：
  ```bash
  git clone https://github.com/1rgs/nanocode.git .thirdparty/nanocode
  ```

---

### 15. nanocode-acl-recovery
- **定位**：Windows 系统下 nanocode 目录 ACL 权限异常排查与还原脚本套件。
- **说明**：非 Git 仓库。包含 `acl-backup-*.json`、PowerShell 权限还原执行脚本 `acl-backup-*.json.ps1` 以及权限检查报告 `acl-report-*.jsonl`。

---

### 16. opencode
- **定位**：全功能开源终端 AI 辅助编程系统（TypeScript / Node.js 实现，支持多模型与 rich TUI）。
- **远端地址**：`https://github.com/anomalyco/opencode.git`
- **检出分支**：`dev`（Commit: `ad6c72c7068812d43b31f3cfb9e413356a19d850`）
- **恢复命令**：
  ```bash
  git clone -b dev https://github.com/anomalyco/opencode.git .thirdparty/opencode
  ```

---

### 17. pi-mono
- **定位**：Mario Zechner (badlogic) 开源的 pi 智能体与跨平台 Monorepo。
- **远端地址**：`https://github.com/badlogic/pi-mono.git`
- **检出分支**：`main`（Commit: `6160683a4a8012f0d1cd30c145df18b4ca6f5176`）
- **恢复命令**：
  ```bash
  git clone https://github.com/badlogic/pi-mono.git .thirdparty/pi-mono
  ```

---

### 18. QwenPaw
- **定位**：基于 AgentScope 与 Qwen 官方模型构建的个人专属智能体助手框架。
- **远端地址**：`https://github.com/agentscope-ai/QwenPaw.git`
- **检出分支**：`main`（标签：`v2.2.1-beta.1`，Commit: `a403b2433af6ac74404d69fc80a289658996226e`）
- **恢复命令**：
  ```bash
  git clone https://github.com/agentscope-ai/QwenPaw.git .thirdparty/QwenPaw
  cd .thirdparty/QwenPaw
  git checkout v2.2.1-beta.1
  ```

---

### 19. screenshot-to-code
- **定位**：视觉多模态智能体，将网页或 UI 设计图截图一键转为 HTML / Tailwind / React / Vue 代码。
- **远端地址**：
  - HTTPS: `https://github.com/abi/screenshot-to-code.git`
  - SSH: `git@github.com:abi/screenshot-to-code.git`
- **检出分支**：`local-glm`（本地定制分支）
- **基准提交**：`32d3fec0dbc4ed8b60f0ddb1a83d43419af7d946`
- **本地改动说明**：
  - 本地提交：`32d3fec feat: 支持用 GLM 驱动本应用`
  - 工作区改动：`backend/codegen/utils.py` 中适配智谱 GLM API 调用与流式输出。
- **恢复命令**：
  ```bash
  git clone https://github.com/abi/screenshot-to-code.git .thirdparty/screenshot-to-code
  cd .thirdparty/screenshot-to-code
  # 检出上游基线
  git checkout d026163
  ```

---

### 20. ZCode
- **定位**：智谱 AI / ZAI 开源的代码生成与开发提效工具套件。
- **远端地址**：`https://github.com/zai-org/ZCode.git`
- **检出分支**：`main`（标签：`v3.14.3`，Commit: `29628c9acdb81b703bbd4080c207a0e7ce5e276e`）
- **恢复命令**：
  ```bash
  git clone https://github.com/zai-org/ZCode.git .thirdparty/ZCode
  cd .thirdparty/ZCode
  git checkout v3.14.3
  ```

---

## 三、一键全量恢复方案

### 1. PowerShell 快捷命令

在仓库根目录下打开 PowerShell 执行以下命令，将自动创建 `.thirdparty/` 目录并拉取所有 17 个外部 Git 仓库：

```powershell
$root = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
$tp = Join-Path $root ".thirdparty"
if (-not (Test-Path $tp)) { New-Item -ItemType Directory -Path $tp -Force }

$repos = @(
    @{ Name = "Antigravity-Hans";        Url = "https://github.com/yuexps/Antigravity-Hans.git";        Branch = "main" },
    @{ Name = "claude-code-transcripts"; Url = "https://github.com/simonw/claude-code-transcripts.git"; Branch = "main" },
    @{ Name = "ClaudeScope";             Url = "https://github.com/Liuziyu77/ClaudeScope.git";          Branch = "main" },
    @{ Name = "codex";                   Url = "https://github.com/openai/codex.git";                   Branch = "main" },
    @{ Name = "commerce-agents";          Url = "https://github.com/anthropics/commerce-agents.git";     Branch = "main" },
    @{ Name = "ContextMenuManager";       Url = "https://github.com/BluePointLilac/ContextMenuManager.git"; Branch = "master" },
    @{ Name = "deepseek-harness";        Url = "https://github.com/deepseek-ai/deepseek-harness.git";   Branch = "master" },
    @{ Name = "dive-into-llms";          Url = "https://github.com/Lordog/dive-into-llms.git";          Branch = "main" },
    @{ Name = "FerretDB";                Url = "https://github.com/FerretDB/FerretDB.git";              Branch = "main" },
    @{ Name = "mini-swe-agent";          Url = "https://github.com/SWE-agent/mini-swe-agent.git";       Branch = "main" },
    @{ Name = "minimax-code";            Url = "https://github.com/MiniMax-AI/minimax-code.git";        Branch = "main" },
    @{ Name = "nanocode";                Url = "https://github.com/1rgs/nanocode.git";                  Branch = "master" },
    @{ Name = "opencode";                Url = "https://github.com/anomalyco/opencode.git";             Branch = "dev" },
    @{ Name = "pi-mono";                 Url = "https://github.com/badlogic/pi-mono.git";               Branch = "main" },
    @{ Name = "QwenPaw";                 Url = "https://github.com/agentscope-ai/QwenPaw.git";          Branch = "main" },
    @{ Name = "screenshot-to-code";      Url = "https://github.com/abi/screenshot-to-code.git";         Branch = "main" },
    @{ Name = "ZCode";                   Url = "https://github.com/zai-org/ZCode.git";                  Branch = "main" }
)

foreach ($r in $repos) {
    $targetDir = Join-Path $tp $r.Name
    if (-not (Test-Path $targetDir)) {
        Write-Host "Cloning $($r.Name)..." -ForegroundColor Cyan
        git clone --branch $r.Branch --depth 50 $r.Url $targetDir
    } else {
        Write-Host "$($r.Name) already exists, skipping." -ForegroundColor Yellow
    }
}
```

### 2. 自动化运维脚本

仓库配备了专用恢复脚本：
```powershell
uv run .scripts/restore-thirdparty.py
```
该脚本采用标准 PEP 723 格式，支持并发检测、缺失补全与分支检出。

---

## 四、维护约定与最佳实践

1. **避免纳入 Git 追踪**：`.thirdparty/` 在根目录 `.gitignore` 中保持忽略状态，严禁通过 `git add -f` 强制提交外部大仓库。
2. **新增项目登记**：若后续在 `.thirdparty/` 下克隆了新的参考库或工具，须同步在本文件（`THIRDPARTY.md`）与 `.scripts/restore-thirdparty.py` 中登记其远端地址、用途及分支信息。
3. **本地定制保存**：若对 `.thirdparty/` 下的项目进行了二次开发（如 `Antigravity-Hans`、`mini-swe-agent`、`nanocode`、`screenshot-to-code`），建议建立自己的 GitHub Fork 并 push 保存，或将 Patch/提交说明记录在对应的项目描述小节中。