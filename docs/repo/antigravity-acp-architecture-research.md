# Google Antigravity ACP Server 架构全景（源码级分析）

> **元信息**
> - 分析对象：`agy_acp_server.exe`（PyInstaller onefile）提取的纯 Python 源码，版本 `antigravity-acp v_1.1.1`
> - 原始路径：`google3/cloud/developer_experience/antigravity_extensions/acp_server/`（google3 monorepo 内部包名未改，import 前缀即 `google3.cloud...`）
> - 源码快照位置：本仓 `.thirdparty/antigravity-acp-src/`（gitignore 本地目录，仅提取源码的机器上可跳转；无该目录时本文仍可独立阅读）
> - 分析方法：源码静态阅读 + 本机运行时进程/目录实测 + `localharness_external.exe` 二进制 strings 验证
> - 本文所有 `file:line` 引用均对应该 v_1.1.1 提取快照，可直接跳转验证
> - 写给 AI 读者：读本文即可建立完整心智模型，无需重新逆向

---

## 0. TL;DR

**三层进程架构：IDE（ACP 客户端）→ Python 协议壳（本源码）→ Go Agent 引擎（localharness）→ Google 云端。**

Python 进程**不跑 Agent 循环**，只做三件事：ACP 协议翻译、OAuth 凭据管理（凭据绝不交给 Go 进程，模型流量经 127.0.0.1 反向代理注入）、权限裁决与企业管控。真正的 Agent 大脑是同目录 spawn 出来的 Go 二进制 `localharness_external.exe`（源自 Google 收购 Windsurf/Exafunction 的 Jetski 代码库），双方通过回环 WebSocket 全双工通信。

```
Zed / IntelliJ（ACP 客户端，stdio JSON-RPC）
   │  initialize → authenticate → session/new → session/prompt
   ▼
agy_acp_server.exe（Python，~430MB PyInstaller onefile）
   │  main.py:94-96 → acp.run_agent(AgyAdapter())
   │
   ├─ authenticate (server.py:2370)
   │    OAuth 回环服务器收 redirect → token 兑换 → acp_token.json
   │    → loadCodeAssist/onboardUser 判订阅 Tier → 解析 project/endpoint
   ├─ session/new → _create_agent_config (server.py:3208)
   │    组装 tools/policies/hooks/MCP/skills → 起本地反代 (127.0.0.1)
   │    → 模型 endpoint 改写为代理 URL（dummy api key，真凭据代理注入）
   ▼
localharness_external.exe（Go，130MB，每会话一个进程）
   │  回环 WebSocket + protobuf(CortexStep)，Python 是 WS 客户端
   │  内部：Agent 循环（规划→调模型→执行工具→循环）
   │    模型调用 → 打回 Python 反代 → 注入 OAuth → CCPA → Gemini
   │    工具调用 → 权限 hook 回传 Python → IDE 弹窗 → 决定返回才继续
   ▼
cloudcode-pa.googleapis.com / daily-cloudcode-pa.googleapis.com（CCPA 后端）
```

---

## 1. 四层职责拆解

| 层 | 进程/组件 | 技术 | 职责 |
|---|---|---|---|
| IDE 层 | Zed / IntelliJ AI Chat | 各 IDE 自有 | ACP 客户端；渲染会话流；弹权限确认框 |
| 协议壳层 | `agy_acp_server.exe` | Python 3.10（本源码） | ACP JSON-RPC 路由、OAuth/凭据、订阅 onboarding、权限裁决、企业管控、遥测归因、本地反代 |
| 引擎层 | `localharness_external.exe` | Go（Jetski） | Agent 循环、工具执行（终端/文件/搜索/图片/MCP）、trajectory 持久化、沙箱 |
| 云端层 | CCPA（CloudCode PA）等 | Google 内部服务 | 模型推理（Gemini）、订阅/Tier 校验、AgentPlugin 下发 |

**关键分界**：凭据只在 Python 进程内；Agent 状态只在 Go 进程与它的 SQLite 里；两者以回环 WS + 本地反代缝合。

