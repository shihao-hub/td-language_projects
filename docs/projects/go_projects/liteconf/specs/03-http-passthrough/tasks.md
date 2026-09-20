# Task List — liteconf CLI 入口与 HTTP 调试透传

以下命令均在子项目目录 `go_projects\liteconf` 内执行。项目保持零第三方依赖（`go.mod` 的 require 列表为空），仅用 Go 1.22 标准库；`http` 子命令运行期依赖 PATH 中的 curlie（`go install github.com/rs/curlie@latest`）。

> 执行说明：本 spec 的 REQ-7 把单元测试列为明确交付物，故执行阶段未按默认方式跳过 `[test]` 任务，任务 7/8/10 全部实施并通过。

- [x] 1. 创建版本注入包 internal/version
  - 新建 `go_projects/liteconf/internal/version/version.go`：`package version`；`var Version = "dev"`，附中文注释说明由 `scripts/build.ps1` 经 `-ldflags "-X github.com/shihao-hub/liteconf/internal/version.Version=<v>"` 注入、未注入时回退 dev
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-2, REQ-5

- [x] 2. 实现 internal/cli 分发、帮助与版本渲染
  - 新建 `go_projects/liteconf/internal/cli/cli.go`：`Options{Stdin io.Reader; Stdout, Stderr io.Writer; LookPath func(string) (string, error)}`，零值可用（nil 回退 `os.Stdin`/`os.Stdout`/`os.Stderr`/`exec.LookPath`）；`Run(args []string, opt Options) int` 分发：无参数/`-h`/`--help`/`help` → 帮助返回 0；`--version`/`version` → stdout 输出 `version.Version`（裸版本号一行）返回 0；`http` → `runHTTP(args[1:])`；`schema` → `runSchema`；其余 → stderr 人读错误（含 `执行 liteconf --help 查看用法`）返回 2；全包不调用 os.Exit
  - 新建 `go_projects/liteconf/internal/cli/catalog.go`：`command{Name, Summary, Usage string; Input, Output map[string]any}`（带 json tag）与手工维护 `commands` 切片（http/schema/version/help 四条；http 条目 Input 声明 passthrough 与不解析语义、Output 声明三流直通与退出码约定）；`renderHelp(opt)` 从 `commands` 渲染人读帮助（用法、子命令摘要、http/schema 示例、curlie 依赖与安装命令、退出码约定）写 stdout 返回 0
  - Run and validate: `cd go_projects\liteconf; go build ./...; go vet ./...`
  - Ref: REQ-2, REQ-4

- [x] 3. 实现 http 透传子命令
  - 新建 `go_projects/liteconf/internal/cli/http.go`：常量 `curlieName = "curlie"`；`runHTTP(args []string, opt *Options) int`：`opt.LookPath(curlieName)` 失败 → stderr 输出未找到说明（含原始错误）与 `请先安装：go install github.com/rs/curlie@latest`，返回 1（stdout 静默）；成功 → `exec.Command(exe, args...)` 参数数组直启（不经 shell），`cmd.Stdin/Stdout/Stderr` 直连 Options；`cmd.Run()` 出错时 `errors.As` 取 `*exec.ExitError`：`ExitCode() >= 0` 原样返回，`-1`（信号终止）→ stderr 说明返回 1；非 ExitError（启动失败）→ stderr 说明返回 1；无错返回 0
  - Run and validate: `cd go_projects\liteconf; go build ./...; go vet ./...`
  - Ref: REQ-3

- [x] 4. 实现 schema 契约导出
  - 新建 `go_projects/liteconf/internal/cli/schema.go`：`contract{Name, Interface, Version string; Commands []command}`（json tag：`name`/`interface`/`version`/`commands`，附中文注释说明无 MCP 入口故 interface 为 cli、依据标准 5.5）；`runSchema(opt *Options) int`：装配 `{name:"liteconf", interface:"cli", version: version.Version, commands: commands}` → `json.MarshalIndent(c, "", "  ")` → stdout 末尾换行，返回 0；写出失败 → stderr 说明返回 1；不解析 PATH、不启动外部程序
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-4

- [x] 5. 创建 cmd/liteconf 组装入口
  - 新建 `go_projects/liteconf/cmd/liteconf/main.go`：`package main`，包注释说明定位（调试 CLI，子命令 http 透传 curlie、schema 导出契约）；`main()` 仅装配：由 `os.Stdin/os.Stdout/os.Stderr` 构造 `cli.Options`（LookPath 留默认），`os.Exit(cli.Run(os.Args[1:], opt))`
  - Run and validate: `cd go_projects\liteconf; go build ./...; go vet ./...`
  - Ref: REQ-2

- [x] 6. 改造构建脚本：双产物 + 版本注入
  - 修改 `go_projects/liteconf/scripts/build.ps1`：param 新增 `[string]$Version = "0.1.0"`；`$ldflags = "-s -w -X github.com/shihao-hub/liteconf/internal/version.Version=$Version"`；产物变量 `liteconf-server.exe` 与 `liteconf.exe`，Push-Location 块内用同一条 ldflags 依次 `go build` 两个入口（各自校验 `$LASTEXITCODE`）；循环校验两产物存在，末尾报告两产物路径与体积；头部注释补 CLI 产物与 `-Version` 用法
  - Run and validate: `cd go_projects\liteconf; .\scripts\build.ps1; .\build\liteconf.exe --version`（应输出 0.1.0）
  - Ref: REQ-5

