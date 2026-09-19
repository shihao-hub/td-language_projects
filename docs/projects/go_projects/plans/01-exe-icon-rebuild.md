# go_projects exe 图标补齐与重建 开发计划

## 项目概述

按《GUIDE-GO-EXE-ICON》为 go_projects 子仓全部 10 个 exe 产出项目补齐默认站标地鼠图标并重新构建：

- 覆盖全部 10 个项目、全部产物（含 liteconf-server、quickaskd、copy_launcher、sublimefolders practice 版）
- clictl 已有图标（icon.ico + syso 已入库），仅重新 build，无文件改动
- glmquotawatch 重新 build 但**不提交**（项目当前整体 untracked，用户确认不入库）
- sublimefolders exe 用默认地鼠，托盘运行时图标（assets/icon.ico，自定义）保持不动
- 4 个无构建脚本项目（exestarter / glmquotawatch / ocstat / zreadmanager）**不补脚本**，改为更新对应 README 构建说明
- ocstat/cmd/practice 为实验代码、无构建入口，不处理

## 资源与产物清单

图标权威源：`docs\assets\projects\go_projects\go-default.ico`（父仓库）。每个主包目录放置 `icon.ico`（值拷贝）+ `rsrc_windows_amd64.syso`（rsrc 生成，go build 自动链接，无需改构建参数）。

13 个主包目录：

| # | 项目 | 主包目录 | 构建产物 |
|---|---|---|---|
| 1 | clictl | cmd/clictl（已有，跳过落盘） | clictl.exe |
| 2 | exestarter | cmd/exestarter | exestarter.exe |
| 3 | glmquotawatch | 项目根（main.go 在根） | glmquotawatch.exe |
| 4 | instancelock | cmd/instancelock | build/instancelock-windows-amd64.exe |
| 5 | liteconf | cmd/liteconf | build/liteconf.exe |
| 6 | liteconf | cmd/liteconf-server | build/liteconf-server.exe |
| 7 | ocstat | 项目根（main.go 在根） | ocstat.exe |
| 8 | pythonlauncher | 项目根（main.go 在根） | launcher.exe |
| 9 | pythonlauncher | scripts/copy_launcher | copy_launcher.exe |
| 10 | quickask | cmd/quickask | bin/quickask.exe |
| 11 | quickask | cmd/quickaskd | bin/quickaskd.exe |
| 12 | sublimefolders | cmd/sublimefolders | build/sublimefolders.exe |
| 13 | sublimefolders | cmd/practice | build/sublimefolders-practice.exe |
| 14 | zreadmanager | cmd/zreadmanager | zreadmanager.exe |

（clictl 不落盘新文件，仅重建，故落盘目录实为 13 个。）

## 实现步骤（分阶段）

### Phase 1：图标资源落位

- [x] 1.1 循环复制 `go-default.ico` → 13 个主包目录 `icon.ico`
- [x] 1.2 循环执行 `rsrc.exe -ico <dir>\icon.ico -o <dir>\rsrc_windows_amd64.syso` 生成 13 份 syso
- [x] 1.3 `git status` 核对新增文件仅落在上述目录（哈希校验 13/13 通过，syso 全仓共 14 = 13 新 + clictl）

**验收标准**：13 个主包目录各有 icon.ico（哈希等于 go-default.ico）与 rsrc_windows_amd64.syso；无其他位置新增文件。

### Phase 2：重新构建全部产物

- [x] 2.1 有脚本项目跑各自脚本：clictl / instancelock / liteconf / pythonlauncher（build.ps1 + copy_launcher go build）/ quickask / sublimefolders（build-tray + build-practice）
- [x] 2.2 无脚本项目按 README 命令构建：exestarter / glmquotawatch / ocstat / zreadmanager
- [x] 2.3 sublimefolders 两脚本补 `New-Item` 建目录（本次提前手动建目录后脚本才通过，证实干净克隆下会失败，按"改 build 脚本"范围修复；copy_launcher 为独立 go.mod 模块，须在其目录内构建且禁用 -trimpath）
- [x] 2.4 glmquotawatch 构建成功但不做任何 git 操作

**验收标准**：上表全部产物重新生成且时间戳为本次构建；各构建命令退出码为 0。

### Phase 3：更新 5 个无脚本项目的 README

- [x] 3.1 exestarter / glmquotawatch / ocstat / zreadmanager 四个 README 构建章节补图标说明（icon.ico + syso 自动链接、换图重出 syso 指引）
- [x] 3.2 pythonlauncher/scripts/copy_launcher/README.md 同步补图标说明

**验收标准**：5 个 README 的构建章节均含图标机制说明；不改动 README 其他内容。

### Phase 4：验证与收尾

- [x] 4.1 对全部新产物执行 `ExtractAssociatedIcon` 校验（预期 32x32）
- [x] 4.2 汇总改动摘要 + 按项目隔离给出 PowerShell git commit 命令（`<project>:feat:` 格式；glmquotawatch 不给提交命令）

**验收标准**：所有产物图标校验输出 32x32；提交命令与改动文件一一对应、无跨项目混提。

（4.1 实测 14/14 产物全部输出 32x32；4.2 提交命令按项目隔离给出，clictl 无文件改动不提交，glmquotawatch 按用户要求不入库。）

## 技术依赖

- `rsrc`（akavel/rsrc）：已安装于 `%USERPROFILE%\go\bin\rsrc.exe`，无需安装
- Go 工具链：主包目录 `*.syso` 自动链接，`rsrc_windows_amd64.syso` 文件名限定 GOOS=windows/GOARCH=amd64 生效

## 关键技术点

- **syso 自动链接**：图标是 PE 资源，与 Go 代码无关，现有 build 脚本/命令无需为链接图标做任何修改（除 2.3 的目录问题）
- **主包位置决定落盘位置**：glmquotawatch / ocstat / pythonlauncher 的 main.go 在项目根，icon 与 syso 必须放项目根
- **提交范围隔离**：每项目一次提交；clictl 无文件改动不提交；glmquotawatch 用户确认不入库；clictl 有一处无关未提交改动（internal/cli/completion.go），不触碰

## 预计时间

| Phase | 估时 |
|---|---|
| Phase 1 资源落位 | 0.2h |
| Phase 2 重新构建 | 0.5h |
| Phase 3 README | 0.3h |
| Phase 4 验证收尾 | 0.3h |
| **总计** | **1.3h** |

## 后续扩展（二期）

- 统一各项目构建脚本的版本号注入与输出目录约定
- goversioninfo 补版本信息块（图标之外的 PE 元数据）

## 注意事项

- glmquotawatch 存在 `glmquotawatch.exe~` 旧备份文件，与本次无关，不动
- instancelock/build/instancelock.exe 为历史产物（脚本只产 -windows-amd64 版），不主动删除
- 资源管理器图标缓存可能导致验证后仍未刷新显示，属正常现象
- pythonlauncher/copy_launcher 禁用 `-trimpath`（README 既有约束，重构建时遵守）

---
**最后更新：** 2026-09-18
**作者：** AI & User
**版本：** v1.1（执行完成，全部 Phase 验收通过）
