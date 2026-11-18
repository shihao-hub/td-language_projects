# Plan for: minieverything 改造为双搜索渠道（默认本地个人实现 + 接入 Everything）

## 问题陈述
现有 `rust_projects/minieverything` 仅支持基于本地 NTFS 全盘扫描与 USN Journal 增量维护的单一实现（`index.bin`）。
为了兼顾"离线私有轻量实现"与"复用系统中已常驻运行的 Voidtools Everything 毫秒级引擎"，需要将 `minieverything` 架构改造为双渠道：
- **渠道一（默认）**：个人原生实现（`local`：NTFS + USN Journal 增量）；
- **渠道二（可选/增强）**：直连系统 Everything 服务（`everything`：通过 Win32 IPC `WM_COPYDATA` 检索）。

用户可以通过命令行参数切换（`--backend everything` 或 `-E`），在 Everything 运行时代替本地读盘索引；**不做自动降级**，Everything 不可用时显式失败。

## 需求
1. **默认行为不破坏**：默认不传新参数时，依然使用 `local` 渠道，结果行与统计行格式**字节级**向下兼容。
2. **新增 Everything 渠道**：`windows-rs` + 手工转译的 SDK 常量，通过标准 Win32 IPC（`WM_COPYDATA`）直连本地运行的 Everything 实例；协议为**异步回复**模型（见「协议流程」），客户端需自建回复窗口。
3. **参数统一映射**：全部搜索选项按下方「选项映射表」映射到双渠道，映射规则是实现与测试的唯一依据。
4. **失败显式报错、不静默降级**：选择 everything 渠道但 IPC 连接失败时，打印多原因提示并以非零码（3）退出；**不自动回退本地**（避免过期索引结果被无声使用）。
5. **代码解耦**：抽象统一 `SearchChannel` trait；搜索（返回结果）与打印（统一格式化器）彻底解耦。

## 背景
- 代码库位于 `rust_projects/minieverything/`，已依赖 `windows` crate 0.58（现有 features：`Win32_Foundation`、`Win32_Security`、`Win32_Storage_FileSystem`、`Win32_System_IO`、`Win32_System_Ioctl`、`Win32_System_WindowsProgramming`）；需新增 `Win32_UI_WindowsAndMessaging`（窗口查找/创建、`SendMessageTimeoutW`、消息循环）。
- 开发/验证环境中 Voidtools Everything 常驻运行（GUI 模式，索引量百万级）。
- Voidtools 官方 IPC 协议（事实源：Everything SDK 1.4 的 `everything_ipc.h`）：客户端用 `FindWindowW(EVERYTHING_IPC_WNDCLASS)` 定位 Everything 窗口，经 `WM_COPYDATA` 发送 `EVERYTHING_IPC_QUERY`，Everything **异步**向客户端指定的回复窗口回发 `EVERYTHING_IPC_LIST`——客户端必须自建窗口并跑消息泵。纯原生，无外部 C 动态库依赖。

## 方案设计

### 架构示意图

```mermaid
flowchart TD
    Cli["CLI Input (main.rs)"] --> Dispatcher["Channel Dispatcher"]
    Dispatcher -->|--backend local (默认)| Local["LocalChannel (channels/local.rs)"]
    Dispatcher -->|--backend everything (-E)| Ev["EverythingChannel (channels/everything.rs)"]

    Local -->|bincode / USN| LocalDisk["Local index.bin & NTFS"]
    Ev -->|WM_COPYDATA / 异步回复窗口| EvService["Voidtools Everything 进程"]

    Local --> Printer["Unified Result Formatter"]
    Ev --> Printer
```

### 模块划分
- `src/channel.rs`: 统一 `SearchChannel` trait、`QueryRequest` 与 `QueryResult`。
  - `QueryRequest` 字段：`pattern`、`limit`、`regex`、`case_sensitive`、`entry_type`、`full_path`、**`no_update`**（`--no-update` 开关必须进查询模型，否则 LocalChannel 感知不到）；
  - `QueryResult` **收缩为 `path` + `is_dir` 两字段**——两渠道的最小公共集（本地 `IndexEntry` 无大小/时间字段，不引入永远为空的 Option 字段；Everything 的 size/时间元信息直接丢弃）。
- `src/channels/local.rs`: 封装现有 `Index`、USN 刷新与匹配逻辑。
- `src/channels/everything.rs`: Win32 IPC 客户端（常量转译、回复窗口、消息泵、防御性解析）。
- `src/main.rs`: 增加 `-b, --backend <local|everything>`（默认 `local`）与 `-E, --everything` 快捷开关；子命令冲突校验（见下）。

### 选项 → 双渠道映射表（核心承诺）

