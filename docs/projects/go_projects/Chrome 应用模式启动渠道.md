# Chrome 应用模式启动渠道

> 状态：v1.0（2026-10-29）；试点项目 clictl 已验证并回填实测结论。
>
> 读者：go_projects 下 Wails v3 GUI 应用的开发者与 AI agent。适用于「同一 WebUI 需要常驻多开」的场景，不适用于需要浏览器内核深度集成（自定义 IPC / WebView2 特性）的应用。
>
> 首个实现与实测见 `docs/projects/go_projects/clictl/plans/07-chrome-app-mode.md`。

## 一、要解决的问题

Wails / WebView2 每个 GUI 进程独占一棵 WebView2 进程树：单实例闲置约 400MB 工作集、约 180MB 私有内存，且无法通过 Chromium 参数剪枝压到量级以下（物理保底 120–150MB/实例，见工程知识库条目 071）。十几个同构启动台类 GUI 长期常驻时，多开的总内存随实例数线性上涨。

Chrome `--app=<url>` 窗口共享**同一个浏览器进程**：第 N 个窗口只新增一个渲染进程（实测约 +36MB 私有内存），URL 重复拉起时 Chrome 会复用既有窗口而不是再开一个。因此对「WebUI + 托盘常驻」型应用，用共享 profile 的 Chrome 应用模式替代 WebView2 壳，是根治多开内存的正解。

实测（同一台机器，3 个界面同时打开）：

| 形态 | 进程模型 | 3 界面合计 WS | 每新增界面增量（私有） |
|---|---|---|---|
| Wails / WebView2 × 3 | 每实例 1 exe + 6 个 WebView2 进程 | ≈ 1230MB | ≈ 180MB |
| Chrome 应用模式 × 3 窗口 | 1 棵浏览器树（9 进程）+ N 渲染 | ≈ 700MB | ≈ 36MB |

代价：**单开**时 chrome 模式反而略高于 Wails（完整浏览器 + crashpad 等常驻进程）。这个方案省的是多开，不是单开。

## 二、契约

| 议题 | 约定 |
|---|---|
| 启用方式 | 显式参数 `--chrome`，默认行为（Wails 窗口）不变 |
| 共享 profile | `%LOCALAPPDATA%\language_projects\chrome-apps\<dev\|prod>`，回退 `~/.language_projects/chrome-apps/<通道>` |
| profile 命名 | **不含项目名**：所有项目逐字共用同一目录，否则裂成多个浏览器进程，方案归零 |
| 通道隔离 | dev / prod 分层，调试实例与常驻正式版互不干扰 |
| chrome 定位 | 环境变量显式覆盖 → 注册表 `App Paths`（HKLM → HKCU）→ 常见安装路径 |
| 失败兜底 | 任一环节失败 → 日志落盘 + 系统默认浏览器打开同一 URL（窗口一定打得开） |
| 窗口生命周期 | 关 chrome 窗口不退 Go 进程；托盘常驻；`a.win` 恒为 nil，几何记忆/WindowClosing 逻辑天然不触发 |
| 单实例 | 第二实例 exit 0，由第一实例按其参数分发：`--chrome` 开 chrome 窗口，无参开 Wails 窗口；带 `--hidden/--tray` 静默优先 |
| 参数集 | 最小集 `--app=<url> --user-data-dir=<profile> --no-first-run --no-default-browser-check`，不做 WebView2 式激进剪枝（这是共享的完整浏览器） |

## 三、参考实现（clictl）

单文件自包含，仅依赖项目内的 `appinfo.Channel/Logf` 与 `api.OpenBrowser`：

```go
const (
    chromePathEnv = "CLICTL_CHROME_PATH" // 各项目替换为自己的前缀
    chromeAppsRoot = "chrome-apps"       // 逐字一致，禁止改
)

// LocateChrome：override → 注册表 App Paths → 常见路径；override 不存在必须报错，不能静默换。
func LocateChrome(override string) (string, error)

// ChromeProfileDir：%LOCALAPPDATA%\language_projects\chrome-apps\<dev|prod>
func ChromeProfileDir() (string, error)

// openChromeAppWindow：拉起失败回退 api.OpenBrowser(url)
func openChromeAppWindow(url string)
```

接线（改四处）：

1. `LaunchGUI` 追加 `chrome bool` 参数，`App` 增加 `chromeMode` 字段；
2. 新增 `openMainChannel(chrome bool)`：chrome → `go openChromeAppWindow(a.serverURL)`，否则 `ensureMainWindow()`；托盘 OnClick / OnDoubleClick / 菜单「打开启动台」三处统一改调它；
3. 启动段三分支：`hidden` 静默 → `chrome` 拉起 chrome 窗口 → 默认 Wails 窗口；
4. `OnSecondInstanceLaunch` 用 `wantsChromeWindow(data.Args)` 分发（`--chrome` 且不含 `--hidden/--tray`）。

## 四、移植清单

- [ ] 复制 `chrome.go`，改 `chromePathEnv` 前缀（如 `TYPEAI_CHROME_PATH`），`chromeAppsRoot` 保持逐字相同
- [ ] `LaunchGUI` 加参、`App` 加 `chromeMode`
- [ ] `openMainChannel` 分发 + 托盘三处替换
- [ ] `main.go` 解析 `--chrome` 并透传（包注释同步）
- [ ] 启动段三分支 + 二实例参数分发
- [ ] 日志/README/使用指南补充契约
- [ ] 前置检查：项目是否有可独立访问的 HTTP API 层。仅有 Wails bindings 的项目（如 winstartupmanager、glmquotawatch）需先补 API 通道，再谈 chrome 模式

## 五、验收要点（clictl 实测结论）

1. `--chrome` 启动：只有 chrome `--app` 窗口，无 Wails 窗口；Go 壳 WorkingSet 实测 ≈ 25–30MB ✓
2. 关 / 杀掉 chrome 窗口后 Go 进程存活，托盘唤起重开 ✓
3. 同 URL 重复 `--app`：Chrome 复用/聚焦既有窗口，不新增窗口 → **无需去重锁** ✓
4. 全新共享 profile 首启：无向导、无恢复气泡，直接渲染 ✓
5. 任务栏图标为 Chrome 图标（WebUI 无 favicon/manifest）；升级路径 = 加 favicon + manifest 走 PWA ✓
6. 二实例矩阵：`--chrome` 重开窗口、无参开 Wails 窗口、`--chrome --hidden` 静默 ✓
7. `CLICTL_CHROME_PATH` 指向不存在文件：日志记录失败原因并回退默认浏览器 ✓
8. dev/prod 隔离：`chrome://version` 确认 user-data-dir 落在 `...\chrome-apps\dev` ✓

## 六、已知限制

- Go 进程重启换动态端口后，旧 chrome 窗口变成死页，需手动关闭（进程存活期内端口稳定）。
- 任务栏图标与品牌图标不作为 chrome 模式的一部分，需要 PWA 化（manifest + 图标）另行升级。
- chrome 模式开机自启暂不支持，自启仍为 `--hidden` 纯托盘。
- 推广须逐项目决策，禁止一次性批量改所有同构项目（仓库隔离纪律）。
