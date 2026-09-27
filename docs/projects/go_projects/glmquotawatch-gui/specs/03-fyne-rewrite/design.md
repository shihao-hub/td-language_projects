# Design Document — glmquotawatch-gui Fyne 重写

## Overview

在 `glmquotawatch-gui` 仓库内原地替换 GUI 层：保留业务核心五包（api / store / quota /
service / cli）与 main 入口分流语义不变，把 `internal/guiapp`（Wails v3 组装层）重写为
**Fyne v2.8.1 纯 Go 实现**，删除整个 `frontend/`（Vue 3）、Taskfile 与 Wails 专用构建资源；
托盘常驻、阈值 Toast（go-toast2 直调）、单实例（命名事件）、开机自启（HKCU Run 直写）、
演示模式、历史自绘折线图全部落位。运行形态收敛为单进程、无 WebView2。

## Context

- 现状（Wails v3.0.0-beta.25 版已交付）：Go 后端 + WebView2 多进程；前端 Vue 3 + Tailwind +
  ECharts 已迭代 4 轮去 AI 味。功能规格见 `specs/01-glmquotawatch-gui/`；Toast 修复见
  `specs/02-demo-toast-no-alert/`。
- 动机：WebView2 进程树内存占用高（小应用 100–300MB）；本机其余 Go 工具均为 10–60MB 级，
  托盘小工具用 webview 框架不成比例。用户决策：Fyne 原生 Material 风、自绘图表、原地改造。
- 本机环境：Go 1.26.0、MSYS2 MinGW64（gcc）、Windows 11。
- **Fyne v2.8.1 关键 API 已对照 pkg.go.dev 文档核实**：

| 能力 | 已核实 API | 依据 |
|---|---|---|
| 托盘 | `desktop.App` 接口（v2.2+）：`SetSystemTrayMenu(*fyne.Menu)` / `SetSystemTrayIcon(fyne.Resource)` / `SetSystemTrayWindow(fyne.Window)`（v2.7+，Windows 支持左键点托盘显示所设窗口） | pkg.go.dev `fyne.io/fyne/v2/driver/desktop` |
| 线程模型 | `fyne.Do(fn)` / `fyne.DoAndWait(fn)`（v2.6+）：后台 goroutine 更新 UI 必须经此；v2.8 起未迁移应用会在启动时打印警告 | pkg.go.dev `fyne.io/fyne/v2` 函数索引 |
| 关窗拦截 | `Window.SetCloseIntercept(func())`；拦截后 `Hide()` 窗口不销毁，应用不退出（默认「最后一个窗口关闭才退出」不触发） | fyne 文档 App/Window 语义 |
| 窗口控制 | `App.NewWindow(title)`、`Window.Resize/Show/Hide`；`app.NewWithID(uniqueID)` | pkg.go.dev |
| 菜单 | `fyne.NewMenu(label, items...)`、`fyne.NewMenuItem(label, action)`、`MenuItem.Checked/Disabled`、`Menu.Refresh()` | pkg.go.dev |
| 通知（备选） | `App.SendNotification(*fyne.Notification)` 存在，但静音/身份控制粒度不足，**不采用**（见技术选型） | pkg.go.dev |
| Toast 直调 | `go-toast/v2 v2.0.3`：`toast.Notification{AppID,Title,Body,Audio}.Push()`；`toast.Silent`/`toast.Default` 常量；`toast.SetAppData(AppData)` 注册 AUMID；**文档明示 Audio 缺省 = 静默** | pkg.go.dev `git.sr.ht/~jackmordaunt/go-toast/v2` |
| 版本 | Fyne v2.8.1（2026-08-26，最新稳定）；需 Go 1.22+、C 编译器 | GitHub Releases / README |

## Goals and Non-Goals

- Goals:
  - 功能语义逐条平移（AC-1 ~ AC-12 不变），GUI 层替换为 Fyne 单进程实现
  - 单实例（激活已有主窗 + `--demo` 转发）、关窗到托盘、左键托盘唤窗、菜单状态行三态
  - 阈值 Toast 保持原生、silent 语义与身份（AUMID）可控
  - 中文字体正确渲染；历史自绘折线图（阈值虚线、空态）
  - 构建链摆脱 npm/wails3：`go build`（CGO）+ rsrc 图标注入；dev/prod 双脚本与数据/单例隔离不变
