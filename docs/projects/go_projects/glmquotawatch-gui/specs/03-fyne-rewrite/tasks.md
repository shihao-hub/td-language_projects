# Task List — glmquotawatch-gui Fyne 重写

执行前置：子仓 `go_projects/glmquotawatch-gui` 已切至 `feat/fyne-rewrite` 分支；本机 gcc
（MSYS2 MinGW64）可用。**任务 2–8 属 `internal/guiapp` 整包置换**，组内中间态该包不可编译，
按序推进至任务 9 恢复整仓可构建；其余任务各自完成后保持可构建。

- [ ] 1. 依赖准备：引入 Fyne 与直调依赖
  - Files: `go_projects/glmquotawatch-gui/go.mod`
  - 实现细节：`go get fyne.io/fyne/v2@v2.8.1 git.sr.ht/~jackmordaunt/go-toast/v2@v2.0.3 golang.org/x/sys@latest`；本轮 **不** `go mod tidy`（Wails 仍被旧 guiapp 引用，留待任务 11 清理）；确认 `CGO_ENABLED=1` 下 `go build ./...` 仍通过（旧版行为不变）
  - Verify: `go build ./...` 通过，且 `go list -m fyne.io/fyne/v2` 输出 v2.8.1
  - Ref: 设计「技术选型」

- [ ] 2. 字体、主题与图标资源
  - Files: `scripts/make-font-subset.py`（新增）、`internal/guiapp/assets/fonts/NotoSansSC-Regular.Subset.ttf`、`internal/guiapp/assets/fonts/NotoSansSC-Bold.Subset.ttf`、`internal/guiapp/assets/tray.png`、`internal/guiapp/theme.go`（新增）、`internal/guiapp/icons.go`（新增）
  - 实现细节：① `make-font-subset.py`（PEP 723 + fonttools + brotli）：从 OFL 许可源（Noto Sans SC / 思源黑体，本机已有字体或从官方源下载）子集化——ASCII 0x20–0x7E、CJK 常用标点、GB2312 全部汉字、`·`；生成 Regular/Bold 两枚 TTF 入库（合计 ≤ 5MB）；② 从 `build/icon_cyan_coral.png` 生成 64×64 `assets/tray.png`；③ `theme.go`：`brandTheme` 包装默认主题，仅 override `Font()`（Bold → Bold 子集，其余 → Regular 子集），`//go:embed` 两枚字体；④ `icons.go`：`//go:embed assets/tray.png` 导出 `TrayIcon []byte`
  - Verify: `go build ./...` 通过；`python -c` 检查字体子集字符数（≈6800+）与文件体积 ≤ 5MB
  - Ref: AC-15、NFR-6、设计 9/10

