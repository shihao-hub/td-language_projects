# Requirements Document — glmquotawatch-gui Fyne 重写

## Summary

把 glmquotawatch-gui 的 GUI 层从 Wails v3 + Vue 3 原地重写为纯 Go 的 Fyne（v2.8.1）实现：
业务核心（api / store / quota / service / cli 五个包）全部复用不动，替换 `internal/guiapp`
组装层与整个 `frontend/`（Vue 前端删除），运行形态从「Go 进程 + WebView2 多进程」收敛为
**单进程、无 WebView2 依赖**。全部既有功能语义与验收标准保持平移（AC-1 ~ AC-12 不变）。

用户已确认决策（2026-09-27）：

- **替换方式**：原地改造（不新建并行项目；复用业务核心，替换 GUI 层，CLI 与数据格式不变）
- **UI 风格**：Fyne 原生 Material 风（不做 Web 风格像素级复刻）
- **历史图表**：自绘 Canvas 折线图（零第三方图表依赖）
- **分支**：子仓 `glmquotawatch-gui` 新建 `feat/fyne-rewrite` 分支实施

已知平台能力差异（Fyne 无托盘 tooltip API）：原版「托盘 tooltip 反映用量状态」改由
**托盘菜单首项状态行**（禁用项动态文本）承载，语义保留（正常 / 已告警 / 采样失败可区分）。

## Functional Requirements

- **FR-1 用量监控（GUI 常驻）**：启动后立即采样一次，此后按 interval 周期采样（默认 5m，合法范围 clamp 至 30s–24h）；单次采样失败不中断监控，下轮自动重试。（语义与校验完全沿用 service 层，不变）
- **FR-2 阈值告警**：对每个 TOKENS_LIMIT 窗口按阈值档位（默认 50/60/80/90%）评估；向上首次越档发送一条原生 Windows Toast，只报本次新触发的最高档（同轮多窗口合并为一条多行通知）；已通知档位持久化记账，重启不重复轰炸；用量回落跌破 min(thresholds) − hysteresis 后重置该窗口的已告警记录；阈值配置变更即整体重置记账。（不变）
- **FR-3 主窗仪表盘**：展示套餐等级、上次采样时间与逐窗口用量视图（窗口人读标签、百分比、进度条、重置倒计时、已通知档位）；提供「立即采样」手动刷新；采样失败展示错误态（含错误信息与下轮重试提示）。Fyne 版为原生控件自绘进度条（分档配色），布局按 Fyne Material 风重新实现，信息项不减。
- **FR-4 历史趋势**：读取本机采样历史（samples-YYYY-MM.jsonl），展示所选窗口在所选近期时间段内的百分比变化曲线；无历史数据时展示空态。Fyne 版曲线为自绘 Canvas 折线（阈值虚线、坐标标签），数据超采样时下采样，不引第三方图表库。
- **FR-5 设置页**：token 设置（trim 后长度 ≥ 20 校验）/ 脱敏显示 / 清除；interval、thresholds、hysteresis、silent 配置项修改；展示数据目录路径。演示模式下整页只读（原有 demo_readonly 语义，改为 UI 禁用 + 服务端拒绝双保险）。
- **FR-6 托盘集成**：关闭主窗即隐藏到托盘，监控持续，退出仅经托盘菜单；托盘菜单含**状态行（首项，禁用、动态文本，替代原 tooltip 语义）**、显示主窗、立即采样、静音开关、开机自启开关、演示模式入口、退出；**左键点击托盘图标显示主窗**（Fyne `SetSystemTrayWindow`）；启动时未配置 token 则引导进入设置页。
- **FR-7 单实例**：重复启动不产生第二个常驻实例，而是激活既有实例的主窗后新进程自行退出；第二实例携带 `--demo` 时，主实例当场进入演示模式（沿用原语义）。
- **FR-8 CLI 壳（面向机器）**：不改动。子命令 `token set/show/remove`、`status`、`config show/set`、`schema`；stdout 恒 JSON 信封；退出码 0/1/2；不带子命令启动进入 GUI。
- **FR-9 schema 导出**：不改动（`schema` 零业务 I/O，`interface: "cli"`）。
- **FR-10 数据持久化**：不改动。config.json / state.json / samples-YYYY-MM.jsonl 三件套、原子写、目录规则（`%APPDATA%\language_projects\glmquotawatch-gui\prod|dev`，demo 为其 `demo` 子目录）全部保持。
- **FR-11 演示模式（时间压缩模拟）**：功能不变。`--demo` 启动参数、托盘菜单入口、独立 demo 数据目录、60 倍速 0→100%、5s 采样间隔、完整告警链路、随时退出恢复真实模式。Fyne 版演示横幅倒计时同样呈现。
- **FR-12 开机自启**：功能不变。托盘菜单开关（勾选可见）；开启注册 `"exe" --hidden`（HKCU Run），登录后托盘静默运行不弹窗；关闭移除；开发版（`-tags dev`）禁止注册（保留防呆）。
- **FR-13 单进程轻量运行（新增）**：GUI 常驻期间为**单进程**，无 WebView2 / 浏览器 / Web 运行时依赖；不携带前端构建产物；构建产物不依赖 Node/npm 工具链（仅 Go + C 编译器）。

