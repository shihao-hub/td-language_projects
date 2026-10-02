# 本机 Agent CLI 非交互接口实测盘点

> 探测日期：2026-10-02
> 探测环境：Windows 11 / Windows PowerShell 5.1.26100.9444（`pwsh` 实际解析为 powershell.exe）
> 探测方法：仅 `--version` / `--help` / 子命令 `--help` / `mcp list` 等只读命令；未执行任何需要网络鉴权的任务、未执行 `mcp add`、未修改任何用户配置、未安装任何东西

---

## 1. 探测结果总览

本机 PATH 上实际存在的 AI agent CLI 共 **9 个**，全部提供非交互/一次性执行入口。

| 工具 | 版本 | 非交互入口 | 机器可读输出 | 工具白名单/沙箱 | MCP 子命令 | 会话续接 | 是否可用 |
|---|---|---|---|---|---|---|---|
| `claude` | 2.1.269 (Claude Code) | `-p` / `--print` | `--output-format text\|json\|stream-json`、`--json-schema`、`--input-format` | `--allowedTools` / `--disallowedTools`、`--tools`、`--permission-mode`、`--restricted` | `claude mcp`（含 `add/list/get/remove/serve/login`） | `-c/--continue`、`-r/--resume`、`--session-id`、`--fork-session` | 可用 |
| `codex` | codex-cli 0.154.0 | `codex exec`（别名 `e`） | `exec --json`(JSONL)、`--output-schema`、`-o/--output-last-message` | `-s/--sandbox read-only\|workspace-write\|danger-full-access`、`-a/--ask-for-approval` | `codex mcp`（`list/get/add/remove/login/logout`） | `codex resume` / `codex fork` / `codex exec resume --last` | 可用 |
| `gemini` | 0.60.0 | `-p` / `--prompt` | `-o/--output-format text\|json\|stream-json` | `--allowed-tools`（已 DEPRECATED，转向 Policy Engine）、`--approval-mode`、`-s/--sandbox`、`--policy` | `gemini mcp`（`add/remove/list/enable/disable`） | `-r/--resume`、`--session-id`、`--session-file`、`--list-sessions` | 可用 |
| `opencode` | 1.18.32 | `opencode run [message..]` | `run --format default\|json` | `--auto`（仅自动批准"未被显式拒绝"的权限），无独立工具白名单 | `opencode mcp`（`add/list/auth/logout/debug`） | `-c/--continue`、`-s/--session`、`--fork` | 可用 |
| `kilo` | 7.2.40 | `kilo run [message..]` | `run --format default\|json` | `--auto`、`--dangerously-skip-permissions` | `kilo mcp`（`add/list/auth/logout/debug`） | `-c/--continue`、`-s/--session`、`--fork`、`--cloud-fork` | 可用 |
| `pi` | 0.87.1 | `-p` / `--print` | `--mode text\|json\|rpc` | `-t/--tools`（白名单）、`-xt/--exclude-tools`（黑名单）、`-nt/--no-tools`、`-nbt/--no-builtin-tools` | 无 `mcp` 子命令 | `-c/--continue`、`-r/--resume`、`--session`、`--session-id`、`--fork` | 可用 |
| `iflow` | 0.4.7 | `-p` / `--prompt`（位置参数 `[query]` 等价） | 无 `--output-format`；仅 `-o/--output-file` 落盘执行信息 | `-y/--yolo`、`-s/--sandbox`、`--plan`、`--autoEdit`、`--allowed-mcp-server-names`、`--max-turns/--max-tokens/--timeout` | `iflow mcp`（`add/remove/list/add-json/get`） | `-c/--continue`、`-r/--resume` | 可用 |
| `agy` | 1.2.11 | `-p` / `--print`（`--prompt` 为别名） | `--output-format text\|json\|stream-json`、`--input-format`、`--json-schema` | `--sandbox`、`--dangerously-skip-permissions`、`--mode accept-edits\|plan` | `agy mcp`（`add/remove/list/enable/disable`） | `-c/--continue`、`--conversation <id>` | 可用 |
| `reasonix` | 0.53.2 | `reasonix run <task>` | `run --transcript <path>`（JSONL 转录稿）；无 `--json` 开关 | 无工具白名单/沙箱开关；有 `--budget <usd>` 美元上限、`--effort` | `reasonix mcp`（`list/search/install/browse/inspect`，属注册表助手，非本地 server 管理） | `-c/--continue`、`sessions`、`replay`、`diff` | 可用 |

