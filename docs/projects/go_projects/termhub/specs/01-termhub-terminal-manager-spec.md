# Spec: termhub —— Windows 终端会话与启动项生命周期管理器

> 状态：已与用户达成设计共识（grill-me 审问 Q1–Q11 收敛），待 to-tickets 切片。
> 日期：2026-10-23

## 1. 目标世界长什么样 (The Destination)

termhub 是一款 Wails 桌面应用，作为 **Windows 终端宿主**替代"常驻多个 WT 窗口"的用法：

- 用户在 termhub 里通过启动项/启动组一键拉起内嵌终端（ConPTY + xterm.js），所有 shell 会话归一个窗口管。
- 每个终端 tab 关闭即回收整棵进程树（含子进程），内存立刻释放 ~100MB 级；命令历史不受影响，因为已落盘。
- 会话面板展示每个会话的运行状态、存活时长、工作目录、最近命令、内存占用。
- 命令记忆双视图：结构化命令清单（默认）+ 与 PowerShell PSReadLine ↑↓/Ctrl-R 同源的机制对齐。
- 终端里跑命令报错时，一键把「最近 N 条命令 + 最后一屏输出」丢给本机已有 agent CLI（agy/pi），结果面板可追问闭环。

核心价值：**终端即用即抛，记忆与状态留给管理器。**

## 2. 怎么算验收通过 (Acceptance Criteria & User Stories)

1. **[拉起终端]** 新建启动项后点击运行：窗口内出现可交互的内嵌 PowerShell 终端，初始目录正确，可正常敲命令、跑交互式程序。
2. **[启动组]** 定义含 2+ 启动项的组后一键拉起：多个终端 tab 按序打开，各自独立运行。
3. **[命令记忆]** 在某终端执行若干命令后，该会话的命令清单视图完整列出这些命令（时序正确）；终端内 ↑↓ 翻得到全局历史（含其他会话写入的命令）。
4. **[历史合并]** 会话期间新执行的命令，在会话存续与结束后都进入全局历史，且不与注入的初始历史重复。
5. **[关闭即回收]** 点 × 关闭任意 tab（经确认弹窗）后：shell 及其子进程全部终止（不留孤儿进程），内存释放；会话转为"已退出"卡片，命令清单仍可查看。
6. **[退出即终止]** termhub 主窗口退出（经确认弹窗）后：所有会话进程树的进程不复存在。
7. **[状态面板]** 会话卡片正确显示状态（运行中/已退出）、存活时长、cwd、最近 N 条命令、shell 进程内存占用；已退出会话保留退出元数据。
8. **[AI 诊断]** 在运行中/刚退出的会话上点击"交给 agent"：工具把最近命令 + 最后一屏输出组装发给本机 agy CLI，结果在面板显示；追问输入框可继续多轮（依赖 agy 会话续聊机制）。
9. **[数据隔离]** 全部运行时数据落在 `%APPDATA%\language_projects\termhub\{dev,prod}\`，验证仅执行确认后触发的命令其历史仍被记录。
10. **[诊断])(兼容性](中文输出在终端与历史文件中均为 UTF-8，无 BOM、无 GBK 乱码，含中文的命令与回显及丢给 agent 的上下文均正确。

## 3. 测试接缝 (Testing Seams)

- **确定的测试接缝 (The Seam)**：后端 **SessionManager 服务接口**（Wails 绑定层暴露给前端的方法集：`StartSession / StopSession / ListSessions / GetSessionHistory / AskAgent / ContinueAgent` 等）。PTY 流的输入输出以 SessionManager 收到的字节流与回调事件为观察点。
- **接缝理由**：它是工具全部能力的唯一公共入口（进程管理、历史读写、agent 调用都从这里发起）；在 Go 侧测试不需要真实 Wails 窗口（`wails binary -ns`），mock 掉前端事件回调即可注入输入捕获输出。ConPTY 行为单测昂贵，可注入 fake PTY 实现替代。
- **测试原则**：测试只在此接缝注入输入并断言输出/事件；严禁面向内部细节写测试；历史合并、退出语义是关键行为断言点。

## 4. 明确不做什么 (Out of Scope)

- ❌ PTY 输出流解析/启发式判断命令运行状态、自动报错触发诊断
- ❌ 幽灵会话/后台保活/断开重连/屏幕回放缓冲
- ❌ 通用进程/exe 托管（终端外的任何程序管理）
- ❌ 通用 agent 自由聊天窗
- ❌ 跨会话时间轴视图、子进程检测智能询问（二期）
- ❌ Bash/wsl 等多 shell 适配（第一版只做 PowerShell，架构预留 shell 抽象）

## 5. 架构决策与环境依赖 (Architectural Invariants)

- **技术栈**：Go + Wails v2 + ConPTY（Go 侧常用库如 `creack/pty` 或 `iamacoyote/go-conpty`）；前端 Vite + 原生 TypeScript + xterm.js；不引 React/Vue。
- **进程树终止**：每个会话的 shell 及其子进程绑入 Windows **Job Object**，关闭时 `TerminateJobObject` 一次全灭（不留孤儿进程）。
- **历史机制**：拉起 shell 时指定/注入该会话独立的历史文件路径；全局历史 = 隔离文件合并视图；启动时注入全局历史；写回合并由工具负责去重。
- **数据布局**（本仓强约束）：`%APPDATA%\language_projects\termhub\{dev|prod}\` 下含会话历史文件、启动项配置 JSON、会话元数据（JSON 或轻量 SQLite）。
- **UI 品味**：浅色亮堂 + 绿主色 + 圆角卡片 + 状态彩点，CC Switch 参照；禁暗色终端风。
- **构建**：统一 `build.py`（uv 单脚本/PEP 723），dev/release 自动判定与 `-ldflags` 注入版本；dev/prod 数据目录与单例 ID 隔离；GUI 项目专属图标流水线。
- **文档**：项目文档统一落父仓 `docs/projects/go_projects/termhub/`（spec 已在此）。
