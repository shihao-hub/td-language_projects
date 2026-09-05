# 001 · taskmon 进程树检测（父进程链 + 树视图）

> 状态：**已完成**（2026-09-03 实施通过，`pnpm typecheck && pnpm test` 96/96 绿）
> 创建：2026-09-03 · 项目：`taskmon/`（本仓库子项目）

## 背景与目标

taskmon 当前数据源为 `tasklist /fo csv /nh`（`src/tasklist.ts`），只有**名称 + PID + 工作集内存**，按进程名分组展示。缺失父进程关系导致：

1. **错误归因**：`node.exe` 组混装 MCP server / LSP / tsserver / 开发服务器，无法回答"这 500MB 是谁拉起来的"。
2. **泄漏识别缺失**："父已死、子还活"是典型的遗留/泄漏进程（实测案例：Zed 的 3 个 opencode.exe ≈ 2.6GB），有父子关系后是 O(n) 判定。
3. **kill 粒度粗**：现在 `k` 按名字组整组快照杀（`src/main.ts`）；有树后可只杀某棵子树。README 记录的深树超时问题（`src/kill.ts` TASKKILL_TIMEOUT_MS 注释）说明项目已隐式依赖进程树语义。
4. **同名进程不可区分**：两个 typescript node 实例谁是 server 谁是 tsserver，只有父链/命令行能区分。

## 决策回显（已与用户确认）

| 决策点 | 结论 |
|---|---|
| 展示模式 | 名字分组视图**组内增强**（展开行加父进程列 + 命令行截断列）+ `T` 键切换**树视图**，两种共存 |
| 数据源 | tasklist 继续供内存数字（2s 主频驱动 UI）；**每帧一次性 PowerShell CIM** 供拓扑（PPID/创建时间/命令行） |
| 命令行 | 采集 + 展开行截断显示 |
| 遗留优化 | 常驻 PowerShell worker 流式快照（替代双数据源）→ 记入 `taskmon/TODO.md` |
| 树缩进符号 | `├─` / `└─` |
| 孤儿标记 | `†` 前缀（父进程已退出） |

## 关键设计

### 双节奏采集（回答"2s 刷一次没问题吧？"）

实测：tasklist 0.2~8s（波动大）、一次性 CIM ~3s（含 powershell 启动 ~1s）> 2s 间隔。若串行"采集→等 2s→再采集"，实际节奏退化成 ~5s。解法：

- tasklist 按 2s 间隔驱动主刷新，界面永远 2s 一动；
- CIM 采集独立异步循环 + **overlap-skip**（上一次没跑完不发起下一次），拓扑用"最近一次快照"，落后 3-5s 无感（父子关系变化慢）；
- CIM 失败 / powershell 不可用 → 降级：父进程列留空、树视图提示"无拓扑数据"，**绝不阻塞主流程**（与单例锁同款降级哲学）。

### 踩坑预防

1. **编码**：WinPS 5.1 管道输出默认 OEM，命令行中文会乱码——脚本内先 `[Console]::OutputEncoding=[Text.Encoding]::UTF8` 再 `ConvertTo-Json`；node 侧按 utf8 读。
2. **日期解析**：WinPS `ConvertTo-Json` 把 DateTime 序列化成 `/Date(毫秒)/`，需专用解析。
3. **PID 复用**：父的 CreationDate 晚于子的 → PPID 指向无关进程 → 该子判为根/孤儿（`src/singleton.ts` 已有 ±5s 比对先例）。
4. **环与自引用**：PPID==PID、A→B→A 环（快照竞态）防死循环，检测到即断链为根。
5. **maxBuffer**：带 CommandLine 后 JSON 约 300-500KB，提到 16MB。
6. **孤儿标记**：父 PID 不在本帧快照 → `†`。

## 改动清单