> `dsnix` 与 `reasonix` 版本号同为 `0.53.2`，`dsnix --help` 输出的 Usage 头仍为 `reasonix`，判定为同一二进制的别名入口，不重复计数。

**统计**：非交互入口 9/9，机器可读输出 8/9（缺 `iflow`），MCP 子命令 8/9（缺 `pi`），工具白名单/沙箱 8/9（缺 `reasonix`），会话续接 9/9。

---

## 2. 逐工具明细

### 2.1 `claude` — Claude Code 2.1.269

- **确切命令**：`claude --version`、`claude --help`、`claude mcp --help`、`claude mcp list`
- **关键输出片段**：

  ```
  Usage: claude [options] [command] [prompt]
  Claude Code - starts an interactive session by default, use -p/--print for
  non-interactive output
  ```

  ```
  -p, --print                           Print response and exit (useful for pipes).
  --output-format <format>              Output format (only works with --print):
                                        "text" (default), "json" (single result),
                                        or "stream-json" (realtime streaming)
  --allowedTools, --allowed-tools <tools...>
                                        Comma or space-separated list of tool names to allow
  --permission-mode <mode>              (choices: "acceptEdits","auto","bypassPermissions",
                                        "manual","dontAsk","plan")
  --json-schema <schema>                JSON Schema for structured output validation
  ```

  `claude mcp list`（触发健康检查，约数秒返回）：

  ```
  chrome-devtools: cmd /c npx -y chrome-devtools-mcp@latest - ✔ Connected
  aoci: C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe --repo D:/Users/language_projects mcp - ✔ Connected
  ```

  另有：`--append-system-prompt`、`--system-prompt`、`--disable-slash-commands`（"Disable all skills"）、`--agents <json>`、`--plugin-dir`；`--bare` 的描述中明确提到 `CLAUDE.md auto-discovery` 可被跳过（即 CLAUDE.md 为约定上下文文件）。

- **一句话结论**：本机契约最完整的一个——非交互 + 三种输出格式 + JSON Schema 强约束 + 工具白/黑名单 + 权限模式 + 完整 MCP 增删查 + 会话续接全部具备，是编排其他工具时的首选被调方。

### 2.2 `codex` — codex-cli 0.154.0

- **确切命令**：`codex --version`、`codex --help`、`codex exec --help`、`codex mcp --help`、`codex mcp list`、`codex sandbox --help`
- **关键输出片段**：

  ```
  Commands:
    agents            Browse all agent sessions on the shared local app-server daemon
    exec              Run Codex non-interactively [aliases: e]
    review            Run a code review non-interactively
    mcp               Manage external MCP servers for Codex
    sandbox           Run commands within a Codex-provided sandbox
    resume            Resume a previous interactive session ... use --last
    fork              Fork a previous interactive session
  ```

  ```
  codex exec:
    --json
            Print events to stdout as JSONL
    --output-schema <FILE>
            Path to a JSON Schema file describing the model's final response shape
  codex:
    -s, --sandbox <SANDBOX_MODE>
            [possible values: read-only, workspace-write, danger-full-access]
    -a, --ask-for-approval <APPROVAL_POLICY>
            [possible values: on-request, never]
  ```

  `codex mcp list`（输出为列对齐表格，Env 列已被 CLI 自身脱敏为 `*****`）：

  ```
  Name       Command                                  Args                                  Env   Cwd  Status   Auth
  aoci       ...\Programs\aoci\aoci.exe               --repo D:\Users\language_projects mcp  -     -    enabled  Unsupported
  node_repl  ...\cua_node\...\bin\node_repl.exe       -                                     ***** -    enabled  Unsupported
  ```

  另有 `~/.codex/AGENTS.md` 与 `~/.codex/skills/`（97 项）存在，属约定文件/目录。

- **一句话结论**：非交互能力集中在 `codex exec` 子命令，沙箱策略是最显式的一档（三值枚举 + 审批策略二值枚举），并按 Windows 提供了 `codex sandbox` 受限令牌执行器。

### 2.3 `gemini` — Gemini CLI 0.60.0