## Non-Functional Requirements

- **NFR-1**：exe 携带仓库站标地鼠默认图标（`docs/assets/projects/go_projects/go-default.ico` 同源资源），托盘图标与 exe 图标同源设计。
- **NFR-2**：通知使用 Windows 原生 Toast，并以本应用自身身份（AUMID）发出；不发 PowerShell 借壳通知。
- **NFR-3**：CLI stdout 只输出纯 JSON；日志与诊断一律 stderr。（不变）
- **NFR-4**：Windows 11 为首要目标平台；构建链依赖 CGO + MinGW gcc（本机 MSYS2 MinGW64 已具备）。
- **NFR-5**：运行期单进程、无 WebView2 依赖；任务管理器中不出现 `msedgewebview2.exe` 子进程。
- **NFR-6**：界面全部中文文本正确渲染（嵌入中文字体子集，零方块字）。
- **NFR-7**：常驻内存占用应显著低于 Wails 版（WebView2 进程树合计）；不设硬性数字，实测记录为准。

## Acceptance Criteria

### AC-1 周期监控刷新
WHEN token 已配置且 GUI 常驻运行，THE SYSTEM SHALL 启动后立即完成首次采样，并按 interval 周期采样，主窗与托盘状态同步刷新为最新结果（上次采样时间随之更新）。

### AC-2 阈值 Toast 与告警记录重置
WHEN 某窗口用量首次升至 ≥ 50% 且该档未通知，THE SYSTEM SHALL 发送恰好一条 Windows Toast（含窗口标签、百分比、档位）；WHEN 随后单轮继续升至 92%（越过 60/80/90），本轮仅按最高新触发档位播报；WHEN 用量跌破 45%（50 − hysteresis 5）后再次升穿 50%，THE SYSTEM SHALL 再次告警；安静档 silent=true 时仍发送通知但无声。

### AC-3 关窗到托盘
WHEN 用户点击主窗关闭按钮，THE SYSTEM SHALL 隐藏窗口并保持托盘与后台采样运行；WHEN 用户经托盘菜单退出，THE SYSTEM SHALL 完全退出（托盘图标移除、采样停止、进程结束）。

### AC-4 单实例
WHEN 已有实例常驻时再次启动，THE SYSTEM SHALL 激活既有实例主窗（主实例收到通知后 Show + 聚焦），新进程自行退出，且全程数据文件无并发损坏；WHEN 第二实例携带 `--demo`，主实例 SHALL 就地进入演示模式。

### AC-5 CLI 恒 JSON
WHEN 任一 CLI 子命令执行成功，THE SYSTEM SHALL 向 stdout 输出 `ok=true` 且含 `data` 的 JSON 信封，退出码 0；WHEN 业务失败，输出 `ok=false` 且含 `error.code/message` 的信封，退出码 1；WHEN 参数或 flag 错误，输出信封，退出码 2。（不变）