- Non-Goals:
  - 像素级复刻 Web 视觉、托盘 tooltip 原样能力、托盘图标状态变体、窗口最小尺寸约束（Out of Scope 见需求文档）
  - 非 Windows 平台验收；MCP / CLI 人读 / daemon 等原版排除项继续排除

## Detailed Design

### 技术选型（已锁定）

| 维度 | 选择 | 理由 |
|---|---|---|
| GUI 框架 | `fyne.io/fyne/v2 v2.8.1` | 用户决策；纯 Go 自绘、单进程、无 WebView2；v2.8.1 含托盘左键唤窗与大量性能修复 |
| 通知 | `git.sr.ht/~jackmordaunt/go-toast/v2 v2.0.3` 直调 | 与 Wails 版同源机制（ms-winsoundevent），silent/身份完全可控；Fyne `SendNotification` 无法直接指定静音与 AUMID，行为不可测 |
| 单实例 | `kernel32.dll` 命名事件（CreateEventW / OpenEventW / SetEvent / WaitForMultipleObjects）+ `golang.org/x/sys/windows` | 零新依赖；同时承载「唤窗」与「--demo 转发」两种信号；CreateEventW 的 `ERROR_ALREADY_EXISTS` 兼作单例判定 |
| 自启 | `golang.org/x/sys/windows/registry` 直写 `HKCU\...\Run` | 替代 Wails Autostart；行为已知（值名 + `"exe" --hidden`），dev 防呆保留 |
| 中文渲染 | 嵌入 OFL 许可字体子集（Noto Sans SC / 思源黑体，Regular + Bold）+ 自定义 `fyne.Theme` override `Font()` | Fyne 默认字体无 CJK，不嵌必然方块字；子集体积可控（预计合计 ≤ 5MB） |
| 图标注入 | `github.com/akavel/rsrc@v0.10.2`（go run 固定版本）生成临时 syso + `go build` | 免装 fyne CLI；沿用原「临时 syso 构建后清理」形状；exe 图标继续用 `build/windows/icon*.ico` |
| 构建前提 | CGO + MinGW gcc（MSYS2 已装） | Fyne Windows 编译硬前提；脚本前置检查并给出明确报错 |

### 复用边界（不动）

`internal/api`、`internal/store`、`internal/quota`、`internal/service`、`internal/cli`、
`internal/env` 全部保持源码级不变（env 仅继续提供 SingleInstanceID / WindowTitle /
DataSubDir / AutostartAllowed）；`main.go` 仅调整 RunOptions 字段（去掉 Assets）。

### 模块设计（internal/guiapp 全部重写）

#### 1. `main.go` — 入口分流（微调）
- `UPDATED` `main.go`
  - **Purpose** 进程唯一入口，分流 GUI / CLI（规则不变）
  - **Changes** 删除 `//go:embed all:frontend/dist`；`RunOptions` 变为 `{Demo, Hidden bool; TrayIcon []byte}`；`icon_*.go` 改 embed 托盘 PNG（见图标卡片）
  - **Complexity** Low

#### 2. `internal/guiapp/app.go` — 组装与窗口
- `REWRITTEN` `internal/guiapp/app.go`
  - **Purpose** Fyne 应用组装、主窗、关窗拦截、退出编排
  - **Changes**
    - `Run(opts RunOptions)` 顺序（不变量 1：第二实例在任何 store 写入前退出）：
      1. `singleInstance(opts)`：第二实例发事件后 `os.Exit(0)`；主实例获得 show/demo 事件句柄并启动等待 goroutine（见 singleinstance.go）
      2. `a := app.NewWithID(env.SingleInstanceID())`；`a.Settings().SetTheme(newBrandTheme())`（中文字体）
      3. 构建三页组件（dashboard / history / settings）与 `App` 结构
      4. `win := a.NewWindow(env.WindowTitle())`；`win.Resize(fyne.NewSize(920, 560))`；`win.SetCloseIntercept(func(){ win.Hide() })`
      5. `buildTray(a, ...)`（见 tray.go）；`desk, ok := a.(desktop.App)`——不 ok 时 panic（托盘是核心功能，Windows driver 必然支持）
      6. `runtime := newMonitorRuntime(ui, notifier)`；`runtime.Start(opts.Demo)`
      7. `if !opts.Hidden { win.Show() }`；`a.Run()`
    - `ensureMainWindow()`：`win.Show()` + `win.RequestFocus()`（主实例被第二实例唤醒 / 托盘菜单 / 左键托盘共用）
    - `quit()`：`runtime.Stop()` → `a.Quit()`（Fyne Quit 不触发 CloseIntercept 语义问题）
    - 界面无「关窗退出」路径：SetCloseIntercept 永远 Hide（真退出仅托盘菜单）
  - **Complexity** High

