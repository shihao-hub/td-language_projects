# termhub 垂直切片看板 (Tickets)

> 来源：`docs/projects/go_projects/termhub/specs/01-termhub-terminal-manager-spec.md`
> 拆解日期：2026-10-23。纪律：单切片单会话（implement + tdd），完成一个 /clear 再做下一个。

## DAG 总览

```
T01 曳光弹：可交互内嵌终端
 └─ T02 启动项与启动组（配置 CRUD + 一键拉起）
     └─ T04 会话状态面板（列表/卡片）
T01 ─ T03 命令记忆与历史合并（隔离存储 + 全局注入）
T05 关闭即回收（确认弹窗 + Job Object 整树终止）   ← blocked by T01
T06 会话元数据持久化与"已退出"回顾               ← blocked by T03, T05
T07 AI 诊断一键丢 agent + 追问闭环               ← blocked by T03, T04
T08 build.py 构建流水线 + 图标 + dev/prod 隔离    ← blocked by None（可并行，独立切片）
T09 托盘常驻与关窗重建 + 窗口几何 + 单实例         ← blocked by T01, T08（对齐 sh-go-wails-desktop）
```

可并行 Frontier：T01、T08；T01 完成后 T03/T05/T09 即解锁。

---

## Ticket 01: 曳光弹——可交互的内嵌终端

**核心交付**: 点击"新建终端"即拉起一个真实可交互的 PowerShell：xterm.js 渲染、能敲命令、能看输出，Wails 事件桥两头打通（穿透 Go/PTY/事件桥/前端全层）。

**测试接缝**: SessionManager 接口（StartSession 返回会话句柄；对流写入输入、从事件回调捕获输出；fake PTY 注入替代真 ConPTY 做单测，真 ConPTY 留给人工验收）。

**前置依赖**: None

**验收条件**:
- [x] 1. SessionManager.StartSession 用 fake PTY 时：输入写入会到达 PTY，PTY 输出经事件回调送达（单测断言）。
- [x] 2. 界面：点按钮出现终端 tab，运行 `dir`、`$PSVersionTable`、交互式 `python` 均正常（人工验收真 ConPTY）。
- [ ] 3. 会话 framebuffer 内能正确回现中文回显（UTF-8 无乱码）。

---

## Ticket 02: 启动项与启动组

**核心交付**: 用户可增删改启动项（名称/初始目录/自动命令），并可把多个启动项存为启动组一键批量拉起成多个 tab。

**测试接缝**: SessionManager 接口（配置层方法：`UpsertEntry / DeleteEntry / ListEntrys / StartGroup`；存储为配置 JSON 文件，测试用临时目录注入）。

**前置依赖**: Ticket 01

**验收条件**:
- [ ] 1. 启动项 CRUD 在接缝处行为正确，JSON 落盘含启动组结构（单测）。
- [ ] 2. 界面：启动项/组管理面板可新建、编辑、删除，点组一键拉起对应数量终端 tab。
- [ ] 3. 带自动命令的启动项拉起后自动执行该命令。

---

## Ticket 03: 命令记忆与历史合并

**核心交付**: 每会话独立历史文件；启动时注入全局历史；工具负责写回合并与去重；终端内 ↑↓/Ctrl-R 与命令清单同源。

**测试接缝**: SessionManager 接口（`GetSessionHistory` 与历史合并逻辑——合并是纯函数级行为，在接缝处用临时历史文件断言）。

**前置依赖**: Ticket 01

**验收条件**:
- [ ] 1. 会话内执行过的命令按序出现在隔离历史文件中（单测，fake PTY 注入命令流后检查文件）。
- [ ] 2. 新会话启动时历史含全局合并结果；会话后合并写入全局不产生重复行（单测）。
- [ ] 3. 界面：命令清单视图按会话展示，可搜索/复制；终端内 ↑↓ 翻到全局历史（人工）。

---

## Ticket 04: 会话状态面板

**核心交付**: 会话列表/卡片：状态（运行中/已退出）、存活时长、cwd、最近 N 条命令、shell 内存占用，点击卡片聚焦对应终端。

**测试接缝**: SessionManager 接口（`ListSessions` 聚合快照——进程信息可用注入 fake 后断言聚合正确性）。

**前置依赖**: Ticket 02（卡片承接启动项产出的会话）；数据依赖 Ticket 03 的历史文件。

**验收条件**:
- [ ] 1. ListSessions 对 fake 进程集合返回正确的聚合快照（单测）。
- [ ] 2. 界面：卡片实时刷新，状态彩点、时长、内存显示正确；点击卡片切到对应 tab（人工）。

