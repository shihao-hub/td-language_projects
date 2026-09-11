# Go CLI + JSON 输出模式参考

> 实例项目：`go_projects/clictl`。本文提炼其"CLI 骨架 + JSON 输出"的通用实现模式，其他 CLI 项目可直接参考套用，与 clictl 的业务（exe 注册/启动记账）无关。

## 这套模式解决什么问题

传统 CLI 工具把人类可读文本直接打到 stdout，导致：

- 脚本/管道消费时要写脆弱的文本解析（正则、split）
- GUI、AI 客户端想接入就得另起一套 API
- 错误信息没有结构，无法按错误码编程处理

解法（源自 lark-cli 的 CLI/GUI 分离思想）：**stdout 永远输出合法 JSON**，人读体验交给 `--pretty` 开关。这样同一命令行既是人用工具，也是机器 API。

## 一、JSON 包络：两种形状，全部出口统一

```json
// 成功
{"ok":true,"data":...}
// 失败
{"ok":false,"error":{"code":"conflict","message":"该 name 已被其他工具使用"}}
```

实现要点：**所有输出走同一个出口函数**，禁止业务代码直接 `fmt.Println`。

```go
// output.go —— 可整体复用
var Pretty bool // 全局开关：--pretty 时缩进输出

func Emit(data any) { // 成功包络
	writeJSON(map[string]any{"ok": true, "data": data})
}

func Fail(code, msg string) { // 失败包络 + exit 1
	writeJSON(map[string]any{"ok": false, "error": map[string]string{"code": code, "message": msg}})
	os.Exit(1)
}

func FailStderr(code, msg string, exitCode int) { // 失败包络走 stderr + 指定退出码
	b, err := marshal(map[string]any{"ok": false, "error": map[string]string{"code": code, "message": msg}})
	if err == nil {
		fmt.Fprintln(os.Stderr, string(b))
	}
	os.Exit(exitCode)
}

func marshal(payload any) ([]byte, error) {
	if Pretty {
		return json.MarshalIndent(payload, "", "  ")
	}
	return json.Marshal(payload)
}

func writeJSON(payload map[string]any) {
	b, err := marshal(payload)
	if err != nil { // 序列化失败兜底：手写最小错误 JSON，绝不 panic
		fmt.Println(`{"ok":false,"error":{"code":"internal","message":"JSON 序列化失败"}}`)
		os.Exit(1)
	}
	fmt.Println(string(b))
}
```

细节：

- `Emit(nil slice)` 会输出 `null`，空列表要初始化为 `[]T{}` 才输出 `[]`
- Go 的 `json.Marshal` 自动做 HTML 转义（`<` → `\u003c`），输出仍合法，介意可加 `json.Encoder.SetEscapeHTML(false)`
- `Fail` 内部直接 `os.Exit(1)`，调用方写 `Fail(...); return 1` 只是给编译器看的

## 二、stdout/stderr 纪律：两类命令两种策略

| 命令类型 | 错误 JSON 走哪 | 理由 |
|---|---|---|
| 管理命令（add/list/...） | **stdout** | stdout 永远是合法 JSON，消费方只需解析一个流 |
| 透传命令（`run xxx`） | **stderr** | stdout 只属于子进程；前置校验失败发生在子进程输出之前，走 stderr 不污染 |

这就是 `Fail`（stdout）与 `FailStderr`（stderr + 自定义退出码）分开的原因。

## 三、退出码语义

```
管理命令：  0 成功 / 1 失败
透传命令：  = 子进程退出码（原样透传）；未注册/文件失效 = 127（借 shell "not found" 惯例）
帮助/版本：  0
```

入口用 `os.Exit(cli.Run(os.Args[1:]))`，让 `Run` 返回退出码而不是到处 `os.Exit`——透传命令必须这样做（退出码是动态的子进程码）。

## 四、错误码体系：领域错误 → JSON code 单点映射

不要在业务代码里到处拼 code 字符串。定义领域错误类型，出口处统一映射：

```go
// store 层：错误自带 code
type MetaError struct{ Code, Message string } // Code 就是 JSON 错误码
type ConflictError struct{ Field string }     // "name" / "path"
var ErrNotFound = errors.New("tool not found")

// cli 层：唯一映射点
func failFromErr(prefix string, err error) {
	var metaErr *store.MetaError
	if errors.As(err, &metaErr) {
		Fail(metaErr.Code, metaErr.Message)
		return
	}
	var confErr *store.ConflictError
	if errors.As(err, &confErr) {
		Fail("conflict", "该 "+confErr.Field+" 已被占用")
		return
	}
	if errors.Is(err, store.ErrNotFound) {
		Fail("not_found", prefix+": 未找到该工具")
		return
	}
	Fail("internal", prefix+": "+err.Error())
}
```

