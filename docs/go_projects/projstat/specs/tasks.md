# Task List — projstat

> 约定：所有命令在 `go_projects/projstat/` 目录下执行（PowerShell）。

- [x] 1. 初始化工程骨架
  - 创建 `go.mod`：`module projstat`、`go 1.26.6`、require `github.com/BurntSushi/toml v1.5.0` 与 `golang.org/x/text v0.41.0`（与 mcp-cleanup 同版本）
  - 创建 `.gitignore`：`projstat.exe`、`*.exe`
  - 创建占位 `main.go`（`package main` + 空 `main()`）
  - 执行 `go mod tidy` 拉取依赖
  - Run and validate: `go build ./...`
  - Ref: REQ-14

- [x] 2. 实现 internal/meta 包
  - 创建 `internal/meta/meta.go`：`Stage` 类型与 `ValidStages`（idea/learning/wip/mvp/usable/paused/dropped）、`Meta` 结构（11 字段 + toml tag，布尔用 `*bool` 表三态）
  - `Validate()`：stage 为空或属枚举；next_due 为空或 `time.Parse("2006-01-02")` 成功；错误信息列出合法取值
  - `Load(dir)`：读 `<dir>/PROJECT.toml`；文件不存在 → `(nil, nil)`；解码失败 → `fmt.Errorf("parse %s: %w", path, err)`
  - `escTOML(s)`：转义 `\` `"` 与 `\n` `\r` `\t` 控制字符，其余原样
  - `Save(dir, m)`：手写发射器，固定字段顺序（name→lang→stage→三布尔仅输出非 nil→summary→next_action→next_due→notes→updated_at），文件头两行注释（"set 重写丢弃手写注释" + stage 枚举提示）；写前设 `UpdatedAt = time.Now().Format(time.RFC3339)`
  - `Skeleton(name, lang)`：仅填 name/lang，其余零值
  - Run and validate: `go build ./... ; go vet ./...`
  - Ref: REQ-3, REQ-15

- [x] 3. 实现 internal/scan 包
  - 创建 `scan.go`：`GitInfo{LastCommitAt time.Time; Tag string}`、`Entry{Dir, Name, Lang, Meta, Git}`
  - `FindRoot(start)`：逐级向上，目录同含 `.git`（目录或文件均可，兼容 worktree）与 `go_projects` 即命中；到盘符未命中 → error 信息含 `--root` 用法
  - `Discover(root)`：遍历 go_projects/python_projects/rust_projects/typescript_projects 的直接子目录（仅目录、按名排序），`meta.Load` 填充 Meta；不触碰 `.archived/`
  - `CollectGit(root, es)`：信号量 8 并发，每 Entry 仅两条只读命令——`git -C <dir> log -1 --format=%cI` → LastCommitAt（time.Parse RFC3339）；`git -C <dir> log -1 --format=%H` 得 commit 后 `git -C <dir> describe --tags --abbrev=0 <hash>` → Tag；任一失败（git 不在 PATH/非仓库/无 tag）→ 该 Entry GitInfo 保持零值，不报错不中断
  - 创建 `console_windows.go`（`//go:build windows`，`SetupConsole()` 经 syscall 调 kernel32 `SetConsoleOutputCP(65001)`）与 `console_other.go`（空实现）
  - Run and validate: `go build ./... ; go vet ./...`
  - Ref: REQ-1, REQ-2, REQ-9, REQ-10, REQ-13