---

## 2. 组件清单（文件级导读）

| 文件 | 职责 | 关键入口 |
|---|---|---|
| `main.py` | 进程入口；定位 localharness 二进制；`acp.run_agent` 启动 | `main.py:42` `_configure_localharness_path`（在 `sys.argv[0]`/`sys.executable` 同目录找 `localharness_external.exe`） |
| `server.py` | **核心**（5178 行）：`AgyAdapter` 实现全部 ACP 方法 | `initialize:2063` `authenticate:2370` `new_session:2691` `prompt:4291` `_create_agent_config:3208` |
| `proxy_agent_config.py` | 把模型 endpoint 改写为本地代理 URL；注入 `X-ACP-Proxy-Token`/`X-ACP-Trajectory-Id` 头 | `_build_harness_config:41`；`create_strategy:101`（接收 `tool_runner`/`hook_runner` 两个 Python 回调） |
| `oauth/credential_manager.py` | OAuth 交互式登录：127.0.0.1 临时端口起 HTTP 服务接 redirect，兑换 token | `_authenticate_interactively:326` `_run_redirect_server:381` |
| `oauth/credential_store.py` | 凭据文件读写；**格式与 jetski(Go)、gemini-cli(TS) 三端对齐** | 文件头注释 `credential_store.py:7` |
| `ccpa_connection/onboard.py` | 订阅 onboarding：`loadCodeAssist` 查 Tier → 不合格自动 onboard 免费 Tier（长任务轮询）→ 解析 project/endpoint | `onboard_user:97`；endpoint 选择 `_determine_endpoint:19`（消费级→daily，企业→prod） |
| `ccpa_connection/ccpa_client.py` | CCPA REST 封装（httplib2 + googleapiclient 风格） | `stream_generate_content:123` `fetch_available_models:205` |
| `ccpa_connection/proxy_server.py` | **本地反向代理**（标准 Gemini 请求 ↔ CCPA 格式互转 + 凭据注入） | `ProxyHandler.do_POST:58`；token 校验 `secrets.compare_digest`（`:64-73`） |
| `baic_connection/` | Gemini Enterprise（企业版）专用：商业授权、license 解析、BAIC 代理 | `business_auth.py:71` `BusinessAuthManager` |
| `tools.py` | Python 侧自定义工具：`safe_view_file`、`client_view_file`/`client_create_file`/`client_edit_file`（借 IDE 的 fs 能力） | `view_file:92` `client_edit_file:304` |
| `hooks.py` | 外部 hook 子进程系统（Pre/PostToolCall、Pre/PostInvocation、OnSessionEnd 等 6 类） | `ExternalPreToolCallDecideHook:432` |
| `browser_subagent.py` | 浏览器子代理：npx 运行 chrome-devtools-mcp，注入 `chrome_*` 工具 + 专属 persona；启动前 preflight 探测 | `build_mcp_server` / `preflight_launcher` |
| `admin_controls_manager.py` | 企业管理管控：模型白名单、终端策略、文件访问策略、MCP 白名单、浏览器开关 | `AdminControls.from_fetch_config:318` |
| `session_store.py` | 会话 trajectory（SQLite）读写、sidecar 元数据、resume 时剥离过期 thought signature | `:224-244` |
| `settings.py` / `settings_writer.py` | `$GEMINI_HOME` 下 settings.json 读写 | `:226` 注释：SDK 从独立线程吸走 harness stderr |
| `paths.py` | 全部路径解析（`$GEMINI_HOME` env 可覆盖） | `gemini_home:68` `sessions_dir:152` `app_data_dir:167` |
| `telemetry.py` | `BaicTelemetryDispatcher`：推理解析/交互事件批量上报，按 canonical UA 归因 | `:152` |
| `terminal_sandbox.py` | 企业 OS 沙箱（exebox）开关透传 | `:132` |
| `workspace_trust.py` | 工作区信任检查 | — |
| `useragent.py` | UA 单一事实源（按认证方式分两种形态） | — |
| `model_selection.py` / `config_options.py` | 模型列表与会话模式（auto_edit/yolo 等） | — |
| `mcp_servers.py` | 客户端 MCP 配置与全局 MCP 配置合并、企业白名单过滤 | — |
| `logout.py` | `/logout` 命令与凭据清理 | — |