---

## Ticket 05: 关闭即回收（Job Object 整树终止）

**核心交付**: 关 tab 弹确认后整棵进程树全灭、不留孤儿；termhub 退出时终止全部会话（同样确认）。

**测试接缝**: SessionManager 接口（StopSession 的进程组终止语义——单测验证 Job Object 绑定与终止调用发生在确切的会话生命周期节点；真实孤儿进程行为留人工验收）。

**前置依赖**: Ticket 01

**验收条件**:
- [ ] 1. StopSession 会先把 shell 进程加入 Job Object，随后 TerminateJobObject（单测，fake 进程句柄）。
- [ ] 2. 界面：关 tab 弹确认窗；确认后 tab 消失、卡片转"已退出"；取消则无副作用（人工）。
- [ ] 3. 人工验收：会话内起 `python`（子进程）后关 tab，任务管理器无残留 python.exe。

---

## Ticket 06: 会话元数据持久化

**核心交付**: 会话起止时间、退出状态等元数据落盘；重启 termhub 后"已退出"会话卡片与命令清单仍可回顾。

**测试接缝**: SessionManager 接口（元数据读写方法，临时目录注入断言持久化往返）。

**前置依赖**: Ticket 03、Ticket 05

**验收条件**:
- [ ] 1. 会话结束后元数据（id/起止/退出方式）完整落盘，重读一致（单测）。
- [ ] 2. 界面：重启工具后历史会话可查看卡片与命令清单（人工）。

---

## Ticket 07: AI 诊断一键闭环

**核心交付**: 会话卡片"交给 agent"：组装最近 N 条命令 + 最后一屏输出发给本机 agy CLI，结果面板显示，追问输入框多轮续聊（agy 会话 id 映射）。

**测试接缝**: SessionManager 接口（AskAgent / ContinueAgent——agent CLI 以接口注入，fake agent 断言 prompt 组装与会话 id 传递）。

**前置依赖**: Ticket 03（历史数据）、Ticket 04（卡片入口）

**验收条件**:
- [ ] 1. AskAgent 组装的 prompt 含最近命令与最后一屏截断输出，且复用已存的 agy 会话 id（单测，fake agent）。
- [ ] 2. 界面：结果面板展示分析，追问得到上下文连贯回复（人工，真 agy）。
- [ ] 3. agy 不存在时给出明确错误提示，不崩溃（单测）。

---

## Ticket 08: 构建流水线与项目基建

**核心交付**: 统一 build.py（dev/release 自动判定 + ldflags 版本注入）、GUI 专属图标流水线（.syso + 窗口图标显式绑定）、dev/prod 数据目录与单例 ID 隔离、项目 README。

**测试接缝**: build.py 自身行为（对临时 fixture 仓库跑构建判定逻辑）。

**前置依赖**: None（可与 T01 并行）

**验收条件**:
- [x] 1. 非 tag/非干净工作区 → 产 `<project>-dev.exe` 带 `-dev`/`-dirty` 版本号；tag+干净 → 正式名（脚本测试）。
- [x] 2. exe 图标为专属图标，非默认白框；任务栏/窗口图标正确（人工）。
- [x] 3. dev 构建数据写 `%APPDATA%\language_projects\termhub\dev`，与 prod 隔离（人工/单测）。

---

## Ticket 09: 托盘常驻与关窗重建

**核心交付**: 关闭主窗口销毁 WebView、进程与终端会话驻留托盘；托盘左键/双击/菜单重建窗口并自动重连全部运行中会话；窗口尺寸/位置/最大化记忆；dev/prod 单实例隔离。

**测试接缝**: SessionManager 快照（`ListSessions` 带 `work_dir`、`Shutdown` 关闭全部 PTY）+ `internal/app/window_state.go` 纯函数（几何往返/脏数据/屏外兜底）。

**前置依赖**: Ticket 01、Ticket 08

**验收条件**:
- [x] 1. 关窗后进程存活、WebView2 子进程退出，`/api/v1/sessions` 仍返回运行中会话（人工 + 快照断言）。
- [x] 2. 托盘图标注册成功；窗口重建与全部 tab 自动重连经单实例唤起实测（托盘点击/菜单共用同一 show 路径）。
- [x] 3. 托盘「退出 termhub」关闭全部 PTY，任务管理器无残留 shell（单测 + 人工）。
- [x] 4. 尺寸/位置/最大化记忆往返正确；外接屏拔除后窗口回中（单测 + 人工）。
- [x] 5. dev 与 prod 可同时运行且各自单实例，重复启动只唤起已有窗口（人工）。
