# clictl MCP 接口文档

> clictl 的 MCP（Model Context Protocol）server 契约：`clictl mcp` 暴露的工具、
> Schema、错误语义与消费方接入方式。
> 与实现同源维护：改动 `internal/mcp/` 时必须同步更新本文档。
> 版本：2026-09-14（首版，协议基线 2025-06-18 握手 + 结构化结果）

## 1. 背景与协议选型

### 1.1 为什么 MCP 化

clictl 第一版已统一 JSON 包络纪律（stdout 永远合法 JSON，见父仓 `Go CLI JSON 输出模式参考.md`），
脚本与 GUI 能消费，但有两个缺口：

1. **无自描述**：消费方必须读文档才知道有哪些命令、参数类型、返回结构——tooldeck 第一版为
   exestarter 写死了整个专用页面，新工具接入 = 新写一个 React 模块；
2. **无标准调用协议**：spawn + 文本约定的联调缺乏工具发现、参数校验、取消等通用机制。

### 1.2 选型结论

| 候选 | 结论 |
|---|---|
| **MCP stdio**（采用） | 工具发现 / inputSchema（JSON Schema 2020-12）/ structuredContent / cancellation 开箱即用；官方 Go SDK + TS SDK + Inspector 联调工具链完整；不依赖 LLM 也能用 |
| JSON-RPC + OpenRPC | 通用 RPC，但生命周期、工具元数据、取消需自行约定，等于重造 MCP |
| HTTP + OpenAPI | 适合远程/浏览器形态，本地 CLI 场景多一层端口管理 |
| gRPC | Protobuf 代码生成与动态表单目标冲突 |

「CLI 界的 GET/POST」不存在现成标准：HTTP 动词语义无法从 CLI 命令推导。本方案把
**结构自描述交给 MCP（协议层）**，**资源语义（哪条命令是列表、谁是行标识）交给消费方声明式
配置（tooldeck 的 `crudConfigs.ts`，JSON Pointer 绑定，无脚本执行）**。

### 1.3 架构

```
CLI 子命令 ─┐
            ├→ internal/service（业务逻辑：校验 + store/runner，无输出、无 os.Exit）
MCP 工具   ─┘
```

- CLI 行为（包络 / 退出码 / 补全）完全不变；MCP 是并行的第二出口
- MCP server 常驻单进程，长持一个 SQLite 连接（WAL，与 CLI 并发安全）
- 协议 stdout 只走 SDK 通道；业务日志全部 stderr，绝不混流

## 2. 协议总则

| 项 | 约定 |
|---|---|
| 传输 | stdio（`clictl mcp`，不解析任何参数；客户端经 stdin/stdout 对话） |
| 工具命名 | `clictl.<verb>`（`clictl.list` / `clictl.add` …） |
| 输入校验 | inputSchema（2020-12）由 SDK 从 Go 结构体推导（`jsonschema` tag 即参数描述）；`omitempty` 字段 = 可选 |
| 成功结果 | `structuredContent`（结构化）+ content（JSON 文本形式，SDK 自动生成） |
| 业务失败 | `isError: true` + content 首条文本为 `code: message`（与 CLI 错误码体系一致）；**不返回协议级 error**（规范要求，客户端才能看到并自我纠正） |
| 部分失败 | `stop` 杀后复探仍存活、`run` 非零退出：`isError: true` 但 structuredContent 完整保留 |
| 取消 | 客户端 `notifications/cancelled` → handler ctx 取消 → run 工具终止整棵进程树并闭环记账 |
| 离线检查 | `clictl schema` 导出与 `tools/list` 同源的工具定义（in-memory 连接真实执行 tools/list，不打开数据库） |

## 3. 工具目录（10 个）

通用错误码（isError 文本中的 code）与 CLI 一致：`bad_args` / `not_found` / `conflict` /
`file_not_found` / `not_exe` / `meta_unknown_key` / `meta_invalid` / `meta_too_large` /
`db_error` / `internal`；run 类另有 `invalid`（文件失效）。

### 3.1 clictl.list