#### 3. `internal/guiapp/tray.go` — 托盘与菜单
- `REWRITTEN` `internal/guiapp/tray.go`
  - **Purpose** 托盘图标/菜单构建、uiBridge 实现
  - **Changes**
    - `desk.SetSystemTrayIcon(fyne.NewStaticResource("tray.png", opts.TrayIcon))`、`desk.SetSystemTrayWindow(win)`（左键唤窗）、`desk.SetSystemTrayMenu(menu)`
    - 菜单项（自上而下）：**状态行**（`fyne.NewMenuItem("GLM 用量监控", nil)`，永久 `Disabled=true`，文本动态三态）、显示主窗、立即采样、静音通知（Checked）、开机自启（Checked；dev 恒 Disabled）、演示模式（文案互斥：进入/退出）、分隔线、退出
    - 状态行文本生成与 runtime 原 `tooltipText()` 三态逻辑一致：正常 `最高 62%（5h 窗口）· 已告警 90%`；失败 `采样失败，下轮自动重试`（notify_failed / state_save_failed 专用文案）；演示 `演示模式 · 45%`
    - uiBridge 实现方法（供 runtime 回调）：`SetStatusText / SetSilentChecked / SetAutostartChecked / SetDemoMode / NotifyError`；全部内部包 `fyne.Do`（runtime 可能来自 daemon goroutine）
    - 菜单项状态变更后调用 `menu.Refresh()`（v2.8.1 起 label 同步修复）
    - `NotifyError`：`dialog.ShowError(err, win)`（Fyne 原生对话框）
  - **Complexity** Medium

#### 4. `internal/guiapp/runtime.go` — 模式运行时（平移）
- `UPDATED` `internal/guiapp/runtime.go`
  - **Purpose** normal/demo 双态、daemon 生命周期、状态分发（原逻辑保留，仅换载体）
  - **Changes**
    - 删除全部 Wails import；`app *application.App` 字段替换为 `ui uiBridge`；`Event.Emit(...)` 替换为对应 ui 方法调用（`OnStatus/OnSampleError/OnNotifyError/OnModeChanged/OnConfigChanged`——由 App 分发到托盘与页面）
    - `toastNotifier` 移入 notify.go；`tooltipText()` 保留为 `statusText()` 供托盘状态行
    - `Start/Stop/EnterDemo/ExitDemo/SampleNow/ToggleSilent/ToggleAutostart/AutostartEnabled/CurrentService/Snapshot` 签名与语义保持（`Snapshot` 的 GUIState 结构保留作控制器数据聚合）
  - **Complexity** Medium

#### 5. `internal/guiapp/controller.go` — 前端绑定 → 直调控制器
- `RENAMED` `internal/guiapp/bindings.go` → `controller.go`
  - **Purpose** 原 BindingsService 方法平移为 UI 直接调用的控制器（无 Wails 生成层）
  - **Changes** 方法集不变：`GetState/SampleNow/SetToken/RemoveToken/SetConfig/SetSilent/ReadHistory/HistoryWindows/EnterDemo/ExitDemo/SetAutostart`；`requireNormal()` demo 只读校验保留；参数校验规则（historyHours 白名单、windowKey 正则）原样保留；`emitConfig` 改为 `ui.OnConfigChanged()`
  - **注意**：所有方法都可能做磁盘/网络 I/O，**调用方（UI 事件处理）必须放 goroutine**，完成后经 `fyne.Do` 回写 UI（见线程模型）
  - **Complexity** Medium

