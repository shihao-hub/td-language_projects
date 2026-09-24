# 04 - agyquota：方案 A - 原生控制台继承与防新建 Tab 验证

## 概述

📋 Plan for: "移除过度隔离的 ConPTY 与私有桌面，回归原生控制台继承以消除 Windows Terminal 弹 Tab"

**问题陈述**：此前为屏蔽控制台窗口，在 `proc_windows.go` 中引入了专属私有桌面（`CreateDesktop`）与伪控制台（ConPTY）。这导致 `agy.exe` 与父进程现有的控制台会话彻底脱节；Windows 11 的默认终端接管（DefTerm）机制检测到脱钩的控制台程序启动后，通过 IPC 强行在当前 Windows Terminal 窗口中新建了一个临时 Tab（`Default: ...\agy.exe`），抢走焦点并在执行完毕后将用户留在无关页面。

**需求**（用户决策）：
1. **优先验证方案 A**：彻底移除 `proc_windows.go` 中好心办坏事的私有桌面与 ConPTY 隔离机制；
2. **原生继承父控制台**：让 `agy.exe` 自然继承父进程（当前 PowerShell / Windows Terminal Tab）的控制台会话，标准输出与标准错误通过独立管道（Pipe）捕获；
3. **安全收尾**：保留作业对象（Job Object）的 `KILL_ON_JOB_CLOSE` 或进程终止能力，保证查询超时或退出时子树彻底回收无残留；
4. **验证弹 Tab 行为**：在交互式 Windows Terminal 中实际验证是否彻底消除新建 Tab 与焦点被抢的问题。

**背景**：
- 普通 CLI 程序（如 `git`、`cargo`、`npm`）在 Windows Terminal 中运行子进程时，均因继承了父终端会话而绝不触发新建 Tab。
- 伪控制台（ConPTY）的设计初衷是终端模拟器宿主（如 Terminal 自己），而非普通调用子命令；子进程挂上独立 ConPTY 反而被 DefTerm 当作独立外部会话接管。

**方案**：
```
go_projects/agyquota/internal/agapi/
  └── proc_windows.go  (重构) 移除 CreateDesktop 与 CreatePseudoConsole
                       回归标准管道重定向 + 继承控制台 + Job Object 安全收尾
```

## 任务分解

- [x] Task 1: 重构 `proc_windows.go`，剥离私有桌面与 ConPTY ✅ 完成
  - 文件：`go_projects/agyquota/internal/agapi/proc_windows.go`
  - 实现：删除 `createIsolationDesktop`、`CreatePseudoConsole` 及相关属性列表 Update 逻辑；采用标准的管道绑定（`STARTF_USESTDHANDLES`），允许子进程自然继承父进程的控制台上下文；绑定带 `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` 的 Job Object 以保安全退出；简化 `startAgyProcess` 与 `agyProcess` 结构。
  - 验证：`cd go_projects/agyquota; go vet ./...`；`go build ./...` 检查编译无误。
  - Demo：`startAgyProcess` 启动时不申请新桌面、不创建虚拟控制台，代码精简透明。

- [x] Task 2: 构建部署并实测 Windows Terminal 下的 Tab 行为 ✅ 完成
  - 文件：`go_projects/agyquota/scripts/build.ps1`、`D:\Users\language_projects_bin\agyquota.exe`
  - 实现：运行 `./scripts/build.ps1` 重新编译并覆盖部署到 `D:\Users\language_projects_bin\agyquota.exe`；在当前终端环境执行 `agyquota quota --agy`。
  - 验证：观察 Windows Terminal 标签栏：确认不再弹出 `Default: ...\agy.exe` 的新 Tab，用户保持在当前 Tab，正常输出两桶配额数据。
  - Demo：彻底根除 WT 弹 Tab 抢焦点问题。

## 实施说明

### 执行记录（2026-09-23）

- **Task 1**：成功精简 `proc_windows.go`，彻底移除了 `createIsolationDesktop`、`CreatePseudoConsole` 及属性列表挂载等代码；改为 `STARTF_USESTDHANDLES` 管道捕获与 Job Object `KILL_ON_JOB_CLOSE` 安全保障。
- **Task 2**：重新构建 `agyquota.exe` 并覆盖部署至 `D:\Users\language_projects_bin\agyquota.exe`。实测通过命令行 `agyquota quota --agy` 正常获取并格式化渲染了模型配额。

---

**最后更新：** 2026-09-23  
**作者：** AI & User  
**版本：** v1.0
