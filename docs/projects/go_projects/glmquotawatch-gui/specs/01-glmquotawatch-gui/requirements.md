# Requirements Document — glmquotawatch-gui

## Summary

把归档项目 `.archived/projects/go_projects/glmquotawatch`（GLM 编码套餐用量采样 + 阈值 Toast 告警 CLI 工具）复活为桌面 GUI 工具：Wails v3（Web 前端 + Go 后端）+ 托盘常驻。GUI 成为面向人的主入口（用量仪表盘、设置、历史趋势、演示模式）；CLI 保留为面向机器的薄壳——所有命令恒输出 JSON 信封，不提供人读模式；MCP 壳不保留（用户决策，偏离理由按《CLI 工具开发标准》记录于设计文档）。业务核心（上游采样、阈值状态机、本地持久化）沿用归档版设计，落在全新项目目录 `go_projects/glmquotawatch-gui/`。

已确认决策（用户 2026-09-25）：

- 框架：Wails v3（beta.25，接受 beta 状态以换取内置托盘/原生通知/单实例能力）
- 形态：托盘常驻（关窗最小化到托盘，后台监控持续）
- 壳：GUI + CLI 双壳，不保留 MCP
- 项目名：`glmquotawatch-gui`（新数据目录，不继承旧数据；token 重新录入一次）

## Functional Requirements