| 输入 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status | string | 否 | `active` / `invalid` 过滤；与 running 互斥 |
| running | boolean | 否 | 只看有后台活实例的工具；与 status 互斥 |

输出 `tools`：统一形状数组（普通模式附加字段省略），行字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| id / name / path / description / status / added_at / size_bytes / launch_count | 同 CLI | |
| meta | object | 可选；展开为对象（非 CLI 的原始 JSON 透传） |
| last_launch | string | 可选 |
| running_pids | int[] | 可选，仅 running 模式 |
| last_start | string | 可选，仅 running 模式 |

### 3.2 clictl.info

输入 `name`。输出 `tool`（同上行形状）/ `recent_launches`（最近 10 条，`duration_ms` 等
可空字段用 JSON null）/ `finished_count` / `total_duration_ms` / `running{alive,pids}`。

### 3.3 clictl.add

| 输入 | 类型 | 必填 | 说明 |
|---|---|---|---|
| path | string | 是 | .exe 后缀且文件存在（服务层校验） |
| name | string | 否 | 缺省为文件名去 .exe 小写化 |
| desc | string | 否 | |
| meta | object | 否 | 白名单 source（≤64 字节）/ tags（≤8 项、单项 ≤32 字节）；字节数限制在 Go 侧校验，Schema 只声明结构 |

输出：新建的 Tool。错误：`not_exe` / `file_not_found` / `conflict` / `bad_args` / meta 系列。

### 3.4 clictl.set

输入 `name` + `meta`（必填，`{}` = 清空）。整体替换语义与 CLI `set` 一致。输出更新后的 Tool。

### 3.5 clictl.rm

输入 `name`。输出 `{removed, name}`。级联删除启动记录。

### 3.6 clictl.start

输入 `name` + `args`（可选数组，不经 shell）。输出 `{name,path,pid,started_at,already_running}`。
后台分离（DETACHED）语义与 CLI `start` 一致：点火即走，退出码无从谈起。

### 3.7 clictl.stop

输入 `name`。输出 `{name,killed[],failed[],already_stopped}`。**部分失败（failed 非空）时
isError=true 但结果完整**。无活实例幂等成功。

### 3.8 clictl.cp

输入 `name` + `dest_dir`（必须已存在）+ `force`（可选）。输出 `{name,src,dest,size_bytes}`。
错误：`dest_not_found` / `dest_exists` / `same_path` / `copy_failed`。

### 3.9 clictl.run（非交互执行）

| 输入 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | |
| args | string[] | 否 | 数组直传，不经 shell |
| timeout_ms | int | 否 | 缺省 60000；≤0 按 60000 |

输出：

| 字段 | 说明 |
|---|---|
| exit_code | 子进程退出码；超时/取消（强杀）为约定值 1 |
| duration_ms | 实际存活时长 |
| stdout / stderr | 各保留最多 1 MiB；超出继续排空管道防死锁，仅标记截断 |
| stdout_truncated / stderr_truncated | 截断标记 |
| timed_out / cancelled | 超时 / 客户端取消 |

行为细节：

- **stdin 关闭**（连 os.DevNull）：本工具面向「填参执行、看结果」的非交互场景；需要交互
  stdin / PTY / TUI 的程序不适用（这是通用性边界，不是缺陷）
- **进程树回收**：Windows 用 Job Object（CREATE_SUSPENDED 挂起启动 → 入 Job → resume，
  杜绝孙进程逃逸竞态；KILL_ON_JOB_CLOSE 保证 server 崩溃时 OS 兜底回收整树）；非 Windows
  用进程组（Setpgid + 负 PID kill）
- **记账闭环**：与 CLI run 同一张 launches 表（duration_ms / exit_code）；超时/取消也闭环
- 非零退出 / 超时 / 取消 → isError=true + 结构化结果照常返回

### 3.10 clictl.version

无输入。输出 `{version}`（与 CLI 构建注入同源）。

## 4. CLI ↔ MCP 对照