### AC-6 schema 零 I/O
WHEN 执行 `schema`，THE SYSTEM SHALL 向 stdout 输出本 CLI 契约目录（含命令名称、描述、输入/输出结构与 `interface: "cli"` 字段），且全程不创建数据目录、不发起网络请求。（不变）

### AC-7 校验规则兼容
WHEN 任一入口提交长度 < 20 的 token，THE SYSTEM SHALL 以稳定错误码拒绝；WHEN interval / thresholds / hysteresis / silent 被设为越界值，THE SYSTEM SHALL 拒绝且原配置保持不变。（不变）

### AC-8 历史曲线
WHEN 打开历史图表且本地 samples 文件有数据，THE SYSTEM SHALL 按所选窗口与时间段渲染百分比变化曲线（自绘折线含阈值虚线）；WHEN 无历史数据，展示明确空态且不报错。

### AC-9 数据目录规则
WHEN 工具产生任何持久化写入，THE SYSTEM SHALL 仅写入 `%APPDATA%\language_projects\glmquotawatch-gui\`（或回退目录）的对应子目录，且写入前目录链已自动创建。（不变）

### AC-10 未配置 token 引导
WHEN GUI 启动时 token 未配置，THE SYSTEM SHALL 展示配置引导（进入设置页完成 token 录入），而非反复弹出错误对话框。

### AC-11 演示模式时间压缩
WHEN 以演示模式启动（`--demo` 或 GUI 菜单入口），THE SYSTEM SHALL 在 5 分钟真实时间内把窗口百分比从 0% 线性推进至 100%，依次触发 50/60/80/90% 档位 Toast，主窗与托盘状态同步变化；且全程只写演示数据目录；WHEN 退出演示并恢复真实模式，THE SYSTEM SHALL 按真实数据目录的原有状态继续工作。（不变）

### AC-12 开机自启开关
WHEN 用户经托盘菜单开启开机自启，THE SYSTEM SHALL 注册自启项（HKCU Run，命令含 `--hidden`）且菜单状态同步勾选，重新登录后应用以托盘形态自动运行（不弹主窗、不抢焦点）；WHEN 关闭该开关，THE SYSTEM SHALL 移除自启项；开发版 SHALL 拒绝注册并给出明确错误。

### AC-13 单进程与无 WebView2
WHEN 应用运行期间查看进程树，THE SYSTEM SHALL 仅存在自身单个进程；无 `msedgewebview2.exe` 或其它浏览器运行时子进程；卸载/未安装 WebView2 的 Windows 11 上功能不受影响。

### AC-14 托盘状态行
WHEN 任一轮采样完成或失败，THE SYSTEM SHALL 在托盘菜单首项展示对应状态文本（如 `最高 62%（5h 窗口）· 已告警 90%` / `采样失败，下轮自动重试` / `演示模式 · 45%`），且菜单项不可点击、随状态刷新。

### AC-15 中文渲染
WHEN 界面展示任何中文文本（页面标题、按钮、通知内容、错误信息），THE SYSTEM SHALL 正确渲染无缺字方块（嵌入字体覆盖全部固定文案字符集）。

## Out of Scope

- Web 前端（Vue/Vite/Tailwind/ECharts）的保留或双轨运行：整体删除，不回退 Wails。
- 像素级复刻原 Web 版视觉（浅色 CC Switch / Raycast 风、圆角卡片阴影体系）：只保信息架构与语义。
- 托盘 tooltip 原样能力：Fyne 无该 API，以菜单状态行替代（见 FR-6）。
- 托盘图标状态变体（正常/告警双图标）：维持单图标；状态经菜单状态行承载。
- 窗口最小尺寸约束：Fyne 无最小尺寸 API，仅设默认尺寸 920×560。
- 非 Windows 平台的构建与验收（Fyne 理论跨平台，不纳入本期验收）。
- MCP server、CLI 人读输出、无头 daemon、旧版数据迁移、TIME_LIMIT 告警、国际版端点、自动更新、多语言、多账号（与原版一致，维持排除）。