#### 6. `internal/guiapp/singleinstance.go` — 单实例（新建）
- `CREATED` `internal/guiapp/singleinstance.go`
  - **Purpose** 重复启动检测 + 唤窗/演示信号
  - **Changes**
    - 事件名：`Local\` + `env.SingleInstanceID()` + `-show` / `-demo`（dev/prod 天然隔离）
    - `kernel32` 经 `windows.NewLazySystemDLL("kernel32.dll")` 取 `CreateEventW/OpenEventW/SetEvent/WaitForMultipleObjects`；错误码用调用返回的 `lastErr`
    - 第二实例判定：`CreateEventW(NULL, FALSE, FALSE, showName)` 后 `lastErr == windows.ERROR_ALREADY_EXISTS` → 说明主实例存在：按 args 带 `--demo` 则 `SetEvent(demo)` 否则 `SetEvent(show)`，`CloseHandle` 后 `os.Exit(0)`（此时未触碰任何 store/网络，满足不变量 1）
    - 主实例：持有事件句柄，起 goroutine `WaitForMultipleObjects({show,demo}, FALSE, INFINITE)` 循环（auto-reset 自动复位）：show → `fyne.Do(ensureMainWindow)`；demo → `fyne.Do(func(){ rt.EnterDemo(); ensureMainWindow() })`
    - 与 CLI 路径无关（仅 GUI 分支调用）
  - **Complexity** Medium

#### 7. `internal/guiapp/notify.go` — Toast 通知（新建）
- `CREATED` `internal/guiapp/notify.go`
  - **Purpose** `service.Notifier` 的 go-toast 实现 + 启动身份注册
  - **Changes**
    - `toastNotifier{appID string}`：`Notify(title, msg, silent)` →
      `n := toast.Notification{AppID: appID, Title: title, Body: msg}`；
      `silent==true → n.Audio = toast.Silent`；`silent==false → n.Audio = toast.Default`（**必须显式**：go-toast 文档明示 Audio 缺省=静默，漏设会把所有告警变静音）
      → `n.Push()`；错误原样返回（runtime 原有 notify-error 链路）
    - 启动时 best-effort：`toast.SetAppData(wintoast.AppData{AppID: appID, Name: "GLM 用量监控", Icon: <exe路径>})`（字段按库定义），失败仅记 stderr 不影响运行
    - AppID：`env.SingleInstanceID()`（dev 后缀天然区分）
  - **Complexity** Low

#### 8. `internal/guiapp/autostart.go` — 开机自启（重写）
- `REWRITTEN` `internal/guiapp/autostart.go`
  - **Purpose** 替换 Wails `app.Autostart`，直写注册表
  - **Changes**
    - 键：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，值名 `glmquotawatch-gui`（与原 Wails Identifier 同名，覆盖写幂等）
    - 写值：`"<os.Executable()>" --hidden`；开启 = `registry.SetStringValue`；关闭 = `registry.DeleteValue`（不存在不报错）；查询 = `registry.GetStringValue` 存在性
    - 保留原防呆：`env.AutostartAllowed()` false（dev）→ 稳定错误 `dev_mode`；`devExecutableGuard()`（Temp 前缀 / 含 `go-build`）→ `dev_executable`（文案与判定照旧，提示改为「用 go build / 构建脚本产物验证」）
  - **Complexity** Low

#### 9. `internal/guiapp/theme.go` + 字体资源 — 中文渲染（新建）
- `CREATED` `internal/guiapp/theme.go`、`internal/guiapp/assets/fonts/{NotoSansSC-Regular.Subset.ttf,NotoSansSC-Bold.Subset.ttf}`、`scripts/make-font-subset.py`
  - **Purpose** 覆盖默认字体为含 CJK 的子集字体
  - **Changes**
    - `brandTheme struct{ fyne.Theme }`：包装 `theme.DefaultTheme()`，仅 override `Font(style)`——`style.Bold` 返回 Bold 子集，否则 Regular 子集
    - 字体获取：OFL 许可源（Noto Sans SC / 思源黑体）下载后经 `scripts/make-font-subset.py`（PEP 723 + fonttools）子集化：ASCII 0x20–0x7E + CJK 常用标点 + GB2312 全部汉字 + `·`；产物（预计合计 ≤ 5MB）入库，脚本留存供复现
    - 风险标注：GB2312 外的生僻字仍会缺字（如上游返回生僻中文错误）；固定文案已全覆盖，属可接受降级
  - **Complexity** Medium

#### 10. `internal/guiapp/icons.go` — 资源嵌入（重写）
- `REWRITTEN` `internal/guiapp/icons.go`（合并现有 icon_dev.go / icon_prod.go 逻辑）
  - **Purpose** 托盘 PNG 资源
  - **Changes** `//go:embed assets/tray.png`；从 `build/icon_cyan_coral.png`（22 号计划选定的用量图标）生成 64×64 `assets/tray.png` 入库；`main.go` 读取字节传入 RunOptions（保持现有「包内不自持二进制资源」风格）
  - **Complexity** Low