- **确切命令**：`gemini --version`、`gemini --help`、`gemini mcp --help`、`gemini mcp list`、`gemini skills --help`
- **关键输出片段**：

  ```
  Gemini CLI - Defaults to interactive mode. Use -p/--prompt for non-interactive (headless) mode.
  Commands:
    gemini mcp                   Manage MCP servers
    gemini extensions <command>  Manage Gemini CLI extensions.
    gemini skills <command>      Manage agent skills.
    gemini hooks <command>       Manage Gemini CLI hooks.
  ```

  ```
  -p, --prompt                    Run in non-interactive (headless) mode ...
  -o, --output-format             [choices: "text", "json", "stream-json"]
  -s, --sandbox                   Run in sandbox?  [boolean]
      --approval-mode             [choices: "default","auto_edit","yolo","plan"]
      --allowed-tools             [DEPRECATED: Use Policy Engine instead ...]
  -r, --resume                    Use "latest" for most recent or index number
  ```

  `gemini mcp list` 输出：`No MCP servers configured.`

- **一句话结论**：非交互契约与 claude 高度同构（`-p` + 三值 `--output-format` + 审批模式枚举），但工具白名单已标记废弃、改由 Policy Engine 接管，属于"旧开关正在被替换"的过渡态。

### 2.4 `opencode` — 1.18.32

- **确切命令**：`opencode --version`、`opencode --help`、`opencode run --help`、`opencode mcp --help`、`opencode mcp list`、`opencode debug --help`
- **关键输出片段**：

  ```
  Commands:
    opencode run [message..]     run opencode with a message
    opencode mcp                 manage MCP (Model Context Protocol) servers
    opencode serve               starts a headless opencode server
    opencode session             manage sessions
  ```

  ```
  opencode run:
    --format       format: default (formatted) or json (raw JSON events)
                                          [choices: "default", "json"] [default: "default"]
    -c, --continue     continue the last session
    -s, --session      session id to continue
        --auto         auto-approve permissions that are not explicitly denied (dangerous!)
  opencode debug:
    opencode debug skill         list all available skills
    opencode debug config        show resolved configuration
  ```

  `opencode mcp list`（自带连接状态）：

  ```
  •  ✓ aoci  connected
  |      C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe --repo D:/Users/language_projects mcp
  •  ✓ chrome-devtools  connected
  |      npx -y chrome-devtools-mcp@latest
  —  2 server(s)
  ```

- **一句话结论**：非交互入口是独立子命令 `run`，机器可读输出用 `--format json`（而不是 `--output-format`）；工具管控方向偏"事后放行"（`--auto`）而非"事前白名单"，`--help` 中未见 `--allowedTools` 一类开关。

### 2.5 `kilo` — 7.2.40（`@kilocode/cli`）

- **确切命令**：`kilo --version`、`kilo --help`、`kilo run --help`、`kilo mcp --help`、`kilo mcp list`
- **关键输出片段**：

  ```
  Commands:
    kilo run [message..]     run kilo with a message
    kilo mcp                 manage MCP (Model Context Protocol) servers
    kilo acp                 start ACP (Agent Client Protocol) server
    kilo run / session / stats / export / import / pr / remote / config / plugin / db
  ```

  ```
  kilo run:
    --format        [choices: "default", "json"] [default: "default"]
        --auto      auto-approve all permissions (for autonomous/pipeline usage)
        --dangerously-skip-permissions
    -c, --continue / -s, --session / --fork / --cloud-fork
  ```

  `kilo mcp list` 输出：

  ```
  !  No MCP servers configured
  —  Add servers with: kilo mcp add
  ```

- **一句话结论**：`opencode` 的 fork（子命令集合、`--format json`、`--attach` 帮助文本里仍写着 "attach to a running **opencode** server"），契约与 opencode 基本一致，额外多了 `--cloud-fork`，`--auto` 的语义比 opencode 更强（"auto-approve **all** permissions"）。

### 2.6 `pi` — 0.87.1（`@earendil-works/pi-coding-agent`）

- **确切命令**：`pi --version`、`pi --help`、`pi list`
- **关键输出片段**：

  ```
  pi - AI coding assistant with read, bash, edit, write tools
  Usage:
    pi [options] [--] [@files...] [messages...]

  Options:
    --mode <mode>                  Output mode: text (default), json, or rpc
    --print, -p                    Non-interactive mode: process prompt and exit
    --tools, -t <tools>            Comma-separated allowlist of tool names to enable
                                   Applies to built-in, extension, and custom tools
    --exclude-tools, -xt <tools>   Comma-separated denylist of tool names to disable
    --no-tools, -nt                Disable all tools by default (built-in and extension)
    --no-context-files, -nc        Disable AGENTS.md and CLAUDE.md discovery and loading
    --skill <path> / --no-skills, -ns
    --system-prompt <text> / --append-system-prompt <text>
    --provider / --model / --thinking <off|minimal|low|medium|high|xhigh|max>
  Built-in Tool Names:
    read, bash, powershell, edit, write, grep, find, ls
  ```

  `pi list` 输出：`No packages installed.`

