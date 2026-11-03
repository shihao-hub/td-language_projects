# winstartupmanager 关窗生命周期对齐 go_projects 家族范式 实施计划

## Context（背景）

用户在进程树工具（taskmon）中观察到：`clictl-gui.exe` 下挂着 `winstartupmanager`（Wails v3 beta.25），其 `msedgewebview2` 子进程在窗口被 X 掉后仍驻留（~129MB）。要求改造为与 go_projects 其他 GUI 项目的退出行为对齐。

**已与用户确认**：目标行为 = 家族范式——× 放行销毁窗口（WebView2 全退）、主进程留托盘常驻、唤起毫秒级懒重建、托盘「退出」才整体退出进程；`--hidden` 自启不建 WebView 窗。

## 根因（已确认）

- `internal/guiapp/app.go:149-151`：WindowClosing 钩子非退出路径执行 `event.Cancel()` + `a.win.Hide()`，窗口只隐藏不销毁，WebView2 七子进程全驻留——正是 KB 071 手记点名的"典型误区代码"。
- `ensureMainWindow`（app.go:161-177）只 `Show()` 不重建，win==nil 时直接 return——配合 Cancel 使 webview 一旦创建就活到进程退出。
- `--hidden` 启动仍预建隐藏 WebView2 窗（app.go:82-85 注释以"避免 runtime 建窗死锁"为由）。
- 退出路径（quit() app.go:179-191）与单实例/几何持久化/GPU 参数剪枝均已合规，无需动。
- `clictl` 代码无任何 winstartupmanager 引用——进程树父子关系只是运行期经其启动台拉起，**clictl 无需改**。

**家族契合证据**：12 个现役 Wails v3 GUI 项目全部为"放行销毁 + 懒重建"范式；同框架版本 beta.25 的 `docsearch-gui/main.go:124-202` 已长期验证同款全部机制（销毁、GetByID 复核、懒重建、`--hidden` 不预建）。原注释 82-85 的"死锁"真实条件是**在事件回调里同步建窗卡住消息泵**，规避法是唤起一律 `go` 异步，与预建无关。

## 改动点清单（仅两个文件 + README）

全部照抄家族范式；参照实现：
- `go_projects/docsearch-gui/main.go`（beta.25 同版本，首选抄法来源）
- `go_projects/deepseeksearch/internal/app/gui.go`（v3.0.0 稳定版同构）
- `go_projects/termhub/internal/app/gui.go`（GetByID 复核 + 铁律注释）

### A1 `app.go:119-137`（createWindowLocked）钩子闭包局部捕获
建窗结果先落局部 `win`、再赋 `a.win`；WindowShow / DidMove / DidResize / Maximise 钩子闭包全部捕获局部 `win` 变量（现闭包隐式解引用 `a.win` 字段，懒重建后旧钩子会错指新窗）。

### A2 `app.go:141-158`（WindowClosing 钩子）放行销毁
- 删除 `event.Cancel()` 与 `a.win.Hide()`；
- 保留：`stopWindowStateTimer` → `saveWindowState(win)`（销毁前同步落盘，现已有）→ `exiting` 分流；
- 放行销毁后：`winMu` 下 `if a.win == win { a.win = nil }` 清悬垂指针；
- 保留延时 GC：`go func(){ sleep 300ms; runtime.GC(); debug.FreeOSMemory() }()`。

### A3 `app.go:26-37`（App 结构体）串行化唤起
新增 `ensureMu sync.Mutex`，序列化唤起/重建，防托盘连点双重建。

### A4 `app.go:161-177`（ensureMainWindow）懒重建
```go
func (a *App) ensureMainWindow() { go a.showMainWindow() }

func (a *App) showMainWindow() {
    a.ensureMu.Lock(); defer a.ensureMu.Unlock()
    if a.exiting.Load() { return }
    if win := a.aliveWindow(); win != nil { // GetByID 复核存活
        if win.IsMinimised() { win.UnMinimise() }
        win.Show(); win.Focus()
        if a.currentWindowState().Maximised && !win.IsMaximised() { win.Maximise() }
        return
    }
    a.winMu.Lock(); a.buildWindowLocked(false); win := a.win; a.winMu.Unlock()
    if win == nil { logx.Errorf("主窗口重建失败"); return }
    win.Show(); win.Focus()
    if a.currentWindowState().Maximised && !win.IsMaximised() { win.Maximise() }
}
```
- 删掉现 `if a.win == nil { return }` 早退；
- 新增 `aliveWindow()`（winMu 内 `a.app.Window.GetByID(win.ID())` 复核 + 顺手清悬垂，四家同款）；
- `buildWindowLocked` = winMu 内调 `createWindowLocked(false)`；重建后 WindowShow 兜底钩子随窗注册自动生效，免新增。

### A5 `app.go:82-85`（预建条件化 + 注释重写）
`if !opts.Hidden { a.buildWindow(false) }`——`--hidden` 启动不再初始化 WebView2，纯 Go 托盘常驻；注释重写为家族口径（唤起一律 goroutine 懒建规避消息泵卡死；非 hidden 首窗保留 Run 前预建）。

