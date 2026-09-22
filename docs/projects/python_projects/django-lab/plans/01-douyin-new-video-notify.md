# Plan for: "douyinnotify — 抖音博主更新监控 + 飞书推送"

## 概述

**问题陈述**：手动刷抖音主页才能发现「Hucci写代码」等博主的新视频，容易漏。需要一套本机自动机制：定时检查被监控博主的作品列表，发现新视频即推送飞书提醒。范围边界：只做"检测新作品 + 推送"，不做视频下载、内容分析、评论抓取。

**需求**（澄清结论）：

- 推送渠道：飞书机器人私聊（用户指向 todo_notify 项目，沿用其 lark-cli bot 模式）
- 运行方式：Windows 计划任务定时跑（同 todo_notify 的 schtasks 模式），检查频率**可配置**（config.json `check_interval_hours` + `schedule_start`，默认 9 点开始每 6 小时；用户决策：9 点开始 6 小时一次）；**等到真正开发完毕才注册计划任务**（开发过程中不建常驻定时任务），且必须支持 uninstall
- 监控对象：支持多个博主（watchlist 配置），默认种子「Hucci写代码」（sec_uid `MS4wLjABAAAA-trbwHWLAaN5ka9E6noUB_0NFl0cQwJlwB-SwiAAHjA`）
- 用户原话决策：以 `todo_notify` 为架构模板（typer + uv + lark-cli + schtasks + 无浏览器 SDK 依赖）
- 用户原话决策：项目命名 `douyinnotify`，不要下划线；`todo_notify` 已被使用所以保持原名不动

**背景**（调研实证）：

