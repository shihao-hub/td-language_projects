# clictl Chrome 应用模式启动渠道（`--chrome`）

- 背景：go_projects 下 13 个 Wails v3 GUI exe 各自独占一棵 WebView2 进程树，闲置即 400~500MB，多开内存爆炸。Chrome `--app=` 窗口共享同一浏览器进程，多开边际成本仅一个渲染进程。
- 目标：clictl 新增「Chrome 应用模式」渠道，`--chrome` 显式开启；默认行为（Wails 窗口）完全不变。
- 非目标：不改其他项目代码（试点验证通过后再按模式文档推广）；不做 PWA 化/图标升级；不做 chrome 模式开机自启；不做激进 chromium 参数剪枝。
- 试点依据：知识库条目 071（verified）——WebView2 物理保底 120–150MB/实例，参数剪枝只能治标，共享浏览器进程是根治。

## 决策（已确认）

| 议题 | 决策 |
|---|---|
| 试点范围 | 仅 `go_projects/clictl`，其余同构项目另行决策 |
| 默认渠道 | Wails 窗口保持默认，`--chrome` 显式切换 |
| 浏览器 profile | 共享专用 user-data-dir，非用户日常 Chrome profile |
| profile 路径 | `%LOCALAPPDATA%\language_projects\chrome-apps\<dev\|prod>`（所有项目逐字共用，禁止加项目名前缀） |
| chrome 定位 | 显式覆盖 → 注册表 App Paths → 常见安装路径 |
| 失败兜底 | 任一环节失败 → 日志落盘 + `api.OpenBrowser(url)` 打开默认浏览器 |
| 窗口生命周期 | 关 chrome 窗口不退 Go 进程；托盘常驻；`a.win` 恒为 nil |
| 单实例 | 二次唤起按 `data.Args` 是否含 `--chrome` 分发；两模式可混用 |

## 一、现状核实

- `internal/app/gui.go:45` `LaunchGUI(dbPath string, port int, hidden bool)`；
- `gui.go:94-98` `OnSecondInstanceLaunch` 仅 `ensureMainWindow()`，`SecondInstanceData.Args` 可取第二实例参数；
- `gui.go:353-359` 托盘 OnClick / OnDoubleClick / 菜单「打开启动台」三处均调 `ensureMainWindow`；
- `gui.go:360` 菜单「在默认浏览器中打开」→ `api.OpenBrowser`（复用为兜底）；
- `cmd/clictl/main.go:23-28` 手撸 `os.Args[1:]` 循环解析 `--hidden/--tray`；
- 窗口本就懒建（`--hidden` 不预建窗口 = 纯 Go ~25MB 形态），chrome 模式只需「永不建 Wails 窗口」；
- `DisableQuitOnLastWindowClosed: true` 已开启，零窗口 + 托盘可常驻；
- go.mod 已含 `golang.org/x/sys`（registry 子包可用）；`internal/app` 仅 GUI 产物编译（`//go:build !cli`）。

## 二、改动清单

| 文件 | 动作 | 内容 |
|---|---|---|
| `clictl/internal/app/chrome.go` | 新增 | 定位 chrome / 共享 profile / 拉起 `--app` 三函数 |
| `clictl/internal/app/gui.go` | 修改 | `App` 加 `chromeMode`；`LaunchGUI` 追加第 4 参；新增 `openMainChannel()`；托盘三处替换；二实例按参数分发；启动三分支 |
| `clictl/cmd/clictl/main.go` | 修改 | 解析 `--chrome`；传第 4 参；包注释补说明 |
| `clictl/README.md` | 修改 | `--chrome` 契约、`CLICTL_CHROME_PATH`、共享 profile 路径与例外理由 |
| `clictl 使用指南.md`（父仓） | 修改 | 面向使用者的参数契约与验证要点 |
| `Chrome 应用模式启动渠道.md`（父仓） | 新增 | 跨项目可复制模式说明（语言层方法论文档） |

## 三、核心实现

```go
// LocateChrome 优先级链：显式覆盖（指向不存在即报错，不静默换）
// → 注册表 App Paths（HKLM/HKCU SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe）
// → 常见路径（ProgramFiles / ProgramFiles(x86) / LocalAppData 下 Google\Chrome\Application\chrome.exe）。
func LocateChrome(override string) (string, error)

// ChromeProfileDir 共享专用 profile：%LOCALAPPDATA%\language_projects\chrome-apps\<dev|prod>
//（os.UserCacheDir() + appinfo.Channel() 分层，dev/prod 不串；失败回退 ~/.language_projects）。
// 所有项目共用同一目录 = 同一浏览器进程的前提；路径常量将来各项目必须逐字一致。
func ChromeProfileDir() (string, error)

// openChromeAppWindow 拉起窗口；Locate/建目录/Start 任一失败 → appinfo.Logf 落盘
// + 回退 api.OpenBrowser(url)。
func openChromeAppWindow(url string)
```

- 拉起参数保持最小集：`--app=<url>`、`--user-data-dir=<profile>`、`--no-first-run`、`--no-default-browser-check`；`cmd.Start()` 成功后 `go cmd.Wait()` 异步回收（参照 `api.revealInExplorer` 惯式）。
- 此 chrome 是多项目共享的完整浏览器（区别于 WebView2 单实例剪枝），不做激进参数剪枝。
- `main.go` 的 `fallbackServe` 不改（前提是 Wails 壳整个起不来，维持默认浏览器兜底）。
- 开机自启注册参数仍 `["--hidden"]` 纯托盘；chrome 模式自启不在试点范围。

## 四、生命周期语义