| 文件 | 改动 |
|---|---|
| `src/types.ts` | `ProcessInfo` 增 `ppid?` / `creationDate?` / `commandLine?` / `parentName?` / `orphan?` |
| `src/cim.ts`（新） | CIM 一次性采集：spawn powershell、UTF-8 处理、`/Date()/` 解析、按 PID 建索引；纯函数可测 |
| `src/proctree.ts`（新） | 树构建：children 索引、孤儿判定、PID 复用断链、环检测、子树内存合计；纯函数可测 |
| `src/main.ts` | 双节奏采集循环；视图状态 `viewMode: 'group' \| 'tree'`；`T` 键切换；树视图下 `k` 走子树 kill |
| `src/render.ts` | ① 组内增强：父进程列（`↖Zed.exe`）、`†` 孤儿、命令行截断列 ② 树视图：根按子树总内存降序、子按内存降序、`├─/└─` 缩进、行内 PID + 自身内存 + 子树合计 |
| `src/kill.ts` | 树视图模式：`k` 只对选中节点发 `taskkill /T /PID`（复用现有 15s 回退逻辑）；组视图维持整组杀 |
| `src/__tests__/` | cim 解析、树构建（孤儿/复用/环）合并逻辑单测；现有测试不动 |
| `taskmon/TODO.md`（新） | 遗留：常驻 PowerShell worker 流式快照方案（省每帧 ~1s powershell 启动；单数据源替代 tasklist+CIM 合并） |
| `README.md` | 新增"进程树视图"章节、按键表加 `T`、数据口径补 PPID 来源与延迟说明 |

## 任务清单

- [x] 0. 创建本计划文件（docs/plans/001-taskmon-process-tree.md）
- [x] 1. 采集层 `src/cim.ts`：CIM 一次性采集 + UTF-8 + `/Date()/` 解析 + 单测
- [x] 2. 数据层 `src/proctree.ts`：树构建（孤儿 / PID 复用断链 / 环检测 / 子树合计）+ 单测
- [x] 3. `src/main.ts` 双节奏采集循环 + 降级路径
- [x] 4. `src/render.ts` 组内增强：`↖` 父进程列、`†` 孤儿、命令行截断列
- [x] 5. `src/render.ts` 树视图 + `T` 键切换 + 光标/滚动适配
- [x] 6. `src/kill.ts` 树视图子树 kill（单 PID `/T`，复用 15s 回退；护栏复用 guardKill 伪分组，kill.ts 本体零改动）
- [x] 7. 验收：`--once --tree` 拓扑输出、对照手工排查场景（WindowsTerminal→opencode 链、System→Memory Compression 可见）、powershell→powershell 子树 kill 实测 PASS
- [x] 8. `taskmon/TODO.md`（遗留：常驻 worker 方案）+ README 更新
- [x] 9. `pnpm typecheck && pnpm test` 全绿（96/96）

## 实施记录（与计划的偏差）

1. **树视图根行不显示 `†`**：实测 Windows 顶层进程（explorer/wininit/firefox）父进程均已退出是系统常态，
   全部标 `†` 是噪音；孤儿信号保留在分组视图成员行。`ppid<=0` 与自引用（System Idle/System）
   判为"从未有父"，不标孤儿。
2. **日期输出 epoch 毫秒**：采集脚本用 `[DateTimeOffset]::ToUnixTimeMilliseconds()` 直接输出数字，
   绕开 `/Date()/` 歧义；解析器仍兼容两种形态（双保险）。
3. **新增 `--tree` 参数**：交互模式初始视图 + `--once` 树快照（计划外的低成本补充，验收用）。
4. **测试**：cim 9 + proctree 18 + render 树 7（含拓扑降级路径），全套 96 通过。
5. 附带产物：`taskmon/scripts/proc-children-mem.ps1`（编辑器子进程内存排查脚本，实施前应手需求产出）。
6. **追加（验收后反馈）**：用户反馈"Zed 在树里找不到"——实为挂在 explorer 大树深处（第 238 行），
   属可发现性缺口。追加 `/` 查找 + `n` 下一个匹配：树视图自动展开祖先链直达目标行
   （`proctree.collectNodes` + main.ts 搜索状态机），README 按键表已更新。
7. **追加（二轮反馈）**：树视图初始默认展开 explorer 根（`proctree.defaultExpandedRootPids`，
   只初始化一次、手动收起不复活、explorer 未运行时下轮补；`--once` 输出不默认展开）。

## 验收标准

1. `--once` 模式输出的拓扑数据无乱码、日期解析正确；
2. 组视图展开行能看到 `↖父进程名` 与命令行截断；孤儿带 `†`；
3. 树视图能复现手工排查场景：`Zed.exe → opencode.exe ×3`、`sublime_text.exe → gopls.exe` 等子树；
4. 杀 CIM 不可用时程序照常运行（降级不阻塞）；
5. 树视图 `k` 只杀选中子树（用临时 notepad→cmd 链实测）；
6. `pnpm typecheck && pnpm test` 全绿。