- 纯 HTTP 不可行：带真实 ttwid 请求主页仍返回 72KB JS 风控挑战页（jsvmprt 混淆），无作品数据；抖音 web API 另需 a_bogus 签名，维护成本高
- 无头 Chrome 可行：`--headless=new` 能通过挑战拿到完整 DOM（已实测）；但一次性 `--dump-dom` 不含懒加载的作品列表，必须 CDP 带等待或拦截 XHR
- **无需登录**：未登录状态主页即展示作品列表（浏览器实测），免 cookie 维护；未登录会弹登录引导弹窗，但它只是 UI 遮罩——不阻断 `aweme/post` 数据 XHR，DOM 锚点也依然存在（选择器查 DOM 结构而非视觉可见性）。处理策略：完全忽略弹窗、全程不点击页面任何元素（防误触登录跳转）；专用 profile 持久化 ttwid，复访弹窗频率降低
- 作品接口 `aweme/v1/web/aweme/post/` 返回 newest-first JSON，是最佳检测信号；兜底信号为 DOM 中 `a[href*="/video/"]` 锚点
- 环境确认：Chrome 在 `C:\Program Files\Google\Chrome\Application\chrome.exe`；lark-cli 在 PATH
- `todo_notify` 分层可复用：`applog / cli / notifier / report / scanner→(本项目为 fetcher+detector) / scheduler`
- 仓库强约束（AGENTS.md + CLI 工具开发标准）：新 CLI 工具默认双入口（CLI + `mcp` 子命令 stdio server）+ `schema` 导出 + `--json` 包络 `{"ok":..,"data":..}` + 退出码 0 成功 / 2 参数错误 / 1 其他失败；运行时数据只放 `%APPDATA%\language_projects\<项目名>\`；子模块内禁止文档目录，项目文档入 README（大写例外），计划文件归父仓库 docs

**方案**：

- 新项目 `python_projects\douyinnotify\`（monorepo 新子目录，不单独 `git init`），uv + src 布局，运行依赖 `typer`、`websocket-client`、`mcp`（FastMCP），dev `pytest`、`pyright`
- 数据流：`check` → 逐博主抓取最新作品列表（CDP 无头 Chrome，专用 profile）→ 与 `state.json` 上次所见比对 → 有新作品则渲染飞书消息并经 lark-cli 发送 → 更新 state；无新作品静默
- 模块：`browser`（Chrome 进程 + CDP 连接生命周期）、`fetcher`（抓取与解析，解析为纯函数便于测试）、`watchlist`（config.json 读写）、`state`（state.json 读写）、`detector`（diff）、`report`（人读/JSON/飞书消息渲染）、`notifier`（lark-cli 子进程）、`scheduler`（schtasks）、`applog`、`cli`、`mcp_server`、`schema_export`
- 抓取实现：启动系统 Chrome `--headless=new --remote-debugging-port=0 --user-data-dir=<APPDATA profile>`，经 DevToolsActivePort 建 CDP 连接，导航主页后启用 Network 域拦截 `aweme/post` 响应（主信号），超时兜底等待 DOM 锚点；每博主一次导航，全程有界超时，结束杀进程树
- 能力表（CLI 标准 §1.1）：

| 业务用例 | CLI 入口 | MCP 工具 | 输入、结果与副作用 | 执行方式与差异 | 暴露理由 |
|---|---|---|---|---|---|
| 立即检查一次 | `check`（默认） | `douyinnotify.check` | 相同抓取、比对、state 写入 | CLI 人读/JSON；MCP 结构化结果；`--notify` 仅 CLI | 双入口都需要 |
| 查看监控状态 | `list` | `douyinnotify.list` | 相同 watchlist + 上次检查快照 | 双入口结构化一致 | 双入口都需要 |
| 添加博主 | `add <主页URL或sec_uid>` | `douyinnotify.add` | 相同归一化校验与持久化 | 双入口一致 | 双入口都需要 |
| 移除博主 | `remove <sec_uid>` | `douyinnotify.remove` | 相同校验与持久化 | 双入口一致 | 双入口都需要 |
| 注册/卸载计划任务 | `install_schedule` / `uninstall_schedule` | 不暴露 | 本机 schtasks 管理 | 终端集成，MCP 会话无意义 | 终端管理操作 |
| 离线契约 | `schema` | —（导出 MCP 工具目录） | 不启动业务依赖 | 与实际注册同源 | 标准硬要求 |
| 协议入口 | `mcp` | —（自身即 server） | stdio | 标准硬要求 | agent 检查入口 |

- 关键决策与假设（批准门可推翻）：
  1. 抓取走"系统 Chrome + 裸 CDP（websocket-client）"而非 Playwright：免下载浏览器与重量驱动，贴合仓库轻依赖风格；若实现期 CDP 稳定性不足，升级 Playwright（channel="chrome"）作为已记录替代方案
  2. watchlist 首次运行自动种子 Hucci 写入 config.json，用户可 `add`/`remove`
  3. 飞书收件人沿用 todo_notify 的 open_id（收件人是用户本人）
  4. 新视频判定 = aweme_id 集合差（new ids 减 state 已见 ids）；首次检查只记录基线不推送，避免历史视频轰炸
  5. 本计划文件按仓库约束放父仓库 `docs\projects\python_projects\douyinnotify\plans\`，项目子目录内不建 plans/
  6. 项目命名 `douyinnotify`（无下划线，用户决策）：项目目录、Python 包、CLI 命令、计划任务名统一用该词；`todo_notify` 保持原名（已被使用，不动）
  7. 类型检查采用 pyright（用户决策）：比 mypy 更成熟——Pylance 同源引擎、类型推断开箱即用、速度快；作为 dev 依赖，Task 1 起配置生效
  8. 计划任务时机（用户决策）：开发过程中不注册常驻定时任务——Task 7 只交付 `install_schedule` / `uninstall_schedule` 代码能力；全部开发完毕后在 Task 9 收尾时才真正 `install_schedule` 定时跑，卸载随时可用 `uninstall_schedule`

## 任务分解

> 执行规范说明：按用户约定默认连续执行、不写测试不跑测试；各任务的"验证"为备用信息，涉及"编写测试"的子项跳过并在汇报中说明。

- [x] Task 1: 项目骨架与配置路径
  - 文件：`python_projects\douyinnotify\pyproject.toml`、`src\douyinnotify\__init__.py`、`__main__.py`、`cli.py`（check 占位）、`applog.py`、`paths.py`、`pyrightconfig.json`
  - 实现：照 todo_notify 搭 uv + hatchling src 布局；dev 依赖 pytest、pyright，`pyrightconfig.json` 限定 `src` 目录用 basic 模式；`paths.py` 解析 `%APPDATA%\language_projects\douyinnotify\`（回退 `~/.language_projects/`，写入前建目录链）；applog 按天轮转保留 14 份；CLI 注册全部子命令占位
  - 验证：`uv sync` 成功；`uv run douyinnotify --help` 列出全部子命令；`uv run pyright` 0 错误；`uv run pytest` 空跑通过
  - Demo：`uv run douyinnotify --help` 输出命令清单

- [x] Task 2: watchlist 与 state 存储（依赖 Task 1）
  - 文件：`src\douyinnotify\watchlist.py`、`state.py`、`tests\test_watchlist.py`、`tests\test_state.py`
  - 实现：config.json（博主列表：sec_uid、昵称、备注；`check_interval_hours` 检查间隔小时数 + `schedule_start` 起始时间 HH:MM，默认 9 点起每 6 小时；兼容读旧 `check_interval_minutes` 字段换算为小时）与 state.json（每博主已见 aweme_id 集合、上次检查时间）读写，原子写（临时文件+替换）；首启种子 Hucci；`list` / `add` / `remove` 接 CLI（URL 或裸 sec_uid 归一化，非法输入退出码 2）
  - 验证：`uv run pytest`（tmp_path 注入隔离，覆盖首启种子、重复 add、remove 不存在项）；`uv run douyinnotify list` 显示种子博主
  - Demo：`uv run douyinnotify add <某主页URL>` 后 `list` 出现新条目

- [x] Task 3: 抓取层 browser + fetcher（依赖 Task 1）
  - 文件：`src\douyinnotify\browser.py`、`src\douyinnotify\fetcher.py`、`tests\test_fetcher_parse.py`、`tests\fixtures\aweme_post_sample.json`
  - 实现：browser 负责 Chrome 进程树生命周期（启动 `--headless=new --remote-debugging-port=0`、DevToolsActivePort 发现、websocket 连接、有界超时、退出杀树）；fetcher 主信号采用 **SSR DOM 提取**——实施实证链：CDP Network 域 `getResponseBody` 对 `aweme/post` 始终返回空体（响应头阶段与 loadingFinished 后皆空）；页面内 hook 可注入（前置条件 `Page.enable`，否则 `addScriptToEvaluateOnNewDocument` 被静默忽略）但捕获到的响应同为空 body；`RENDER_DATA` 无作品数据——未登录下作品列表为 SSR HTML 直出，唯一可用数据源是 DOM。导航后轮询 `a[href*="/video/"]` 锚点提取 (id, title)（created_at 不可得置 None，新视频判定只做 id 集合差不受影响）；解析为纯函数便于离线测试；全程不与页面交互（忽略登录弹窗、不点任何按钮），弹窗不影响取数
  - 验证：`uv run pytest`（用 fixtures 样本测解析：空列表、字段缺失容错）；`uv run douyinnotify check --json --no-save`（临时调试口）对真实页面返回首条 id `7687214195997232419`
  - Demo：`check --json` 输出 Hucci 当前最新视频 id 与标题

- [x] Task 4: 检测与消息渲染（依赖 Task 3）
  - 文件：`src\douyinnotify\detector.py`、`src\douyinnotify\report.py`、`tests\test_detector.py`、`tests\test_report.py`
  - 实现：detector 计算新视频集合（首检只记基线不推送）；report 出三种渲染：人读文本、`{"ok":..,"data":..}` JSON、飞书 post markdown（博主名+视频标题+链接，标题行作消息首行）
  - 验证：`uv run pytest`（首检基线、增量检出、无新视频静默三态）
  - Demo：单测模拟 state 旧、列表新 → 输出含新视频链接的消息体

- [x] Task 5: 飞书通知 notifier（依赖 Task 4）
  - 文件：`src\douyinnotify\notifier.py`、`tests\test_notifier.py`
  - 实现：移植 todo_notify 的 lark-cli bot 发送（shutil.which 解析 .cmd、`--content` JSON 单行、message_id 解析、NotifyError）；build_command / build_post_content 供 dry-run 复用
  - 验证：`uv run pytest`（命令构造、非 JSON 响应容错）；`uv run douyinnotify check --notify --dry-run` 打印将执行命令与消息体
  - Demo：dry-run 输出完整 lark-cli 命令与 markdown 消息

- [x] Task 6: check 主流程接线（依赖 Task 2/3/4/5）
  - 文件：`src\douyinnotify\cli.py`（check 实现）、`tests\test_cli_check.py`
  - 实现：串联 watchlist→fetcher→detector→state→report→notifier；`--notify`/`--dry-run`/`--json`/`--no-save`；退出码 0/2/1（发送失败 1，参数错误 2）；抓取失败不破坏 state；发送与 state 更新顺序保证"发了不重发"（先原子写 state 再发，失败下次漏发可接受 vs 先发后写崩溃重发——取先写后发，文档记录该取舍）；**抖动抑制**：实施实证未登录下同一博主每次 SSR 返回的作品集合可能完全不同（抽样抖动），单博主单轮新增 > `MAX_NEWS_PER_CHECK`（3）条视为抖动——id 全量并入 seen 但不推送，防止误报轰炸（代价：博主单次连发 >3 条会漏推，README 已知限制记录）
  - 验证：`uv run pytest`（CliRunner + monkeypatch fetcher/notifier：新视频发送路径、静默路径、抓取异常路径）；`uv run douyinnotify check` 真实跑通
  - Demo：手工改 state 后 `check --notify` 飞书收到新视频提醒，再跑一次静默

- [x] Task 7: 计划任务调度能力（依赖 Task 6；只交付代码，不注册常驻任务）
  - 文件：`src\douyinnotify\scheduler.py`、`tests\test_scheduler.py`
  - 实现：照 todo_notify 的 schtasks 模式实现 `install_schedule`（`/SC HOURLY /MO <check_interval_hours> /ST <schedule_start>` 注册 `douyinnotify_check`，/TR 指向 venv 内 **`pythonw.exe -m douyinnotify --notify`**——console exe 被计划任务在交互会话运行会弹控制台窗口，pythonw 无窗口（用户决策：不得弹终端窗），stdout 失效由 `_print` 容错兜底、排障靠日志），间隔与起始时间读 config.json；与对称的 `uninstall_schedule`；install 前检测已存在任务防重复注册，uninstall 幂等（任务不存在给提示不报错）；全部 subprocess 调用（schtasks/taskkill/lark-cli/Chrome）加 `CREATE_NO_WINDOW` 杜绝 conhost 闪现。**本任务不执行正式注册**——按用户决策，等到全部开发完毕（Task 9 收尾）才真正定时跑
  - 验证：`uv run pytest`（monkeypatch schtasks 调用，断言注册/卸载命令行参数）；真实自清理验证：`install_schedule` → `schtasks /Query /TN douyinnotify_check` 存在 → `uninstall_schedule` → `/Query` 确认消失，验证后不残留常驻任务
  - Demo：注册→查询→卸载→查询消失的全流程演示，结束时系统无 `douyinnotify_check` 任务

- [ ] Task 8: MCP 入口与 schema 导出（依赖 Task 6）
  - 文件：`src\douyinnotify\mcp_server.py`、`src\douyinnotify\schema_export.py`、`tests\test_mcp_stdio.py`
  - 实现：FastMCP stdio server 暴露 `douyinnotify.check/list/add/remove`（inputSchema/outputSchema 与业务 DTO 同源，readOnly/idempotent 标注按实填）；`schema` 子命令导出与注册同源的工具目录 JSON，不启动业务依赖
  - 验证：`uv run pytest`（真实 stdio 子进程：initialize → tools/list → check 调用（monkeypatch 抓取）→ stdout 无污染）；`uv run douyinnotify schema` 输出与 tools/list 对照一致
  - Demo：`uv run douyinnotify schema` 打印契约目录；MCP stdio 测试通过

- [ ] Task 9: 交付收尾与端到端验收（依赖 Task 7/8，接线收尾）
  - 文件：`python_projects\douyinnotify\README.md`、（如需）`docs\projects\python_projects\douyinnotify\` 下补充说明
  - 实现：README 记录能力表、运行方式、`install_schedule` / `uninstall_schedule` 使用说明、配置与数据目录（含 `check_interval_minutes` 说明：修改后需重跑 `install_schedule` 才对已注册计划任务生效）、已知限制（首检基线不推送、先写 state 后发消息的取舍、抖动抑制漏推、CDP 依赖本机 Chrome、抖音风控可能导致偶发检查失败重试下轮）与 MCP 使用；对照 CLI 标准 §9.3 发布前清单逐项核对；**全部开发完毕后执行 `install_schedule` 正式注册计划任务**（按配置间隔定时跑，即"开发完毕再定时"）；端到端：改 state 模拟新视频 → `schtasks /Run /TN douyinnotify_check` → 飞书收到推送
  - 验证：README 步骤照跑可行（含 `uninstall_schedule` 卸载后重装）；发布前清单全勾；`schtasks /Query /TN douyinnotify_check` 可见且下次运行时间正确
  - Demo：计划任务触发的一次完整"检测→推送"链路证据（日志 + 飞书消息）
  - **实施说明(2026-09-21,端到端受阻待用户决策)**:Task 1-8 已完成且 pyright 0 错误;`install_schedule` 已真实验证(注册/查询/卸载/重装),任务命令最终定为 `pythonw.exe -m douyinnotify --notify`(用户要求零弹窗:console exe 被计划任务运行会弹控制台,pythonw 无窗口;全部 subprocess 另加 `CREATE_NO_WINDOW`),pythonw 链路经 `/Run` 真实验证可执行。端到端推送卡住--实施实证推翻计划前提"无需登录":未登录 SSR 返回的是 SEO 混合内容(`href` 带 `?source=Baiduspider`,标题与博主无关、每轮全变),抓到的"作品列表"不可信 → 集合差持续抖动 → 抑制逻辑永不放行 → 推送无法触发。定时任务已临时卸载防止空转。待用户在“扫码登录（推荐）/其他信号源”间决策后修订计划再继续。

> **后续（2026-09-22）**：用户决策「先 D 止血、再 B 换源」。已实证新数据源无需登录：在页面上下文内 `fetch` 作品接口即可拿到完整 JSON；`fetcher` 已改为该取数方式并硬化失败语义，Task 1-3 全部完成且端到端推送验收通过。详见 [`plans/02-douyin-fetch-api-source.md`](./02-douyin-fetch-api-source.md)。

---

**最后更新：** 2026-09-21
**作者：** AI & User
**版本：** v1.2.0
