# tooldeck 开发计划（PLAN）

> 状态：已实施（八条操作流待用户手工验收）
> 日期：2026-09-12（实施完成日）
> 范围：exestarter CLI 增强 + tooldeck（Electron GUI，第一阶段仅 exestarter 模块）+ tooldeck-tauri 占位

## 1. 项目概述

### 1.1 背景与目标

go_projects 四个 CLI（exestarter / filesync / quickask / zreadmanager）已统一 JSON 包络纪律（`{"ok":true,"data":...}` / `{"ok":false,"error":{code,message}}`，参考 `docs/go_projects/clictl/Go CLI JSON 输出模式参考.md`）。本计划为它们建设统一的桌面 GUI 壳 **tooldeck**（Electron + React + TS），采用**单应用多模块**形态：左侧导航切换模块，本次只实现 exestarter 模块（对齐已归档的 exe-launcher Win32 GUI 功能面），其余三个模块灰置"待接入"。

核心架构原则：**GUI 是 CLI 的前端壳，一切数据操作走 CLI 子命令 + JSON 包络，GUI 不直接读写 config.json**。

### 1.2 已确认决策

| 决策点 | 结论 |
|---|---|
| CLI 缺口 | 先给 exestarter 补 `tag` / `update` 子命令 |
| 桌面壳 | Electron（electron-vite 脚手架）；另建 `tooldeck-tauri/` 占位目录 |
| 单实例 | Electron 原生 `app.requestSingleInstanceLock()` + `second-instance` 聚焦窗口（不用 instancelock） |
| 应用形态 | 单应用多模块，左侧导航 |
| 命名 | `tooldeck`（工具甲板）；Tauri 占位目录 `tooldeck-tauri` |
| 介绍窗口（.md 渲染） | 砍掉，不做 |
| README 笔误 | 顺带修正 exestarter README 与 EmitHelp notes 中的配置路径笔误 |
| 接口文档 | 产出 `docs/go_projects/exestarter/接口文档.md` 作为联调契约 |
| 探索项 | CLI 契约 schema 化 / MCP 化写进 tooldeck TODO.md，本次不实施 |

### 1.3 砍掉的功能（明确不做）

- exe 同目录同名 `.md` 的 Markdown 介绍窗口
- filesync / quickask / zreadmanager 模块（后续计划）

## 2. 涉及仓库与目录

| 位置 | 改动 |
|---|---|
| `go_projects/exestarter/` | 补 `tag` / `update` 子命令（含 EmitHelp）、README 笔误修正 |
| `go_projects/instancelock/` | 新增 `TODO.md`（通知信道等待办） |
| `typescript_projects/tooldeck/` | 新项目（Electron + React + TS） |
| `typescript_projects/tooldeck-tauri/` | 占位目录 + `TODO.md` |
| `docs/go_projects/exestarter/接口文档.md` | 新增（父仓库） |
| `docs/typescript_projects/tooldeck/PLAN.md` | 本文档（父仓库） |

## 3. 阶段 0：exestarter CLI 增强

### 3.1 新增子命令

**`tag <name> [--systag K] [--usertag T]`** —— 给已有条目设置标签

- 用 `fs.Visit` 区分"显式传入"与"未传"：**传了才更新，传空串 = 清除该标签**，未传的保持原值
- `--systag` 校验枚举：`todo | verify | broken | stable`，非法值报 `bad_args`
- 未注册 / 重名错误语义对齐 `remove`：`not_found` / `conflict`（重名提示手改配置文件）
- 成功输出更新后的完整条目（Emit）

**`update <name> --path P`** —— 改路径（exe 搬家后只更新路径）

- 校验：`.exe` 后缀、文件存在（`model.FileExists`）
- CLI 层先遍历查重（大小写不敏感 Clean 后比较），与其他条目重复报 `conflict`
- 调 `model.UpdatePath()`（名称跟随新文件名、标签与 AddedAt 原样保留），落盘
- 成功输出更新后的完整条目（Emit）