### A6 `tray.go:51` 托盘退出异步化
`a.quit()` → `go a.quit()`（避免占用 UI 消息泵；家族同款）。quit() 主体已合规，不加 termhub 式 watchdog（本项目无 server/子进程收尾，deepseeksearch/docsearch-gui 均未加而稳定）。

### A7 README.md:26-33 语义修正
以新语义重写"极简低内存常驻架构"段：报窗销毁 WebView2 子进程、毫秒级懒重建、`--hidden` 纯 Go 常驻，保持中文克制篇幅（30-33 行几何/自启/通道不动）。

**不动**：`window_state.go` 全量、`autostart.go`、`main.go`、`build.py`、bindings、前端。

## 验证（手动矩阵，dev 产物 `build/winstartupmanager-dev.exe`）

1. 默认启动开窗，几何/最大化按 `window.json` 恢复；
2. × 后任务管理器确认 `msedgewebview2` 7 进程归零，主进程仍在、托盘在线；
3. 托盘唤起重开：毫秒级重建、几何与最大化恢复、拔屏拉回主屏；
4. ×→唤起 循环 ≥10 次：`webview2` 数据目录无膨胀、内存回落稳定、日志无错；
5. 托盘双击 + 右键"打开主界面"连打：日志仅一次 `主窗口已创建`；
6. 托盘退出：主进程消失，立即再次双击可正常启动（互斥体已释放）；
7. `--hidden` 启动：全程无任何 `msedgewebview2`，托盘唤起首次建窗正常；
8. 二次启动唤起（开窗态与 --hidden 态各验）；
9. 拖移/缩放/最大化 → 700ms 防抖落盘正确，×关窗同步落盘一次；
10. `go test ./internal/guiapp/` 全绿。

构建：`uv run build.py --dev`（项目内构建脚本，dev/release 双形态既有）。

## 风险与缓解

- **beta.25 支持销毁重建？** 低风险：docsearch-gui（战略合作 beta.25 精确一致）同款长期放行；另 3 处跨版本同构。
- **连点双重建**：`ensureMu` 串行 + aliveWindow 命中即走唤起分支。
- **旧钩子错指**：A1 局部捕获 + A2 `a.win == win` 守卫 + GetByID 兜底。
- **防抖定时器在窗销毁后触发**：家族共同残留，句柄返零值被 min 尺寸守卫拒写，接受（可选以后置 GetByID 守卫一行）。
- **重建失败**：3 秒复核 + Errorf 日志（家族默认仅日志；若实测失败再补 MessageBox）。
- **退出挂死互斥体不释放**：极低；实测矩阵第 6 项若复现，再补 termhub 式 6 行 watchdog。

## 收尾工序

- 子模块内单条 commit（`D:\Users\language_projects\go_projects` 子仓）：`winstartupmanager:fix: 关窗对齐家族范式，放行销毁窗口释放 WebView2`，body 列根因/家族依据/验证；README 修订随同 commit。
- AOCI：代码达标后调用一次 `aoci_maintain`（按 GLOBAL.md 收尾必维）。
- docs 同步：`docs/projects/go_projects/` 下无 winstartupmanager 目录，确认无需新建。

### 未决问题（已全部解决）
- [x] 关闭行为目标形态 → 用户拍板：家族范式（× 销毁窗口 + 托盘常驻 + 懒重建）
- [x] clictl 是否需改 → 否（无代码耦合，本身已合规）
- [x] README 失实描述 → 随改造一并修正（A7）

## 实施结果（2026-11-03 归档）

- A1-A7 全部落地：app.go（钩子闭包局部捕获 / 放行销毁清悬垂 / ensureMu 串行唤起三件套 / --hidden 预建条件化）、tray.go 退出异步化、README 常驻架构段修正。
- 脚本化运行时矩阵 15 项全 PASS：--hidden 零 WebView2 子进程；WM_CLOSE 后 7 个子进程归零且主进程与托盘驻留；懒重建按 window.json 快照恢复最大化与几何；托盘口令路径连点日志创建计数不变；移动/最大化 700ms 防抖落盘与关窗同步落盘逐项吻合。
- go test ./... 全绿；`uv run build.py --dev` 产物 `build/winstartupmanager-dev.exe`（v0.1.0-dev-dirty，commit 7d5ee40 构建态）。
- 踩坑记录：验证初段发现 11-01 遗留的旧代码 dev 实例以 Cancel+Hide 形态驻留两天、挂 6 个 WebView2 子进程（即 bug 活标本），且持有 dev 单例互斥使新构建被截停；终杀该实例并轮转 dev 日志后重测。重测数据（window.json/log）已备份还原、探针脚本用后即删。
- 待用户日常实测：矩阵第 4 项（×→唤起 ≥10 循环观察 webview2 目录无膨胀）与第 6 项（托盘「退出」后互斥体释放、可立即再启）。
- 子模块 commit：`6771bd0 winstartupmanager:fix: 关窗对齐家族范式，放行销毁窗口释放 WebView2`（README 随同）。