#### 11. `internal/guiapp/ui_dashboard.go` + `usagebar.go` — 仪表盘（新建）
- `CREATED` `internal/guiapp/ui_dashboard.go`、`internal/guiapp/usagebar.go`
  - **Purpose** FR-3 全项
  - **Changes**
    - 结构：`dashboard struct{ card 区（Level + 上次采样时间 + 立即采样按钮）、窗口卡片列表（VBox 动态重建）、错误横幅、无 token 引导卡片（跳设置页回调）}`
    - `usagebar`：自定义 widget（`widget.BaseWidget` + renderer）——背景 `canvas.Rectangle`、填充矩形（宽度=百分比，颜色 <50 绿 / 50–79 黄 / ≥80 红，用固定 RGB 常量）、阈值刻度（`canvas.Rectangle` 细线）、右侧百分比文本（`canvas.Text`）
    - 窗口卡片：标签 + `usagebar` + `重置倒计时`（Label）+ `已通知: 50 60`（Label）
    - 刷新入口 `Refresh(view service.StatusView)`：显示时重建窗口卡片（条目少，直接 RemoveAll+重建，避免增量 diff 复杂度）
    - 「立即采样」：点击 → 禁用按钮 + 文案「采样中…」→ goroutine `controller.SampleNow()` → `fyne.Do` 恢复按钮 + 展示结果/错误
    - 倒计时：由 App 级每秒 ticker 调 `RefreshCountdown()`（窗口不可见时跳过）
  - **Complexity** High

#### 12. `internal/guiapp/ui_history.go` + `chart.go` — 历史（新建）
- `CREATED` `internal/guiapp/ui_history.go`、`internal/guiapp/chart.go`
  - **Purpose** FR-4 全项
  - **Changes**
    - 控制行：窗口 `widget.Select`（选项来自 `controller.HistoryWindows()` + 当前 status 窗口）+ 范围 `widget.Select`（24h / 7d）+ 刷新按钮；空态 Label「暂无历史数据」
    - `historyChart`（自绘）：`widget.BaseWidget`；renderer 内 `container.NewWithoutLayout` 承载 canvas 对象；`SetData(points, thresholds)` 触发重建：
      - **下采样**：目标点数 `min(len(points), max(60, int(width/2)))`，按桶取均值（纯函数 `downsample(points, target)`，可单测）
      - 折线：相邻点 `canvas.NewLine`（主色，StrokeWidth 1.5）
      - 阈值虚线：每条阈值画等长小线段循环（dash）
      - 坐标标签：Y 轴 0/50/100%（左缘 `canvas.Text`）、X 轴起止时间（底缘）
      - `Resize` 时重采样重建（防抖：仅尺寸变化超阈值时）
    - 读取流程：选择变化 → goroutine `controller.ReadHistory(key, hours)` → `fyne.Do` 注入 chart
  - **Complexity** High

#### 13. `internal/guiapp/ui_settings.go` — 设置（新建）
- `CREATED` `internal/guiapp/ui_settings.go`
  - **Purpose** FR-5 全项
  - **Changes**
    - `widget.Form` 字段：token（`Entry{Password:true}` + 脱敏现值 Label + 保存/清除按钮）、interval/`thresholds`/`hysteresis`（Entry）、silent（`widget.Check`）、数据目录（只读 Entry 便于复制）
    - 保存：goroutine 调 controller → 错误 code/message 显示在页内错误 Label；成功就地刷新
    - demo 模式：整 `Form.Disable()` + 顶部提示 Label「演示模式下配置只读」（控制器仍会返回 `demo_readonly`，双保险）
  - **Complexity** Medium