**执行期追加**：scan 噪音目录过滤补 `target`（Rust cargo 构建产物，阶段 4 验收时发现扫描结果混入大量 `build-script-build.exe`，已在 exestarter 修复并测试）

### 3.2 笔误修正

- `internal/cli/commands.go` EmitHelp 的 notes：`UserConfigDir/exe-launcher/config.json` → `UserConfigDir/exestarter/config.json`（实际代码 config.go:21 用的就是 exestarter 目录）
- `README.md`：命令列表补 `tag` / `update` 两行；两处配置路径笔误修正

### 3.3 验收标准

- [x] `go build ./...`、`go test ./...` 通过
- [x] `tag`：设/改/清空系统标签、用户标签各自生效；未传的 flag 不覆盖原值；非法 systag、未注册、重名报错正确
- [x] `update`：改路径后名称跟随新文件名、标签与添加时间保留；路径重复报 conflict；非 .exe / 文件不存在报错
- [x] `help` 输出包含两个新命令，notes 路径正确

## 4. 阶段 0.5：exestarter 接口文档（联调契约）

新增 `docs/go_projects/exestarter/接口文档.md`，结构借鉴 OpenAPI 的组织方式：

1. **协议总则**：JSON 包络格式、stdout 永远合法 JSON、错误走 stdout（管理命令）/ stderr（透传命令）、退出码表（0 成功 / 1 失败 / 127 未注册或失效）、`--pretty`、run 的透传豁免
2. **通用错误码表**：`bad_args` / `not_found` / `conflict` / `file_not_found` / `internal` / `spawn_error`
3. **数据模型**：Entry 字段表（name / path / valid / sys_tag / user_tag / added_at）、SysTag 枚举表（key / 中文 / 颜色）
4. **逐命令章节**（scan / list / add / remove / prune / run / open / shell / tag / update / version / help）：用途、参数表（flag / 位置参数、类型、必填、默认、约束）、成功响应 JSON 示例、该命令可能的错误码
5. **消费方示例**：PowerShell（`ConvertFrom-Json`）一例 + Node `child_process.spawn` 消费一例（tooldeck bridge 即真实参考实现）

验收：与阶段 0 实际实现逐一核对无出入；tag / update 章节含"传空清除"语义说明。✅ 已完成（docs/go_projects/exestarter/接口文档.md）

## 5. 阶段 1：tooldeck 脚手架

### 5.1 初始化

```powershell
cd typescript_projects
pnpm create @quick-start/electron tooldeck --template react-ts
```

（electron-vite 脚手架；若交互参数不可用则按其文档调整）

### 5.2 目录结构（清理示例代码后）

```
tooldeck/
├── package.json                # scripts: dev / typecheck / build / dist
├── electron.vite.config.ts
├── electron-builder.yml        # portable 打包配置
├── TODO.md                     # 探索项（schema 化 / MCP 化）
├── README.md
├── src/
│   ├── main/                   # Electron 主进程
│   │   ├── index.ts            # 窗口创建 + 单实例锁 + IPC 注册
│   │   ├── single-instance.ts  # requestSingleInstanceLock + second-instance 聚焦
│   │   ├── ipc.ts              # cli:exec / cli:detect / dialog:*
│   │   └── cli-runner.ts       # spawn + 包络解析 + 超时
│   ├── preload/
│   │   └── index.ts            # contextBridge 白名单暴露
│   └── renderer/
│       ├── index.html
│       └── src/
│           ├── App.tsx         # 应用壳（左侧导航 + 模块切换）
│           ├── modules/
│           │   ├── exestarter/ # 主模块（页面 + 子组件 + hooks + client）
│           │   └── pending/    # filesync/quickask/zreadmanager 灰置占位
│           ├── common/         # 类型定义、toast、确认框、手写 CSS
│           └── main.tsx
```

### 5.3 关键实现