| CLI 选项 | local 渠道现状 | everything 渠道映射 |
|---|---|---|
| `pattern`（纯文本） | 子串匹配，默认不区分大小写 | 包装为 `*pattern*` 对齐子串语义；Everything 默认同样不区分大小写 |
| `pattern` 含 `*`/`?` | 自动切换 glob 通配 | 原样透传（Everything 原生支持 `*` `?` 整文件名通配） |
| `-r, --regex` | Rust `regex` crate | `EVERYTHING_IPC_REGEX` + 原始 pattern（引擎方言差异见「已知行为差异」） |
| `-c, --case-sensitive` | 预先 lowercase 比较 | `EVERYTHING_IPC_MATCHCASE`（仍保留 `*` 包装） |
| `--full-path` | 匹配完整路径而非 basename | `EVERYTHING_IPC_MATCHPATH` |
| `-t file` / `-t dir` | 按 `is_dir` 过滤 | `EVERYTHING_IPC_FILTER_FILES` / `EVERYTHING_IPC_FILTER_FOLDERS` |
| `-l, --limit`（0 = 不限） | 显示满 N 条截断 | `w32_max_results`；IPC 下 `0` 是否等价不限需照头文件实测确认，不等价则以 `u32::MAX` 代入 |
| `--no-update` | 跳过搜索前 USN 增量刷新 | local 渠道专属，everything 渠道忽略（Everything 自维护实时索引） |

> flag 名、取值、结构体布局一律以官方 SDK `everything_ipc.h` 为准，1:1 转译为 `#[repr(C)]` 并在代码注释中标注出处；禁止凭记忆硬编码数值。

### Everything IPC 协议流程与可靠性设计

1. `FindWindowW(EVERYTHING_IPC_WNDCLASS)` 定位 Everything 窗口；找不到即进入错误处理（见下），**不得**判定为"未运行"。
2. 查询前客户端创建**一次性回复窗口**（`RegisterClassW` + `CreateWindowExW`，`WNDPROC` 接收 `WM_COPYDATA`），查询结束立即销毁。
3. 构建 `EVERYTHING_IPC_QUERY`：填 `hwndReply`（回复窗口句柄）、`w32_offset = 0`、`w32_max_results`、flag 位（按映射表）与 UTF-16 pattern。
4. 以 `SendMessageTimeoutW(WM_COPYDATA, ..., SMTO_ABORTIFHUNG, 2s)` 发送；**禁止 `SendMessageW`**（目标挂起会永久阻塞本进程）。发送超时/失败 → 显式报错退出。
5. 跑消息泵（`GetMessageW`/`PeekMessageW` 循环）等待回发 `WM_COPYDATA`（`EVERYTHING_IPC_COPYDATAREPLYW`），设**整体 10s 截止时间**；超时 → 显式报错退出，不无限等待。
6. `EVERYTHING_IPC_LIST` 反序列化必须**防御性校验**：`totitems`/`numitems`/`cbData` 相互一致、各 item offset 与文件名/路径 offset 落在缓冲区内、字符串 NUL 终止；任一违规 → 返回"回复数据损坏"错误，**不得 panic**（越界 slice 会直接崩掉 CLI）。
7. 由 item 的卷标/路径/文件名拼接完整 `path`，按属性位判定 `is_dir`，组装 `QueryResult`。

### 输出与统计行格式
- 结果行：每行一个 `path` 到 stdout，统一格式化器打印；local 渠道输出与现状**字节级一致**。
- local 统计行（stderr，保持现状格式不变）：
  `显示 {shown} 条{more}（扫描 {scanned} 条，耗时 {ms:.0} ms）`，`more` 在截断时为 `（已达 --limit 上限）`，否则为空。
- everything 统计行（stderr，新定义，标注来源、无"扫描"概念）：
  `显示 {shown} 条（共 {totitems} 条匹配，来自 Everything，耗时 {ms:.0} ms）`。
- 渠道统计用枚举 `ChannelStats::Local { shown, total_scanned, truncated }` / `ChannelStats::Everything { shown, totitems }` 表达，格式化器按变体分发——两渠道统计字段天然不同，不做强行统一。
- 排序差异：local 保持索引序（扫描序），everything 返回 Everything 默认排序；统一输出**不强制排序**，README 说明同查询两渠道顺序可能不同。

### 错误处理与退出码
- IPC 窗口未找到 / 发送失败 / 回复超时 / 回复损坏：统一 `EverythingIpcUnavailable` 错误（**不得**命名 `EverythingNotRunning`——找不到窗口不等于进程不存在）。报错信息枚举可能原因：
  - Everything 未运行；
  - Everything 以服务模式运行且无 GUI（无 IPC 窗口）；
  - Everything 以管理员运行而本程序未提权（UIPI 拦截 `WM_COPYDATA`）；
  - 使用了窗口类不同的版本（如 1.5 alpha）。
- 退出码：`2` = 本地索引不存在（沿用现状）；`3` = Everything IPC 不可用（新增）。
- **不静默降级**：显式指定 `--backend everything`/`-E` 失败后不自动改用 local；未来如需可加显式 `--fallback` 参数，本期不做。

