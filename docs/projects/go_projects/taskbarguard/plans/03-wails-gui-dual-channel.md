# 03 - TaskbarGuard 双通道桌面化改造（Wails v3 GUI + CLI）

> 依据：`sh-go-wails-desktop` SOP + 本目录《v3 架构调研》。目标是把纯 CLI 的 `taskbarguard`
> 改造成「service 内核 + 两个产物」：`taskbarguard-gui`（只开窗口/托盘）与
> `taskbarguard-cli`（只跑终端），两者共用同一 HTTP Handler 与同一 service。

## 目标产物

| 通道 | 产物 | 子系统 |
| :--- | :--- | :--- |
| dev | `taskbarguard-gui-dev.exe` + `taskbarguard-cli-dev.exe` | WINDOWS_GUI / CONSOLE |
| release | `taskbarguard-gui.exe` + `taskbarguard-cli.exe` | WINDOWS_GUI / CONSOLE |

## 分层

```text
cmd/taskbarguard/main.go   //go:build !cli   只开窗口；--hidden/--tray 静默托盘
cmd/taskbarguard/cli.go    //go:build cli    现有命令 + serve（同 Handler）
internal/core/             service：发现/补丁/回退/配置/计划任务，Runner 可注入
internal/api/              Handler()：/api/* + 内嵌 WebUI；GUI 与 cli serve 共用
internal/web/              go:embed 原生 HTML/CSS/JS
internal/app/              Wails 壳、窗口几何、数据目录、日志、自启、图标
```

## 关键决策

1. **路径语义**：`config.json` 迁到 `%APPDATA%\language_projects\taskbarguard\<dev|prod>\`；
   `scripts/` 按 exe 同级目录解析；`--config` / `--scripts-dir` 仍可显式覆盖。
   首次启动从 exe 同级旧 `config.json` 复制，旧文件保留。
2. **GUI 范围**：应用卡片 + 款式选择 + 启用开关 + apply/revert + kill/restart-explorer +
   计划任务状态；不做 PE 图标覆盖探测。
3. **前端**：原生 HTML/CSS/JS，无 node 构建链，`go:embed` 内嵌。
4. **计划任务**：`install-task` 注册同目录 `taskbarguard-cli.exe apply`，不再指向 GUI 产物。
5. **并发**：service 内部互斥，避免 GUI 与 CLI 同时驱动 uv 改写图标。
6. **图标**：release 专属盾牌+任务栏图标由 `scripts/render_icon.py` 生成；dev 用 Go 地鼠。

## 任务

- [ ] 1. 依赖与骨架：`go get wails v3`、`cmd/`、`internal/{core,api,web,app}`
- [ ] 2. core service 迁移：discover/run/revert/apply/config/task，Runner 注入
- [ ] 3. 迁移并扩展现有测试到 `internal/core`（全部使用 mock Runner）
- [ ] 4. HTTP 层：meta/apps/config/apply/revert/task + WebUI 静态托管
- [ ] 5. WebUI：应用卡片、款式切换、应用/恢复、日志区、计划任务
- [ ] 6. GUI 壳：托盘、单实例、窗口几何记忆、失败降级 serve
- [ ] 7. CLI 壳：现有命令全保留 + `serve`
- [ ] 8. 资产与构建：图标、winres、manifest、info.json、build.py 双通道
- [ ] 9. 文档：README 更新（双产物、APPDATA、serve）
- [ ] 10. 静态校验：`gofmt` + `go build`（不运行测试、不执行产物、不跑 uv）

## 未决问题

无（用户已确认全部按建议执行）。

## 安全边界

- 改造过程**不运行** `go test` / 产物 exe / `uv run` 业务脚本。
- 仅 `go build` 与 `gofmt` 做静态校验；图标渲染只写项目内资产，不触碰系统图标。