- **单实例**：主进程 `app.requestSingleInstanceLock()` 失败 → `app.quit()`；`second-instance` 事件 → 聚焦已有窗口（对齐原 exe-launcher"提示并激活"体验）
- **安全基线**：`contextIsolation: true`、`nodeIntegration: false`，preload 只暴露白名单 API
- **样式**：手写 CSS，紧凑工具风，不引 UI 库 / Tailwind
- **窗口**：默认 1000×640，最小 860×520

### 5.4 验收标准

- [x] `pnpm dev` 打开空窗口（含左侧导航骨架）
- [x] `pnpm typecheck` 通过
- [x] 第二次启动被拒并聚焦首实例窗口（生产包实测：A 存活、B 被锁拒绝）

## 6. 阶段 2：CLI bridge 层

### 6.1 主进程 IPC

| 通道 | 入参 | 出参 | 说明 |
|---|---|---|---|
| `cli:exec` | `{exePath, args, timeoutMs?}` | `{ok, data?, error?, exitCode}` | spawn exestarter.exe，收集 stdout，`JSON.parse` 解包；默认超时 15s |
| `cli:detect` | `{explicit?: string}` | `string \| null` | 探测顺序（按环境分流，每步打主进程日志）：dev = 显式配置 > 开发态相对路径（app 路径向上找 `go_projects/exestarter/exestarter.exe`）> PATH；生产 = 显式配置 > tooldeck.exe 同级 `bin/exestarter.exe` > PATH；全失败返回 null（UI 引导到设置页） |
| `dialog:pickExe` | `{defaultPath?}` | `string \| null` | 文件选择框，过滤 `.exe` |
| `dialog:pickDir` | `{defaultPath?}` | `string \| null` | 目录选择框 |

### 6.2 渲染层

**核心类型**：

```ts
// CLI 包络（对应 exestarter 输出纪律）
type Envelope<T> =
  | { ok: true; data: T }
  | { ok: false; error: { code: string; message: string } }

// list 输出的条目行
interface Entry {
  name: string; path: string; valid: boolean
  sys_tag?: string; user_tag?: string; added_at: string
}

// 系统标签（与 model/tags.go 对齐）
const SYS_TAGS = [
  { key: 'todo',   label: '待完善', color: '#E08A00' },
  { key: 'verify', label: '待验证', color: '#2070C0' },
  { key: 'broken', label: '有问题', color: '#C03030' },
  { key: 'stable', label: '稳定',   color: '#309040' },
] as const
```

**`exestarterClient`**：`list / add / remove / prune / scan / tag / update / run / open / shell / version` 类型化封装。

**串行纪律**：CLI 每次进程级读写 `config.json`，并发写会互相覆盖——bridge 层内部维护 Promise 链队列，**所有写类命令强制串行**。

**run 特殊处理**：启动前用列表数据 `valid` 预检（失效直接提示清理 / 改路径，不发起 spawn）；有效则 detached spawn 不等退出码，toast"已启动"。

### 6.3 验收标准

- [x] 渲染进程调用 `client.list()` 得到真实条目数组
- [x] 错误场景（exe 不存在 / CLI 报错）返回结构化错误而非异常（no_cli / bad_envelope / CLI 错误码透传）
- [ ] 连续快速触发两个写命令，观察 config.json 无丢写（串行队列已落地：Promise 链，写命令强制串行；并发压测并入日常使用观察）

**实施增补**：IPC 通道在计划四条外新增 `cli:exec-detached`（run 透传豁免用）与 `settings:get` / `settings:set`（设置持久化到 userData/settings.json，GUI 仍不碰 CLI 的 config.json）；`cli:detect` 探测顺序调整为按环境分流并全程打日志（见 6.1 表）；探测改为直接扫描 PATH 环境变量（弃用 where.exe 子进程，避免 GBK 乱码泄漏控制台）。

## 7. 阶段 3：主界面