### 与子命令的交互
`-E`/`--backend` 仅在搜索模式（无子命令）下有效：与 `update`/`status` 子命令同用时，解析后显式报错（"该参数仅搜索模式可用"），防止参数被静默吞掉。

## 已知行为差异（写入 README，用户可见承诺）
1. `--regex`：两侧引擎不同（Rust `regex` vs Everything 内置），环视/反向引用等语法命中结果可能不同。
2. `pattern` 含 Everything 查询语法字符（如 `;`、`|`、`wfm:` 等修饰符）时，everything 渠道按 Everything 语法解释，结果可能偏离 local 渠道；本期不做转义。
3. 两渠道结果排序不同（见「输出与统计行格式」）。

## 任务分解

- [ ] Task 1: 抽象搜索渠道 Trait 与查询模型
  - 文件：`src/channel.rs`、`src/channels/mod.rs`
  - 实现：定义 `QueryRequest`（上述 7 字段）与 `QueryResult`（`path` + `is_dir`）；定义 `trait SearchChannel`（输入 `QueryRequest`，输出结果集 + `ChannelStats`）。
  - 验证：在 `rust_projects/minieverything` 目录 `cargo check` 通过；契约单测（构造请求、默认值正确）。
  - Demo：能够通过契约类型构造空查询请求。

- [ ] Task 2: 搜索行为测试先行 + LocalChannel 改造
  - 文件：`src/channels/local.rs`、`src/search.rs`、`src/main.rs`
  - 实现：**先补行为测试，再重构**——为搜索核心补纯函数测试（不再与打印融合）：子串命中/大小写、子串 + `-c`、`*`/`?` 自动通配、`--regex` 与大小写、`--full-path` 与 basename、`-t file`/`-t dir`、`--limit` 截断与 `truncated` 标志、空结果。随后将打印从 `run_search` 解耦（匹配返回 `Vec<QueryResult>` + 统计，打印移交统一格式化器），封装为 `LocalChannel` 实现 `SearchChannel`，保留搜索前 USN 增量（受 `no_update` 控制）。
  - 验证：目录内 `cargo test` 全绿（含新增行为测试）；默认参数下结果行与统计行同重构前**字节级一致**（同索引文件、两侧均加 `--no-update` 后重定向对比，排除 USN 刷新干扰）。
  - Demo：实例化 `LocalChannel` 并执行一次本地查询，返回与原逻辑一致的结果集。

- [ ] Task 3: Everything IPC 客户端
  - 文件：`src/channels/everything.rs`、`Cargo.toml`（新增 `Win32_UI_WindowsAndMessaging` feature）
  - 实现：按「协议流程与可靠性设计」1:1 转译常量与结构体（以 `everything_ipc.h` 为准并注释出处）；实现回复窗口、消息泵、`SendMessageTimeoutW` 发送、10s 回复截止、防御性反序列化；连接类失败统一归并 `EverythingIpcUnavailable`。
  - 验证：`cargo check`/`cargo test`；**纯逻辑单测（回复 buffer 解析、offset 边界、NUL 终止、损坏数据拒绝）不依赖外部 Everything**；需真实 Everything 的连接探测测试标 `#[ignore]` 作为手动验证步骤，保证 CI/无 Everything 机器 `cargo test` 可通过。
  - Demo（手动）：对运行中的 Everything 执行 `cargo run -- MoreItems -E -l 5`，输出前 5 条结果与 everything 统计行。

- [ ] Task 4: CLI 双渠道调度与统一输出接线
  - 文件：`src/main.rs`
  - 实现：`Cli` 增加 `-b, --backend` 与 `-E`（`-E` 等价 `--backend everything`）；解析后按参数分发到对应 Channel；子命令 + `-E`/非默认 backend 组合显式报错；统一格式化器按 `ChannelStats` 变体打印结果行与各自统计行；退出码按「错误处理与退出码」。
  - 验证：`cargo test` 增加纯调度逻辑测试（默认 → local、`-E` → everything、`update -E` → 报错）；手动运行 `cargo run -- MoreItems`（local，字节级兼容）与 `cargo run -- MoreItems -E`（everything 统计行）。
  - Demo：默认与 `-E` 两种模式搜索 `MoreItems` 均能打印结果，且 `-E` 统计行标注"来自 Everything"。

---

**最后更新：** 2026-10-06  
**作者：** Antigravity & User  
**状态：** 待审批（只读阶段）  
**修订记录：** 2026-10-06 对抗评审后修订：补选项→IPC flag 映射表；补异步回复窗口/消息泵/超时/防御性解析设计；结果模型收缩为最小公共集；统计行按渠道定义输出契约；明确失败显式报错不降级与退出码；定义子命令交互；搜索行为测试先行；统一 everything 模块命名；枚举 windows-rs feature。
