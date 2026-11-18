# Task List

> 依赖链：1 → 2 → 3 → 4 → 5。每个任务完成后代码库保持可构建。
> 代码任务均在 `go_projects/clictl/` 内执行（以下 Files 相对该项目根）；任务 5 另涉及父仓文档。

- [ ] 1. 执行原语下沉：进程树与有界收集平移至 runner 包，新增捕获执行低层原语
  - Files: `internal/runner/proctree_windows.go`（新，自 `internal/mcp/exec_windows.go` 平移）、`internal/runner/proctree_other.go`（新，自 `internal/mcp/exec_other.go` 平移）、`internal/runner/captured.go`（新）、`internal/mcp/exec.go`（删去被平移部分）
  - 实现细节：包名 mcp→runner；先比对 runner 现有标识符，冲突则统一 `procTree` 前缀改名；`limitedBuffer` 平移语义不变；新增 `CapturedResult` 与 `RunCaptured(ctx, path, args, timeoutMs)`（流程 = 现 `mcp/exec.go:102-147` 原样上移，仅启动失败返 error）；导出 `MaxStreamBytes`、`DefaultRunTimeoutMs`；本任务先不删 `execTool`（留到任务 2 接新用例时一并改薄），保证每步可构建
  - Verify: `go build ./...` 与 `go vet ./...` 零错误（备用信息，执行阶段不跑）
  - Ref: AC-4（机制底座）

- [ ] 2. 捕获运行公共用例：service.RunCaptured 落地，MCP execTool 改薄壳
  - Files: `internal/service/captured.go`（新）、`internal/mcp/exec.go`（改薄）、`internal/mcp/exec_windows.go` 与 `internal/mcp/exec_other.go`（删除，已平移）
  - 实现细节：`CapturedRun{Name, Path string; Result runner.CapturedResult}`；`RunCaptured(name, args, timeoutMs)` 逐行对齐原 execTool 编账语义（PreflightRun → InsertLaunch → runner.RunCaptured → FinishLaunch，启动失败 finish(127)）；mcp 侧 `runOut` 结构体与 `failureSummary` 原样保留，`execTool` 改为调 `svc.RunCaptured` 后的形状映射（wire 契约零变化，缺省超时改引 `runner.DefaultRunTimeoutMs`）
  - Verify: `go build ./...`、`go vet ./...` 零错误；`go test ./...` 全部通过（现有 `mcp_test.go` 回归保护薄壳化，备用信息，执行阶段不跑）
  - Ref: AC-4

- [ ] 3. GUI server 骨架：internal/gui 包 + cli 接线，`clictl gui` 可启动可探测
  - Files: `internal/gui/gui.go`（新）、`internal/gui/web/index.html` 与 `internal/gui/web/static/app.css`、`internal/gui/web/static/app.js`（本任务先放最小占位：index 含 `__CLICTL_TOKEN__` meta 与页面骨架空壳，css/js 空注释文件——go:embed 编译期要求文件存在）、`internal/cli/commands.go`（分发 + cmdGui + EmitHelp 补行）
  - 实现细节：按 design 模块三实现——token 生成与注入、Host 校验中间件、`/api/*` 路由全集（列表合并/详情/add/rm/set/start/stop/run 直接接 service 用例）、包络 writeOK/writeErr、端口策略（默认 17630 → 探测 `/api/version` 复用旧实例 → 失败回退随机端口）、openBrowser（GOOS 分支）、signal 优雅关停（Shutdown 3s + service.Close）；cmdGui 解析 `--port`/`--no-open`；handler 内请求 ctx 直通 RunCaptured
  - Verify: `go build ./...` 零错误；`uv run scripts/build.py` 后 `./clictl.exe gui --no-open` 启动且 stderr 打印地址（备用信息，执行阶段不跑）
  - Ref: AC-1、AC-6、AC-7、AC-8

- [ ] 4. 前端单页完整实现：列表/详情/启停/捕获运行/注册管理
  - Files: `internal/gui/web/index.html`、`internal/gui/web/static/app.css`、`internal/gui/web/static/app.js`（替换任务 3 占位）
  - 实现细节：按 design 模块三前端约定——卡片网格（status/running 徽标、操作行）、搜索过滤、10s 轮询（无弹层且页面可见时）、详情侧滑、运行弹层（args 每行一个、timeout、AbortController 取消、输出分块与截断/超时/取消徽标、交互式程序提示）、注册/编辑弹层（tags 逗号分隔）、rm 自绘确认（含级联删除文案）、api 封装（meta token + X-Clictl-Token、!ok toast code+message+suggestions）、操作后刷新；视觉按浅色亮堂 + 绿主色 + 圆角卡片执行
  - Verify: `uv run scripts/build.py` 后 `./clictl.exe gui` 打开浏览器完成一轮手工冒烟：列表与 `clictl list` 一致 → start/stop 一个工具 → 对任一非交互工具（如 clictl.exe 自己 `--version`）捕获运行看输出 → add/rm/set 各一次（备用信息，执行阶段不跑）
  - Ref: AC-1、AC-2、AC-3、AC-4、AC-5、AC-6

- [ ] 5. 文档收尾：README、父仓使用指南、CHANGELOG
  - Files: `README.md`（子仓根级，原地更新）、父仓 `docs/projects/go_projects/clictl/clictl 使用指南.md`、`CHANGELOG.md`
  - 实现细节：README 命令表补 `clictl gui [--port N] [--no-open]` 行 + 特性一条 + run/start 在 GUI 中的形态说明；使用指南新增「GUI 模式」章节（启动、端口与二次启动行为、四类操作、安全说明、已知限制）并附 CLI/MCP/GUI 三入口迷你能力表；CHANGELOG 按现有格式追加。**提交注意范围隔离**：子仓两文件一笔，父仓文档一笔
  - Verify: 通读确认与实现一致（备用信息）
  - Ref: AC-1～AC-8（交付记录）
