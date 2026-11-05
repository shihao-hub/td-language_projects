# Task List

- [x] 1. proc_windows.go：实现挂起启动与 Job 前台隔离原语
  - Files: go_projects/agyquota/internal/agapi/proc_windows.go
  - 实现细节：引入 `golang.org/x/sys/windows`（go.mod 既有 indirect，任务 5 统一 tidy）；自定义常量 `jobObjectUILimitSetForeground = 0x00000100`；`setNoWindow` 改名 `startSuspended`（HideWindow + CREATE_NO_WINDOW + CREATE_SUSPENDED）；新增 `foregroundIsolation` 类型、`attachForegroundIsolation`（OpenProcess → CreateJobObject → SetInformationJobObject(LimitFlags) → AssignProcessToJobObject → 遍历线程 ResumeThread）、`shutdown`（TerminateJobObject + CloseHandle，幂等）
  - Verify: go build ./...（备用）
  - Ref: AC-1、AC-4
  - 实施说明：UI 限制经 `JobObjectBasicUIRestrictions` 类下发（见 design.md 实施期修正记录 1）；`startSuspended` 最终采用 `DETACHED_PROCESS | CREATE_SUSPENDED`（见实施期修正记录 2，用户实测否决仅 Job 方案后升级，实测 agy 进程链中 conhost 彻底消失）

- [x] 2. proc_other.go：非 Windows 对齐签名（依赖任务 1 的接口形状）
  - Files: go_projects/agyquota/internal/agapi/proc_other.go
  - 实现细节：`setNoWindow` 同步改名 `startSuspended`（空体）；新增空 `foregroundIsolation` 类型、空 `attachForegroundIsolation`（恒零值,nil）与 `shutdown`
  - Verify: `$env:GOOS="linux"; go build ./...`（备用）
  - Ref: AC-4
  - 实施说明：交叉编译 GOOS=linux 实测通过

- [x] 3. client.go：接入前台隔离并移除 taskkill 收尾（依赖任务 1）
  - Files: go_projects/agyquota/internal/agapi/client.go
  - 实现细节：`setNoWindow` → `startSuspended`；`Start()` 成功后 `attachForegroundIsolation`，失败路径 `Process.Kill` + `Wait` + 包装错误返回；`defer iso.shutdown()` 替代 `defer killProcessTree(pid)`；删除 `killProcessTree` 函数、`pid` 变量与 `strconv` import；函数头注释同步为 job 收口语义
  - Verify: go vet ./...（备用）
  - Ref: AC-2、AC-3

- [x] 4. 版本 bump 与构建脚本校正（依赖任务 3 完成功能改动）
  - Files: go_projects/agyquota/internal/cli/root.go、go_projects/agyquota/scripts/build.ps1
  - 实现细节：`Version` 0.2.1 → 0.2.2；build.ps1 默认 `-Version` 0.2.0 → 0.2.2（修正长期漂移），头注释同步
  - Ref: AC-3

- [x] 5. 依赖整理、构建验证与产物更新（依赖任务 1-4）
  - Files: go_projects/agyquota/go.mod、go_projects/agyquota/agyquota.exe
  - 实现细节：`go mod tidy`（x/sys 由 indirect 转直接依赖）；`go build ./...`、`go vet ./...` 零错误；`scripts/build.ps1 -Version 0.2.2` 重建产物 exe；AC-1/AC-2 前台行为与无残留为手动验收（不自动执行）
  - Verify: `go build ./...` 输出为空（成功）；`go vet ./...` 无告警（备用）
  - Ref: AC-1、AC-2、AC-3
  - 实施说明：build/vet/交叉编译均通过；0.2.2 已构建并 install.ps1 部署至 D:\Users\language_projects_bin；实测查询成功且查询后无 agy 残留进程（AC-2 机制层验证通过）；AC-1 前台焦点行为（无窗口切换）留待用户日常使用观察

- [x] 6. 零进程直连最终方案（用户实测否决 DETACHED 方案后追加，依赖任务 1-5 的隔离底座）
  - Files: go_projects/agyquota/internal/agapi/proc_windows.go、go_projects/agyquota/internal/agapi/proc_other.go、go_projects/agyquota/internal/agapi/cred_windows.go、go_projects/agyquota/internal/agapi/cred_other.go、go_projects/agyquota/internal/agapi/zed.go、go_projects/agyquota/internal/agapi/client.go
  - 实现细节：`GetAgyQuotaToken` 读凭据管理器 `gemini:antigravity` 的 token.access_token/expiry；`FetchQuotaDirect` 用该 token 直连 `retrieveUserQuotaSummary`（同 zed 端点/UA，project=aicode-consumers）；`FetchUsage` 直连优先、过期或失败回退 spawn agy（保留 ConPTY + 私有桌面 + 双 UI 限制隔离底座）；proc_windows.go 重构为手工 CreateProcess 体系（`agyProcess`：伪控制台/私有桌面/管道/作业全句柄管理，shutdown 幂等收尾）
  - Verify: 直连模式实测零进程（agy 不启动）、查询数据等价、agy 链路零 conhost/OpenConsole（备用）
  - Ref: AC-1、AC-1b、AC-3、AC-4
  - 实施说明：实测直连路径 HTTP 200 且数据与 agy 输出一致；监控轮 console-session 事件仅剩监控自身噪声；前台表现待用户交互式实测最终确认
