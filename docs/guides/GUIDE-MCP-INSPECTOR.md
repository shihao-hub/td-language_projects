---
name: mcp-inspector-setup
description: 用 MCP Inspector（官方 @modelcontextprotocol/inspector v2.x）测试与调试自定义 stdio MCP server 的完整配置工作流：server 列表持久化机制（~/.mcp-inspector/mcp.json writable catalog）、Web 表单字段与 JSON 条目对照、liteconf 实测示例、连接后测试路径，以及自写脚本灌 JSON-RPC 消息必踩的协议时序坑。当用户说"用 inspector 测一下 mcp"、"配到 inspector"、"npx @modelcontextprotocol/inspector 怎么用"、"mcp.json 怎么配"、"inspector 页面里怎么加 server"，或要把自己项目的 mcp 子命令接入调试工具时使用。
---

# GUIDE-MCP-INSPECTOR：配置与测试自定义 stdio MCP server

适用于本仓各语言子项目（`liteconf mcp`、未来的其他 MCP 入口）在 MCP Inspector 中注册、连接与冒烟。核心结论一句话：**Inspector 的 server 列表就是一个本地 JSON 文件 `~/.mcp-inspector/mcp.json`，直接编辑它（或填 Web 表单，两者等价）即可把任何 stdio MCP server 配进去。**

## 配置存放机制（先懂这个，一切操作都有据可依）

- 启动：`npx @modelcontextprotocol/inspector`（Web UI，默认）；`--cli` / `--tui` 为另外两种形态。
- Web UI 的 Servers 列表持久化在 **writable catalog**：`C:\Users\<用户>\.mcp-inspector\mcp.json`（环境变量 `MCP_CATALOG_PATH` 可改路径）。
- 首次启动 Web 时自动 seed 三个示例 server（`filesystem-server-default` 等）——看到它们即说明 catalog 文件已生成。
- Web UI 里 Add / Edit / Remove server 实际就是在改这个文件；反过来手改文件后**刷新页面**即生效（不生效则重启 npx）。
- 易混项：`npx @modelcontextprotocol/inspector --config <file>` 是**只读会话**（文件缺省直接报错，UI 隐藏增删改），用于借用别人的配置文件；自己的工作集不需要它。

## 配置方式 A：直接编辑 mcp.json（推荐，AI 可代办）

在 `~/.mcp-inspector/mcp.json` 的 `mcpServers` 对象里追加条目。**Command 必须用绝对路径**（Inspector 子进程的工作目录是它自己的 `{inherit}`，不是你的项目目录，相对路径必然找不到 exe）：

```json
{
  "mcpServers": {
    "liteconf": {
      "type": "stdio",
      "command": "D:\\Users\\language_projects\\go_projects\\liteconf\\build\\liteconf.exe",
      "args": ["mcp"]
    }
  }
}
```

通用模板（stdio 类型）：

```json
"<server-id>": {
  "type": "stdio",
  "command": "<exe 或命令的绝对路径>",
  "args": ["<子命令>", "<参数1>", "..."],
  "env": { "KEY": "VALUE" },
  "cwd": "<可选，子进程工作目录>"
}
```

改完校验 JSON 合法性再刷新页面：

```powershell
(Get-Content "$env:USERPROFILE\.mcp-inspector\mcp.json" -Raw) | ConvertFrom-Json
```

注意 `env:TEMP` 等环境变量在某些执行链路下可能为空，脚本里别依赖它定位该文件。

## 配置方式 B：Web 表单（Add server 弹窗）

| 表单字段 | 对应 JSON | 填写要点 |
|---|---|---|
| Server ID | `mcpServers` 的键 | 字母/数字/连字符/下划线，如 `liteconf` |
| Transport | `type` | 本地子进程选 `stdio (local process)` |
| Command | `command` | **绝对路径**，如 `D:\...\build\liteconf.exe` |
| Arguments | `args` 数组 | **每行一个参数**；liteconf 只需一行 `mcp`（要连其他 server 实例再加 `-server`、URL 两行） |
| Environment | `env` 对象 | 一般留空 |
| Working directory | `cwd` | 留空（`{inherit}`） |

## 实测示例：liteconf（已配置，可直接复用流程）

已写入 `~/.mcp-inspector/mcp.json` 的条目即上文方式 A 的 liteconf 块，`mcp` 子命令默认连 `http://127.0.0.1:8646`。

测试路径（按序）：

1. 启动数据面（不启动也能连接与发现，但工具调用返回 `server_unreachable`——正好用于验证错误分支）：

   ```powershell
   cd D:\Users\language_projects\go_projects\liteconf
   .\build\liteconf-server.exe
   ```

2. 刷新 Inspector 页面 → Servers 列表出现 `liteconf` → 打开开关连接（stdio 子进程由 Inspector 托管，断开即回收）。
3. `Tools` 页签应列出 3 个工具（`liteconf.discovery` / `liteconf.config.get` / `liteconf.config.put`），每个带 inputSchema、outputSchema 与 annotations（readOnly/destructive/idempotent hint）。
4. 调用 `liteconf.discovery`（空参）→ `structuredContent.ok = true`；`liteconf.config.put`（app=`demo`, env=`dev`, content=`{"hello":"world"}`）→ 返回 `version:1`；`liteconf.config.get` 读回 content，再加 `path=hello` 验证点路径。
5. 停掉 liteconf-server 再调用任一工具 → 应得到 `isError=true` 且 `error.code = "server_unreachable"`。

## 自写脚本灌 JSON-RPC 消息的坑（冒烟测试必读）

| 陷阱 | 规避 |
|---|---|
| **协议时序**：把 initialize、`notifications/initialized`、tools/list 等消息一口气灌进 stdin，触发 `initialized before initialize` 断连 | 必须交互式时序：发 initialize → **读到响应** → 再发 initialized 通知 → 之后才能 tools/list / tools/call。真实 MCP 客户端（含 Inspector）都这么做，只有手写脚本会踩 |
| PS 5.1 把无 BOM UTF-8 脚本按 ANSI 解析，中文注释导致解析错乱 | 冒烟脚本纯 ASCII（英文注释），或存成带 BOM 的 UTF-8 |
| 管道重定向读大响应死锁 | 用文件重定向（`cmd /c "exe < in.jsonl > out.jsonl 2> err.jsonl"`）或逐发逐收（`StandardInput.WriteLine` + `StandardOutput.ReadLine`） |
| 以为 CRLF 行尾会导致解析失败 | go-sdk 的 stdio 读取用 `json.Decoder`，明确支持 `\r\n`，无需转换 |
| 端口上有僵尸 server 干扰 | 实验后 `Stop-Process` 清理；用 `netstat -ano | Select-String <端口>` 排查 |

## 验证清单

- [ ] 刷新页面后 Servers 列表出现新条目（catalog 文件生效）
- [ ] 连接成功且 `tools/list` 返回预期工具集（含 schema 与 annotations）
- [ ] 至少完成一次写工具调用并在数据面看到副作用（如 liteconf 的 `configs/<app>/<env>.json` 落盘、version 递增）
- [ ] 停掉数据面后复测，结构化错误码符合契约（如 `server_unreachable`）

## 参考

- 配置文件格式权威文档：<https://github.com/modelcontextprotocol/inspector/blob/main/docs/mcp-server-configuration.md>（`--catalog` 可写 vs `--config` 只读、Inspector 特有字段 `protocolEra`/`roots`/OAuth 等）
- liteconf MCP 契约与工具表：`go_projects/liteconf/README.md`「MCP 工具」一节；开发计划：`docs/projects/go_projects/liteconf/plans/01-mcp-server.md`
