# 实施计划 - 开发版与生产版隔离及双构建脚本支持

**问题陈述**：
当前 `glmquotawatch-gui` 在单例互斥锁（SingleInstance UniqueID）、开机自启（Autostart Registry）、数据持久化目录（AppData 路径）上均未区分 Dev 与 Prod 环境。导致日常开发调试新代码时与后台常驻的生产监控实例发生互斥冲突（开发版进程直接 exit 0），开机自启键位相互踩踏，且缺乏规范的自动化构建脚本产出对应命名的可执行文件。

**需求**：
1. 澄清决策：`1=a`，开发版（dev exe）严禁开机自启（执行报错或拦截保护，防止污染系统开机自启）；
2. 澄清决策：`2=a`，数据目录隔离为 `<project_name>/dev` 与 `<project_name>/prod`；
   - 生产环境：`%APPDATA%\language_projects\glmquotawatch-gui\prod`
   - 开发环境：`%APPDATA%\language_projects\glmquotawatch-gui\dev`
3. 单例模式隔离：
   - 生产环境：`shihao.langproj.glmquotawatch-gui`
   - 开发环境：`shihao.langproj.glmquotawatch-gui.dev`
4. 窗口标题辨识：开发版窗口标题增加 `[DEV]` 后缀（`GLM 用量监控 [DEV]`），便于直观区分；
5. 构建脚本支持：
   - `scripts/build-prod.ps1`：编译生产版 `bin/glmquotawatch-gui.exe`（无调试控制台，启用生产优化与版本号）；
   - `scripts/build-dev.ps1`：编译开发版 `bin/glmquotawatch-gui-dev.exe`（带 `-dev` 命名，注入开发环境变量及 Dev 标识）。

**背景**：
- 项目采用 Go + Wails v3 beta.25。Wails v3 支持 build tags（`-tags dev` / `-tags production`）以及通过 `-ldflags` 注入变量；
- 数据目录原由 `internal/store.DefaultDir()` 统一定位；
- 单例和窗口标题位于 `internal/guiapp/app.go`。

**方案**：
1. 建立环境标识包 `internal/env/env.go`：
   - 导出 `IsDev bool`（通过构建标签 `dev` / `production` 或 `-ldflags` 注入，双重保障）；
   - 导出 `AppName()`、`SingleInstanceID()`、`WindowTitle()`、`DataSubDir()`（`dev` 对应 `dev`，生产对应 `prod`）；
2. 升级 `internal/store/store.go`：
   - `DefaultDir()` 改为使用 `filepath.Join(baseDir, "language_projects", "glmquotawatch-gui", env.DataSubDir())`；
3. 升级 `internal/guiapp/app.go` 与 `autostart.go`：
   - `SingleInstance.UniqueID` 使用 `env.SingleInstanceID()`；
   - 窗口标题使用 `env.WindowTitle()`；
   - `setAutostart` 在 `env.IsDev` 时直接返回错误或拦截，禁止开发版注册自启；
4. 编写构建脚本 `scripts/build-prod.ps1` 与 `scripts/build-dev.ps1`：
   - `build-prod.ps1`：产出 `bin/glmquotawatch-gui.exe`；
   - `build-dev.ps1`：产出 `bin/glmquotawatch-gui-dev.exe`。

**任务分解**：

- [x] Task 1: 建立核心环境抽象与条件编译体系 已完成
  - 文件：`internal/env/env.go`、`internal/env/env_dev.go`、`internal/env/env_prod.go`
  - 实现：定义环境感知接口与默认常量（IsDev、DataSubDir、SingleInstanceID、WindowTitle），通过 build tags（`dev` vs `production`）及 ldflags 默认回退机制确保可靠识别。
  - 验证：`go test ./internal/env/...` 通过。
  - Demo：能够根据编译参数准确输出 dev 或 prod 对应的环境元数据。

- [x] Task 2: 改造数据目录与持久化存储隔离 已完成
  - 文件：`internal/store/store.go`、`internal/store/store_test.go`
  - 实现：更新 `DefaultDir()` 使得路径拼接 `/dev` 或 `/prod`；更新对应单元测试确保断言符合最新结构。
  - 验证：`go test ./internal/store/...` 通过。
  - Demo：开发模式与生产模式分别读写隔离的子目录，互不干扰。

- [x] Task 3: 改造单例互斥锁、自启拦截与开发期窗口标识 已完成
  - 文件：`internal/guiapp/app.go`、`internal/guiapp/autostart.go`
  - 实现：单例 UniqueID 接入环境隔离，窗口标题在 dev 态标注 `[DEV]`，`setAutostart` 明确拦截 dev 环境自启注册。
  - 验证：`go build -tags dev ./...` 编译无错误。
  - Demo：运行开发版时不触发生产版的单例唤醒，二者可同时或独立运行。

- [x] Task 4: 编写双构建脚本并验证输出产物 已完成
  - 文件：`scripts/build-prod.ps1`、`scripts/build-dev.ps1`、`README.md`
  - 实现：编写两个 PowerShell 构建脚本，统一调用前端构建与 Go 编译，分别输出 `bin/glmquotawatch-gui.exe` 和 `bin/glmquotawatch-gui-dev.exe`。
  - 验证：分别执行两脚本，检查 `bin/` 目录下产物命名、文件大小及版本号。
  - Demo：一键执行 `./scripts/build-dev.ps1` 产出 `glmquotawatch-gui-dev.exe`，执行 `./scripts/build-prod.ps1` 产出 `glmquotawatch-gui.exe`。