# 计划 40：altscan —— Alt 域全局热键冲突检测 CLI（Rust）

> 状态：已批准待实施
> 创建：2026-10-06
> 交付目标：`rust_projects/altscan` 独立项目 + 父仓使用文档 + 飞书指南补章

## 1. 背景与目标

AutoHotkey v2 应用切换方案（`app_switcher.ahk`，9 个 Alt+单键热键，随开机自启）已交付使用。未来持续追加 `Alt+X` 键位存在与其他软件全局热键冲突的风险，需要一个检测工具：

1. **加新键前预检**（preflight）：确认目标组合键当前空闲；
2. **全量体检**（audit）：扫描整个 Alt+0-9/A-Z 域，输出占用地图，并区分「我的正常键 / 冲突现场 / 纯外部占用」。

### 1.1 事实基础（2026-10-06 双路调研定案）

- **RegisterHotKey 语义**（微软官方）：同组合键全局唯一，后注册者失败（`ERROR_HOTKEY_ALREADY_REGISTERED = 1409`）；试探注册法（注册成功=空闲、1409=被占）是 Windows **唯一受官方支持**的程序化检测途径，无公开枚举/归因 API；
- **AHK v2 冲突真实行为**（源码 `hotkey.cpp` 实证）：别的进程先注册同组合键时，脚本**零警告静默回退键盘钩子并反抢**——自己的键不坏，但**对面软件的该热键静默失效**。所以检测是双向体检：既查「谁抢我的」，也查「我抢了谁的」；AHK 内 `ListHotkeys` 显示 `k-hook` 类型即为冲突现场；
- **工具生态**：HotkeyDetective（本机 D:\Users\Softwares\HotkeyDetective，官方 v1.1.0）纯 GUI、无 CLI、无导出、需真实按键、Win11 25H2 疑似失效（issue #35）、DLL 驻留，**不可编排**；Hotkey Screener（NTWind，2026-08 仍活跃）支持 Win7–11 全量枚举 + 归因 + 导出，是**手工归因首选**；Windows Hotkey Explorer 在 Win8+ 危险禁用；ActiveHotkeys 32 位已死；PowerToys 无此能力。

## 2. 需求决策记录

| # | 决策 | 结论 |
|---|---|---|
| Q1 | 使用场景 | 预检 + 全量体检双模式，不做常驻监控 |
| Q2 | 检测范围 | Alt+0-9 / A-Z 共 36 键（预留修饰组合参数化能力） |
| Q3 | 冲突定义 | 双向：全系统 Alt 域占用地图 + 我的脚本中实际走了钩子回退的键 |
| Q4 | 归因 | 必须归因到进程；程序化无法归因，统一交 Hotkey Screener 手工完成 |
| Q5 | 形态 | 独立 CLI 工具入库；**豁免 MCP**，保留 `--json` 与 `--schema` |
| Q6 | 语言与位置 | **Rust + rust_projects**（用户指定试 Rust；沿用 whoholds 先例） |
| Q7 | 命名 | `altscan` |
| Q8 | 我的键来源 | 自动解析 `app_switcher.ahk`（默认路径 + `--ahk` 可改 + `--mine` 覆盖）；**项目文档须强调与 AHK 脚本的关联** |
| Q9 | 归属判定 | 两阶段 diff（AHK 运行中存基线 → 退出 AHK 后对比），非交互、可脚本化 |
| Q10 | 文档交付 | 计划文档 + 项目文档 + 飞书 AHK 指南追加「冲突检测」一节 |

### 2.1 试过但不行的路线（勿回头）

- **编排 HotkeyDetective**：无 CLI / 无导出 / 输入依赖真实按键 / 按键会真实触发占用进程动作 / 本机 Win11 25H2 疑似失效 / v1.1.0 DLL 驻留进程；
- **自研注入式归因**（钩子 DLL 注入全进程拦 WM_HOTKEY）：GPL-3.0 传染 + 需管理员 + 注入副作用，收益配不上脏度；
- **Windows Hotkey Explorer 路线**（实际触发全部组合键观察反应）：Win8+ 无按键抑制，灾难性副作用；
- **ActiveHotkeys**：仅 32 位，x64 系统不可用；
- **指望 PowerToys**：只做重映射，无第三方全局热键检测能力。

