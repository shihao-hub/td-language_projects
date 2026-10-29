# clictl 试点：Chrome 应用模式启动渠道（--chrome）

## 一、背景（Context）

- go_projects 下 13 个 Wails v3 GUI exe，每个独占一棵 WebView2 进程树，闲置即 400~500MB，多开内存爆炸。
- Chrome `--app=` 窗口共享同一浏览器进程，多开边际成本仅一个渲染进程 → 新增「Chrome 应用模式」渠道。
- 已确认决策（用户拍板）：
  1. **试点 clictl**（同构项目验证后另行推广，本次不动其他项目代码）；
  2. **默认 Wails 窗口不变，`--chrome` 显式开启**；
  3. **共享专用 profile**（独立 user-data-dir，非用户日常 Chrome）。
- 知识库条目 071（verified）已证：WebView2 物理保底 120–150MB/实例，参数剪枝只能治标；共享浏览器进程是根治。

## 二、已核实的 clictl 现状

- `go_projects/clictl`，Wails v3.0.0-beta.33；前端 vanilla（`internal/web` go:embed）+ `internal/api` 纯 HTTP，**零 Wails bindings**。
- 关键接线（已读码确认）：
  - `internal/app/gui.go:45` `LaunchGUI(dbPath string, port int, hidden bool)` — 需追加第 4 参；
  - `gui.go:94-98` `OnSecondInstanceLaunch` 目前仅 `ensureMainWindow()`（`SecondInstanceData.Args` 可取第二实例参数）；
  - `gui.go:353-359` 托盘 OnClick/OnDoubleClick/菜单「打开启动台」三处均调 `ensureMainWindow`；
  - `gui.go:360` 菜单「在默认浏览器中打开」→ `api.OpenBrowser`（复用为兜底）；
  - `cmd/clictl/main.go:23-28` 手撸 `os.Args[1:]` 循环解析 `--hidden/--tray`；
  - 窗口本就懒建（`--hidden` 不预建窗口 = 纯 Go ~25MB 形态），chrome 模式只需「永不建 Wails 窗口」；
  - `DisableQuitOnLastWindowClosed: true` 已开启，零窗口 + 托盘可常驻。
- go.mod 已含 `golang.org/x/sys`（registry 子包可用）；`internal/app` 仅 GUI 产物编译（`//go:build !cli`）。

## 三、改动清单

| 文件 | 动作 | 内容 |
|---|---|---|
| `clictl/internal/app/chrome.go` | 新增 | 定位 chrome / 共享 profile / 拉起 `--app` 三函数（草图见 §四） |
| `clictl/internal/app/gui.go` | 修改 | ① `App` 加 `chromeMode bool`；② `LaunchGUI` 追加第 4 参 `chrome bool`；③ 新增 `openMainChannel()` 分发（chrome 模式 → `openChromeAppWindow(a.serverURL)`，否则 `ensureMainWindow()`）；④ 托盘三处 `ensureMainWindow` 调用点全部改调 `openMainChannel`（「在默认浏览器中打开」项不动）；⑤ `OnSecondInstanceLaunch` 按 `data.Args` 含 `--chrome` 与否分发；⑥ 启动段改三分支：`hidden` 静默 / `chrome` 拉 chrome 窗口 / 默认 Wails 窗口 |
| `clictl/cmd/clictl/main.go` | 修改 | ① 解析循环加 `case "--chrome"`；② 调 `app.LaunchGUI("", 0, hidden, chrome)`；③ 包注释补 `--chrome` 说明 |
| `clictl/scripts/build.py` | 不改（可选） | 仅 docstring「唯一语义参数」措辞同步 |
| `clictl/README.md`（子仓） | 修改 | 记录 `--chrome` 契约、`CLICTL_CHROME_PATH`、共享 profile 路径与 §四数据目录约定的共享型例外理由 |
| `docs/projects/go_projects/clictl/clictl 使用指南.md`（父仓） | 修改 | 同上，面向使用者的参数契约 |
| `docs/projects/go_projects/clictl/plans/07-chrome-app-mode.md`（父仓） | 新增 | 本计划落盘（编号顺延，01–06 已存在），**落盘后立即单独 commit** |
| `docs/projects/go_projects/Chrome 应用模式启动渠道.md`（父仓） | 新增 | 跨项目可复制模式说明（语言层方法论文档，落位同「CLI 工具开发标准.md」） |

## 四、核心代码草图（internal/app/chrome.go，单文件自包含）

```go
// LocateChrome 优先级链：显式覆盖(CLICTL_CHROME_PATH，指向不存在即报错不静默换)
// → 注册表 App Paths（HKLM/HKCU SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe）
// → 常见路径（ProgramFiles / ProgramFiles(x86) / LocalAppData 下 Google\Chrome\Application\chrome.exe）。
func LocateChrome(override string) (string, error)

// ChromeProfileDir 共享专用 profile：%LOCALAPPDATA%\language_projects\chrome-apps\<dev|prod>
//（os.UserCacheDir() + appinfo.Channel() 分层，dev/prod 不串；失败回退 ~/.language_projects）。
// 所有项目共用同一目录 = 同一浏览器进程的前提；路径常量将来各项目必须逐字一致。
// 属 AGENTS §四数据目录约定的共享型例外（profile 含大量缓存不漫游），文档记录理由。
func ChromeProfileDir() (string, error)

// openChromeAppWindow 拉起窗口；Locate/建目录/Start 任一失败 → appinfo.Logf 落盘
// + 回退 api.OpenBrowser(url)（默认浏览器，复用既有 rundll32 三分支）。
func openChromeAppWindow(url string) {
    cmd := exec.Command(exe,
        "--app="+url,
        "--user-data-dir="+profile,
        "--no-first-run",
        "--no-default-browser-check",
    )
    // cmd.Start() 成功后 go cmd.Wait() 异步回收（参照 api.revealInExplorer 惯式）
}
```