- **应用壳**：左侧导航（exestarter 激活 + 另三个灰置"待接入"）+ 主区
- **exestarter 模块布局**（对齐原 Win32 GUI）：
  - 工具栏：添加 / 扫描导入 / 打标 / 改路径 | 启动 / 定位 / 开终端 | 删除 / 清理失效
  - 表格：名称 / 路径 / 标签（系统标签圆点着色 + 用户标签文本）/ 添加时间；失效行红字；双击 = 启动；右键菜单与工具栏共用命令；选中态驱动工具栏可用性
  - 筛选：状态下拉（全部 / 有效 / 失效）+ 系统标签下拉（全部 / 四枚举），**前端本地过滤**（一次拉全量）
  - 状态栏：总数 / 有效 / 失效 / 各系统标签计数
- 数据刷新时机：模块加载、窗口聚焦、每次写操作后

### 验收标准

- [x] 真实 CLI 数据渲染，标签着色、失效红字正确（扫描预览实测真实数据）
- [ ] 筛选、双击启动、右键菜单可用（已实现，待用户手工过一遍）

## 8. 阶段 4：操作流

| 操作 | 流程 | CLI 命令 |
|---|---|---|
| 添加 | `.exe` 文件选择框 → 添加 → 刷新 | `add <path>` |
| 扫描导入 | 目录选择 → 预览列表 → 勾选 → 串行注册 → 汇总（成功 N / 已存在跳过 M） | `scan --dir D`（仅预览）→ 逐条 `add <path>` |
| 打标 | 对话框：系统标签四选一（含"无"）+ 用户标签文本 → 确定全量提交 | `tag <name> --systag K --usertag T` |
| 改路径 | 文件选择框（默认定位旧路径所在目录）→ 更新 | `update <name> --path P` |
| 启动 | valid 预检 → 后台启动 → toast | `run <name>`（detached） |
| 定位 / 开终端 | 直接执行 → toast | `open <name>` / `shell <name>` |
| 删除 | 确认框 → 删除 → 刷新 | `remove <name>` |
| 清理失效 | 确认框（显示失效数）→ 清理 → toast 移除数 | `prune` |

统一错误处理：toast 展示 `code + message`；所有写操作完成后刷新列表。

### 验收标准

- [ ] 造临时测试 exe（复制 notepad.exe 等无害程序），上述八条流程全部手工通过（扫描导入已实测，并由此发现/修复 target 过滤问题；其余流程待用户验收）
- [x] 每条流程的错误分支（未选中条目、失效条目、CLI 报错）均有可读提示（toast 统一展示 code+message）

## 9. 阶段 5：设置 + 打包

- **设置面板**：exestarter.exe 路径输入 + 「自动探测」按钮 + 当前 CLI 版本（`version` 命令回显）
- **打包**：electron-builder 配置 portable 目标，产物冷启动可用
- **代码质量**：eslint（typescript-eslint），`pnpm lint` 通过

### 验收标准

- [x] portable 产物在无 node 环境下可运行，探测不到 CLI 时引导到设置页（81.4MB，启动实测；探测失败链日志完整）
- [x] `pnpm lint`、`pnpm typecheck` 通过

**实施增补**：探测的生产分支用 `PORTABLE_EXECUTABLE_DIR` 定位 portable 原始目录（portable 运行时自解压到临时目录，`getPath('exe')` 指向解压目录会找错位置）；分发形态 = portable exe + 同级 `bin\exestarter.exe`。

## 10. 阶段 6：tooldeck-tauri 占位 + 各 TODO 文件

**`typescript_projects/tooldeck-tauri/TODO.md`**：Tauri 2 复刻要点占位——shell 插件替代主进程 spawn、single-instance 插件、fs 直读、体积对比（预期 ~10MB vs Electron 150MB+）。仅占位不写代码。

**`typescript_projects/tooldeck/TODO.md`**（探索项，本次不实施）：