## 3. 领域术语表

| 术语 | 定义 |
|---|---|
| 空闲（free） | 试探 RegisterHotKey 成功，任何进程均可注册使用 |
| 占用（occupied） | 试探返回 1409，某进程已持有该组合键 |
| 自有注册（mine-reg） | 基线扫（AHK 运行中）占用、退出 AHK 后复扫空闲 ⇒ AHK 正常持有（绿色健康） |
| 冲突现场（conflict） | 脚本定义了该键，但退出 AHK 后复扫仍被占用 ⇒ 注册者是第三方 ⇒ AHK 走了钩子回退、正在反抢对方（红色告警） |
| 纯外部占用（foreign-held） | 与我的脚本无关、被第三方占用的键（选键时避开；归因清单对象） |
| 归因（attribution） | 确定「占用进程是哪个 exe」，Windows 无公开 API，交 Hotkey Screener 手工完成 |
| 两阶段 diff | 基线扫描（AHK 在）与对比扫描（AHK 退出）结果做差集，推导上述分类 |

## 4. CLI 契约

遵循《CLI 工具开发标准》：默认人读、`--json` 机器输出（`{"ok":true,"data":…}` / `{"ok":false,"error":{"code","message"}}` 包络）、`schema` 导出声明 `"interface":"cli"` 且零 I/O、Service 核心与 CLI 壳分层。

### 4.1 命令

| 命令 | 语义 | 关键参数 |
|---|---|---|
| `altscan scan` | 扫 Alt 域 36 键，输出占用地图 | `--ahk <path>`（默认 Startup 下 app_switcher.ahk）、`--mine <k1,k2>` 覆盖、`--save <file>` 存基线、`--diff <file>` 对比基线出四分类、`--json` |
| `altscan probe alt+x` | 单键预检（加新键前用） | `--json`；建议在未绑定前探测 |
| `altscan schema` | 导出命令契约 JSON | `interface:"cli"`，不触任何 I/O |
| `--version` / `--help` | 常规 | 版本取自 Cargo.toml |

### 4.2 退出码

- `0`：成功（probe 语义下 = 目标键空闲）；
- `3`：probe 查到目标键被占用——**业务结果非错误**，`--json` 携带完整数据；
- `1`：运行失败；`2`：参数错误。

### 4.3 输出

- 人读：表格 `键 | 状态（free/mine-reg/conflict/foreign-held/occupied*） | 说明`；单扫无 diff 时 mine 键仅能标 `occupied*`（归属未知，提示跑两阶段）；
- `--json`：scan 输出每键 `{key, modifiers, vk, status, mine}` + `meta`（单扫/diff 模式、ahk 路径、时间戳）；probe 输出单键结果。

### 4.4 已知限制（写入 README）

- 扫描的毫秒级注册窗口内若真按下该组合键，会被工具瞬时吞掉（概率极低，扫描全程 <1s）；
- probe 在键已绑定时只能报「被占用」，定性归属须两阶段 diff；
- 基线扫描时若 AHK 未运行，mine 键全部显示空闲 ⇒ 工具须显式告警「AHK 似乎未运行」。

## 5. 两阶段 diff 流程

```text
1) altscan scan --save base.json        # AHK 运行中，存基线
2) 托盘退出 AutoHotkey（或 Suspend）
3) altscan scan --diff base.json        # 复扫 + 差集分类
   基线占用 → 现在空闲        = mine-reg（我的正常键）
   脚本定义 ∧ 两次都被占      = conflict（我正在反抢对方，红色）
   脚本未定义 ∧ 被占          = foreign-held（外部占用，进归因清单）
   两次都空闲                 = free（可用空位）
4) 对 conflict / foreign-held 键，按文档用 Hotkey Screener 逐个归因
```

## 6. 技术方案