---

## 3. 核心链路详解

### 3.1 启动与 initialize

1. IDE 按 ACP Registry 把 `agy_acp_server.exe` 当子进程拉起（stdio JSON-RPC）。安装位置（Zed 实测）：`%LOCALAPPDATA%\Zed\external_agents\registry\antigravity-acp\v_1.1.1_<hash>\`，与 `localharness_external.exe` 同目录。
2. `main.py`：禁用 protobuf 运行时版本校验（`:34`，内部 gencode 与 PyPI 运行时混用的兜底）→ 定位 localharness → `acp.run_agent(AgyAdapter())`（Zed 官方 `acp` PyPI 库）。
3. `initialize`（server.py:2063）：回广告能力（load_session/auth logout/list/resume/image/audio/embedded_context/MCP http+sse）+ 4 种认证方式按钮。

### 3.2 authenticate（server.py:2370）

4 种 `method_id` 分支：

| 方式 | 行为 |
|---|---|
| `oauth-personal`（消费者 Google 账号） | `_ensure_oauth_logged_in` → OAuth 回环流（下述）→ CCPA onboarding |
| `oauth-business`（Gemini Enterprise） | BusinessAuthManager 交互登录 + license 解析，project/location 来自 settings.json |
| `api-key` | 只读环境变量 `GEMINI_API_KEY`（`:2423`），SDK 直连开发者 API，不走代理 |
| `agent-platform`（原 vertex-ai） | ADC/API key + `GOOGLE_VERTEX_*` env 或 settings.json gcp 字段，Vertex endpoint 直连 |

**OAuth 回环流**：`_run_redirect_server`（credential_manager.py:381）在 `127.0.0.1` 临时端口起 WSGI HTTP 服务 → 打开浏览器走 Google OAuth → redirect 落回本地 → code 兑换 token → 存 `$GEMINI_HOME/acp_token.json`。

**Onboarding**（onboard.py:97）：`loadCodeAssist` 查当前 Tier → 无 Tier 则 `onboardUser(tierId=free-tier)` 发起长任务并轮询至 done（`_POLL_LIMIT=30` 次）→ 返回 `(project_id, endpoint_url)`。**endpoint 按 `usesGcpTos` 二选一**：消费级（Free/Pro/Ultra）→ `daily-cloudcode-pa.googleapis.com`；企业 → `cloudcode-pa.googleapis.com`（onboard.py:19-33）。

认证方式真实切换时，存活会话整体在新凭据下重建（server.py:2468-2480）。

### 3.3 session/new（server.py:2691）

顺序：断言已认证 → 拉企业管控 → 预创建 trajectory 空文件 → `_list_available_models` → `_create_agent_config`（`:3208`）→ `sdk_agent_factory` → 进入 agent 异步上下文（**此刻 spawn harness + 连 WS**）→ 写 sidecar → 返回 configOptions/models/modes。

`_create_agent_config` 的组装内容（全部进 `HarnessConfig` proto）：

- **工具**：禁 harness 内置 `VIEW_FILE` 换 Python 的 `safe_view_file`（工作区限定）；IDE 若声明 `fs.read_text_file/write_text_file` 能力，追加 `client_view_file/client_create_file/client_edit_file`（文件操作借道 IDE，权限由 harness pre-tool hook 统一把关，避免二次弹窗 `:3274-3278`）；
- **策略**：`policy.safe_defaults(handler)` 打底 + ask_question 放行 + `read_url_content` 强制询问（防注入 `:3303-3317`）+ 企业 outside-workspace DENY/ASK 规则；
- **MCP**：客户端配置与全局配置合并 → 企业白名单过滤；浏览器子代理按需注入（npx preflight 失败则跳过并记一次性通知，绝不拖死会话 `:3348-3367`）；
- **认证路由**（`:3553-3631`）：
  - `oauth` → `GeminiAPIEndpoint(api_key="dummy_api_key")` + **CCCP 本地代理**（dummy key 仅为满足 SDK 客户端校验，真实凭据由代理注入 `:3580-3592`）；
  - `oauth-business` → `VertexEndpoint(project, location)` + BAIC 代理；
  - `agent-platform` / `api-key` → 直连 `LocalAgentConfig`，无代理。

**本地反向代理**（proxy_server.py）：进程级单例（健康检查线程死了会重启 `:3646`，最后一个会话销毁时停掉）。ThreadingHTTPServer 绑 127.0.0.1 随机端口，`X-ACP-Proxy-Token`（`secrets.compare_digest` 恒时比较）鉴权。职责：把标准 Gemini 形状请求包装成 CCPA `GenerateContentRequest`（带 project path）、注入 OAuth token / canonical UA / `X-ACP-Trajectory-Id`（= 会话 id）/ `X-Aicode-Prompt-Id`，流式响应再拆回标准 SSE 形状。

### 3.4 一个回合（session/prompt，server.py:4291）

1. 前置：`/logout` 命令拦截、企业管控刷新、浏览器不可用一次性通知、记录 prompt_id（供代理打 tracing 头）；
2. `agent.chat(chat_prompt)`（`:4397`）发出回合，随后 `agent.conversation.receive_steps()`（`:4403`）并发消费 harness 回传的 step 流；
3. `_stream_live_step` 把 `trajectory_pb2.Step`（oneof：`view_file`/`file_change`/`run_command`/`code_search`/`generate_image`/`mcp_tool`…，见 `_extract_tool_output:4979`）翻译成 ACP `session/update` 通知；
4. **权限闭环**：harness 触发 pre-tool hook → 经 `hook_runner` 回调 Python `_permission_handler` → `client.session/request_permission` → IDE 弹窗 → 决定原路返回 harness，允许后才执行；
   - "Allow Always" 缓存规则（`_allow_always_signature:76`）：exec 工具按**精确命令行字符串**缓存；文件写工具**永不缓存**（降级为单次允许）；其余按工具名缓存；
5. **异常恢复**：捕 `websockets.ConnectionClosed` → 判定 harness 已死 → 重建 agent（新 harness 进程 + 从 SQLite trajectory 重放历史）重试一次（`:4387-4437`，防死循环只重建一次）；
6. 终端类工具调用在回合干净结束后转入 `persisted_open_tool_calls`（后台任务跨回合存活 `:4408-4415`）；任何未闭合的 tool_call 统一补终态（默认 failed，干净结束才 completed，`:4385`）；
7. `cancel`（`:2787`）→ `agent.conversation.cancel()` 中途打断。

### 3.5 持久化与 resume

- trajectory：`$GEMINI_HOME/conversations/<session_id>.db`（SQLite，**由 Go harness 直接读写**；Python 在 spawn 前改写它做 resume 前处理，如剥离过期 thought signature `:3444`）+ `.meta` sidecar（cwd/mode_id）；
- harness 工件：`$GEMINI_HOME/brain/<conversation_id>/.system_generated/{logs,steps,tasks,subagents}` + `scratch`（tasks 下即终端命令输出日志，本机实测 `task-*.log`）；
- 能力广告 `load_session=True` + `session/list`/`resume`，resume = 新 harness 进程 + DB 历史重放。

---

## 4. localharness_external.exe 深挖

### 4.1 身份（多源证据）

| 证据 | 结论 |
|---|---|
| 二进制 strings：`go1.`、`third_party/jetski/cortex_pb/options.proto` | **Go 编写**，出自 google3 `third_party/jetski`（Exafunction/Windsurf 收购代码） |
| strings：`.antigravity.localharness.memory_filesystem`、`ConsumeTrajectory called on a closed state`、`Executor` | 即 HarnessConfig proto 的消费方、Agent 循环本体 |
| `proxy_agent_config.py:29` 注释：`--define=ext_ver_local_connection=true` 的 release 变体 | `_external` 后缀 = 对外发布版（区别于 google3 内部构建） |
| 本机进程实测：1×`agy_acp_server` + N×`localharness_external`（每会话一个） | 进程隔离模型：会话崩溃不传染 |

### 4.2 它是 WebSocket **服务端**

二进制内含 `101 Switching Protocols` / `Upgrade: websocket` / `Connection: Upgrade` / `Sec-WebSocket-Accept`（只有服务端计算 Accept）+ `127.0.0.1:0`（Go 绑随机端口惯用法）+ `ws://127.0.0.1:%s%s` 端点拼串。