#### 14. 页面容器与全局刷新（并入 app.go）
- `App` 持 `tabs *container.AppTabs`（Tab 图标用主题内置 Home/History/Settings）；顶部演示横幅（Label + 退出按钮，仅 demo 显示）
- 分发规则：`OnStatus → dashboard.Refresh + tray.SetStatusText`；`OnSampleError/OnNotifyError → dashboard 错误横幅 + tray.SetStatusText`；`OnModeChanged → dashboard 切换（引导/横幅）+ history 清空 + settings Disable 切换 + tray.SetDemoMode`；`OnConfigChanged → settings 重新载入 + dashboard 刷新`
- App 级 1s ticker：`fyne.Do` 刷新 dashboard 倒计时与 demo 横幅（`win.Visible()` 为假且非 demo 时跳过）

### 线程模型（硬规则）

- 主线程：Fyne 事件回调（按钮、菜单、ticker 内的 `fyne.Do`）
- 后台 goroutine：daemon 采样回调、controller I/O 调用、单实例等待、ticker
- **任何后台 goroutine 触碰 UI（含托盘菜单项属性）一律经 `fyne.Do`**；违反会触发 v2.8 线程警告并可能竞态
- controller 的 I/O 方法禁止在主线程直接调用（网络超时可长）；UI 侧统一 goroutine + `fyne.Do`

### 构建链与脚本

- `scripts/build-dev.py` / `scripts/build-prod.py`（重写，保持 PEP 723 + uv 形状与 dev/prod 隔离决策）：
  1. 前置检查：`shutil.which("gcc")` 缺失即报错（提示装 MSYS2 MinGW64 并加入 PATH）
  2. `go run github.com/akavel/rsrc@v0.10.2 -ico build/windows/icon[-dev].ico -o rsrc_windows_amd64.syso`
  3. `go build`：环境 `CGO_ENABLED=1`；dev：`-tags dev -buildvcs=false -gcflags=all=-l`，prod：`-tags production -trimpath -buildvcs=false`；ldflags 均含 `-H windowsgui`（dev 可用 `--show-console` 关掉）与 `-X glmquotawatch-gui/internal/cli.Version=<ver>`；产物 `bin/glmquotawatch-gui[-dev].exe`
  4. finally 清理根目录 `*.syso`（原行为）
- 仓库清理：删除 `frontend/`（整目录）、`Taskfile.yml`、`build/Taskfile.yml`、`build/config.yml`、`build/darwin/`、`build/linux/`、`build/docker/`、`build/windows/` 下 Wails 专用文件（`wails.exe.manifest`、`info.json` 等，实施时按实际清单核对）；保留 `build/windows/icon.ico`、`icon-dev.ico`、`build/icon_*.png`、`render_icon.py`
- `.gitignore`：删除 frontend 相关项（node_modules/dist/bindings），保留 `bin/`、`*.exe`、`.task/` 等；新增 `*.syso`
- `go.mod`：+`fyne.io/fyne/v2 v2.8.1`（direct）、`git.sr.ht/~jackmordaunt/go-toast/v2 v2.0.3`（direct）、`golang.org/x/sys`（direct）；`go mod tidy` 移除 Wails 及其独有传递依赖（coder/websocket、godbus、xdg 等）
- `README.md`：重写构建/运行说明（gcc 前提、双脚本、CLI 用法不变）

### 错误处理（逐操作）

