# Task List — glmquotawatch-gui

> 依据 `specs/01-glmquotawatch-gui/` 已批准的需求与设计。执行默认：从任务 1 连续执行到最后，不写新测试、不跑测试（Verify 为备用信息）；`[test]` 任务默认跳过。
> 所有命令的工作目录：`D:\Users\language_projects\go_projects\glmquotawatch-gui`（T1 创建）。

- [ ] 1. 项目脚手架：Wails v3 + Vue 3 工程落地
  - Files: `go_projects/glmquotawatch-gui/`（整目录：go.mod、main.go、Taskfile.yml、build/、frontend/、.gitignore、icon.ico、rsrc_windows_amd64.syso）
  - 实现细节：
    - 安装 wails3 CLI：`go install github.com/wailsapp/wails/v3/cmd/wails3@v3.0.0-beta.25`（GOPROXY 已配 goproxy.cn）
    - 临时目录执行 `wails3 init -n glmquotawatch-gui -t vue-ts`（模板名以 `wails3 init -l` 实际清单为准，无 vue-ts 则用 vue 补 TS 配置），产物迁入 `go_projects/glmquotawatch-gui/`（子仓内直接建子目录，禁止单独 git init）
    - module 名改为 `glmquotawatch-gui`；主窗参数改为 Title「GLM 用量监控」、480x760
    - 复制父仓 `docs\assets\projects\go_projects\go-default.ico` → 项目根 `icon.ico`，按《GUIDE-GO-EXE-ICON》生成 `rsrc_windows_amd64.syso`（rsrc 工具：go install github.com/akavel/rsrc）
    - frontend 增加 `tailwindcss` + `@tailwindcss/vite` + `echarts` 依赖，接入 Tailwind v4（vite 插件方式）
    - `.gitignore`：`frontend/node_modules/`、`frontend/dist/`、`frontend/bindings/`、`dist/`、`build/bin/`、`*.exe`
  - Verify: `cd go_projects\glmquotawatch-gui; npm install; wails3 build` → 构建成功产出 exe，双击出现空主窗（无业务功能）
  - Ref: AC-1~12 前置（工程地基）

- [x] 2. api 层移植与模拟上游
  - Files: `internal/api/client.go`、`internal/api/client_test.go`（移植）、`internal/api/fetcher.go`、`internal/api/demo.go`
  - 实现细节：client.go 自归档版逐行移植（Usage/Limit/rawEnvelope/FetchUsage/HTTPError/APIError），仅改包注释与环境变量名 `GLMQUOTAWATCH_GUI_API_BASE`；`Fetcher` 接口（client 天然实现）；`DemoFetcher{start time.Time}`：`pct=min(100, elapsed/300s×100)`、单窗口 `Limit{Type:"TOKENS_LIMIT",Unit:3,Number:5,Percentage,NextResetTime:start+300s 毫秒}`、`Level="DEMO"`、data 原文由 `json.Marshal(api.Usage{…})` 产生（禁止手工拼 map）
  - Verify: `cd go_projects\glmquotawatch-gui && go build ./... && go vet ./internal/api/` → 编译与静态检查通过
  - Ref: AC-2、AC-11

- [x] 3. store 与 quota 移植
  - Files: `internal/store/store.go`、`internal/store/store_test.go`（移植，去 Lock 用例）、`internal/quota/threshold.go`、`internal/quota/format.go`、`internal/quota/quota_test.go`（移植）
  - 实现细节：store 移植后三处调整——`DefaultDir()` 指向 `%APPDATA%\language_projects\glmquotawatch-gui`（回退 `~/.language_projects/glmquotawatch-gui`）；删除 `Lock/LockError/pid_alive*.go`；新增 `ResetDir(target) error`（内部二级校验：`filepath.Base(target)=="demo"`、拒绝空串/卷根）。quota 两文件仅改 import 路径，逻辑零改动（`pid_alive_windows.go`、`pid_alive_other.go` 不移植）
  - Verify: `go build ./... && go vet ./internal/store/ ./internal/quota/` → 通过
  - Ref: AC-2、AC-7、AC-9