好处：错误码清单一目了然，新错误类型只改一个函数。

## 五、Go 标准库 flag 的三个坑（clictl 全踩过）

### 坑 1：遇到第一个位置参数就停止解析

`clictl add path --name N` 这种混合顺序下，`flag.Parse` 见到 `path` 就停，后面的 flag 全进位置参数。解法：先手工分离，再喂给 flag：

```go
// splitFlags 把 args 拆成 (flag 段, 位置参数段)。
// 约定：所有 flag 均带值（--key value 或 --key=value），无布尔 flag。
func splitFlags(args []string, known map[string]bool) (flags, positional []string) {
	for i := 0; i < len(args); i++ {
		a := args[i]
		if a != "-" && strings.HasPrefix(a, "-") {
			name := strings.TrimLeft(a, "-")
			if strings.Contains(name, "=") {
				flags = append(flags, a) // --key=value 自带值
				continue
			}
			if known[name] && i+1 < len(args) {
				flags = append(flags, a, args[i+1]) // --key value
				i++
				continue
			}
			flags = append(flags, a) // 未知/缺值，交给 flag.Parse 报错
			continue
		}
		positional = append(positional, a)
	}
	return flags, positional
}

// 用法
flags, positional := splitFlags(args, map[string]bool{"name": true, "desc": true, "meta": true})
fs.Parse(flags) // positional 就是位置参数
```

### 坑 2：默认 usage 输出污染 stdout

flag 包遇到非法参数会往 stderr 打 usage 文本。解法：`fs.SetOutput(io.Discard)`，统一走 JSON 错误。

### 坑 3：`-h/--help` 被当解析错误

用户敲 `-h` 时 flag 返回 `flag.ErrHelp`。捕获它输出 JSON 帮助而不是报错：

```go
func parseFlags(fs *flag.FlagSet, flags []string) bool {
	if err := fs.Parse(flags); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			EmitHelp() // 帮助也是 JSON
			return false
		}
		Fail("bad_args", fs.Name()+": "+err.Error())
		return false
	}
	return true
}
```

帮助数据也走 `Emit`（usage + commands 表 + global_flags），子命令级 `-h` 和顶层 `help/-h/--help`、无参数三种入口都指向它。

## 六、--pretty 全局开关与透传豁免

`--pretty` 可出现在子命令前后，但**透传命令的参数段必须原样留给子进程**：

```go
cmd, rest := args[0], args[1:]
if cmd != "run" {
	rest = stripPretty(rest) // 非 run：过滤掉 --pretty 并置位 Pretty
}
```

| 命令 | `--pretty` 归属 |
|---|---|
| `tool --pretty list` | 工具自身（缩进输出） |
| `tool list --pretty` | 工具自身 |
| `tool run foo --pretty` | **子进程 foo** |

## 七、目录结构建议

```
cmd/<name>/main.go        # 入口：os.Exit(cli.Run(os.Args[1:]))
internal/cli/output.go    # Emit/Fail/marshal —— JSON 出口唯一
internal/cli/commands.go  # 子命令分发 + 各命令实现
internal/store/           # 业务存储（错误类型自带 code）
```

## 八、Windows 注意事项

- **PowerShell 5.1 传 JSON 参数**：`--meta '{\"source\":\"go\"}'`（用 `\"`，CRT 才能还原引号）；PowerShell 7 无此问题
- **控制台中文**：输出是 UTF-8，旧 conhost 按 GBK codepage 显示会乱码，Windows Terminal 或 `chcp 65001` 正常——这是终端配置问题，不要为此改输出编码
- **修改含中文的源文件**：用编辑工具而非 PowerShell `Set-Content`（PS 5.1 按 ANSI 读写会毁掉 UTF-8 中文，clictl 踩过）

## 迁移清单（新项目套用时）

1. 抄 `output.go` 全文（Emit/Fail/FailStderr/marshal/writeJSON + Pretty 变量）
2. 定义领域错误类型 + `failFromErr` 单点映射
3. 入口 `os.Exit(cli.Run(...))`，命令函数返回退出码
4. 抄 `splitFlags`/`parseFlags`/`newFlagSet`（io.Discard）
5. 透传类命令：错误走 stderr、退出码透传、参数段不过滤全局 flag
6. 帮助/版本也是 JSON，exit 0