| 操作 | 失败条件 | 处理 | 层 |
|---|---|---|---|
| 定时采样 | 网络/上游错误 | daemon 记日志继续；UI 横幅 + 托盘状态行 | service→runtime |
| 通知发送 | go-toast Push 失败 | 记日志；经 OnNotifyError 更新状态行（保持原语义） | runtime |
| SetAppData 注册 | 注册表异常 | best-effort，仅 stderr 提示；Toast 仍尝试发送 | notify |
| 单实例事件创建 | CreateEventW 失败（非 ALREADY_EXISTS） | 视同单实例锁不可用：记 stderr 后继续启动（不阻塞主功能） | singleinstance |
| 第二实例发信号 | OpenEvent/SetEvent 失败 | 静默 `os.Exit(0)`（目标只是不产生第二实例） | singleinstance |
| 自启写注册表 | 权限/异常 | 返回 error；托盘勾选回退 + 错误对话框（原语义） | autostart |
| 演示目录清理 | ResetDir 失败 | 拒绝进入 demo（原语义） | runtime |
| 历史读取 | 坏行/文件缺失 | 跳坏行；缺失=空数据（原语义） | service |
| 控制器 I/O | 任意错误 | goroutine 内捕获 → `fyne.Do` 显示 code/message | controller/UI |
| 字体资源缺失 | 嵌入文件损坏 | 启动 panic（编译期 embed 保证存在，属构建事故） | theme |

### 输入校验（外部输入一览）

- token / interval / thresholds / hysteresis / silent：全部沿用 service 层校验（不变）
- `ReadHistory(windowKey, hours)`：白名单与正则校验沿用 controller（不变）
- `--demo` / `--hidden`：GUI 路径仅认这两个 flag 或空；其余交 CLI（不变）

### 不变量与归属

1. **第二实例在任何 store/网络 I/O 前退出**——singleInstance 判定是 `guiapp.Run` 第一步（先于 `app.NewWithID`、先于 runtime.Start）。
2. **token 永不明文出口**——service 层不变（MaskToken/HasToken）。
3. **数据目录唯一规则**——store 层不变；demo 子目录双防线保留。
4. **阈值状态机语义与归档版逐条一致**——quota 包零改动。
5. **CLI stdout 恒纯 JSON / schema 零 I/O**——cli 包零改动。
6. **UI 线程规则**——所有后台 goroutine 的 UI 触碰经 `fyne.Do`（本设计线程模型节为唯一裁决）。
7. **通知 Audio 显式设置**——silent 与否必须映射 `toast.Silent` / `toast.Default`，禁止依赖缺省（缺省=静默）。
8. **托盘状态行永久 Disabled**——状态行仅展示，防止误触发空 action。

### Module Collaboration and Data Flow

- 依赖方向：`main → guiapp → service → {api, store, quota}`；`cli → service`（不变）；guiapp 内 `app/tray/runtime/controller/singleinstance/notify/autostart/theme + ui_* + chart` 平铺，`App` 为唯一组装与分发中心。
- 组装顺序：main 分流 → `guiapp.Run`：单实例判定 → Fyne App（主题）→ 主窗 → 托盘 → runtime.Start（起 daemon）→ `win.Show()`（按 hidden）→ `Run()` 阻塞。
- 关键数据流：daemon 采样 → runtime 回调 → `fyne.Do` → dashboard 刷新 + 托盘状态行 + 倒计时 ticker；用户操作（按钮/菜单）→ controller（goroutine）→ service → 回调刷新。
- 通知流：daemon 越档 → `service.Notifier` → `toastNotifier.Push`（独立于 UI 线程）。

### Acceptance Criteria Mapping

| AC | 设计落点 |
|---|---|
| AC-1 周期监控 | runtime.Start daemon（原逻辑）+ OnStatus 分发 |
| AC-2 阈值 Toast | quota 零改动 + notify.go（Audio 显式映射）+ Notifier 链路 |
| AC-3 关窗到托盘 | app.go SetCloseIntercept → Hide；托盘「退出」→ quit() |
| AC-4 单实例 | singleinstance.go（CreateEventW 判定 + show/demo 事件 + ensureMainWindow） |
| AC-5 CLI 恒 JSON | cli 包零改动 |
| AC-6 schema 零 I/O | cli 包零改动 |
| AC-7 校验兼容 | service/controller 校验零改动 |
| AC-8 历史曲线 | ui_history.go + chart.go（自绘、下采样、空态） |
| AC-9 数据目录 | store 零改动 + runtime demo 防呆原样 |
| AC-10 token 引导 | dashboard 引导卡片 → 切换到设置页 |
| AC-11 演示模式 | runtime.EnterDemo/ExitDemo 原逻辑 + demo 横幅/倒计时 |
| AC-12 开机自启 | autostart.go（registry 直写 + dev 防呆） |
| AC-13 单进程无 WebView2 | 架构性成立（Fyne 自绘单进程）；真机进程树核验 |
| AC-14 托盘状态行 | tray.go 状态行 + runtime.statusText 三态 |
| AC-15 中文渲染 | theme.go + 子集字体资源 |