- **一句话结论**：唯一在 `--help` 里明确写出 `AGENTS.md and CLAUDE.md discovery and loading` 的工具；工具白/黑名单是 9 个里设计最完整的（allowlist + denylist + 全禁 + 仅禁内置四档），且 `--mode rpc` 是本机唯一提供的 RPC 输出模式。

### 2.7 `iflow` — 0.4.7（`@iflow-ai/iflow-cli`）

- **确切命令**：`iflow --version`、`iflow --help`、`iflow mcp --help`、`iflow mcp list`
- **关键输出片段**：

  ```
  iFlow CLI - Launch an interactive CLI, use -p/--prompt for non-interactive mode
  Positionals:
    query  Optional query to process (equivalent to -p for non-interactive or -i for interactive mode)
  ```

  ```
  -p, --prompt                          Prompt. Appended to input on stdin (if any).
  -s, --sandbox                         Run in sandbox?
  -y, --yolo                            Automatically accept all actions
      --plan                            Use plan mode (planning without execution)
      --autoEdit                        Use auto-edit mode
      --allowed-mcp-server-names        Allowed MCP server names  [array]
      --max-turns / --max-tokens / --timeout
  -o, --output-file                     Output file path to save execution information (non-interactive mode only)
  ```

  `iflow mcp list` 输出：`No MCP servers configured.`

- **一句话结论**：**本机唯一没有机器可读输出开关的 agent CLI**——只能靠 `--output-file` 落盘纯文本；反过来它是唯一在顶层就提供 `--max-turns` / `--max-tokens` / `--timeout` 三重预算法上限的工具。

### 2.8 `agy` — 1.2.11（Antigravity CLI，`C:\Users\29580\AppData\Local\agy\bin\agy.exe`）

- **确切命令**：`agy --version`、`agy --help`、`agy mcp --help`、`agy mcp list`、`agy models`
- **关键输出片段**：

  ```
  Usage of agy.exe:
    -p                              Short alias for --print
    --print                         Run a single prompt non-interactively and print the response
    --output-format                 Output format for print mode (text, json, stream-json) (default text)
    --input-format                  (text, stream-json) ... requires --output-format stream-json
    --json-schema                   Optional JSON schema string or path to a schema file to enforce structured output
    --sandbox                       Run in a sandbox with terminal restrictions enabled
    --dangerously-skip-permissions  Auto-approve all tool permission requests without prompting
    --mode                          Set the agent execution mode for this session (accept-edits, plan)
    --conversation                  Resume a previous conversation by ID
    --disable-slash-commands        Disable slash command and skill expansion in print mode

  Available subcommands:
    agent / agents / changelog / help / install / mcp / mic-serve / models / plugin / plugins / remote-control / update
  ```

  `agy mcp list` 输出：`No MCP servers configured.`

  补充：`agy --help` 与 `agy models` 均以 **exit code 1** 返回（Go flag 包打印 usage 的惯例），但输出内容完整可用；`agy models` 真实拉到模型列表（`gemini-3.8-flash-high` 等），说明该命令会走网络但不写配置。

- **一句话结论**：唯一以 Go 原生二进制（而非 npm 包）分发的工具，`--print` + 三值 `--output-format` + `--json-schema` + stream-json 输入的组合与 claude 几乎一致；注意其 `--help` 退出码为 1，脚本中不能靠退出码判断帮助是否成功。

### 2.9 `reasonix` — 0.53.2（DeepSeek 原生智能体框架；`dsnix` 为同一二进制的别名）