| CLI 命令 | MCP 工具 | 差异 |
|---|---|---|
| list / info / add / set / rm / cp / start / stop / version | 同名工具 | meta 在 MCP 侧展开为对象；`--pretty` 等输出开关不适用 |
| run | clictl.run | **语义不同**：CLI 是前台透传（stdio 直通、退出码透传）；MCP 是非交互收集（见 3.9）。需要"打开一个真终端跑它"的场景仍用 CLI run / start |
| completion | 不暴露 | shell 补全脚本与 MCP 无关 |
| help / schema | 不暴露 | 帮助走 CLI；工具发现走 tools/list |

## 5. 通用性边界（评估结论）

| 接入条件 | 可获得的能力 |
|---|---|
| MCP server + inputSchema | 自动发现、动态表单、校验、执行、取消 |
| 返回 structuredContent | 自动结果表格 / 详情 / 折叠 JSON |
| + 消费方声明式 CRUD 配置 | 资源表格 + 增删改 + 行动作 |
| 仅有帮助文本的传统 CLI | 无法可靠推导参数类型与副作用，需显式适配 |
| 交互 stdin / PTY / TUI / 二进制输出 / 持续日志流 | MCP tools/call 单请求-单结果模型不覆盖，需 task 流 / 进度通知等扩展 |

## 6. 其余 go_projects 项目迁移矩阵

| 项目 | 迁移路径 | 备注 |
|---|---|---|
| exestarter | 套用 clictl 模式：service 层抽取 + `mcp` 子命令 | `run/open/shell` 是"打开新窗口/透传"语义，MCP 侧应只暴露管理命令，启动类留给 CLI；跨平台文件已有 build tag 拆分 |
| filesync | 同上，但 `run` 是分钟级长任务 | 需要 MCP 进度通知（progress）或 task 流；删除确认（--yes 两段式）在 MCP 侧可变成 isError + diff 结果驱动的确认 UI |
| quickask | 已有自定义 NDJSON 协议（quickaskd） | 迁 MCP task / `callToolStream` 获得流式问答展示；presets/config 管理命令可直接静态化 |
| zreadmanager | start/stop/restart/status 直接映射 | 非常适合 MCP 化（生命周期管理天然是工具调用） |
| instancelock | `hold` 常驻阻塞、退出码 3 是业务结果 | 不能套短调用模型；`try/list` 可 MCP 化，`hold` 需要 task 语义 |
| ocstat | 先把输出结构化（当前人读格式） | 再 MCP 化；watch 模式 = 持续刷新，需 task 流 |
| pythonlauncher | 参数/退出码透传启动器 | 无自有命令面，不 MCP 化；作为被 clictl 注册启动的程序存在 |
| taskmon | 当前为占位程序 | 先定义功能范围 |

跨平台注意：clictl 的 runner（探活/树杀）目前 Windows-only；`internal/mcp` 的执行核心已按
build tag 拆分（exec_windows.go / exec_other.go），整体 CLI 跨平台化时 MCP 层无需再动。

## 7. 消费方接入示例

### 7.1 Node（tooldeck 主进程真实参考实现）

```ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'

const client = new Client({ name: 'my-client', version: '1.0.0' })
await client.connect(
  new StdioClientTransport({ command: 'clictl.exe', args: ['mcp'], stderr: 'pipe' })
)
const { tools } = await client.listTools() // 工具 + inputSchema 自描述
const res = await client.callTool({ name: 'clictl.list', arguments: {} })
if (res.isError) {
  // 业务失败：res.content[0].text 形如 "not_found: …"
} else {
  // res.structuredContent.tools
}
```

### 7.2 MCP Inspector（联调）

```powershell
npx @modelcontextprotocol/inspector D:\path\to\clictl.exe mcp
```

### 7.3 离线检查工具定义

```powershell
clictl schema --pretty   # 与 tools/list 同源导出（不打开数据库）
```

## 8. 已知限制

- `clictl.list --running` 与 `--status` 的互斥在 MCP 侧靠 handler 校验（bad_args），
  Schema 无法表达跨字段约束
- run 的 stdout/stderr 按 UTF-8 解码；非 UTF-8 输出（GBK 老工具）会替换为 U+FFFD
- 并发写经 service 层串行（单连接排队 + WAL）；等待长进程（run）期间不持有数据库事务