- [x] 4. service 层移植与注入点改造
  - Files: `internal/service/service.go`、`internal/service/daemon.go`、`internal/service/history.go`、`internal/service/service_test.go`、`internal/service/daemon_test.go`（移植适配，daemon_test 调用点补第 4 参 nil）
  - 实现细节：
    - service.go 移植全部用例与校验；调整：`Open(dir string, opts ...Option)` 显式收目录；`WithFetcherFactory(func() api.Fetcher)`（默认按 config token 现读构造 Client，demo 传固定 DemoFetcher 工厂）；新增 `WithFixedInterval(d)`（非零时 daemon 启动与热加载直用，跳过 clamp）
    - daemon.go：`RunDaemon(ctx, n, log, onSample func(StatusView))`（nil 安全）；`fixedInterval != 0` 时跳过 interval 热加载；移除 Lock 调用
    - history.go 新增：`ReadHistory(windowKey string, since time.Time) ([]HistoryPoint, error)` + `store.ListSampleFiles()`（按月文件名排序）；行解析失败跳过；单文件 8 MiB 读取上限
  - Verify: `go build ./... && go vet ./internal/service/` → 通过
  - Ref: AC-1、AC-2、AC-5、AC-7、AC-8

- [x] 5. CLI 恒 JSON 壳
  - Files: `internal/cli/root.go`、`internal/cli/output.go`、`internal/cli/schema.go`、`internal/cli/cli_test.go`（移植适配）
  - 实现细节：子命令 `token set/show/remove`、`status`、`config show/set`、`schema`、`version`；删 start/mcp 与 `--json` flag；output.go 删除人读分支（envelope 恒输出）；`--help`/`--version` 信封化（SetHelpFunc / SetVersionTemplate）；schema.go 由 `newRootCmd()` 命令树结构化生成 commands 骨架 + 手写 map 补 args/退出码（零 I/O，`interface:"cli"`）；退出码 0/1/2
  - Verify: `go run . schema` → 输出含 `interface:"cli"` 的 JSON 目录；`go run . --help` → 信封 usage；`go run . token set short` → `ok:false` 信封退出码 1
  - Ref: AC-5、AC-6、AC-7

- [ ] 6. main 分流与 guiapp 壳（窗口/托盘/单实例/关窗到托盘）
  - Files: `main.go`、`internal/guiapp/app.go`、`internal/guiapp/icons.go`
  - 实现细节：
    - main.go 分流：args 空或全部 ∈ {`--demo`,`--hidden`} → `guiapp.Run(demo, hidden)`；其余 → `os.Exit(cli.Run(args))`
    - app.go：纯内存构造 Options → `application.New()`（第二实例在此 `os.Exit(0)`）→ 主窗（Hidden 视 flag）→ 托盘/菜单（显示主窗/立即采样/静音/开机自启/进入演示模式/退出，demo 态静音置灰）→ runtime.Start() → app.Run()
    - 关窗到托盘：`RegisterHook(events.Common.WindowClosing)` + `event.Cancel()` + `Hide()`；exiting 原子标志；「显示主窗」`ensureMainWindow()` 兜底重建；单实例 `UniqueID:"shihao.langproj.glmquotawatch-gui"`、`ExitCode:0`、Args 精确匹配 `--demo` 转发 EnterDemo
    - icons.go：`//go:embed icon.ico` 供托盘 SetIcon
  - Verify: `wails3 build` → exe 双击：主窗+托盘出现；关窗隐藏到托盘、托盘可恢复；二次启动激活既有窗口（真机手工）
  - Ref: AC-3、AC-4、AC-10