- [ ] 3. 通知与单实例（新增文件）
  - Files: `internal/guiapp/notify.go`（新增）、`internal/guiapp/singleinstance.go`（新增）
  - 实现细节：① `toastNotifier{appID}` 实现 `service.Notifier`——**Audio 显式映射**（`silent → toast.Silent`，否则 `toast.Default`），`Push()` 错误原样返回；`registerToastAppData()` best-effort 调 `toast.SetAppData`；② 单实例：事件名 `Local\` + `env.SingleInstanceID()` + `-show`/`-demo`；kernel32 经 `windows.NewLazySystemDLL` 调 `CreateEventW/OpenEventW/SetEvent/WaitForMultipleObjects`（x/sys 若有现成封装则优先用）；`CreateEventW` 后 `lastErr == windows.ERROR_ALREADY_EXISTS` 判第二实例（按 args 发 demo/show 信号后 `os.Exit(0)`）；主实例起等待 goroutine（auto-reset 事件，show → 唤窗回调，demo → 进入演示+唤窗回调，回调经 `fyne.Do`）
  - Verify: `go vet ./internal/guiapp` 通过（本包整体可编译前仅做语法检查）；`go build ./internal/guiapp` 若因旧文件冲突失败属预期
  - Ref: AC-4、AC-13、设计 6/7

- [ ] 4. 开机自启改为注册表直写
  - Files: `internal/guiapp/autostart.go`（重写）
  - 实现细节：`golang.org/x/sys/windows/registry` 直写 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，值名 `glmquotawatch-gui`，值 `"<exe>" --hidden`；查询/删除对应实现；保留 `env.AutostartAllowed()` 与 `devExecutableGuard()`（`dev_mode` / `dev_executable` 稳定错误；提示文案改为「用构建脚本产物验证」）；函数签名改为 `setAutostart(enabled bool) error` / `autostartEnabled() bool`（去掉 Wails app 参数，旧调用点由任务 5/9 适配）
  - Verify: 编译随任务 9 统一验证；`go vet` 单文件语法检查
  - Ref: AC-12、设计 8

- [ ] 5. runtime 平移与控制器
  - Files: `internal/guiapp/runtime.go`（更新）、`internal/guiapp/controller.go`（由 bindings.go 改名）
  - 实现细节：① runtime 删除全部 Wails import；`uiBridge` 接口改为 `SetStatusText/SetSilentChecked/SetAutostartChecked/SetDemoMode/NotifyError/OnStatus/OnSampleError/OnNotifyError/OnModeChanged/OnConfigChanged`；`Event.Emit` 全部替换为 ui 回调调用；`tooltipText()` 更名 `statusText()` 并保留三态文案；Notifier 构造改走 notify.go；其余（Start/Stop/EnterDemo/ExitDemo/SampleNow/ToggleSilent/ToggleAutostart/AutostartEnabled/CurrentService/Snapshot）逻辑原样；② bindings.go → controller.go：方法集不变，`SetAutostart` 调新签名，`emitConfig` → `ui.OnConfigChanged()`，demo 只读与参数校验保留；GUIState/ErrInfo 结构保留
  - 实现细节补充：runtime 内所有 ui 回调调用点允许来自 daemon goroutine——`fyne.Do` 包装统一在 App 实现侧（任务 9 的 tray/分发层），runtime 不直接 import fyne
  - Verify: 随任务 9 统一编译；`go vet` 语法检查
  - Ref: AC-1~4、AC-10~12、设计 4/5

- [ ] 6. 仪表盘页与自绘进度条
  - Files: `internal/guiapp/ui_dashboard.go`（新增）、`internal/guiapp/usagebar.go`（新增）
  - 实现细节：① `usagebar`：`widget.BaseWidget` + renderer（背景/填充矩形、阈值刻度、百分比文本），颜色 <50 绿 / 50–79 黄 / ≥80 红 固定 RGB；② dashboard：套餐 Level + 上次采样时间 + 立即采样按钮（禁用+「采样中…」+ goroutine + `fyne.Do`）、窗口卡片列表（标签/条形/倒计时/已通知）、错误横幅、无 token 引导卡片（跳到设置页回调）、演示横幅（倒计时 + 退出按钮）；`Refresh(StatusView)` 与 `RefreshCountdown()` 入口
  - Verify: 随任务 9 统一编译
  - Ref: AC-1、AC-3、AC-10、AC-11、设计 11

- [ ] 7. 历史页与自绘折线图
  - Files: `internal/guiapp/ui_history.go`（新增）、`internal/guiapp/chart.go`（新增）
  - 实现细节：窗口 `Select` + 范围 `Select(24h/7d)` + 刷新按钮；`historyChart` 自绘（折线 + 阈值虚线 + 0/50/100 标签 + 起止时间），`downsample(points, target)` 纯函数（桶均值，target = min(len, max(60, width/2))）；`Resize` 超阈值时重采样；空态 Label；读取经 goroutine + `fyne.Do`
  - Verify: 随任务 9 统一编译
  - Ref: AC-8、设计 12

- [ ] 8. 设置页
  - Files: `internal/guiapp/ui_settings.go`（新增）
  - 实现细节：`widget.Form`：token（Password Entry + 脱敏现值 + 保存/清除）、interval/thresholds/hysteresis（Entry）、silent（Check）、数据目录（只读 Entry）；保存经 goroutine，错误 code/message 页内展示；demo 模式 `Form.Disable()` + 只读提示（控制器仍拒）
  - Verify: 随任务 9 统一编译
  - Ref: AC-5、AC-7、AC-10、设计 13

- [ ] 9. app/tray/main 组装切换（本任务后整仓恢复可构建）
  - Files: `internal/guiapp/app.go`（重写）、`internal/guiapp/tray.go`（重写）、`main.go`（更新）、删除 `internal/guiapp/bindings.go`、删除 `icon_dev.go`/`icon_prod.go`（项目根）
  - 实现细节：① app.go：单实例判定第一步 → `app.NewWithID` + `SetTheme` → 页面构建 → 主窗（标题/尺寸/SetCloseIntercept→Hide）→ tray → runtime.Start → `win.Show()`（按 hidden）→ `Run()`；`ensureMainWindow/quit`；`fyne.Do` 分发层（uiBridge 实现集中在此或 tray.go）；App 级 1s ticker（不可见且非 demo 跳过）；② tray.go：`desktop.App` 断言 + 图标/菜单（状态行 Disabled 首项、显示主窗、立即采样、静音、自启、演示、退出）+ `SetSystemTrayWindow(win)` + uiBridge 各方法（含 `menu.Refresh()`）；`NotifyError` 用 `dialog.ShowError`；③ main.go：删 embed assets；`RunOptions{ Demo, Hidden bool; TrayIcon []byte }` 传 `guiapp.TrayIcon`；分流规则不变
  - Verify: `go build ./...` 与 `go vet ./...` 全部通过（CGO_ENABLED=1）
  - Ref: AC-1~4、AC-13、AC-14、设计 2/3/14

- [ ] 10. 构建脚本重写
  - Files: `scripts/build-dev.py`（重写）、`scripts/build-prod.py`（重写）
  - 实现细节：删除 npm/wails3 步骤；① gcc 前置检查（`shutil.which("gcc")` 缺失报错提示 MSYS2）；② `go run github.com/akavel/rsrc@v0.10.2 -ico build/windows/icon[-dev].ico -o rsrc_windows_amd64.syso`；③ `go build`（`CGO_ENABLED=1`；dev `-tags dev -gcflags=all=-l`、可选 `--show-console`；prod `-tags production -trimpath`；ldflags `-H windowsgui` + `-X glmquotawatch-gui/internal/cli.Version=<ver>`；产物 `bin/glmquotawatch-gui[-dev].exe`）；④ finally 清理 `*.syso`；保留 PEP 723 头与中文输出风格
  - Verify: `uv run scripts/build-dev.py` 与 `uv run scripts/build-prod.py` 均产出 exe（记录体积）
  - Ref: NFR-4、设计「构建链与脚本」

- [ ] 11. 仓库清理与文档
  - Files: 删除 `frontend/`（整目录）、`Taskfile.yml`、`build/Taskfile.yml`、`build/config.yml`、`build/darwin/`、`build/linux/`、`build/docker/`、`build/windows/` Wails 专用文件（`wails.exe.manifest`、`info.json` 等，按实际清单核对）；更新 `.gitignore`（删 frontend 条目，加 `*.syso`）；更新 `README.md`（Fyne 构建说明/gcc 前提/双脚本/CLI 不变）；`go mod tidy`（移除 Wails 及独有传递依赖）
  - 实现细节：删除前 `git status` 核对无未提交改动混入；tidy 后确认 `go build ./...` 仍通过；README 说明托盘左键唤窗与状态行差异
  - Verify: `go build ./...` 通过；`git status` 仅含预期文件；`go mod graph | grep wails` 为空
  - Ref: 设计「构建链与脚本」、Out of Scope

- [ ] 12. 编译回归与真机验收
  - Files: 无（验证任务）
  - 实现细节：`go build ./...` + `go vet ./...`；`bin\glmquotawatch-gui-dev.exe status` 与 `schema` 检查恒 JSON 与零 I/O；随后按 AC 清单真机走查：AC-1 周期刷新、AC-2 Toast（含 silent）、AC-3 关窗到托盘、AC-4 双开激活与 `--demo` 转发、AC-8 历史曲线（含空态）、AC-10 无 token 引导、AC-11 演示全链路、AC-12 自启注册/注销、AC-13 任务管理器进程树单进程无 `msedgewebview2.exe`、AC-14 托盘状态行三态、AC-15 中文无方块字
  - Verify: 上述每项均有明确结果记录（含失败偏差与修复）
  - Ref: AC-1~15

- [ ] 13. [test] 可选单测：下采样与事件名一致性
  - Files: `internal/guiapp/chart_test.go`、`internal/guiapp/singleinstance_test.go`
  - 实现细节：`downsample` 边界（空/单点/目标大于源/极值桶）；单实例事件名与 `env.SingleInstanceID()` 拼装一致性断言
  - Verify: `go test ./internal/guiapp/ -run 'Downsample|EventName'` 通过
  - Ref: 设计「测试策略」
