# 03 - agyquota：恢复纯 agy CLI 命令行执行模式

## 概述

📋 Plan for: "恢复 --agy 纯命令行执行模式，剥离凭据直连"

**问题陈述**：此前为规避 Windows 11 下 Windows Terminal / OpenConsole 抢焦点弹窗问题，在 `internal/agapi/client.go` 中引入了 Windows 凭据管理器 `gemini:antigravity` 读取与 Google 端点直连逻辑。这导致 `--agy` 数据源名实不符（提示为 CLI 却走直连），且绕过了 Google 官方 `agy` 客户端机制。

**需求**（用户决策）：
1. **纯命令优先**：坚持纯命令调用路线，彻底移除 `client.go` 中的凭据直连分支，让 `--agy` 100% 通过 `startAgyProcess` 执行 `agy -p /usage --output-format json`。
2. **与 zed 严格解耦**：`--agy` 不走类似 `zed` 的凭据与 HTTP 直连逻辑，保持 `agy` 官方 CLI 的高安全性与原生性。
3. **弹窗问题后续处理**：当前优先保证业务逻辑与调用路径的纯粹安全，控制台无弹窗优化后续单独演进。
4. **代码整洁**：清理为 agy 直连引入的冗余结构与函数（如 `GetAgyQuotaToken`、`FetchQuotaDirect`）。

**背景**：
- `startAgyProcess` 已在 `internal/agapi/proc_windows.go` 中实现了伪控制台（ConPTY）、私有隔离桌面、独立管道、Job Object UI 限制（`UILIMIT_SETFOREGROUND | UILIMIT_DESKTOP`）全套隔离原语，并在非 Windows 平台具备对齐实现。
- `internal/service/quota.go` 的 `parseSnapshot` 具备对 `agy` 原生 JSON 响应（`command.data.groups`）的完整解析能力。

**方案**：
```
go_projects/agyquota/
  ├── internal/agapi/
  │    ├── client.go        (修改) 移除 FetchUsage 中的直连分支，恢复直接调用 startAgyProcess
  │    ├── cred_windows.go  (修改) 移除 GetAgyQuotaToken / AgyQuotaToken 结构，保留 GetAgyLoggedEmail
  │    ├── cred_other.go    (修改) 同步清理非 Windows 桩
  │    └── zed.go           (修改) 清理仅用于 agy 直连的 FetchQuotaDirect 函数
  ├── internal/cli/root.go  (修改) 版本号递增 (0.2.3)
  └── scripts/build.ps1     (修改) 默认版本对齐 0.2.3 并完成编译与部署
```

## 任务分解

- [x] Task 1: 移除 `client.go` 中凭据直连分支，恢复纯 `agy` 命令行调用 ✅ 完成
  - 文件：`go_projects/agyquota/internal/agapi/client.go`
  - 实现：删除 `Client.FetchUsage` 开头的 `GetAgyQuotaToken` 与 `FetchQuotaDirect` 直连判定代码块；保留 `startAgyProcess` 进程隔离启动、管道读取、超时/取消监听与 `shutdown` 原子收尾逻辑；确保每次调用 `--agy` 均严格通过 `agy -p /usage --output-format json` 获取配额。
  - 验证：`cd go_projects/agyquota; go vet ./...`；`go build ./...` 检查无语法与类型错误。
  - Demo：调用 `Client.FetchUsage` 时 100% 走 `startAgyProcess` 执行命令，控制台明确打印执行 `agy -p /usage` 日志，无直连插桩。

- [x] Task 2: 清理凭据与网络层冗余直连逻辑 ✅ 完成
  - 文件：`go_projects/agyquota/internal/agapi/cred_windows.go`、`go_projects/agyquota/internal/agapi/cred_other.go`、`go_projects/agyquota/internal/agapi/zed.go`
  - 实现：清理 `GetAgyQuotaToken` 及其跨平台空桩（保留获取登录邮箱的 `GetAgyLoggedEmail`）；清理 `zed.go` 中专门为 agy 直连暴露的 `FetchQuotaDirect` 函数；保持 `zed` 与 `agy` 职责完全解耦。
  - 验证：`cd go_projects/agyquota; go vet ./...` 检查无孤立引用或编译错误。
  - Demo：`agy` 模块完全自治，不再侵入式引用 `zed` 内部的 HTTP 直连方法。

- [x] Task 3: 构建、冒烟测试与产物部署验证 ✅ 完成
  - 文件：`go_projects/agyquota/internal/cli/root.go`、`go_projects/agyquota/scripts/build.ps1`
  - 实现：版本号递增至 0.2.3；运行 `./scripts/build.ps1` 构建 `agyquota.exe` 并部署至 `D:\Users\language_projects_bin\agyquota.exe`；实际运行 `.\agyquota.exe quota --agy` 验证真实调用 `agy` 命令输出配额。
  - 验证：`D:\Users\language_projects_bin\agyquota.exe --version` 确认输出 0.2.3；`D:\Users\language_projects_bin\agyquota.exe quota --agy` 成功通过 `agy` CLI 获取到配额数据并正确渲染表格。
  - Demo：`agyquota` 使用纯 `agy` CLI 命令行稳定返回最新配额，日志与行为完全一致。

## 实施说明

### 执行记录（2026-09-23）

- **Task 1**：移除 `client.go` 中伪造的直连 bypass 代码块，完全恢复直接调用 `startAgyProcess(c.AgyPath)` 执行命令。
- **Task 2**：从 `cred_windows.go`、`cred_other.go` 清理未使用的 `GetAgyQuotaToken` / `AgyQuotaToken`，从 `zed.go` 移除 `FetchQuotaDirect`，实现模块解耦。
- **Task 3**：版本递增至 `0.2.3`，完成编译构建并将产物复制到 `D:\Users\language_projects_bin\agyquota.exe`。实测 `agyquota quota --agy` 成功调用 `C:\Users\29580\AppData\Local\agy\bin\agy.exe -p "/usage" --output-format json` 并成功输出双桶配额。

---

**最后更新：** 2026-09-23  
**作者：** AI & User  
**版本：** v1.0