- **关 chrome 窗口 ≠ Go 进程退出**：托盘常驻照旧；`a.win` 恒为 nil，`aliveWindow`/WindowClosing/几何记忆逻辑天然不触发，零改动。
- **单实例矩阵**（第二实体均照常 exit 0，由第一实体执行）：
  - `--chrome` 二次唤起 → `data.Args` 命中 → 重开 chrome 窗口（指向第一实体 serverURL）；
  - 无参二次唤起 → 懒建 Wails 窗口（两模式可混用，反之亦然）。
- Go 进程重启换动态端口 → 旧 chrome 窗口成死页需手动关（进程存活期内端口稳定，接受）。

## 五、验证（dev 构建手动验证）

构建：`uv run scripts/build.py` 产 `bin/clictl-gui-dev.exe`。

1. `.\bin\clictl-gui-dev.exe --chrome`：chrome `--app` 窗口打开、无 Wails 窗口、托盘在；Go 进程 WorkingSet ≈ 纯 Go 水位（~25–30MB）。
2. 关 chrome 窗口 → Go 进程存活；托盘左键/双击/菜单 → 重新拉起 chrome 窗口。
3. **[验证点]** 同 URL 重复 `--app` 拉起：chrome 新开窗口还是聚焦既有窗口（决定是否需去重锁）。
4. **[验证点]** 全新共享 profile 首启是否残留向导/恢复气泡（必要时补 `--hide-crash-restore-bubble` 等）。
5. **[验证点]** 任务栏图标为 chrome 图标；升级路径 = WebUI 加 favicon/manifest 升级 PWA（试点不做）。
6. 第二实例矩阵三项（§四）+ `--chrome --hidden` 静默组合。
7. `CLICTL_CHROME_PATH=C:\nonexistent\x.exe` → 回退默认浏览器 + 日志落盘。
8. dev/prod 隔离：`chrome://version` 查 user-data-dir 落在 `...\chrome-apps\dev`。

内存对比（报告口径）：闲置 / 单开 / 多开三场景，`Get-Process clictl-gui-dev` 测 Go 壳 + 按 `CommandLine -like '*language_projects\chrome-apps*'` 过滤 chrome 进程树汇总；基线 = 现状 Wails 多开（每 exe 一棵 WebView2 树）。

## 六、推广要点

- 其余约 10 个同构项目（架构 A）移植 = 整文件复制 `chrome.go`（仅依赖 `appinfo.Channel/Logf` + `api.OpenBrowser`，签名一致）+ main.go 加 case + `LaunchGUI` 加参 + `openMainChannel` 分发 + 托盘三处替换 + 二实例分发。
- **共享 profile 路径常量各项目必须逐字相同**（禁止加项目名前缀——加了就裂成 N 个浏览器进程，方案归零）。
- winstartupmanager / glmquotawatch（Vue + Wails bindings，无 HTTP API 层）需先补 API 通道，后续单独决策。
- 按仓库隔离纪律：推广由用户逐项决策，先回填试点验证点结论到模式文档。

## 七、实施结果

- [x] `internal/app/chrome.go` 新增（定位 / profile / 拉起 / 回退）
- [x] `internal/app/gui.go` 加 `chromeMode`、`LaunchGUI` 第 4 参、`openMainChannel`、托盘三处与二实例分发
- [x] `cmd/clictl/main.go` 解析 `--chrome` 并透传
- [x] README / 使用指南 / 跨项目模式文档补充契约与共享 profile 例外理由
- [x] 验证点 3/4/5 实测结论回填（见 §八）

## 八、实测结论（dev 构建，2026-10-29）

验证 1–8 全部通过（`bin/clictl-gui-dev.exe`）：

- 启动：只有 Chrome `--app` 窗口（无地址栏/标签栏），Go 壳无 Wails 窗口；关/杀 chrome 窗口后 Go 进程存活，二实例 `--chrome` 重开窗口。
- **验证点 3（重复 `--app`）**：第二实例与手工重复拉起均未新增窗口，Chrome 复用既有窗口 → **无需去重锁**。
- **验证点 4（首启气泡）**：删除全新共享 profile 后首启直接渲染工作台，无向导、无恢复气泡。
- **验证点 5（任务栏图标）**：任务栏为 Chrome 图标（WebUI 无 favicon/manifest）；升级路径仍是 PWA 化。
- 组合语义：无参二实例开 Wails 窗口、`--chrome --hidden` 静默（二实例带 `--hidden` 同样静默，静默优先）。
- 兜底：`CLICTL_CHROME_PATH=C:\nonexistent\x.exe` → 日志记「CLICTL_CHROME_PATH 指向的文件不存在」并回退默认浏览器。
- 隔离：实际 `--user-data-dir` 为 `<LocalAppData>\language_projects\chrome-apps\dev`。

内存实测（WorkingSet 口径，含共享内存，故总量偏高；私有内存更能反映增量）：

| 场景 | 组成 | WS | 私有 |
|---|---|---|---|
| 闲置（`--hidden`） | 仅 Go 壳 | 21.8MB | — |
| Chrome 单开 | Go 25.7 + chrome 树 573.5 | 599.2MB | ≈ 282MB |
| Chrome 3 窗口 | Go 25.7 + chrome 树 670.4 | 700.2MB | ≈ 355MB |
| Wails 单实例（基线） | Go 44.4 + WebView2 树 369.6 | 414.1MB | ≈ 169MB |
| Wails 3 实例（基线） | 3 × 约 414 | ≈ 1230MB | ≈ 510MB |

结论：单开时 chrome 模式略贵；多开时第 N 个窗口增量约 36MB 私有内存，是同构 Wails 实例（约 180MB）的 1/5，3 界面合计省约 43%。