握手时序：Python SDK spawn harness → harness 回环随机端口起 WS 监听 → 通告端点（SDK 另有线程持续吸 harness stderr 作日志，settings.py:226 注释）→ Python `websockets` 库作为**客户端**连入。

### 4.3 全双工且是双向请求-响应

同一条 WS 上：

- **Python → harness**：`chat` 发回合、`cancel` 打断；
- **harness → Python（主动发起）**：CortexStep 事件流；权限/policy hook 请求（等 Python 答复才继续）；ask_user；**宿主工具回调**（`client_view_file` 等工具实现在 Python，harness 经 `tool_runner` 调过来执行——见 `create_strategy(*, tool_runner, hook_runner)` proxy_agent_config.py:101）。

### 4.4 harness 职责清单

1. Agent 循环：消费 trajectory → 调模型（strings：`{model}:streamGenerateContent?alt=sse`）→ 解析 Thought/Text/ToolCall → 执行 → 循环；
2. 工具执行：run_command（可进 exebox 沙箱）、code_search（配套 `%LOCALAPPDATA%\antigravity\bin\rg_embedded-*.exe` 内嵌 ripgrep）、文件编辑、generate_image、MCP 工具宿主（浏览器 = spawn npx chrome-devtools-mcp）；
3. 直连 `cloudcode-pa.googleapis.com` 拉取 AgentPlugin 列表（strings 证据）；
4. 落盘：conversations/*.db + brain 工件目录；
5. 策略执行点：workspace containment（可由 Python 关闭改用企业策略，proxy_agent_config.py:49）。

---

## 5. 凭据与安全模型

1. **凭据不出 Python 进程**：Go harness 拿到的是 dummy api key + 代理 URL；真实 OAuth token 只在 Python 反代进程内注入。模型流量必经回环代理 → 凭据、UA 归因、计费头（trajectory/prompt id）全部收口。
2. **代理鉴权**：`X-ACP-Proxy-Token` 恒时比较；错误响应前先 drain 请求体避免 RST（proxy_server.py:30-39 细节注释）。
3. **权限三层**：harness 内置 workspace containment（非企业默认硬限制）→ Python policy 规则（safe_defaults + 特例）→ IDE 用户确认（request_permission）。文件写工具永不缓存允许。
4. **prompt 注入防护**：`read_url_content` 专门从"只读放行"降级为强制询问（server.py:3303 注释明确说明理由）；未知 MCP 工具参数无法按参数域缓存是已知接受的风险（`:106-111` 注释）。
5. **企业管控**：admin controls 后台轮询刷新，回合开始前应用变更（必要时重建 agent）；模型白名单/终端审查/MCP 白名单/浏览器开关/JS 执行策略。
6. **OAuth 回环**：临时端口一次性 WSGI 服务；凭据文件格式与 jetski(Go)、gemini-cli(TS) 三端兼容（credential_store.py:7）。
7. **诚实边界**：WS 连接本身是否有握手鉴权未知——SDK（`google.antigravity` 包）未提取；仅能确认"回环 + 临时端口"隔离。

---

## 6. 关键设计决策与为什么

| 决策 | 理由（源码证据） |
|---|---|
| **Python 壳 + Go 芯** | 最大化复用收购资产：Jetski 引擎原封不动；Python 层全是 google3 现成轮子（google-auth/googleapiclient/absl/protobuf）+ Zed 官方 `acp` 库，胶水层无性能瓶颈 |
| **PyInstaller onefile** | ACP 部署模型 = IDE 拉子进程，用户机器零依赖；`main.py` 的 `pkgutil.get_data` 兜底、从 `sys.executable` 同目录找 harness 都是 onefile 形态专用设计 |
| **本地反向代理** | 凭据隔离 + 统一 UA/计费/追踪归因 + 保持 SDK 的标准 Gemini API 契约（CCPA 私有格式转换收在代理内） |
| **每会话一个 harness 进程** | 崩溃隔离；断连后单次重建 + SQLite 重放即可恢复（server.py:4387） |
| **dummy api key** | 仅为满足 Python SDK 对非 Vertex 连接的客户端校验（server.py:3669 注释），真实凭据在代理侧 |
| **双 endpoint** | 消费级与企业在 CCPA 是不同后端域（onboard.py:16 `_PROD_DAILY_ENDPOINT`），按 `usesGcpTos` 自动路由 |
| **`_external` 构建变体** | 同一代码库 internal/external 两种发布形态，release 变体不接受内部参数（proxy_agent_config.py:29-35） |

---

## 7. 运行时目录布局（本机实测）

```
%LOCALAPPDATA%\Zed\external_agents\registry\antigravity-acp\v_1.1.1_<hash>\
    agy_acp_server.exe          # ~430MB PyInstaller onefile
    localharness_external.exe   # 130MB Go 引擎（server spawn 它）

~/.gemini/antigravity-acp/              # 本 ACP 的 $GEMINI_HOME
    acp_token.json  settings.json
    conversations/<uuid>.db/.meta       # trajectory（harness 写）
    brain/<uuid>/.system_generated/{logs,steps,tasks,subagents} + scratch

~/.gemini/antigravity/                  # Antigravity IDE 的 home（同构布局）
    builtin/skills/{agy-customizations,antigravity_guide,generative_ui,
                    migrate-workflows,permissioned-github}/SKILL.md
    bin/{webm_encoder.exe, agentapi.bat}

~/.gemini/antigravity-cli/              # Antigravity CLI 的 home
    jetski_state.pbtxt                  # ← CLI 即 Jetski Go 程序的直接证据
    bin/webm_encoder.exe

%LOCALAPPDATA%\antigravity\bin\rg_embedded-<hash>.exe   # 内嵌 ripgrep
```

三个 home（IDE/ACP/CLI）目录结构同构（brain/conversations/...），同一 Go 引擎家族的不同宿主。

---

## 8. 生态位：Antigravity 家族与多团队协作

| 组件 | 技术 | 来源 |
|---|---|---|
| Antigravity IDE 桌面应用 | TypeScript / Electron（VSCode fork） | Windsurf/Codeium 收购 |
| Agent 引擎 localharness/cortex | Go（`third_party/jetski`） | Jetski/Exafunction 收购 |
| antigravity CLI | Go（`jetski_state.pbtxt` 为证） | 同 Jetski 系 |
| **ACP server（本源码）** | **Python** | Google developer_experience 团队新写，为第三方 IDE 接入 |
| gemini-cli | TypeScript 开源 | Gemini Code Assist 团队 |
| 浏览器自动化 | chrome-devtools-mcp（Node/npx） | 直接复用社区 MCP |
| CCPA 后端 | Google 内部服务 | CloudCode PA 团队 |

**统一手段是协议而非语言**：IDE↔agent 用 ACP（stdio JSON-RPC）；壳↔引擎用回环 WS+protobuf（CortexStep）；引擎↔云保持标准 Gemini API 形状；工具生态用 MCP；凭据文件格式三端对齐。历史脉络：早期社区（`jiridan/agy-acp` 等）自己封装 ACP 桥 → Google Antigravity 2.0 官方出 `agy_acp_server` 注册进 ACP Registry（`id: antigravity-acp`）替代社区方案。

---

## 9. 证据索引

### 9.1 源码关键跳转表

| 论断 | 证据位置 |
|---|---|
| Python 不跑 Agent 循环，SDK spawn harness | `main.py:42-70`；server.py:4397 `agent.chat`；server.py:3436 "the Go LocalHarness replays it" |
| WS 客户端在 Python 侧 | server.py:33 `import websockets`；`:4419` 捕 `websockets.ConnectionClosed` |
| tool/hook 双向回调 | proxy_agent_config.py:101-135 `create_strategy(*, tool_runner, hook_runner)` |
| 凭据不进 Go、代理注入 | server.py:3580-3592（dummy key 注释 `:3669-3672`）；proxy_server.py:92-97 |
| X-ACP-Proxy-Token / X-ACP-Trajectory-Id | proxy_agent_config.py:59-68；proxy_server.py:64-73；server.py:4361-4366 |
| 消费级/企业双 endpoint | onboard.py:15-33 |
| Allow Always 缓存规则 | server.py:76-112 `_allow_always_signature` |
| harness stderr 被 SDK 吸走 | settings.py:226-227 注释 |
| 三端凭据格式对齐 | oauth/credential_store.py:7 |
| 浏览器 = npx chrome-devtools-mcp | server.py:3348-3374；browser_subagent.py |
| WS 断连重建+重放 | server.py:4387-4437 |

### 9.2 localharness_external.exe 二进制 strings（130,971,800 bytes）

`go1.` ／ `third_party/jetski/cortex_pb/options.proto` ／ `.antigravity.localharness.memory_filesystem` ／ `ConsumeTrajectory called on a closed state` ／ `Executor` ／ `101 Switching Protocols`+`Upgrade: websocket`+`Sec-WebSocket-Accept` ／ `127.0.0.1:0` ／ `ws://127.0.0.1:%s%s` ／ `{model}:streamGenerateContent?alt=sse` ／ `cloudcode-pa.googleapis.com/AgentPlugin`

### 9.3 运行时实测（2026-09 本机）

- 进程拓扑：1×`agy_acp_server` + 多个×`localharness_external`（每会话一个）；
- `~/.gemini/antigravity-acp/brain/<id>/.system_generated/tasks/task-*.log` = harness 终端任务输出；
- `~/.gemini/antigravity-cli/jetski_state.pbtxt` 内容为 Jetski 状态机枚举。

---

## 10. 未解之处（读源码前先知道边界）

1. **`google.antigravity` SDK 未提取**（在 PyInstaller 依赖层）：spawn 的命令行参数、WS 端点通告通道（推断为 stdout，未证实）、WS 是否有连接鉴权——均不可考；
2. `acp` 库（Zed 官方）同样未提取，ACP 方法到 `AgyAdapter` 的分发细节靠命名约定推断；
3. 本目录 `_private__agy_acp_server_bin.lazy_imports_info.json` 显示完整 google3 依赖树（matplotlib/IPython/grpc 等），说明 onefile 体积主要是内部依赖残留，核心链路只用其中一小部分；
4. 行号引用随上游版本漂移，跨版本请以符号名定位。

---

## 附录：快速验证命令（PowerShell）

```powershell
# 进程拓扑
Get-Process -Name 'agy_acp_server','localharness_external' | Select-Object Name, Path

# 安装目录（Zed 拉起的二进制）
Get-ChildItem "$env:LOCALAPPDATA\Zed\external_agents\registry\antigravity-acp" -Recurse -Include *.exe

# harness 是否 Go + 是否 WS 服务端（strings 验证）
$exe = (Get-ChildItem "$env:LOCALAPPDATA\Zed\external_agents\registry\antigravity-acp" -Recurse -Filter localharness_external.exe | Select-Object -First 1).FullName
$text = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($exe))
@('go1.', 'Sec-WebSocket-Accept', 'ws://127.0.0.1', 'third_party/jetski') | ForEach-Object { "{0}: {1}" -f $_, ($text.Contains($_)) }

# 运行时 home
Get-ChildItem "$env:USERPROFILE\.gemini\antigravity-acp" | Select-Object Name
```
