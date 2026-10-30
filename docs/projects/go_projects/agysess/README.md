# agysess —— 轻量级 agy CLI 会话管理与 Windows Terminal 联动工具

> 项目路径：`go_projects/agysess`  
> 规范依据：[`docs/projects/go_projects/CLI 工具开发标准.md`](../CLI%20工具开发标准.md)  
> 实施计划：[`docs/projects/go_projects/agysess/plans/01-agysess-implementation-plan.md`](plans/01-agysess-implementation-plan.md)  
> 数据存储：`%APPDATA%\language_projects\agysess\`  

---

## 1. 建设背景与价值

在日常开发与 AI 辅助编程中，Google Antigravity 官方生态存在两个两极化的体验盲区：
1. **官方桌面端过重**：Electron + `language_server.exe` 启动常驻 1~1.5GB 内存，多开窗口极易造成系统卡顿与资源浪费；
2. **`agy` CLI 虽轻但缺管理视图**：`agy` CLI 非常快速，但管理会话极为繁琐，难以一眼浏览会话历史，且多个会话对应的终端窗口散落各处，无法集中定位与回收。

`agysess` 采用纯 Go 语言 + 原生轻量 GUI **Fyne**（`fyne.io/fyne/v2`）打造，彻底摆脱 Chromium / WebView2 运行时负担，常驻内存仅数十 MB，提供：
- 会话列表结构化多维查询、排序与关键字搜索；
- 会话归档、解档、自定义标题覆盖与独立备注；
- Windows Terminal 深度联动（一键在新标签页/新窗口打开会话或新建会话）；
- 活跃运行中 agy 进程实时探活与面板高亮；
- 面板一键关窗（树级安全终止进程，回收终端与系统资源）。

---

## 2. 能力契约与多壳架构

严格遵循《CLI 工具开发标准》v1.0：
- **Service 核心驱动**：`internal/service` 作为统一业务内核，CLI 壳与 GUI 壳为外部适配器；
- **标准包络输出**：`--json` 输出稳定的 `{"ok": true, "data": ...}` 或 `{"ok": false, "error": ...}`；
- **零 I/O 极速契约反射**：`<prog> schema` 与 `<prog> --schema` 离线输出 JSON Schema，严禁触发数据库连接与 I/O；
- **数据目录隔离**：自有数据仅存放在 `%APPDATA%\language_projects\agysess\`，严禁污染 `~/.gemini` 原生数据库；
- **只读并发安全**：以 `mode=ro` 方式读取 `conversation_summaries.db`，严格显式声明字段，禁止 `SELECT *`。

---

## 3. CLI 命令清单

| 命令 | 用途 | 关键参数 | 机器输出 |
|---|---|---|---|
| `agysess list` | 列表查询与过滤 | `-q` 关键词, `-p` 项目, `-a` 显示全部, `--archived` 仅归档, `--sort` 排序, `--limit` | `--json` |
| `agysess show <id>` | 查看单个会话详细信息 | `<session-id>` | `--json` |
| `agysess archive <id>` | 归档指定会话 | `<session-id>` | `--json` |
| `agysess unarchive <id>` | 取消归档指定会话 | `<session-id>` | `--json` |
| `agysess rename <id> <title>` | 设置会话自定义标题 | `<session-id>`, `<title>` | `--json` |
| `agysess note <id> <notes>` | 更新会话备注信息 | `<session-id>`, `<notes>` | `--json` |
| `agysess open <id>` | 在 WT 中打开/恢复会话 | `<session-id>`, `-w` 独立窗口 | `--json` |
| `agysess new` | 在 WT 中拉起新会话 | `-d` 目录, `-p` 项目, `-m` 模型, `--mode` 模式, `-i` 提示词 | `--json` |
| `agysess running` | 探测当前活跃运行中的进程 | 无 | `--json` |
| `agysess kill <id>` | 关闭会话终端窗口/进程 | `<session-id>` | `--json` |
| `agysess schema` | 零 I/O 导出完整 JSON Schema | 无 | 原生 JSON |
| `agysess gui` | 唤起 Fyne 原生桌面管理面板 | 无 | 启动 GUI |

---

## 4. GUI 面板功能

- **搜索与视图**：实时关键词搜索、所属项目下拉过滤、活跃/全部/已归档视图快速切换、多维排序；
- **列表卡片**：直观展示会话标题、步数徽章、相对修改时间、工作区目录与内容摘要；
- **状态高亮**：运行中会话显示 `● [RUNNING: PID]`，并显露红色「关闭窗口」按钮；
- **新建与编辑**：图形化弹窗快速选择目录新建会话，或为旧会话补充自定义备注与标题。

---

## 5. 构建与产物

项目提供 `scripts/build.py`（PEP 723 规范）：
```powershell
python go_projects/agysess/scripts/build.py
```
- `bin/agysess.exe`：全功能控制台二进制文件；
- `bin/agysess-gui.exe`：带 `-H=windowsgui` 的无黑框桌面程序。
