# Bug Fix Document: Silent Agy Copy Validation & Hardening

## Summary

Windows 环境下调用 `agyquota --agy` 时，底层静默副本生成失败会静默回退至原始控制台程序 `agy.exe`，导致终端焦点抢占防御失效；同时启动日志未体现实际执行路径与静默副本使用状态；缓存校验缺少对文件真实存在、PE Subsystem == 2 及源文件 SHA-256 绑定的完整校验；daemon 重启场景缺少静默副本持久使用验证。

## Reproduction

1. **静默回退未报错**：人为破坏 `bin/agy_silent.exe` 的生成（例如目标路径写入权限受阻或生成后损坏），执行 `agyquota --agy`，程序未报错中断，而是静默恢复使用 `agy.exe`，再度触发控制台会话与 DefTerm 窗口抢焦点行为。
2. **日志误导**：运行 `agyquota --agy`，终端日志输出 `[agyquota] 正在执行 C:\Users\...\agy.exe -p "/usage" --output-format json ...`，即使底层实际使用了 `agy_silent.exe`，日志依然显示原始路径，无法判断是否生效。
3. **缓存校验薄弱**：若 `agy_silent.exe` 被意外清空、损坏或 Subsystem 未成功改为 2，只要其 `Size` 和 `ModTime` 与源 `agy.exe` 巧合一致（或元数据被篡改），校验依然通过，导致启动异常或失去静默特性。

## Root Cause

1. **静默回退隐患**（`internal/agapi/proc_windows.go`）：
   原代码在 `ensureSilentAgyExe(exePath)` 出错时，将 `runPath` 重设为 `exePath` 并附加 `CREATE_NO_WINDOW` 试图容错。然而对于 Windows 11 DefTerm 而言，`agy.exe` 内部无条件触发控制台会话，`CREATE_NO_WINDOW` 无法完全杜绝跨终端抢焦点。静默副本失败时必须立刻中止并报错。
2. **日志路径写死**（`internal/agapi/client.go`）：
   `FetchUsage` 中的日志输出写死了 `c.AgyPath`（原始可执行文件路径），而静默副本路径由底层 `startAgyProcess` 计算，上层无从感知，导致日志与真实执行路径脱节。
3. **缓存校验维度不足**（`internal/agapi/pe_windows.go`）：
   原缓存校验仅检查 `dstStat.Size() == srcStat.Size() && dstStat.ModTime().Equal(srcStat.ModTime())`。未校验目标文件是否为常规文件、未读取 PE OptionalHeader 验证 `Subsystem == 2`（IMAGE_SUBSYSTEM_WINDOWS_GUI），亦未持久化源文件 SHA-256 哈希作为强一致性凭证。
4. **子进程链防御不足**（`internal/agapi/proc_windows.go`）：
   原 `startAgyProcess` 在执行静默副本时未同时指定 `CREATE_NO_WINDOW`；若 `agy_silent.exe` 衍生出控制台子进程，可能逃逸或重新请求控制台。

## Impact

- 影响所有通过 `--agy` 数据源查询配额的场景（CLI 人读、JSON 输出、daemon 后台常驻服务及 MCP 工具）。
- `--zed` 数据源走纯 HTTP 协议，不受影响。

## Fix Acceptance Criteria

### AC-1（静默失败硬拦截）
WHEN 在 Windows 下生成或校验 `agy_silent.exe` 失败（如源文件损坏、写入权限失败等），
THEN `FetchUsage` 立即返回明确错误，绝对不回退到原始 `agy.exe` 执行。

### AC-2（启动日志真实性）
WHEN 启动 agy 执行配额查询时，
THEN 进度日志必须打印实际运行的 `runPath`，并明确标注是否使用了 `agy_silent.exe`（例如：`正在执行 <runPath> -p "/usage" --output-format json (使用静默副本: true) ...`）。

### AC-3（多维缓存校验）
WHEN 检查 `agy_silent.exe` 缓存时，
THEN 必须同时满足以下条件才判定缓存命中，否则重新生成：
1. `agy_silent.exe` 确实存在且为非空常规文件；
2. 文件大小与源文件一致；
3. 解析 PE 头部，确认 `OptionalHeader.Subsystem == 2`（GUI 子系统）；
4. 读取绑定源文件的 SHA-256 哈希文件（`agy_silent.exe.sha256`），确认与当前源文件一致（文件不存在或不匹配时重新生成并绑定）。