- 不做激进参数剪枝：此 chrome 是多项目共享的完整浏览器（区别于 WebView2 单实例剪枝），pilot 保持最小参数集。
- `main.go` 的 `fallbackServe` **不改**（其前提是 Wails 壳整个起不来，维持默认浏览器兜底）。
- 开机自启注册参数仍 `["--hidden"]` 纯托盘；chrome 模式自启不在试点范围。

## 五、生命周期语义

- **关 chrome 窗口 ≠ Go 进程退出**：托盘常驻照旧；`a.win` 恒为 nil，`aliveWindow`/WindowClosing/几何记忆逻辑天然不触发，零改动。
- **单实例矩阵**（第二实体均照常 exit 0，由第一实体执行）：
  - `--chrome` 二次唤起 → `data.Args` 命中 → 重开 chrome 窗口（指向第一实体 serverURL）；
  - 无参二次唤起 → 懒建 Wails 窗口（两模式可混用，反之亦然）。
- Go 进程重启换动态端口 → 旧 chrome 窗口成死页需手动关（进程存活期内端口稳定，接受）。

## 六、验证（dev 构建手动验证）

构建：按 `clictl/scripts/build.py` 使用说明产 `clictl-gui-dev.exe`。

1. `.\bin\clictl-gui-dev.exe --chrome`：chrome `--app` 窗口打开、无 Wails 窗口、托盘在；Go 进程 WorkingSet ≈ 纯 Go 水位（~25–30MB）。
2. 关 chrome 窗口 → Go 进程存活；托盘左键/双击/菜单 → 重新拉起 chrome 窗口。
3. **[验证点]** 同 URL 重复 `--app` 拉起：chrome 新开窗口还是聚焦既有窗口（决定是否需去重锁）。
4. **[验证点]** 全新共享 profile 首启是否残留向导/恢复气泡（必要时补 `--hide-crash-restore-bubble` 等）。
5. **[验证点]** 任务栏图标为 chrome 图标；升级路径 = WebUI 加 favicon/manifest 升级 PWA（试点不做）。
6. 第二实例矩阵三项（§五）+ `--chrome --hidden` 静默组合。
7. `CLICTL_CHROME_PATH=C:\nonexistent\x.exe` → 回退默认浏览器 + 日志落盘。
8. dev/prod 隔离：`chrome://version` 查 user-data-dir 落在 `...\chrome-apps\dev`。

内存对比（报告口径）：闲置 / 单开 / 多开三场景，`Get-Process clictl-gui-dev` 测 Go 壳 + 按 `CommandLine -like '*language_projects\chrome-apps*'` 过滤 chrome 进程树汇总；基线 = 现状 Wails 多开（每 exe 一棵 WebView2 树）。

## 七、提交拆分（含 plans 独立提交铁律）

1. 父仓 `docs(plans): 新增 clictl Chrome 应用模式实施计划`（计划落盘立即单独提交）；
2. go_projects 子仓内 `clictl:feat: 新增 --chrome Chrome 应用模式渠道`（代码 + README，均在 clictl 范围内）；
3. 父仓 `docs: 更新 clictl 使用指南补充 --chrome 渠道`；
4. 父仓 `docs: 新增 Chrome 应用模式启动渠道模式说明`；
5. 父仓 `chore: 更新 go_projects 子模块指针`；
6. 收尾调用一次 `aoci_maintain` 对齐索引，元数据变更独立提交。
（所有提交带 Co-Authored-By: Claude Code 尾注。）

## 八、推广要点（本次只沉淀文档，不动其他项目代码）

- 其余约 10 个同构项目（架构 A）移植 = 整文件复制 `chrome.go`（仅依赖 `appinfo.Channel/Logf` + `api.OpenBrowser`，签名一致）+ main.go 加 case + `LaunchGUI` 加参 + `openMainChannel` 分发 + 托盘三处替换 + 二实例分发。
- **共享 profile 路径常量各项目必须逐字相同**（禁止加项目名前缀——加了就裂成 N 个浏览器进程，方案归零）。
- winstartupmanager / glmquotawatch（Vue + Wails bindings，无 HTTP API 层）需先补 API 通道，后续单独决策。
- 按仓库隔离纪律：推广由用户逐项决策，先回填试点验证点结论到模式文档。

## 未决问题与阻塞确认清单

- [ ] 验证点 3/4/5（重复 --app 行为、首启气泡、任务栏图标）需 pilot 实测回填，不阻塞开工
- [ ] 共享 profile 放 `%LOCALAPPDATA%\language_projects\chrome-apps\dev|prod` 属对 §四约定的共享型例外，需用户认可（默认按此执行）

## 实施结果（2026-10-29，已收尾）

- 代码：`chrome.go` 新增，`gui.go`/`main.go`/`README`/`build.py` 接线，`chrome_test.go` 覆盖定位与分发；子仓提交 `f9bccce`
- 验证 1–8 全通过；验证点 3 = 复用既有窗口（无需去重锁）、4 = 首启无气泡、5 = 任务栏为 Chrome 图标
- 内存：chrome 3 窗口 ≈700MB WS / 355MB 私有，Wails 3 实例 ≈1230MB WS / 510MB 私有
- 正式计划与实测明细：`docs/projects/go_projects/clictl/plans/07-chrome-app-mode.md`
- 跨项目模式文档：`docs/projects/go_projects/Chrome 应用模式启动渠道.md`