- **CLI 契约 schema 化**：让 `help` 输出每命令的参数 JSON Schema，GUI 动态渲染界面——相当于 CLI 界的 OpenAPI 自描述
- **MCP 化**：四个 CLI 各包一层 MCP server（stdio JSON-RPC），可被 LLM 客户端直接当工具调用，quickask 最适合先行

**`go_projects/instancelock/TODO.md`**：

- 通知信道：第二实例被拒时把 argv / 消息递给持锁进程（先例：Electron 原生锁 = named mutex + 命名管道回传 argv），可设计 `notify` 子命令 + hold 进程可选监听
- 对比记录：Windows named mutex（内核对象、零残留）vs 当前文件锁（锁文件残留、跨平台统一），评估是否加 Windows 原生互斥体后端
- `list` 命令输出 JSON（当前 tabwriter 人读格式，机器消费不便）

## 11. 提交切分（完成后提供可执行命令）

| # | 仓库 | 提交 | 范围 |
|---|---|---|---|
| 1 | go_projects | `exestarter:feat: 补 tag 与 update 子命令` | exestarter（代码 + EmitHelp + 模型测试） |
| 2 | go_projects | `exestarter:docs: 修正配置路径笔误` | exestarter README |
| 3 | go_projects | `exestarter:fix: 扫描过滤 Rust target 构建目录` | exestarter scan（执行期新增） |
| 4 | go_projects | `instancelock:docs: 增加通知信道等待办` | instancelock TODO.md |
| 5 | typescript_projects | `tooldeck:feat: exestarter 模块 Electron GUI` | tooldeck 新项目整体 |
| 6 | typescript_projects | `tooldeck-tauri:chore: Tauri 2 复刻占位待办` | tooldeck-tauri |
| 7 | 父仓库 | `docs: 新增 exestarter 接口文档` | docs/go_projects/exestarter/ |
| 8 | 父仓库 | `docs: 新增 tooldeck 开发计划` | docs/typescript_projects/tooldeck/PLAN.md |

（跨仓库 / 跨子项目严格分开提交，符合 AGENTS.md 提交范围隔离规则）

## 12. 估时

| 阶段 | 内容 | 估时 |
|---|---|---|
| 0 | exestarter tag/update + README | 0.5h |
| 0.5 | 接口文档 | 0.5h |
| 1 | 脚手架 + 单实例 | 0.5h |
| 2 | CLI bridge | 1h |
| 3 | 主界面 | 1.5h |
| 4 | 操作流 | 1.5h |
| 5 | 设置 + 打包 | 1h |
| 6 | 占位 + TODO 文件 | 0.2h |
| 合计 | | ~6.7h |

## 13. 注意事项与风险

1. **CLI 并发写**：exestarter 无文件锁，config.json 读写竞态靠 GUI 侧串行队列规避；接口文档需明示"消费方不应并发调用写命令"
2. **run 阻塞语义**：`run` 是前台透传（等子进程退出），GUI 必须 detached 调用；启动前 valid 预检降低 127 概率，但 spawn 后的失败无法完整回传（toast 只报"已发起"）
3. **打包后路径探测**：portable 包内无 go_projects 相对路径，探测必失败——首启引导到设置页手配路径
4. **electron-vite 脚手架交互**：若 `pnpm create` 需要交互输入，改用其非交互参数或手工搭目录
5. **instancelock 不参与本方案**：tooldeck 单实例用 Electron 原生锁；instancelock 仅更新其 TODO（它仍是独立通用工具）
6. **AGENTS.md 文档约束**：PLAN.md / 接口文档均放父仓 `docs/`；子项目内只保留全大写豁免文件（README.md / TODO.md）

## 14. 执行顺序

阶段 0 → 0.5 → 1 → 2 → 3 → 4 → 5 → 6，每阶段验收通过后进入下一阶段；全部完成后按第 11 节切分提交。

---

**最后更新：** 2026-09-12（全部阶段实施完毕，操作流手工验收与提交待完成）
**版本：** v1.1
