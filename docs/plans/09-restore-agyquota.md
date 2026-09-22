# Plan: 恢复 agyquota 项目并重构为基于 agy 命令获取配额

## 问题陈述
原 `agyquota` 项目因为通过 HTTP 直接请求 Google 内部 `daily-cloudcode-pa.googleapis.com` 接口遭到 Google 客户端身份校验（429 限流/封锁），而归档至 `.archived/projects/go_projects/agyquota`。
现在已安装好官方 Antigravity CLI（`agy`），其内置的 `agy -p "/usage" --output-format json` 可以稳定、合法地直接返回完整的 5 小时与周配额数据（JSON 结构完整包含 groups、buckets、remaining_fraction、reset_time 等）。
因此，用户要求将 `agyquota` 从 `.archived` 恢复回 `go_projects`，并**重构内部获取逻辑，改为调用 `agy` 命令**获取并解析配额，使 `agyquota` 彻底复活。

## 需求
1. **项目恢复**：
   - 严格按照 `docs/guides/GUIDE-RESTORE.md` 规范把 `agyquota` 从父仓 `.archived/projects/go_projects/agyquota` 还原至 `go_projects/agyquota`。
   - 保持 monorepo 提交纪律（子仓移入+提交+push，父仓移除副本+强制更新指针+push）。
2. **代码重构（复活方案）**：
   - 将底层配额数据源重构：不再走易受阻的底层 HTTP 直接调用，而是通过执行 `agy -p "/usage" --output-format json` 获取官方权威配额数据。
   - 保留 `agyquota` 既有的标准接口：
     - CLI 终端人读表格输出
     - `agyquota quota --json`（标准 JSON 信封输出）
     - `agyquota quota --raw`（打印 agy 的原始输出）
     - MCP 服务 `agyquota mcp` 及 `agyquota schema`
   - 更新文档：同步更新 `README.md` 与相关说明。
3. **验证与回归**：
   - 编译 `agyquota.exe` 并测试人读和 `--json` 输出，验证实际拿到当前 5 小时与周额度。

## 任务分解

- [x] Task 1: 物理恢复 agyquota 项目目录回子仓
  - 文件：`D:\Users\language_projects\.archived\projects\go_projects\agyquota` -> `D:\Users\language_projects\go_projects\agyquota`
  - 实现：使用 PowerShell `Move-Item -LiteralPath` 移动，验证绝对路径下 `go.mod`
  - 验证：`Test-Path "D:\Users\language_projects\go_projects\agyquota\go.mod"` 为 True
  - Demo：目录落位于 `go_projects/agyquota`

- [x] Task 2: 重构配额获取逻辑为基于 agy 命令
  - 文件：
    - `D:\Users\language_projects\go_projects\agyquota\internal\service\service.go`
    - `D:\Users\language_projects\go_projects\agyquota\internal\service\quota.go`
    - `D:\Users\language_projects\go_projects\agyquota\internal\agapi\client.go`
  - 实现：
    1. 在 `internal/agapi/client.go` 中实现自动探测 `agy` 并执行 `agy -p "/usage" --output-format json`；
    2. 解析 `agy` 返回的 JSON 数据中的 `groups` / `buckets`，适配为原系统的 `Snapshot` 结构；
    3. 清理废弃的底层 token 读取与 429 退避代码。
  - 验证：`go build ./...` 成功通过
  - Demo：业务核心成功支持 agy 数据源

- [x] Task 3: 编译验证与功能测试
  - 文件：`D:\Users\language_projects\go_projects\agyquota`
  - 实现：
    1. 在 `go_projects/agyquota` 目录下执行 `go build -trimpath -o agyquota.exe ./cmd/agyquota`；
    2. 执行 `.\agyquota.exe`，成功输出 Gemini 与 Claude 的 5h 与周额度；
    3. 执行 `.\agyquota.exe quota --json`，成功输出完整的 JSON 信封格式；
    4. 执行 `.\agyquota.exe schema`，MCP 契约导出一致。
  - 验证：真实命令均返回 0，额度解析准确完整
  - Demo：`agyquota` 恢复并运行正常

- [x] Task 4: 更新文档与使用说明
  - 文件：`D:\Users\language_projects\go_projects\agyquota\README.md`
  - 实现：更新设计说明与 README，说明现在配额由底层 `agy` 官方 CLI 驱动，解决 429 限流问题
  - 验证：检查 README 内容准确性
  - Demo：文档清晰描述新驱动模式

- [x] Task 5: 子仓提交与推送
  - 文件：`D:\Users\language_projects\go_projects`
  - 实现：子仓精确暂存 `agyquota` 目录，提交 `agyquota:feat: 重构为基于 agy CLI 获取配额并从归档恢复` (`5628c81`)，并执行 `git push origin main`
  - 验证：`git status -sb` 显示干净且与远端同步
  - Demo：子仓生成规范的恢复与重构提交

- [x] Task 6: 父仓库移除副本、更新指针并推送（两次提交）
  - 文件：父仓库 `.archived` 与 `go_projects`
  - 实现：
    1. 精确暂存归档移除，提交 `chore: 移除已恢复项目 agyquota 的归档副本` (`f39778d`)；
    2. 强制更新指针 `git add --force go_projects`，提交 `chore: 更新 go_projects 子模块指针` (`5ed53bc`)；
    3. 推送父仓库：`git push origin main`。
  - 验证：`git submodule status` 显示无 `+` 差异（对齐于 `5628c81`）
  - Demo：完成父子仓库同步闭环

---
**最后更新：** 2026-09-23
**作者：** Antigravity & User
**状态：** 全部完成