- [x] 4. 实现 internal/report 包
  - 创建 `render.go`：
    - `UseColor` 全局变量（`os.Stdout.Stat()` 含 `os.ModeCharDevice` 且非 --json 时为 true）
    - `Width(s)`：逐 rune `x/text/width.LookupRune`，EastAsianWide/Fullwidth → 2，否则 1；`Pad(s, w)` 按显示宽补空格
    - `RelTime(t)`：`"<1h" "3h" "2d" "3w" "1y"`，零值 → `"-"`；`Red(s)` ANSI 红色包裹（仅 UseColor 生效）
    - `Table(es)`：表头 `NAME|LANG|STAGE|SRC|USE|TST|COMMIT|NEXT_DUE`，三态列 ✓/✗/-，next_due 逾期红
    - `NextTable(es)`：`NAME|LANG|STAGE|DUE|ACTION`，action 按 40 显示宽截断加省略号
    - `Show(e)`：key-value 详情 + git 小节（最后提交时间、最近 tag）
    - `Envelope(data, count, elapsed)`：`{"status":"ok","data":…,"count":n,"elapsed_ms":x}` 单行 JSON
  - 创建 `json.go`：`EntryJSON`（含 `tag`、`overdue`、三态 `*bool`）与 `EntryToJSON(e)`
  - Run and validate: `go build ./... ; go vet ./...`
  - Ref: REQ-5, REQ-6, REQ-8, REQ-11, REQ-13

- [x] 5. 实现 main.go 子命令分发
  - `main()`：先 `scan.SetupConsole()`，再 `os.Exit(run(os.Args[1:]))`；计时起点在 run 开头
  - 全局 flag：`--root`（FindRoot 失败时显式指定根）、`--json`
  - `init`：Discover → 对 Meta==nil 者写 `Skeleton`；输出 `created N, skipped M`
  - `list`：`--lang`/`--stage` 过滤 → `--sort name|commit|due`（name 默认不分大小写；commit=LastCommitAt 降序零值垫底；due=NextDue 升序空值垫底）→ Table 或 JSON 数组
  - `show <name>`：名称解析——按 Entry.Name 全局匹配，恰 1 个执行；0 个 → 退出码 1 列近似名；>1 个 → 退出码 1 列候选并提示 `<lang>/<name>`；支持二段式 `python/zedhub`
  - `set <name>` + `--stage --source-read --usable --tested --summary --next --due --notes --lang`：`flag.Visit` 只应用显式设置的 flag（bool flag 天然支持 `--usable` 与 `--usable=false`）；Load 无则 Skeleton；Validate 失败 → 退出码 2 且不写文件；Save 后输出单行确认
  - `next`：过滤 NextAction != "" → 逾期置顶 → due 升序空值最后 → NextTable 或 JSON；无待办输出提示退出码 0
  - 错误路径：--json 时 stdout 输出 `{"status":"error","message":…}` 且退出码 1；退出码约定 0/1/2
  - Run and validate: `go build ./... ; go vet ./...`
  - Ref: REQ-4, REQ-5, REQ-6, REQ-7, REQ-8, REQ-12

- [x] 6. 真实环境验证与自举
  - `go run . init` 为全部项目生成 PROJECT.toml
  - `go run . set projstat --stage usable --summary "项目状态标注 CLI"`
  - 验证文件数（应为 24）：`(Get-ChildItem ..\..\go_projects,..\..\python_projects,..\..\rust_projects,..\..\typescript_projects -Directory | Where-Object { Test-Path "$($_.FullName)\PROJECT.toml" }).Count`
  - `go run . list`、`go run . show zedhub`、`go run . list --json` 人工过目：中文对齐、逾期红、信封合法
  - Ref: REQ-1, REQ-4, REQ-11, REQ-13

- [x] 7. README 与构建产物
  - 创建 `README.md`：项目定位、命令表与示例、PROJECT.toml 字段表、stage 枚举中文释义、明示"set 重写会丢弃手写注释"、PowerShell 乱码时 `chcp 65001` 提示
  - `go build -o projstat.exe .` 产出单 exe
  - 从 `..\..\python_projects\zedhub` 目录运行 `..\..\go_projects\projstat\projstat.exe list`，验证根自动发现
  - Run and validate: `go build -o projstat.exe . ; go vet ./...`
  - Ref: REQ-2, REQ-15

- [x] 8. meta 包单元测试 [test]
  - 创建 `internal/meta/meta_test.go`：Validate 的枚举/日期/三态边界；Save→Load 往返一致；escTOML 转义（引号、反斜杠、换行）
  - Run and validate: `go test ./internal/meta/`
  - Ref: REQ-3, REQ-15