- **单 crate**（`rust_projects/altscan`），Rust 2024 edition，clap derive + serde/serde_json，`[profile.release] lto = true`——对齐 whoholds 形态；
- **手写 FFI 零第三方 Win32 绑定**（沿 whoholds 先例）：`RegisterHotKey` / `UnregisterHotKey`（user32）+ `GetLastError`（kernel32），共 3 个函数；注册 `hwnd=NULL`（WM_HOTKEY 落调用线程队列，立即注销即可，无需消息泵），**注册成功必须立即注销**；
- **分层**（对齐标准 Service/Shell）：
  - `src/winapi.rs` —— FFI 声明与探测原语（probe_combo → Free/Occupied）；
  - `src/ahk.rs` —— 解析 `!x::` 行热键定义；
  - `src/service.rs` —— 纯逻辑：组合键解析（`alt+g` → MOD_ALT+VK）、36 键域生成、diff 分类；可单测；
  - `src/cli.rs` / `src/output.rs` —— 参数、人读渲染、JSON 包络、退出码；
  - `src/schema.rs` —— 静态契约导出（serde 序列化常量，零 I/O）；
- **无运行时数据文件**：工具无状态；`--save` 是用户显式指定路径的输出物，不落 APPDATA 数据目录；
- **无图标 / 无 build.py**：rust_projects 无 go_projects 的图标与统一构建脚本约定，dev=cargo debug、release=cargo release（README 说明，沿 whoholds）；
- 单元测试：组合键解析、AHK 脚本解析、diff 分类矩阵；FFI 链路做真机冒烟（`cargo test` + 手跑 scan/probe）。

## 7. 非目标与豁免

- **不提供 MCP**：用户明确豁免；个人本机体检工具，无长期服务语义与外部客户端场景，`--json` + `--schema` 已覆盖机器调用（依标准 §0.1 例外条款记录于此，并同步写入项目 README）；
- 不做注入式归因、不做常驻监控、不扫非 Alt 域（修饰组合仅留参数化扩展位）、不管理/修改任何热键（纯只读检测）。

## 8. 交付物

1. `rust_projects/altscan`：Cargo 工程 + README（用法、两阶段流程、已知限制、MCP 豁免理由、**与 app_switcher.ahk 的关联说明——默认路径、9 键清单、AHK 静默回退机制背景**）；
2. `docs/projects/rust_projects/altscan/altscan 使用指南.md`：安装构建、预检/体检操作手册、**Hotkey Screener 下载与归因操作步骤**（https://www.ntwind.com/freeware/hotkey-screener.html ）、HotkeyDetective 为何仅作备胎；
3. 飞书《AutoHotkey 极速应用切换与 Toggle 自动化配置指南》追加「冲突检测」一节（AHK 代码块走 XML 实体转义，沿前次经验）；
4. 本计划勾选归档。

## 9. 验收清单

- [ ] `cargo build` / `cargo test` / `cargo clippy` 全绿（在 altscan 目录执行）；
- [ ] `--help` / `--version` / `schema` 零 I/O、秒回，schema 声明 `interface:"cli"`；
- [ ] scan 人读表格 + `--json` 可解析且包络合规；AHK 未运行时有显式告警；
- [ ] 两阶段 diff 真机验证：基线→退出 AHK→diff，9 个 mine 键应全部判 mine-reg（或如实出 conflict）；
- [ ] probe：空闲键退出码 0、占用键退出码 3 且 `--json` 数据完整；
- [ ] README / 使用指南 / 飞书章节与实现一致。

## 10. 任务清单

- [ ] Task 1：Cargo 工程骨架 + winapi FFI 探测原语 + 单键 probe
- [ ] Task 2：AHK 脚本解析 + 36 键域 scan（单扫模式）
- [ ] Task 3：--save/--diff 两阶段分类 + 告警逻辑
- [ ] Task 4：--json / schema / 退出码契约 + 单元测试补全
- [ ] Task 5：真机验收（含 AHK 退出复扫）+ README
- [ ] Task 6：父仓使用文档 + 飞书指南补章 + 计划归档
