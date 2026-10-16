# 实施计划 - 优化 WebView2 进程生命周期与常驻内存

**问题陈述**：
当前 `glmquotawatch-gui` 在点击关闭（`X`）时仅调用 `a.win.Hide()` 隐藏窗口，并未销毁 WebView2 宿主环境。导致底层 Chromium 启动的 6 个子进程（主浏览器、GPU 渲染、Renderer、Network 服务、Storage 存储服务、Crashpad 守护）持续占用约 290MB 内存。加上 Go 运行时的约 55MB 内存，常驻后台闲置内存高达 **~347MB**。

**需求**：
1. **解除常驻高内存（阶段一）**：
   - 用户点击关闭（`X`）按钮时，关闭并销毁 WebView2 窗口，彻底释放 Chromium 全部子进程（~290MB）；
   - 应用常驻托盘守护，仅保留 Go 协程服务（仅占 ~20-30MB）；
   - 用户从系统托盘重新呼出界面时，毫秒级按需重建 WebView2 窗口并呈现；
   - 用户点击最小化（`-`）保持原生 Windows 行为（任务栏可见，不销毁页面）；
   - 保证后台监控轮询、数据采样（`samples-*.jsonl`）、阈值判定和 Windows Toast 告警持续独立稳定运行，零中断、零影响。
2. **Chromium 进程剪枝（阶段二）**：
   - 通过 Wails v3 `WindowsOptions.AdditionalBrowserArgs` 注入 Chromium 调优参数（如 `--disable-gpu`、`--disable-software-rasterizer`、`--renderer-process-limit=1` 等），裁撤多余 GPU 与 Utility 独立子进程，降低窗口打开时的峰值内存。
3. **数据目录治理收拢**：
   - 配置 `WindowsOptions.WebviewUserDataPath`，将 WebView2 用户数据缓存收纳到 `%APPDATA%\language_projects\glmquotawatch-gui\<dev|prod>\webview2`，符合 AGENTS.md 数据强约束。
4. **阶段三放行/延后**：
   - 暂不改动前端 ECharts 代码，优先通过生命周期治理与底层进程参数实现最大化收益。

**方案设计**：
1. **配置 `WindowsOptions` 基础参数**：
   - 设置 `DisableQuitOnLastWindowClosed: true`，确保所有窗口关闭后，Wails 事件循环与托盘常驻进程不退出；
   - 设置 `WebviewUserDataPath` 指向规范目录；
   - 注入 `AdditionalBrowserArgs` 参数列表裁剪子进程。
2. **窗口生命周期钩子重构**：
   - 拦截 `WindowClosing` 事件时，放行窗口关闭或主动调用 `a.win.Destroy()` / 释放资源；
   - 窗口关闭后清理引用 `a.win = nil`，显式调用 Go `runtime.GC()` 与 `debug.FreeOSMemory()` 促使 Go 运行时向操作系统归还内存；
   - 在 `ensureMainWindow()` 中检测 `a.win == nil`，自动调用 `a.buildWindow(false)` 重建窗口并居中聚焦。
3. **分层验证与实测**：
   - 编译运行后通过 PowerShell `Get-Process` 采样实测：
     - 常驻托盘闲置态：总内存是否降至 20~30MB 左右；
     - 窗口展示运行态：对比裁剪前后的内存消耗；
     - 验证双击托盘、单例重复拉起、以及后台数据采样的连续性。

**任务分解**：

- [ ] Task 1: 升级 Wails v3 应用选项配置
  - 文件：`go_projects/glmquotawatch-gui/internal/guiapp/app.go`
  - 实现：
    - 在 `application.Options.Windows` 中启用 `DisableQuitOnLastWindowClosed = true`；
    - 配置 `WebviewUserDataPath = filepath.Join(env.DataDir(), "webview2")`（确保符合目录规范）；
    - 注入 `AdditionalBrowserArgs`（`--disable-gpu`、`--disable-software-rasterizer`、`--disable-features=NetworkServiceOutOfProcess`、`--renderer-process-limit=1`）。
  - 验证：`go build ./...` 编译通过。

- [ ] Task 2: 改造窗口关窗销毁与按需重建逻辑
  - 文件：`go_projects/glmquotawatch-gui/internal/guiapp/app.go`
  - 实现：
    - 修改 `WindowClosing` 钩子：当非 `exiting` 状态点击 `X` 时，允许窗口真实关闭销毁，解除对 WebView2 窗口的持久持有；
    - 在窗口关闭回调（或钩子处理完后）将 `a.win` 置为 `nil`，并触发一次 `runtime.GC()` 与 `debug.FreeOSMemory()`；
    - 完善 `ensureMainWindow()`，若 `a.win == nil` 则平滑重新调用 `a.buildWindow(false)` 重建并显示；
    - 保证真退出（托盘右键“退出”）时先停监控，再置 `exiting = true`，调用 `app.Quit()`。
  - 验证：测试托盘双击与菜单“显示主窗”多次关开无泄漏、无 panic。

- [ ] Task 3: 最小化与关闭语义分离验证
  - 文件：`go_projects/glmquotawatch-gui/internal/guiapp/app.go`
  - 实现：
    - 确保最小化按钮（`-`）保持系统原生行为，保留在任务栏，不销毁 WebView2；
    - 确保关闭按钮（`X`）触发关窗释放 WebView2，隐藏任务栏图标，常驻托盘；
    - 验证 `--hidden` 静默自启路径，启动时不预创建 WebView2 实例，完全按需冷启动。
  - 验证：本地交互与任务栏表现符合预期。

- [ ] Task 4: 端到端构建与内存对照实测
  - 文件：`go_projects/glmquotawatch-gui/`
  - 实现：
    - 统一通过 `build.py` 编译生产与开发版二进制；
    - 使用 PowerShell 监控脚本采集内存数据（对比优化前的 347.6MB）；
    - 验证关窗常驻状态内存是否降至 30MB 以下；
    - 验证后台定时采样、JSONL 记录追加与 Toast 告警弹窗正常工作。
  - 交付：实测内存数据对比表格与功能验收说明。

### 未决问题与阻塞确认清单
- [ ] 1. 确认上述实施计划是否获批，是否同意按照 Task 1 -> Task 4 顺序开始执行？
- [ ] 2. 在关窗释放 WebView2 后，重新从托盘打开窗口大约需要 200~300ms 重新加载本地 UI，该体验是否完全符合预期？
