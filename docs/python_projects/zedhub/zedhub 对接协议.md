# zedhub 对接协议

> zedhub 为程序化消费提供两个**标准协议**入口:JSON-RPC 2.0(`zedhub rpc`)与
> MCP(`zedhub mcp`)。对接方只需阅读对应协议规范,配合本文的方法表即可,
> 不需要了解 zedhub 的私有信封。
>
> - JSON-RPC 2.0 规范:https://www.jsonrpc.org/specification
> - MCP 规范:https://modelcontextprotocol.io
>
> 对应源码:`src/zedhub/api.py`(方法注册表,单一事实源)、`rpc.py`、`mcp_server.py`。

## 共同约定

- **只读**:两个入口都只读 Zed 数据库(快照方式,Zed 运行中也可安全调用)。
- **每次调用独立快照**:响应永远基于调用时刻的数据库状态,无缓存、无脏读。
- **datetime 格式**:本地时区 ISO 字符串(与 CLI JSON 信封一致)。
- **payload 形状**:与 CLI 信封 `data` 字段完全一致,三端(CLI/RPC/MCP)数据同源。
- **无鉴权**:面向本机子进程/stdio 场景,不做任何身份验证。

## 1. JSON-RPC 2.0(`zedhub rpc`)

**传输**:line-delimited stdio——stdin 每行一个 JSON-RPC request 对象,stdout
每行一个 response 对象,UTF-8。

- 单行 pipe = one-shot 调用(EOF 后进程退出,退出码 0)
- 连续多行 = 会话式调用,直到 EOF
- 不支持 batch(数组)请求与位置参数(`params` 数组),违反时返回 `-32600`
- notification(无 `id`)按规范静默执行、不回包

### 方法表

| 方法 | 参数 | 返回 |
|---|---|---|
| `rpc.discover` | 无 | OpenRPC 风格服务描述(见下节) |
| `threads.list` | `project?` `agent?` `archived?` `since?` `until?` `search?` `limit?` | thread 数组 |
| `threads.show` | `thread_id`(必填) | 单个 thread |
| `projects` | 无 | 项目统计数组 |
| `stats` | 无 | 全局概览对象 |

### 服务发现:`rpc.discover`