- **FR-1 用量监控（GUI 常驻）**：启动后立即采样一次，此后按 interval 周期采样（默认 5m，合法范围 clamp 至 30s–24h）；单次采样失败不中断监控，下轮自动重试。
- **FR-2 阈值告警**：对每个 TOKENS_LIMIT 窗口按阈值档位（默认 50/60/80/90%）评估；向上首次越档发送一条原生 Windows Toast 通知，只报本次新触发的最高档（同轮多窗口合并为一条多行通知）；已通知档位持久化记账，重启不重复轰炸；用量回落跌破 min(thresholds) − hysteresis 后重置该窗口的已告警记录，再次越档会重新告警；阈值配置变更即整体重置记账。
- **FR-3 主窗仪表盘**：展示套餐等级、上次采样时间与逐窗口用量视图（窗口人读标签、百分比、进度条、重置倒计时、已通知档位）；提供「立即采样」手动刷新；采样失败展示错误态（含错误信息与下轮重试提示）。
- **FR-4 历史趋势**：读取本机采样历史（samples-YYYY-MM.jsonl），展示所选窗口在所选近期时间段内的百分比变化曲线；无历史数据时展示空态。
- **FR-5 设置页**：token 设置（trim 后长度 ≥ 20 校验）/ 脱敏显示 / 清除；interval、thresholds、hysteresis、silent 配置项修改；展示数据目录路径。
- **FR-6 托盘集成**：关闭主窗即隐藏到托盘，监控持续，退出仅经托盘菜单；托盘菜单含显示主窗、立即采样、静音开关、开机自启开关、演示模式入口、退出；托盘图标或 tooltip 反映当前用量档位（正常 / 已告警等可区分）；启动时未配置 token 则引导进入设置页。
- **FR-7 单实例**：重复启动不产生第二个常驻实例，而是激活既有实例的主窗后新进程自行退出。
- **FR-8 CLI 壳（面向机器）**：子命令 `token set <token>`、`token show`、`token remove`、`status`、`config show`、`config set <key> <value>`、`schema`；stdout 恒输出 JSON 信封 `{"ok":true,"data":…}` / `{"ok":false,"error":{"code","message"}}`；不提供人读输出模式，也无 `--json` flag（恒等 JSON）；`status` 语义与归档版一致（立即采样一次、落历史、推进告警状态、不发通知）；不带子命令启动即进入 GUI。
- **FR-9 schema 导出**：`schema` 输出本 CLI 自身的命令输入/输出契约 JSON，声明 `interface: "cli"`；导出流程零业务 I/O（不发网络请求、不读写配置、不创建数据目录）。
- **FR-10 数据持久化**：config.json（配置，含 token）、state.json（已告警档位记录）、samples-YYYY-MM.jsonl（采样历史）三类文件，位于 `%APPDATA%\language_projects\glmquotawatch-gui\`（取不到 AppData 时回退 `~/.language_projects/glmquotawatch-gui/`），写入前自动创建完整目录链；文件结构与归档版兼容；GUI 进程与 CLI 进程并发读写不产生损坏文件（原子写）。
- **FR-11 演示模式（时间压缩模拟）**：提供 `--demo` 启动参数与 GUI 菜单触发入口两种形态；启用后数据源切换为内置模拟上游——窗口百分比在 5 分钟真实时间内从 0% 线性增长至 100%（模拟 5 小时窗口 60 倍速），重置倒计时同步压缩，采样间隔自动缩短（秒级）；演示期间照常走完整链路（档位记账、Toast 告警、托盘与主窗刷新、历史曲线）；演示使用独立数据目录并自动注入虚拟 token，不污染真实 token、配置、采样历史与告警记账；演示可随时退出并恢复真实模式。
- **FR-12 开机自启**：托盘菜单提供开机自启开关（当前状态在菜单中勾选可见）；开启后注册 Windows 自启项，登录后应用自动启动并以托盘形态静默运行（不弹主窗、不抢焦点）；关闭则移除自启项；自启项以本工具自身身份注册，卸载或删除 exe 后不留无效残留提示（残留项不产生副作用即可）。

## Non-Functional Requirements

- **NFR-1**：exe 携带仓库站标地鼠默认图标（`docs/assets/projects/go_projects/go-default.ico`），托盘图标同源。
- **NFR-2**：通知使用 OS 原生 Toast（以本应用自身身份发出），不再借用 PowerShell AUMID 身份。
- **NFR-3**：CLI stdout 只输出纯 JSON（信封 + 末尾换行）；日志与诊断信息一律 stderr。
- **NFR-4**：Windows 11 为首要目标平台（WebView2 系统自带）；CLI 壳不依赖 GUI 运行。

## Acceptance Criteria

### AC-1 周期监控刷新
WHEN token 已配置且 GUI 常驻运行，THE SYSTEM SHALL 启动后立即完成首次采样，并按 interval 周期采样，主窗与托盘状态同步刷新为最新结果（上次采样时间随之更新）。

### AC-2 阈值 Toast 与告警记录重置
WHEN 某窗口用量首次升至 ≥ 50% 且该档未通知，THE SYSTEM SHALL 发送恰好一条 Toast（内容含窗口标签、百分比、档位）；WHEN 随后单轮继续升至 92%（越过 60/80/90），本轮仅按最高新触发档位播报；WHEN 用量跌破 45%（50 − hysteresis 5）后再次升穿 50%，THE SYSTEM SHALL 再次告警。

### AC-3 关窗到托盘
WHEN 用户点击主窗关闭按钮，THE SYSTEM SHALL 隐藏窗口并保持托盘与后台采样运行；WHEN 用户经托盘菜单退出，THE SYSTEM SHALL 完全退出（托盘图标移除、采样停止、进程结束）。

### AC-4 单实例
WHEN 已有实例常驻时再次启动，THE SYSTEM SHALL 激活既有实例主窗，新进程自行退出，且全程数据文件无并发损坏。

### AC-5 CLI 恒 JSON
WHEN 任一 CLI 子命令执行成功，THE SYSTEM SHALL 向 stdout 输出 `ok=true` 且含 `data` 的 JSON 信封，退出码 0；WHEN 业务失败，输出 `ok=false` 且含 `error.code/message` 的信封，退出码 1；WHEN 参数或 flag 错误，输出信封，退出码 2。

### AC-6 schema 零 I/O
WHEN 执行 `schema`，THE SYSTEM SHALL 向 stdout 输出本 CLI 契约目录（含各命令名称、描述、输入/输出结构与 `interface: "cli"` 字段），且全程不创建数据目录、不发起网络请求。

### AC-7 校验规则兼容
WHEN 任一入口提交长度 < 20 的 token，THE SYSTEM SHALL 以稳定错误码拒绝；WHEN interval / thresholds / hysteresis / silent 被设为越界值，THE SYSTEM SHALL 拒绝且原配置保持不变。

### AC-8 历史曲线
WHEN 打开历史图表且本地 samples 文件有数据，THE SYSTEM SHALL 按所选窗口与时间段渲染百分比变化曲线；WHEN 无历史数据，展示明确空态且不报错。

### AC-9 数据目录规则
WHEN 工具产生任何持久化写入，THE SYSTEM SHALL 仅写入 `%APPDATA%\language_projects\glmquotawatch-gui\`（或回退目录），且写入前目录链已自动创建。

### AC-10 未配置 token 引导
WHEN GUI 启动时 token 未配置，THE SYSTEM SHALL 展示配置引导（进入设置页完成 token 录入），而非反复弹出错误对话框。

### AC-11 演示模式时间压缩
WHEN 以演示模式启动（`--demo` 或 GUI 菜单入口），THE SYSTEM SHALL 在 5 分钟真实时间内把窗口百分比从 0% 线性推进至 100%，依次触发 50/60/80/90% 档位 Toast（每档恰好一条，时序与百分比对应），主窗与托盘状态同步变化；且全程只写演示数据目录，真实数据目录的 token、配置、采样历史与告警记账不受影响；WHEN 退出演示并恢复真实模式启动，THE SYSTEM SHALL 按真实数据目录的原有状态继续工作。

### AC-12 开机自启开关
WHEN 用户经托盘菜单开启开机自启，THE SYSTEM SHALL 注册自启项且菜单状态同步勾选，重新登录 Windows 后应用以托盘形态自动运行（不弹主窗、不抢焦点）；WHEN 关闭该开关，THE SYSTEM SHALL 移除自启项，下次登录不再自动启动。

## Out of Scope

- MCP server：用户明确放弃；按《CLI 工具开发标准》第 0 章例外条款，偏离理由与替代入口（GUI 面向人 + CLI 恒 JSON 面向机器）记录于设计文档。
- 无头常驻监控命令（CLI `start`）：GUI 托盘是唯一常驻监控形态。
- 旧版（glmquotawatch 目录）数据迁移：token 重录一次即可；如需采样历史，用户手工复制 samples-*.jsonl。
- TIME_LIMIT（MCP 月度额度）告警、突发消耗检测、z.ai 国际版端点适配（留二期）。
- 自动更新、多语言、多账号。