- [x] 7. 单元测试：分发与错误路径 [test]
  - 新建 `go_projects/liteconf/internal/cli/cli_test.go`（`package cli`）：辅助 `testOptions(stdout, stderr)` 注入内存缓冲与必失败的 LookPath；用例——未知子命令 `foo` 与未知 flag `--unknown` → 退出码 2、stdout 为空、stderr 含人读说明；帮助四变体（无参数/`-h`/`--help`/`help`）→ 0、stdout 含 `http` 与 `schema`、stderr 为空；`--version`/`version` → 0、TrimSpace 后等于 `version.Version`；`schema` → 0、stdout 可 `json.Unmarshal` 且 `interface == "cli"`、commands 含 `http`、stderr 为空；注入返回错误的 LookPath 模拟 curlie 缺失 → `http GET localhost:8646/api/app1/dev` 退出码 1、stdout 为空、stderr 含 `go install github.com/rs/curlie@latest`
  - Run and validate: `cd go_projects\liteconf; go test ./...`
  - Ref: REQ-7

- [x] 8. 单元测试：透传编排参数原样传递 [test]
  - 新建 `go_projects/liteconf/internal/cli/http_test.go`：常量 `fakeCurlieEnv = "LITECONF_TEST_FAKE_CURLIE"`；`TestHelperFakeCurlie`——env 不为 1 直接 return；为 1 时找到 os.Args 中 `--` 之后的参数以 `\x1f` 分隔拼一行写 stdout，`io.Copy(os.Stdout, os.Stdin)` 转发 stdin，`os.Exit(7)`；用例 `TestHTTPPassthroughVerbatim`——`t.Setenv` 打开标记，`LookPath` 注入返回 `os.Args[0]`，Stdin 注入 `strings.NewReader("hello-from-stdin")`，执行 `Run([]string{"http", "-test.run=TestHelperFakeCurlie", "--", "GET", "localhost:8646/api/app1/dev", "--print", "--help", "a b"}, opt)`，断言：退出码 7（curlie 码透传）、stdout 含 `\x1f` 拼接的逐字参数串（证明 `--help`/`--`/含空格参数未被消费）、stdout 含 stdin 回显内容
  - Run and validate: `cd go_projects\liteconf; go test ./...`
  - Ref: REQ-7

- [x] 9. 更新子项目 README
  - 修改 `go_projects/liteconf/README.md`：特性列表新增调试 CLI 条目；「快速开始」的构建注释改为两产物，新增「调试 CLI（liteconf.exe）」小节（curlie 安装前提、`http GET/:8646/api/discovery/PUT key=value`/`schema` 示例、退出码约定、`-Version` 注入说明）；「项目结构」树加入 `cmd/liteconf/`、`internal/cli/`（cli.go/http.go/catalog.go/schema.go）、`internal/version/`；「定位与边界」末句改写：已提供独立调试 CLI；无 MCP 的例外理由（纯终端透传、无自身数据面与状态，标准 0.1 节）
  - Run and validate: 人工通读核对与实现一致
  - Ref: REQ-6

- [x] 10. 全量验证与真实透传冒烟 [test]
  - 环境前提：`curlie --version` 可解析（缺失则执行 `go install github.com/rs/curlie@latest`）
  - `cd go_projects\liteconf; go build ./...; go vet ./...; go test ./...; .\scripts\build.ps1`
  - 冒烟（PowerShell 下用 `$LASTEXITCODE` 核对退出码）：`.\build\liteconf.exe --help`（人读帮助）；`--version`（0.1.0）；`schema`（JSON 含 interface=cli）；`liteconf foo`（stderr + 2）；`liteconf-server.exe` 照常启动后 `.\build\liteconf.exe http :8646/api/discovery`（真实透传）与 `.\build\liteconf.exe http --version`（`--version` 归 curlie 而非 liteconf）
  - Run and validate: 按上述命令逐项核对输出与退出码
  - Ref: REQ-1, REQ-2, REQ-3, REQ-7
  - 实施说明：①本机 curlie 缺失，已执行 `go install github.com/rs/curlie@latest` 装好 v1.8.2（REQ-1 满足）；②`go build/vet/test` 全绿，`.\scripts\build.ps1` 产出两二进制且 `--version` 输出 0.1.0；③发现 curlie 1.8.2 省略 HTTP 方法时 server 返回 `Method Not Allowed`——属 curlie 自身行为，直调 curlie 与经 liteconf 透传输出完全一致，透传契约成立；帮助与示例中的方法均显式书写；④本机 8646 已有用户在运行的 liteconf-server 实例（新起实例绑定失败退出属预期），真实透传直接对该实例验证：GET discovery 返回 200 包络、未知路径返回 not_found 包络，与直调 curlie 逐字节一致、退出码一致。