JSON-RPC 2.0 规范本身不含服务发现;zedhub 按 OpenRPC 惯例提供保留方法
`rpc.discover`(https://spec.openrpc.org):一跳拿到全部方法、参数
schema(type/enum/default/required)与描述,调用方(AI agent 或普通程序)
无需读文档即可程序化得知怎么调用。它是纯元数据,**数据库缺失时也可用**。
方法表由 `api.py` 的 METHOD_SPECS 生成——与分发器同一事实源,不会漂移。

```powershell
'{"jsonrpc":"2.0","id":1,"method":"rpc.discover"}' | .\zedhub.exe rpc
```

返回(节选,`result.data` 内):

```json
{
  "openrpc": "1.3.2",
  "info": {"title": "zedhub", "version": "0.1.0"},
  "methods": [
    {
      "name": "threads.list",
      "summary": "List agent threads, newest first.",
      "params": [
        {"name": "archived", "description": "'no' = active only (default), ...",
         "required": false, "schema": {"type": "string", "enum": ["no", "only", "all"], "default": "no"}},
        ...
      ],
      "result": {"name": "data", "schema": {"type": "array"}}
    }
  ]
}
```

参数说明:

| 参数 | 类型 | 说明 |
|---|---|---|
| `project` | string | 项目路径子串匹配 |
| `agent` | string | agent id 精确匹配,如 `opencode` |
| `archived` | string | `no`=仅活跃(默认)/ `only`=仅归档 / `all` |
| `since` / `until` | string | `YYYY-MM-DD` 或 ISO datetime(本地时区) |
| `search` | string | title/agent/id 的大小写不敏感子串 |
| `limit` | int | 结果上限,缺省不限 |
| `thread_id` | string | thread uuid(取自 `threads.list`) |

### 成功响应

```json
{"jsonrpc": "2.0", "result": {"data": ..., "count": 3, "elapsed_ms": 77}, "id": 1}
```

`result` 内:`data` 为方法载荷(形状见 CLI 文档),`count` 为列表条数(非列表
为 1),`elapsed_ms` 为服务端耗时。

### 错误码

| code | 含义 |
|---|---|
| `-32700` | 行不是合法 JSON |
| `-32600` | 非法请求(非对象 / batch / 位置参数 / 缺 `jsonrpc` 字段) |
| `-32601` | 方法不存在 |
| `-32602` | 参数校验失败(类型、枚举、日期格式) |
| `-32603` | 内部错误 |
| `-32000` | 服务端错误(数据库缺失 / schema 不兼容),`error.data.type` 给出异常类型 |
| `-32001` | 资源不存在(如未知 thread id) |

> `rpc.discover` 为保留方法,不会返回 `-32601`;其余以 `rpc.` 开头的方法名
> 视为保留,当前未注册的实现会返回 `-32601`。

### 示例(PowerShell)

```powershell
# one-shot
'{"jsonrpc":"2.0","id":1,"method":"stats"}' | .\zedhub.exe rpc

# 多请求一次管道
@(
  '{"jsonrpc":"2.0","id":1,"method":"threads.list","params":{"agent":"opencode","limit":5}}'
  '{"jsonrpc":"2.0","id":2,"method":"projects"}'
) | .\zedhub.exe rpc
```

> 注意 GBK 控制台直接看 UTF-8 输出可能乱码,落盘查看:
> `... | Out-File -Encoding utf8 out.json`。

## 2. MCP(`zedhub mcp`)

**面向 AI agent 客户端**(Zed / Claude Code / opencode / Cursor 等),stdio
transport,长驻由客户端管理进程生命周期。tool 的参数 schema 由签名自动生成,
`tools/list` 自描述——AI 客户端无需任何文档即可发现并正确调用。

### tool 表(与 RPC 方法一一对应)

| tool | 对应 RPC 方法 |
|---|---|
| `threads_list` | `threads.list` |
| `threads_show` | `threads.show` |
| `projects` | `projects` |
| `stats` | `stats` |

参数与 JSON-RPC 完全同名同义。工具失败(参数错、找不到 thread、数据库缺失)
以 MCP tool error 返回,message 格式 `<异常类型>: <原因>`。

### 客户端接入配置

Zed(`settings.json` 的 `context_servers`):

```json
{
  "context_servers": {
    "zedhub": {
      "command": "C:\\WorkingProjects\\language_projects\\python_projects\\zedhub\\zedhub.exe",
      "args": ["mcp"]
    }
  }
}
```

Claude Code:

```powershell
claude mcp add zedhub -- "C:\WorkingProjects\language_projects\python_projects\zedhub\zedhub.exe" mcp
```

opencode(`opencode.json` 的 `mcp.local`):

```json
{
  "mcp": {
    "local": {
      "zedhub": {
        "type": "local",
        "command": ["C:\\WorkingProjects\\language_projects\\python_projects\\zedhub\\zedhub.exe", "mcp"]
      }
    }
  }
}
```

> 指定非默认数据库时,以上配置的 `args`/`command` 追加 `["--db", "<路径>"]`。

## 实现备注

- 方法注册表 `api.py` 是单一事实源:CLI 信封、RPC、MCP 三端的序列化与参数
  校验都经过它;方法元数据(`METHOD_SPECS`/`PARAM_SPECS`/`PARAM_DOCS`)
  同时驱动 RPC 分发、`rpc.discover` descriptor 与 MCP tool 描述,不会漂移。
- MCP 依赖官方 `mcp` SDK(2.x,`MCPServer`);`zedhub mcp` 为延迟导入,不影响
  其他 CLI 命令的启动速度。
- 现有 CLI 子命令与 JSON 信封**保持不变**,人类用法与既有前端不受影响。
