# 02 - agyquota：agy 直连模式防冷副本与降级占位数据抖动修复（渠道严格隔离）

## 概述

📋 Plan for: "agyquota --agy 直连模式防 Google 冷副本与降级占位抖动"

**问题陈述**：`agyquota --agy` 在直连 Google 配额接口（零进程模式）时，若命中 Google 未同步用量的冷节点副本，会返回全 100% 且重置倒计时为初始值（如 weekly 为 6天23小时）的假满额占位数据；待后续查询命中热节点时才恢复真实用量（如 weekly 99%，5天21小时）。

**需求**（含渠道严格隔离约束）：
1. **渠道与账号绝对隔离**：`--zed` 与 `--agy` 是两个完全独立的不同渠道、不同登录账号、不同凭据源：
   - `zed` 渠道：凭据来自 `~/.gemini/antigravity-acp/acp_token.json`，自有缓存 `.quota_token_cache.json`，独立维护。
   - `agy` 渠道：凭据来自 Windows 凭据管理器 `gemini:antigravity`，自有独立缓存 `.agy_quota_cache.json`，独立维护。
   - 两者**严禁共享任何缓存、状态或账号数据**，彼此完全互不干扰。`zed.go` 与 `ZedClient` 保持既有独立实现不受影响。
2. **`--agy` 专有防降级与校准机制**：
   - 针对 `agy` 渠道的直连请求，增加专有的冷节点探测（识别全 100% 且缺少有效 description 描述的占位包）。
   - 命中占位包时执行 1~2 次 150ms 快速换副本重试。
   - 若重试后仍为占位包，且 `agy` 本地缓存（`.agy_quota_cache.json`）存在属于该 `agy` 账号未过期的真实历史快照，则使用该快照校准。
   - 查询到有效真实用量后，落盘更新到 `agy` 专有缓存 `.agy_quota_cache.json`。
3. **诊断日志**：在检测到副本延迟并触发重试/校准时，非 `--json` 模式下输出控制台提示日志。

**背景**：
- Google `retrieveUserQuotaSummary` 接口存在多副本集群，冷节点在无主动同步时会返回默认的初始桶状态（全 100%、无 description 描述、resetTime 为默认整周期）。
- `--agy` 直连链路需要补齐属于 `agy` 专有链路的防降级保护。

**方案**：
```
go_projects/agyquota/internal/agapi/
 ├── client.go        (修改) FetchUsage: 完善 agy 专有直连链路，集成冷副本探测、150ms 重试、.agy_quota_cache.json 读写与校准
 ├── zed.go           (只读/不改动) 保持 ZedClient 与 .quota_token_cache.json 独立，严格互不影响
 └── root.go / build  (修改) 版本递增与构建部署
```

## 任务分解

- [ ] Task 1: 在 agapi 中为 agy 专有链路实现防降级探测与专有快照缓存
  - 文件：`go_projects/agyquota/internal/agapi/client.go`
  - 实现：
    1. 定义 `agyQuotaCache` 结构（仅存 `LastQuotaRaw`、`LastQuotaAt`、`GeminiResetAt`、`Account`）。
    2. 实现 `agy` 专有的 `loadAgyCache()` 与 `saveAgyCache()`，路径严格固定为 `%APPDATA%\language_projects\agyquota\.agy_quota_cache.json`。
    3. 在 `Client.FetchUsage` 的零进程直连分支中：
       - 请求 Google 配额接口后，探测是否为冷副本占位包；
       - 若是，触发 1~2 次 150ms 快速重试；
       - 若重试仍为占位包且本地 `agy` 快照有效，自动校准并输出提示日志；
       - 拿到真实数据后落盘更新 `.agy_quota_cache.json`。
    4. 确保不修改 `ZedClient` 的任何逻辑与缓存，保持双渠道完全隔离。
  - 验证：`go vet ./...` 检查无语法与类型错误；`go test ./...`（若有）通过。
  - Demo：`agy` 渠道具备专有的防冷副本与快照校准能力，不依赖也不干扰 `zed` 渠道。

- [ ] Task 2: 本地实测与多轮查询验证
  - 文件：`go_projects/agyquota/internal/agapi/client.go`
  - 实现：编译本地测试二进制，分别执行 `agyquota --agy` 与 `agyquota --zed`，确认：
    1. `--agy` 首次查询即能获取真实用量（如 99% 5天21小时），不再闪现 100% 假象；
    2. `--agy` 与 `--zed` 分别读写各自独立的缓存文件（`.agy_quota_cache.json` vs `.quota_token_cache.json`），账号与数据严格互不串扰。
  - 验证：`go build ./...` 编译通过；运行 `.\agyquota.exe --agy` 与 `.\agyquota.exe --zed` 输出预期数据。
  - Demo：双渠道独立运行、数据准确。

- [ ] Task 3: 构建、部署并验证 0.2.3 产物
  - 文件：`go_projects/agyquota/internal/cli/root.go`、`go_projects/agyquota/scripts/build.ps1`
  - 实现：版本号递增至 0.2.3；运行构建脚本并将产物部署到 `D:\Users\language_projects_bin\agyquota.exe`。
  - 验证：`D:\Users\language_projects_bin\agyquota.exe --version` 输出 0.2.3；`D:\Users\language_projects_bin\agyquota.exe --agy` 正常运行且输出真实数据。
  - Demo：生产路径下的 `agyquota.exe` 正式升级 0.2.3。

---

**最后更新：** 2026-09-23  
**作者：** AI & User  
**版本：** v1.1
