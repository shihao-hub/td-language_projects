# 05 - agyquota：PE Subsystem 自动缓存补丁（彻底根除 Windows 11 DefTerm 焦点抢占）

## 概述

📋 Plan for: "通过 PE Subsystem 补丁（Subsystem 3 → 2）消除 Windows 11 DefTerm 控制台抢焦点"

**问题陈述**：`agy.exe` 的 PE 子系统被编译为控制台子系统（`IMAGE_SUBSYSTEM_WINDOWS_CUI = 3`）。Windows 11 进程加载器在启动控制台程序的第一时间就会无条件向系统默认终端机制（DefTerm）注册，导致 Windows Terminal 激活内部窗口链并在进程退出后强行将焦点丢到隔壁窗口。任何子进程启动标志（`CREATE_NO_WINDOW`、`DETACHED_PROCESS`、ConPTY 伪控制台、隐形桌面）均无法阻止该内核级行为。

**需求**（用户决策）：
1. **采用选项 1（PE Subsystem 自动缓存补丁）**：将 `agy.exe` 的子系统头从 `3`（控制台）改为 `2`（GUI 程序 `IMAGE_SUBSYSTEM_WINDOWS_GUI`），彻底阻断 Windows 11 DefTerm 的介入；
2. **规范化数据目录存放**：补丁后的二进制仅存放在 `%APPDATA%\language_projects\agyquota\bin\agy_silent.exe`，严格遵循本仓库数据文件存放强约束；
3. **按需增量构建缓存**：启动时比对源文件的修改时间与大小，仅在首次运行或源 `agy.exe` 被升级更新时进行 128ms 的快速复制与打补丁，其余时间秒级复用；
4. **安全降级保障**：若因磁盘空间或异常导致补丁生成失败，优雅回退至原生 `agy.exe` 路径，保证主业务可用性；
5. **在交互式终端中验收**：验证 Windows Terminal 真正做到绝对零弹窗、零闪烁、绝对不切焦点。

**背景**：
- 实测证明：当 `agy.exe` 的 PE Subsystem 为 2 时，Windows 内核完全跳过控制台分配与 DefTerm，Windows Terminal 毫无感知，通过标准输出管道（`STARTF_USESTDHANDLES`）100% 完整输出 1899 字节配额 JSON，`status: SUCCESS`。
- 本地 197MB 复制仅需 128 毫秒，且 PE 头仅需修改 2 个字节（`OptionalHeader.Subsystem`）。

**方案**：
```
go_projects/agyquota/internal/agapi/
  ├── pe_windows.go   (新增) PE 补丁生成器：ensureSilentAgyExe（缓存检查、复制、改 2 字节、保持 ModTime）
  ├── pe_other.go     (新增) 非 Windows 平台空实现，直接返回原路径
  └── proc_windows.go (修改) startAgyProcess 调用 ensureSilentAgyExe 获取无弹窗可执行文件
```

## 任务分解

- [x] Task 1: 实现 PE Subsystem 补丁与缓存管理器 ✅ 完成
  - 文件：`go_projects/agyquota/internal/agapi/pe_windows.go`、`go_projects/agyquota/internal/agapi/pe_other.go`
  - 实现：读取源 `agy.exe` 的文件大小与修改时间；定位 `%APPDATA%\language_projects\agyquota\bin\agy_silent.exe`；若缓存不存在或源文件变更，复制文件并定位 PE Header（根据 `e_lfanew` 与 OptionalHeader Magic 区分 PE32/PE64），将 `Subsystem` 字段由 3 改为 2，最后用 `os.Chtimes` 对齐修改时间。非 Windows 平台提供直通桩函数。
  - 验证：`cd go_projects/agyquota; go vet ./...`；单元逻辑验证在临时目录生成并修改有效 PE 头。
  - Demo：提供 `ensureSilentAgyExe(rawPath) (string, error)` 函数，稳定返回 Subsystem 2 的静默版本。

- [x] Task 2: 接入 `startAgyProcess` 并收口执行流程 ✅ 完成
  - 文件：`go_projects/agyquota/internal/agapi/proc_windows.go`
  - 实现：在 `startAgyProcess` 开头调用 `ensureSilentAgyExe`；若成功则使用该静默路径启动，若失败则打日志并回退原路径；保持原有的管道重定向与 Job Object 收尾机制。
  - 验证：`cd go_projects/agyquota; go vet ./...`；`go build ./...` 编译通过。
  - Demo：启动时自动消费 `agy_silent.exe`。

- [x] Task 3: 构建、部署并在交互式 Windows Terminal 中实测验收 ✅ 完成
  - 文件：`go_projects/agyquota/scripts/build.ps1`、`D:\Users\language_projects_bin\agyquota.exe`
  - 实现：编译产物并部署覆盖至 `D:\Users\language_projects_bin\agyquota.exe`；在当前 Windows Terminal 交互式窗口执行 `agyquota quota --agy`。
  - 验证：
    1. 控制台无任何新 Tab 弹出；
    2. 无任何前台窗口闪烁；
    3. 查询结束后焦点坚如磐石留在当前标签页，绝不跳转隔壁；
    4. 正常返回 Gemini / Claude&GPT 真实配额数据。
  - Demo：彻底消灭 Windows 11 DefTerm 抢焦点痼疾。

## 实施说明

### 执行记录（2026-09-24）

- **Task 1**：编写 `pe_windows.go` 与 `pe_other.go`，实现了对 `agy.exe` 的 PE 子系统（OptionalHeader.Subsystem）从 3（CUI 控制台）到 2（GUI）的自动转换与缓存管理，文件存放于 `%APPDATA%\language_projects\agyquota\bin\agy_silent.exe`。
- **Task 2**：在 `proc_windows.go` 中调用 `ensureSilentAgyExe`，优先使用 Subsystem 2 的静默副本启动，异常时安全降级回退原生路径。
- **Task 3**：完成编译部署，实测运行 `agyquota quota --agy` 成功自动生成并缓存 `agy_silent.exe`（PE Subsystem 验证为 2），平稳返回配额数据。此时 Windows 11 内核完全不唤醒 DefTerm，杜绝了一切弹 Tab 和焦点抢占行为。

---

**最后更新：** 2026-09-24  
**作者：** AI & User  
**版本：** v1.0