- [ ] 7. guiapp 行为层：runtime 模式管理 + bindings + 自启 + 通知
  - Files: `internal/guiapp/runtime.go`、`internal/guiapp/bindings.go`、`internal/guiapp/autostart.go`
  - 实现细节：
    - runtime.go：`MonitorRuntime{Start/EnterDemo/ExitDemo/Stop}`；onSample → 托盘 tooltip 三态（正常/`· 已告警 N%`/`（采样失败）`）+ `Emit("status")`；采样失败 `Emit("sample-error")`；EnterDemo：cancel 旧 daemon → demo 目录全等校验 + ResetDir（失败拒绝）→ 写 demo config（虚拟 token 64 字符、thresholds 50,60,80,90、hysteresis 5）→ DemoFetcher + `WithFixedInterval(5s)` → 起 daemon；Notifier 适配器（silent → `Sound:&NotificationSound{Silent:true}`）；notifications Service 注册
    - bindings.go：GetState/SampleNow/SetToken/RemoveToken/SetConfig/ReadHistory/SetSilent/SetAutostart/EnterDemo/ExitDemo；demo 态写保护（`demo_readonly`）；写后 `Emit("config-changed")`
    - autostart.go：HKCU `…\CurrentVersion\Run` 值名 `glmquotawatch-gui`、数据 `"<exe>" --hidden`；dev 防呆（TempDir 前缀或含 `go-build` 拒绝，错误 `dev_executable`）
  - Verify: `wails3 build` → 真机手工：托盘立即采样/静音勾选/自启开关注册表生效；进入演示后 5 分钟内依次 4 条 Toast（依赖任务 8 前端展示，可先用托盘 tooltip 观察）
  - Ref: AC-1、AC-2、AC-11、AC-12

- [ ] 8. 前端：布局 + 仪表盘 + 事件
  - Files: `frontend/src/App.vue`、`frontend/src/pages/Dashboard.vue`、`frontend/src/components/UsageCard.vue`、`frontend/src/composables/useEvents.ts`、`frontend/src/style.css`（Tailwind 暗色主题）
  - 实现细节：顶栏（应用名 + 模式徽标 + tab：仪表盘/历史/设置）；UsageCard（大号百分比、按档分色进度条 <50 绿/50-79 黄/80+ 红、阈值刻度、本地每秒重算倒计时、已通知档位 tags）；「立即采样」loading 态；无 token 引导卡片；demo 横幅（剩余倒计时 + 退出演示）；`Events.On` 订阅 status/sample-error/mode-changed/config-changed；bindings 经 `wails3 generate bindings` 生成后调用
  - Verify: `wails3 dev` → 仪表盘渲染、立即采样联动、演示模式横幅与告警刷新（真机手工，配合任务 7）
  - Ref: AC-1、AC-2、AC-8、AC-10、AC-11

- [ ] 9. 前端：历史曲线 + 设置页
  - Files: `frontend/src/pages/History.vue`、`frontend/src/pages/Settings.vue`
  - 实现细节：History——窗口下拉（取自最新 status）+ 范围 24h/7d → `ReadHistory`；ECharts 折线（y 0-100、阈值 markLine 虚线、tooltip）；空态。Settings——token 脱敏显示/录入/清除；interval/thresholds/hysteresis/silent 表单（service 错误 code+message 原样展示）；数据目录路径展示；demo 态禁用编辑（服务端已拒，前端同步置灰）
  - Verify: `wails3 dev` → 演示模式积累样本后历史曲线可渲染；设置修改即生效（真机手工）
  - Ref: AC-7、AC-8

- [ ] 10. 收尾：README + 版本注入 + 最终构建与验收清单
  - Files: `README.md`（子项目根级）、`Taskfile.yml`（ldflags 版本注入：`-X glmquotawatch-gui/internal/cli.Version=v0.1.0`）
  - 实现细节：README 含构建（wails3 build / 纯 go build 前置条件）、CLI 恒 JSON 用法（含 schema）、数据目录、通知排查、CLI 标准偏离记录（无 MCP、恒 JSON）；`wails3 build` 最终产物验证；输出对照 AC-1~12 的真机手工验收清单（标注 beta 升级必回归 4 项）
  - Verify: `wails3 build` → 成功；`go run . version` → `{"ok":true,"data":{"version":"v0.1.0"}}`（ldflags 注入后）
  - Ref: 全部 AC

- [ ] 11. [test] 可选测试任务（默认跳过）
  - Files: `internal/api/demo_test.go`、`internal/service/history_test.go`、`internal/cli/cli_test.go`（schema 一致性断言）
  - 实现细节：DemoFetcher 时序（固定时钟注入断言 150/180/240/270s 越档值）；ReadHistory（临时目录造 JSONL 含坏行）；cli_test 断言 schema 命令名集合 == 命令树名称集合
  - Verify: `go test ./...` → 全绿
  - Ref: AC-2、AC-6、AC-8