- **确切命令**：`reasonix --version`、`reasonix --help`、`reasonix run --help`、`reasonix mcp --help`、`dsnix --help`
- **关键输出片段**：

  ```
  Usage: reasonix [options] [command]
  DeepSeek 原生智能体框架 — 专为缓存命中和低成本令牌构建。
  Commands:
    run [options] <task>           以非交互方式运行单个任务，流式输出。
    chat [options]                 具有实时缓存/成本面板的交互式 Ink TUI。
    acp [options]                  run reasonix as an Agent Client Protocol (ACP) agent
    sessions / replay / diff / stats / doctor / commit / index / prune-sessions
    mcp                            模型上下文协议 (MCP) 助手 — 发现服务器，测试您的设置。
  ```

  ```
  Usage: reasonix run [options] <task>
  Options:
    -m, --model <id>       DeepSeek 模型 ID（例如 deepseek-v4-flash）
    -s, --system <prompt>  覆盖默认系统提示词
    --effort <level>       推理强度 — low|medium|high|max
    --budget <usd>         会话美元上限
    --transcript <path>    JSONL 转录稿路径
    --mcp <spec>           MCP 服务器规格（可重复） (default: [])
    --no-config            本次运行忽略 ~/.reasonix/config.json
  ```

  `dsnix --help` 首行同样输出 `Usage: reasonix [options] [command]`，确认为别名。

- **一句话结论**：`run` 是纯流式、无 `--json` 开关，机器可读性靠 `--transcript` 落 JSONL；`mcp` 子命令做的是**注册表发现/安装**（`list/search/install/browse/inspect`），本地 server 是每次运行用 `--mcp <spec>` 传入的，与其余 8 个"写配置文件"的模型不同。

---

## 3. 未安装 / 未探测到的工具

以下工具经 `Get-Command` 逐个探测，本机 PATH 上**未安装**：

`aider`、`goose`、`crush`、`qwen`、`cursor-agent`、`copilot`、`amp`、`kimi`、`droid`、`cline`、`continue`、`windsurf`、`vibe`、`plandex`、`shell-gpt`、`sgpt`、`llxprt`、`charm`、`gptme`、`openai`、`anthropic`

补充说明（避免误判）：