### AC-4（子进程链双重防御）
WHEN 在 Windows 下启动 `agy_silent.exe` 时，
THEN 进程创建标志必须显式附带 `CREATE_NO_WINDOW` 与作业对象 Job Object，即使子进程链中有模块尝试创建控制台，也不会弹出窗口或抢占焦点。

### AC-5（Daemon 重启验证）
WHEN daemon 启动、退出并在有缓存情况下重启时，
THEN daemon 进程执行配额查询依然稳定复用已验证的 `agy_silent.exe` 静默副本，不重新篡改、不回退、日志一致。

## Fix Approach

1. **重构 `pe_windows.go`**：
   - 提取 `readPESubsystem(path string) (uint16, error)`：读取 PE 头部获取 Subsystem。
   - 增加 SHA-256 辅助函数 `calcFileSHA256(path string) (string, error)`。
   - 改造 `ensureSilentAgyExe(srcPath string) (string, error)`：
     - 若出错统一返回 `("", err)`，杜绝返回 `srcPath`。
     - 校验逻辑：检查目标文件存在 -> 大小匹配 -> `readPESubsystem(dstPath) == 2` -> 读取并验证 `dstPath + ".sha256"`。
     - 若校验不通过，生成 tmp 文件 -> `copyAndPatchPE` -> 校验 tmp 文件的 `Subsystem == 2` -> 计算源文件 SHA-256 并写入 `.tmp.sha256` -> 原子 rename 替换目标 exe 与 sha256 文件 -> 对齐时间戳。
2. **重构 `proc_windows.go` 与 `proc_other.go`**：
   - `startAgyProcess` 入参改为已确认的 `runPath`。
   - Windows 下 `createFlags` 统一为 `windows.CREATE_SUSPENDED | windows.CREATE_NO_WINDOW`，提供底层防抢焦点的双保险。
3. **改造 `client.go`**：
   - `FetchUsage` 首先调用 `ensureSilentAgyExe(c.AgyPath)`。
   - 若返回错误，直接中断返回错误，不继续启动。
   - 获取 `runPath` 后，判断 `isSilent := filepath.Base(runPath) == "agy_silent.exe"`。
   - 通过 `c.Logf` 打印实际的 `runPath` 与静默副本状态。
   - 将 `runPath` 传入 `startAgyProcess(runPath)`。
4. **增加单元测试与集成测试**：
   - 增加 `internal/agapi/pe_windows_test.go`：测试 PE 读取、Subsystem 校验、SHA-256 绑定、篡改后自动重新生成、禁止回退等。
   - 增加 `internal/daemon/daemon_silent_test.go`：验证在 daemon 启动、查询、stop、再启动的生命周期中持续使用静默副本。

## Tasks

- [x] 1. 在 `pe_windows.go` 中实现 PE Subsystem 读取与 SHA-256 绑定及多维校验逻辑
  - Files: `internal/agapi/pe_windows.go`
  - 实现细节：实现 `readPESubsystem`、`calcFileSHA256`、完善 `ensureSilentAgyExe` 错误不回退与四重校验（存在、大小、Subsystem=2、SHA-256）
  - Verify: `go test -v ./internal/agapi -run TestEnsureSilentAgyExe`
  - Ref: AC-1, AC-3
- [x] 2. 改造 `proc_windows.go` 与 `client.go`，禁止回退、日志打印真实 runPath 与静默标记、强制 CREATE_NO_WINDOW
  - Files: `internal/agapi/proc_windows.go`, `internal/agapi/proc_other.go`, `internal/agapi/client.go`
  - 实现细节：`startAgyProcess` 接收 `runPath` 并追加 `CREATE_NO_WINDOW`；`FetchUsage` 提前解析 `runPath` 并格式化输出真实日志
  - Verify: `go test -v ./internal/agapi -run TestFetchUsage`
  - Ref: AC-1, AC-2, AC-4
- [x] 3. 编写单元测试与集成测试，覆盖静默副本生成、校验、篡改自愈、防回退及 daemon 重启持久使用
  - Files: `internal/agapi/pe_windows_test.go`, `internal/daemon/daemon_silent_test.go`
  - 实现细节：构建针对 PE Subsystem 校验、SHA-256 校验和 daemon 重启后使用静默副本的测试用例
  - Verify: `go test -v ./internal/...`
  - Ref: AC-3, AC-5