### 测试策略

- 业务层既有测试（quota/store/service/daemon/cli）不受影响，可随 `go test ./...` 回归（执行阶段默认不跑）。
- 新增 `[test]` 任务（可选）：`downsample` 纯函数用例；singleinstance 事件名一致性用例。
- 真机手工清单（AC-1~4、8、10~15 走查）：托盘左键/菜单、关窗隐藏、双开激活、--demo 转发、Toast 有无声、自启注册与注销、进程树单进程、中文渲染、历史曲线。
- 构建验证：`go build ./...`（CGO）、两个构建脚本跑通。

## Design Review Notes

自审（对照现有源码与已核实 API 逐项排查）发现与处理：

- **D-1 [HIGH] go-toast Audio 缺省即静默**：若不显式设置，`silent=false` 的告警也会无声——已修复：notify.go 强制映射 `Silent`/`Default`，并写入不变量 7。
- **D-2 [MEDIUM] 单实例时序**：第二实例必须在任何 store 写入前退出（原 Wails 版的核心不变量）——已修复：判定放入 `Run` 第一步，明确先于 app 构建与 runtime 启动（不变量 1）。
- **D-3 [MEDIUM] Fyne 线程规则**：daemon goroutine 直改 UI 会触发 v2.8 警告/竞态——已修复：线程模型节立硬规则，tray/runtime 回调统一 `fyne.Do`，controller I/O 禁主线程直调。
- **D-4 [MEDIUM] 中文字体**：Fyne 默认字体无 CJK，不处理全界面方块字——已修复：theme.go + 子集字体 + AC-15；缺字风险显式标注。
- **D-5 [MEDIUM] 托盘 tooltip 能力缺失**：需求已改述为菜单状态行（FR-6/AC-14），设计以状态行 + 左键唤窗替代。
- **D-6 [MEDIUM] 历史数据量**：7d × 5min ≈ 2016 点直绘线段过重——已修复：下采样至 ≤ 约 600 点（纯函数 + 尺寸驱动重采样）。
- **D-7 [MEDIUM] CGO/gcc 构建前提**：原 Web 构建链无此前提——已修复：脚本前置检查 + README 说明 + NFR-4。
- **D-8 [NIT] SampleNow 网络调用阻塞 UI**：已修复：按钮禁用 + goroutine + fyne.Do 回写。
- **D-9 [NIT] 倒计时 ticker 泄漏**：已修复：App 级单 ticker，窗口不可见且非 demo 时跳过。
- **D-10 [NIT] 自启值名迁移**：与原 Wails Identifier 同名 `glmquotawatch-gui`，覆盖写幂等，无需迁移脚本。
- **D-11 [NIT] go-toast COM/线程**：Push 可能涉及 COM 初始化，交由库内部处理；调用方失败仅记日志（验证项：真机 Toast 清单覆盖）。
- **D-12 [NIT] Fyne 升级回归点**：升级 fyne 版本后必须复核——托盘左键唤窗（SetSystemTrayWindow）、`fyne.Do` 语义、SetCloseIntercept 行为、MenuItem.Checked/Disabled 渲染、ToolTip 若未来提供可回收状态行方案。

**已验证假设**：desktop.App 接口三方法签名；`fyne.Do` 存在与用途；`SetCloseIntercept` 存在；go-toast Notification/SetAppData/Audio 常量；Fyne v2.8.1 为当前最新稳定；Fyne 需 Go 1.22+（本项目 1.26 满足）。

**未验证假设（实现期首查）**：`WaitForMultipleObjects` 在 `x/sys/windows` 的封装可用性（不可用则 NewProc 直调同名函数）；`SetSystemTrayIcon` 对 PNG 32/64px 的清晰度（必要时生成 64px 变体）；go-toast `SetAppData` 所需字段的精确取值。

## Implementation Notes

（实现期修订将追加于此）
