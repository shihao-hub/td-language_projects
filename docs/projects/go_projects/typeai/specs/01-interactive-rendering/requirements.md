# Requirements Document

## Summary

`typeai` 第一期已经提供单进程 REPL、OpenAI 兼容 SSE、session JSON 原子持久化，以及 `reasoning_content` 的原始透传。本次优化把无参数交互升级为 Bubble Tea TUI：思考流默认折叠且可展开；AI 回复按基础 Markdown 在流式过程中渲染；同时补齐滚动、尺寸变化、请求状态和错误呈现。session 持久化语义和既有管理命令保持不变。

## Functional Requirements

- FR-1 无参数且标准输入/输出为 TTY 时，`typeai` 进入单进程 Bubble Tea TUI；不启动守护进程，不改变 `help`、`version`、`schema`、`config` 的既有入口语义。
- FR-2 TUI 提供多轮对话区、输入区、模型/session 状态区和请求状态区；历史对话可滚动，新输出默认跟随底部。
- FR-3 `reasoning_content` 属于当前进程的临时 UI 数据，可按轮折叠；默认折叠，用户可切换展开。展开时只显示有界窗口内的最近内容，避免超长思考流撑爆界面。
- FR-4 AI 回复的 Markdown 在流式接收过程中增量刷新渲染，不需要等整轮结束。基础能力覆盖标题、段落、粗体/斜体、行内代码、fenced code block、有序/无序列表、引用、分隔线和链接。
- FR-5 用户输入内容按纯文本展示，不作为 Markdown 渲染；只有 assistant 回复进入 Markdown 渲染器。
- FR-6 Enter 发送输入，Ctrl+J 插入换行，Ctrl+T 切换思考流展开状态，PageUp/PageDown 和方向键滚动对话区；`/exit`、`/quit` 和 Ctrl+C 结束当前进程。
- FR-7 终端尺寸变化后，文本重新换行，Markdown 渲染缓存按新宽度失效，界面不出现横向滚动。
- FR-8 请求进行中不发起第二个请求；失败时错误保留在 TUI 状态区，已完成的历史轮不回滚，失败轮不写入 session，也不进入后续上下文。
- FR-9 成功轮仍然只持久化 user/assistant 正式回答；schema_version 保持 1，不新增持久化字段，思考流不落盘。

## Non-Functional Requirements

- NFR-1 保持单进程、无后台守护架构；TUI 与 LLM 流式请求运行在同一个 OS 进程内。
- NFR-2 Markdown 重渲染节流，避免每个 SSE 字符都触发全量解析；同一时刻最多一个渲染任务在执行。
- NFR-3 渲染失败时降级为原始文本显示，不得中断请求、破坏 TUI 或写入 session。
- NFR-4 不展示 API Key；`NO_COLOR` 下不使用彩色样式；Markdown 渲染只在本地转换文本，不抓取远程图片或执行 HTML。
- NFR-5 轻量命令仍保持零业务 I/O；`--help` 的暖启动耗时不应因本次依赖明显退化。

## Acceptance Criteria

### AC-1

WHEN 在 Windows TTY 执行无参数 `typeai`，THEN 程序显示单进程 TUI，包含对话区、输入区、模型/session 状态和当前请求状态，且进程列表中没有额外守护进程。

### AC-2

WHEN GLM 返回 `reasoning_content` 增量，THEN 界面默认只显示折叠状态和统计信息，不显示思考正文；成功轮的 session JSON 不包含 `reasoning_content` 或思考文本字段。

### AC-3

WHEN 用户按 Ctrl+T，THEN 当前思考流在展开和折叠之间切换；再次发起新一轮时思考流恢复默认折叠。

### AC-4

WHEN assistant 增量包含 Markdown 标题、列表、代码块、行内样式或链接，THEN 对话区在流式过程中逐步显示对应终端富文本，而不是先输出原始 Markdown 再等待整轮结束才转换。

### AC-5

WHEN 用户输入包含 `#`、`*` 或反引号，THEN 用户消息仍按输入原文纯文本显示，assistant 后续回复才执行 Markdown 渲染。

### AC-6

WHEN 请求失败，THEN TUI 显示稳定业务错误摘要；失败轮不更新 session 文件，下一轮发送的历史仍只包含此前成功轮。

### AC-7

WHEN 终端宽度变化，THEN 当前对话在下一个刷新周期重新换行；已渲染内容不要求横向滚动，旧缓存不按旧宽度复用。

### AC-8

WHEN 执行 `typeai schema`、`--help`、`--version`，THEN 输出契约与新交互一致；`schema` 仍不读取配置、不创建数据目录、不访问网络。

## Out of Scope

- 不做 session resume、列表、搜索、export 和上下文裁剪。
- 不做用户输入的 Markdown 预览或所见即所得编辑器。
- 不做主题配置、完整 Markdown 规范、表格、图片下载、数学公式或语法高亮插件系统。
- 不把思考流写入 session，也不新增持久化 schema。
- 不提供 MCP；既有“终端长交互不适用普通 MCP tools/call”的例外理由保持不变。
