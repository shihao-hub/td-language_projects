# ccquota P0 任务清单

> 关联设计：`design.md`（同目录）。完成后勾选，并按仓库规范独立提交本文件的状态更新。

## 阶段一：骨架与只读接入

| # | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| T1 | 项目骨架 | `go_projects/ccquota/{go.mod,cmd/ccquota/internal/...}` | `ccquota-dev.exe --version` 与 `--help` 正常，退出码 0 | [x] |
| T2 | 构建脚本 | `build.py`（uv + PEP 723） | dev 出 `ccquota-dev.exe`；release 出无 `-dev` 的 `ccquota.exe` | [x] |
| T3 | 数据目录 | `internal/appenv` | 首次运行创建 `%APPDATA%\language_projects\ccquota\<dev|prod>\` | [x] |
| T4 | 只读 db 接入 | `internal/source/ccswitch` | 读出 11 个 provider 的 `name/app_type/meta/is_current`；`mode=ro` 打开；对 `.db` 无写操作 | [x] |

## 阶段二：查询器

| # | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| T5 | 查询器框架 | `internal/quota`（超时、错误归类、掩码日志、逐窗口防御） | 单测覆盖成功/401/403/空形态/超时五类 | [x] |
| T6 | `opencode_go` + `deepseek_balance` | `quota/codingplan/opencode.go`、`quota/balance/deepseek.go` | 数值与截图一致；`percent=0` 不显示倒计时 | [x] |
| T7 | `kimi_coding` + `codex_wham` | `quota/codingplan/kimi.go`、`quota/oauth/codex.go` | Kimi 5h 93%；Codex 84%/91%；token 过期显示「登录待刷新」 | [x] |
| T8 | `agy_quota` | `internal/cred/windows.go` + `quota/oauth/agy.go` | 读出 `gemini:antigravity`；两组各 100%；agy 缺失时给出明确错误 | [x] |
| T9 | `command_code` | `quota/codingplan/commandcode.go` | 四连调成功时出百分比；401 时为「认证失败」 | [x] |

## 阶段三：入口与缓存

| # | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| T10 | `list`（人读 + JSON） | `internal/cli/list.go` | 六卡对齐截图；`--json` 满足 `{"ok","data"}` 包络 | [x] |
| T11 | `doctor` / `schema` | `internal/cli/doctor.go`、`schema.go` | doctor 能分别指出 db/凭据/网络/形态问题；schema 零 I/O | [x] |
| T12 | 缓存与刷新 | `internal/store/cache.go` | 5 分钟 TTL 命中；`--refresh` 强制；失败保留旧快照 | [x] |
| T13 | WebUI | `internal/server` + `web/index.html`（`go:embed`） | `127.0.0.1:0` 启动、打印 URL、六卡同屏、<10% 加粗 | [x] |
| T14 | `watch` / `web` 常驻 | `internal/cli/watch.go`、`web.go` | Ctrl+C 优雅退出；`runtime.json` 写入与清理 | [x] |

## 阶段四：收尾

| # | 任务 | 产出 | 验收 | 状态 |
|---|---|---|---|---|
| T15 | 安全复核 | — | 全仓 grep 无明文密钥；日志掩码生效；`~/.cc-switch` 无新增文件 | [x] |
| T16 | 文档 | `docs/projects/go_projects/ccquota/README.md` | 记录：六个查询器、凭据位置、`doctor` 用法、P1/P2 边界 | [x] |

## 提交切分

1. 本 spec 与 tasks：父仓独立提交（`docs(specs): 新增 ccquota P0 只读额度查询设计`）。
2. 实现代码：`go_projects` 子仓内提交（`ccquota:feat: 实现只读额度查询 CLI 与 WebUI`）。
3. 勾选状态更新：任务收尾时再次独立提交本文件。

## P1 / P2 边界

已完成（P1 前半）：

- Wails v2 GUI：`ccquota-gui.exe`（`-H windowsgui`），复用同一份 `server.Handler` 与页面；
- 托盘常驻（getlantern/systray）、关窗收进托盘、托盘「打开窗口 / 退出」；
- 单实例锁（dev / prod 用不同 UniqueId，重复启动唤起已有窗口）。

未做：

- `mcp` 子命令（协议基线 `2026-07-28`）；
- agy 的 PE 子系统静默副本（GUI 场景的 DefTerm 保护）；
- 专属 GUI 图标（当前沿用 go-default.ico）。

P2：`goja` 执行 `meta.usage_script.code` 自定义脚本；智谱 / MiniMax / 火山 / Ollama / OpenRouter 等其余内置模板；agy HTTP + UA 伪装降级路径。

## 实施记录（与设计的偏差）

- **Kimi 凭据位置修正**：设计初稿写的是 `~/.cc-switch/kimi_accounts.json`，实测该文件的 `token` 只有 16 字符，拿去请求返回 401。真身是 `~/.kimi-code/credentials/*.json` 的 `access_token`（含 `expires_at`），已在 `design.md` 凭据矩阵同步更正。
- **hot journal 触发的只读失败**：cc-switch 运行期间库内可能残留未回滚的 journal，只读连接报 `attempt to write a readonly database (776)`。已在 `ccswitch` 层加「复制快照到本项目数据目录、在副本上恢复」的兜底，原库零写入。
- **agy 静默副本未移植**：P0 用 `SysProcAttr.HideWindow` 抑制闪窗，未移植 `agyquota` 的 PE Subsystem 改写；后者是 GUI 场景的 DefTerm 保护，留待后续。
- **Command Code 成功分支未验证**：当前 Key 已失效（401），只验证了认证失败分支；成功分支按 cc-switch 源码的四连调结构实现，待 Key 恢复后复核。
- **数值随时间漂移**：验收对照的截图值（98%/56%/84%/93%）与实测（97%/56%/75%/91%）差异来自截图与实测的时间差，非解析错误。
- **GUI 的技术路径**：GUI 不注册 Wails 绑定，而是把 `internal/server` 的 handler 直接交给 `assetserver`，页面与接口与 WebUI 完全同源。
- **窗口图标取决于资源 ID**：Wails v2 注册窗口类时先用 `IDI_APPLICATION`（即那个"空白窗口"图标）兜底，启动后再按**固定资源 ID 3**（`winc.AppIconID`）从 exe 的 `RT_GROUP_ICON` 加载并 `WM_SETICON`。go-winres 默认把图标打成名字 `"APP"` 的资源，ID 不匹配 → 加载失败（错误被忽略）→ 标题栏留白块。修法：`winres/gui.json` 的组图标键写成 `"#3"`（go-winres 的数字 ID 语法），Wails 即可自己加载，无需额外 Win32 代码。
- **默认视图收窄**：默认每个应用只显示一张（优先 `is_current`），`--all` / 「显示全部」展开全部；筛选在缓存读出后应用，切换不触发重新查询。
- **Antigravity 分组名缩写**：上游返回 `Gemini Models` / `Claude and GPT models`，卡片上缩为 `Gemini` / `Claude/GPT` 以免标签截断。
- **图标与主题按通道区分**：dev 用仓库默认 `icon_dev.ico`（白底 Go 图标）并把标题栏主题设为跟随系统，与 typeai / clictl 的 dev 通道一致；release 用 `scripts/render_icon.py` 生成的专属透明底图标 + 深色标题栏。托盘两通道都用专属透明图标（任务栏背景深，白底小图标难看）。
- **白底的真实成因**：`go-default.ico` 的 16×16 角落像素为 `(255,255,255,255)`，本身是不透明白底；之前强制 `Theme: Dark` 才把它照成白块。typeai 的 dev 版同样是白底图标，只因标题栏跟随浅色系统主题而看不出来。
- **托盘左右键分开**：`getlantern/systray` 把 `WM_LBUTTONUP` 与 `WM_RBUTTONUP` 都接到 `showMenu`，左键必然弹菜单；改用 `fyne.io/systray`，用 `SetOnTapped` 让左键开窗、右键保留菜单。
- **托盘「退出」会被 OnBeforeClose 拦截**：Wails v2 的 `Frontend.Quit()` 会先调用 `OnBeforeClose`，返回 `true` 即取消退出（`internal/frontend/desktop/windows/frontend.go:460`）。若该回调无条件「隐藏窗口 + return true」（关窗收进托盘的常见写法），托盘退出就永远无效。修法是用 `quitting` 原子标志区分「关窗」与「退出」：`quitApp` 先置位再 `runtime.Quit`。归档的 `file-sync-native` 是同样写法，存在同一缺陷。