- **`dsh`**：PATH 上**未探测到** `dsh` 命令；`%APPDATA%\npm`、`%USERPROFILE%\.local\bin`、`D:\nvm4w\nodejs`、`%LOCALAPPDATA%\Programs\` 下均无 `dsh.cmd` / `dsh.exe`。DSH 在本机是 Electron 桌面应用（`D:\Users\29580\AppData\Local\Programs\DeepSeek Harness\DeepSeek Harness.exe`，同目录仅有 `resources/`、`locales/` 与 Electron 运行时 DLL），**不提供 CLI 入口**。`deepseek-harness` 命令同样不存在。
- **`ollama`**：存在（`ollama version is 0.17.1`），但它是**本地模型运行时**而非 agent CLI，不计入上表 9 个。
- **`claude-code-ui` / `cloudcli`**：存在（1.23.2），`cloudcli --help` 显示为 "Claude Code UI - Command Line Tool"，是给 Claude Code 起 Web 服务的 UI 外壳，非独立 agent，不计入。
- **`lark-cli`**（1.0.97）、**`ccundo`**（1.1.1）、**`vsce`**、以及 `~/.local/bin` 下的 `gitingest` / `litecli` / `deeptutor` / `claude-mux`：均为工具类 CLI 或 Claude Code 的会话包装器，非独立 agent CLI，不计入。
- **`~/.qwen`、`~/.amp`、`~/.goose`、`~/.crush`、`~/.aider`、`~/.antigravity` 配置目录均不存在**；`~/.cursor`、`~/.copilot` 目录存在但只有 `argv.json` / `ide` 等残留，无对应 CLI 可执行文件，故 `cursor-agent`、`copilot` 判定为未安装。

**跳过探测的工具**：无。本次所有被探测到的工具，其 `--version` / `--help` / 子命令 `--help` 均在本地完成、未触发登录流程，因此没有任何工具因"`--help` 会触发登录或写配置"而被跳过。唯一需注意的是 `agy --help` / `agy models` 退出码为 1（内容正常），以及 `claude mcp list` 会做 MCP server 健康检查（只读、不写配置，约数秒）。

---

## 4. 本机 MCP 配置统计

以下统计全部只读；含密钥字段的文件只读取键名，**未输出任何 token / apiKey 值**。

### 4.1 agent CLI 自身配置

| 客户端 | 配置路径 | server 数量 | server 名称列表 |
|---|---|---|---|
| Claude Code | `C:\Users\29580\.claude.json`（json-path `mcpServers`） | 2 | `chrome-devtools`、`aoci` |
| Codex CLI | `C:\Users\29580\.codex\config.toml`（`[mcp_servers.*]`） | 2 | `aoci`、`node_repl` |
| OpenCode | `C:\Users\29580\.config\opencode\opencode.json`（key `mcp`） | 2 | `aoci`、`chrome-devtools` |
| Gemini CLI | `C:\Users\29580\.gemini\settings.json`（`mcpServers`） | 0 | —（文件内容即 `{"mcpServers": {}}`） |
| Antigravity / agy | `C:\Users\29580\.gemini\config\mcp_config.json` | 0 | —（**0 字节空文件**） |
| iFlow CLI | `C:\Users\29580\.iflow\settings.json` | 0 | —（无 `mcpServers` 键；该文件含 `apiKey` / `searchApiKey` / `cna` 等敏感字段，值一律记作 `***`） |
| Kilo | `C:\Users\29580\.config\kilo\` | 0 | —（`kilo mcp list` → `No MCP servers configured`） |
| pi | `C:\Users\29580\.pi\agent\settings.json` | 0 | —（无 mcp 键；pi 无 mcp 子命令） |
| reasonix | `C:\Users\29580\.reasonix\config.json` | 0 | —（无 mcp/servers 键，仅 `apiKey`/`model`/`projects` 等，值记作 `***`；server 由 `run --mcp <spec>` 每次传入） |

交叉验证命令与结果：

- `codex mcp list` → 2 行（`aoci` enabled、`node_repl` enabled，Env 列由 CLI 自身输出为 `*****`）
- `claude mcp list` → `chrome-devtools: ✔ Connected`、`aoci: ✔ Connected`
- `opencode mcp list` → `2 server(s)`，两个均 `✓ connected`
- `gemini mcp list` / `agy mcp list` / `iflow mcp list` / `kilo mcp list` → 均为 0

### 4.2 其他 MCP 客户端（顺带扫到的配置）

| 客户端 | 配置路径 | server 数量 | server 名称列表 |
|---|---|---|---|
| MCP Inspector | `C:\Users\29580\.mcp-inspector\mcp.json` | 4 | `filesystem-server-default`、`everything-server-default`、`example-server-default`、`liteconf` |
| CodeGeeX agent | `C:\Users\29580\.codegeex\agent\configs\mcp_config.json` | 3 | `frontend_server`、`backend_server`、`terminal` |
| Qoder | `C:\Users\29580\.qoder\mcp.json`（及 `shared_client\mcp.json`） | 0 | — |
| Lingma | `C:\Users\29580\.lingma\extension\local\mcp.json` | 0 | — |
| WorkBuddy | `C:\Users\29580\.workbuddy\mcp.json` | 0 | — |

### 4.3 合计

- **已注册 MCP server 条目总数（含跨客户端重复注册）：13**
  （Claude Code 2 + Codex 2 + OpenCode 2 + MCP Inspector 4 + CodeGeeX 3）
- **去重后的 server 名称：10 个**
  `aoci`、`chrome-devtools`、`node_repl`、`filesystem-server-default`、`everything-server-default`、`example-server-default`、`liteconf`、`frontend_server`、`backend_server`、`terminal`
- **跨客户端复用**：`aoci` 被 3 个客户端注册（Claude Code / Codex / OpenCode），`chrome-devtools` 被 2 个注册（Claude Code / OpenCode）——即 13 条配置里只有 10 个不同的 server。
- **项目级 `.mcp.json`**：`D:\Users\language_projects\.mcp.json` **不存在**；对整个仓库做 `**/.mcp.json` 全量匹配也**未发现任何**项目级 `.mcp.json`（尽管 `AGENTS.md` 的 AOCI 段落提到"project's `.mcp.json`"，本仓库实际未落地该文件，aoci 是通过用户级配置注册的）。另外 `~/.mcp.json` 也不存在。
- `~/.claude.json` 的 `projects` 下有 100+ 个项目条目，逐个检查其 `mcpServers`，**全部为 0**，仅顶层 `mcpServers` 有 2 个。

---

## 5. 观察到的共性规律

**规律一：`-p/--print` 类短开关已成事实标准，但"非交互入口"的落点分成两派，且两派泾渭分明。**

9 个工具全部提供非交互入口，但形态分裂为：
- **标志位派（5 个）**：`claude -p`、`gemini -p/--prompt`、`iflow -p/--prompt`、`agy -p/--print`、`pi -p/--print` —— 复用同一个根命令，只加一个开关；
- **子命令派（4 个）**：`codex exec`、`opencode run`、`kilo run`、`reasonix run` —— 非交互是独立的子命令树。

分派与"是否有 MCP 子命令"无关，但与**代码同源关系**高度相关：`opencode` 与 `kilo` 同为子命令派且都是 `run --format json`，`codex` 的子命令派则是为了承载 `exec resume` / `exec review` 这层嵌套。

**规律二："非交互模式 + 结构化输出 + 工具白名单"确实构成三件套，但完整命中的只有 4/9，缺口位置各不相同。**

实测满足三项全有的仅 `claude`、`codex`、`gemini`、`agy`：
- `claude`：`-p` + `--output-format` + `--allowedTools`
- `codex`：`exec` + `--json` + `--sandbox`
- `gemini`：`-p` + `--output-format` + `--approval-mode`（`--allowed-tools` 已 DEPRECATED）
- `agy`：`--print` + `--output-format` + `--sandbox`

其余 5 个各缺一角，且缺口不是随机的：
- `iflow` 缺**机器可读输出**（只有 `-o/--output-file` 落纯文本），但它是唯一顶层就带 `--max-turns`/`--max-tokens`/`--timeout` 的执行预算三件套；
- `opencode` / `kilo` 缺**事前工具白名单**，改用 `--auto`（事后放行）——`kilo` 的措辞更强（"auto-approve **all** permissions"）；
- `pi` 的工具白名单最完整（`-t` allowlist + `-xt` denylist + `-nt` 全禁 + `-nbt` 仅禁内置），缺的是 MCP 子命令；
- `reasonix` 两者都缺，取而代之的是 `--budget <usd>` 金额上限 + `--effort` 推理档位。

**结论**：三件套在头部工具（含商业化大厂 CLI）中已收敛为标配，但"第三个角"用**权限/沙箱**还是用**工具名单**实现并不统一——`codex`/`agy` 选沙箱，`claude`/`pi` 选工具名单，`gemini` 正在从工具名单迁移到 Policy Engine。

**规律三：MCP 的"注册方式"比"MCP 子命令是否存在"更能区分工具代际，本机出现了三种不同代际并存。**

8/9 有 `mcp` 子命令（仅 `pi` 无），但拆开看是三套模型：
1. **写用户级配置（多数派，6 个）**：`claude mcp add` → `~/.claude.json`；`codex mcp add` → `~/.codex/config.toml`；`gemini`/`agy mcp add` → settings JSON；`opencode`/`kilo mcp add` → `~/.config/{opencode,kilo}/`。这派的本机实测结果是 `aoci` 被重复注册 3 次、`chrome-devtools` 被重复注册 2 次——13 条配置只对应 10 个不同 server，**配置重复是本机最明显的 MCP 治理问题**。
2. **不落配置文件（`reasonix`）**：`mcp` 子命令只是注册表浏览器（`list/search/install/browse/inspect`），本地 server 靠每次 `run --mcp <spec>` 传入，命令行即配置源。
3. **完全缺席（`pi`）**：`--help` 中无 MCP 任何字样，扩展能力走 `pi install <source>` 的 extension 机制。

**结论**：MCP server 清单目前是"每个客户端各存一份"的孤岛状态，本机 3 个客户端各自维护 `aoci` 的同一份路径（`C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe --repo D:/Users/language_projects mcp`），任何路径变更都需改 3 处——这正是项目级 `.mcp.json`（本仓库当前**未落地**）本该解决的问题。

---

## 附：本仓库 `AGENTS.md` / `CLAUDE.md` 关系（一行确认）

`D:\Users\language_projects\AGENTS.md`（32758 B）与 `D:\Users\language_projects\CLAUDE.md`（10 B）**均存在**，`CLAUDE.md` 的全部内容就是 `@AGENTS.md`（即通过引用指向 `AGENTS.md`），反向**不成立**——`AGENTS.md` 中不含任何 `CLAUDE` 字样（匹配 0 行），因此是**单向引用**（`CLAUDE.md → AGENTS.md`）。另：仓库根 `GEMINI.md`、`IFLOW.md` **均不存在**，`~/.codex/AGENTS.md` 存在但为 0 字节空文件。
