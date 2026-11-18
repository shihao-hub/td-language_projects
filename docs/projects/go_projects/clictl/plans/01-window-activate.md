# clictl 显露/唤起运行中工具窗口（Activate Window）

- 背景：WebUI 与 CLI 当前提供「启动」、「停止」、「定位」（打开所在文件夹），当工具已被拉起并在运行时，若窗口被其他全屏软件遮挡、最小化到任务栏、或者关窗退到了系统托盘，用户往往需要在任务栏反复寻找，缺乏一键将目标窗口唤起置顶的手段。
- 目标：
  1. 在 WebUI 详情页操作栏新增「显露窗口」（或「唤起窗口」）按钮，仅在运行中状态高亮可用；
  2. CLI 同步支持 `clictl activate <name>`（或 `clictl focus <name>`），输出标准 JSON；
  3. 支持 Win32 穿透唤起（绕过 Windows 任务栏闪橙光限制），支持自动还原最小化窗口；
  4. 支持模态/多级弹窗按 Z-Order 顶层连带拉起，主窗口与弹窗协同浮出；
  5. 兼顾“托盘驻留/无可见窗口”状态：优先通过单实例机制敲醒（覆盖 Go Wails 全家桶），并在 Python `zedhub` 中对齐同等无弹窗托盘唤醒能力。

---

## 一、关键决策与机制契约

| 决策点 | 选定方案 | 决策依据 / 备选排除 |
|---|---|---|
| **置顶穿透 API** | `SwitchToThisWindow(hwnd, TRUE)` 优先，辅以 `ShowWindow(SW_RESTORE)` | 排除单纯的 `SetForegroundWindow`（易踩 Windows Foreground Lock 导致任务栏仅闪烁橙光无法弹出） |
| **窗口匹配策略** | 目标 PID + 子进程整树递归快照匹配 | 解决 Wails/Electron/Chrome/包装脚本主进程无窗口、子进程才画界面的脱节问题 |
| **多窗口与弹窗优先级** | 按 Windows 桌面 Z-Order 拾取最顶层的可见有效窗口进行前置 | 依据 Windows 拥有者（Owner）连带规则，激活最上层模态弹窗可安全带起底层主窗口，避免主窗口被模态阻断产生系统警报音（“咚”） |
| **幽灵窗口防御** | 严格校验 `IsWindowVisible` 且过滤长宽为 0 的后台消息哨兵 | 杜绝将隐藏剪贴板监听、透明调度窗口误当成主窗口激活 |
| **托盘驻留（无窗口）处理** | 探测无可见窗口时，触发一次点火触发单实例唤醒（Secondary Launch） | Go Wails 生态内置 `OnSecondInstanceLaunch` -> `ensureMainWindow()`；非单实例工具则返回明确状态提示，绝不盲目多开 |
| **zedhub 生态补齐** | `zedhub-gui` 增加 Windows Named Event 监听与唤醒，去弹窗化 | 将 `zedhub` 从“弹 MessageBox 提示”升级为“自动触发 `show_requested.set()` 重建并前置窗口”，与 Go 项目看齐 |

---

## 二、架构与分层设计

### 1. 后端底层（`internal/runner/window_windows.go`）
- 结构体定义：
  ```go
  type WindowInfo struct {
      HWND    uintptr
      PID     uint32
      Title   string
      IsIconic bool
  }
  ```
- 核心功能：
  1. `CollectProcessTree(rootPIDs []int) []int`：通过 Toolhelp32Snapshot 收集根 PID 及其全部存活子进程。
  2. `FindTopWindowsForPIDs(pids []int) []WindowInfo`：`EnumWindows` 枚举全部顶层窗口，过滤不可见、尺寸为 0x0 的窗口，按 Z-Order 前后顺序返回匹配的窗口列表。
  3. `ActivateWindow(hwnd uintptr) error`：
     - 若 `IsIconic(hwnd)`，调用 `ShowWindow(hwnd, SW_RESTORE)` 还原最小化；
     - 调用 `SwitchToThisWindow(hwnd, true)` 穿透前台锁定，强制前置并赋予输入焦点。

### 2. 业务逻辑层（`internal/service/process.go`）
- 方法：`Activate(name string) (*ActivateResult, error)`
- 执行时序：
  ```
  1. 查询 tool 详情并探活当前 running_pids；
  2. 若 running_pids 为空 -> 报错 ErrNotRunning (400)；
  3. 收集主进程 + 子进程 PID 列表；
  4. FindTopWindowsForPIDs 查找可用桌面窗口；
  5. 分支判断：
     ├─ 找到 1 个或多个可见窗口：
     │  对 Z-Order 最顶层的窗口执行 ActivateWindow；
     │  返回 status = "activated", windows_found = len(windows)
     └─ 未找到任何可见窗口（可能退入系统托盘）：
        执行一次受控 Secondary Launch（走已有 start 逻辑）：
        - 若属于 Wails/SingleInstance 程序，托盘老实例被唤醒重建窗口并退出子进程；
        - 返回 status = "woken_up" 或 "in_tray"
  ```

### 3. API 层（`internal/api/server.go`）
- 注册端点：`POST /api/tools/{name}/activate`
- 响应形状：
  ```json
  {
    "ok": true,
    "data": {
      "name": "typeai-gui-dev",
      "status": "activated",
      "pids": [35284],
      "windows_found": 1,
      "message": "已将窗口置顶显示"
    }
  }
  ```
- 错误映射：未运行返回 `tool_not_running`（400）。

### 4. CLI 层（`internal/cli/commands.go`）
- 新增命令：`clictl activate <name>`（别名 `focus`）
- 行为：请求 API 或直接调 service，始终输出结构化 JSON，支持 `--pretty`。

### 5. 前端 WebUI（`internal/web/assets`）
- **操作栏按钮布局**：
  在 `detail-actions` 中插入按钮（置于「启动/后台启动」之后，「停止」之前）：
  ```html
  <button class="btn btn-primary" id="startBtn">启动</button>
  <button class="btn" id="startAltBtn" hidden>后台启动</button>
  <button class="btn" id="activateBtn" title="将已启动的窗口恢复并置顶到最前">显露窗口</button>
  <button class="btn" id="stopBtn">停止</button>
  <button class="btn" id="revealBtn">定位</button>
  <button class="btn" id="metaBtn">meta</button>
  <button class="btn btn-danger" id="deleteBtn">删除</button>
  ```
- **交互与状态联动**：
  - 当工具处于未运行状态：`activateBtn.disabled = true`；
  - 当工具处于运行中状态：`activateBtn.disabled = false`；
  - 点击时带 `withBusy` 状态保护；
  - Toast 反馈：
    - 成功置顶：`已置顶窗口`；
    - 托盘唤醒：`已唤醒托盘窗口`；
    - 托盘无唤醒支持：`该程序在系统托盘运行，请在右下角托盘点击唤出`。

### 6. Python 生态对齐（`python_projects/zedhub`）
- 修改 `zedhub/gui/app.py`：
  - 主实例创建 Windows 命名事件（`zedhub-gui-{channel}-wake`）；
  - 启动后台监听线程：当事件置起时，触发 `_show_window()` -> `show_requested.set()` 重建窗口；
  - 第二个实例如果 `acquire()` 锁失败，不再调用 `_message_box`，而是直接 `SetEvent` 激活老实例并秒退。

---

## 三、任务分解（Tasks）

- [ ] **Task 1: Win32 窗口枚举、过滤与置顶核心库**
  - 在 `go_projects/clictl/internal/runner/` 新增 `window_windows.go`（以及非 Windows 空实现 `window_other.go`）；
  - 实现 `SwitchToThisWindow`、`EnumWindows`、`GetWindowThreadProcessId`、`IsIconic`、`ShowWindow` 动态加载；
  - 实现进程树递归聚合与 Z-Order 顶层有效窗口挑选；
  - 补充针对最小化、普通遮挡、0x0 隐藏窗口的单元测试与逻辑验证。

- [ ] **Task 2: Service 逻辑与 REST API 端点实现**
  - 在 `internal/service/process.go` 增加 `Activate(name string)` 方法；
  - 在 `internal/api/server.go` 注册 `POST /api/tools/{name}/activate`；
  - 编写 `server_test.go` 覆盖正常唤起、未运行报错、无窗口分支。

- [ ] **Task 3: CLI 命令行支持 `activate`**
  - 在 `internal/cli/commands.go` 增加 `activate` / `focus` 子命令；
  - 保证 JSON 包络一致性与退出码规范（未运行退出码 1，成功退出码 0）。

- [ ] **Task 4: WebUI 界面新增「显露窗口」按钮与状态联动**
  - `index.html`：在详情页按钮区增加 `#activateBtn`；
  - `app.js`：添加按钮点击事件、绑定 `/api/tools/{name}/activate` 调用；根据 `running` 状态切换按钮可用性；
  - `style.css`：微调详情按钮排布响应式样式（防止按钮过多换行错位）。

- [ ] **Task 5: 对齐 `zedhub` 桌面壳二次启动托盘唤醒**
  - 在 `python_projects/zedhub/src/zedhub/gui/app.py` 中引入命名事件机制；
  - 消除二次启动时的弹窗阻断，实现后台静默唤醒。

- [ ] **Task 6: 构建与多场景实机验证**
  - 编译 `clictl-gui-dev.exe` 与 `clictl-cli-dev.exe`；
  - 场景 1：普通 GUI 窗口（如 `typeai`、`notepad`）被遮挡时一键置顶；
  - 场景 2：窗口被最小化到任务栏时一键恢复并置顶；
  - 场景 3：模态对话框处于前台时一键连带带出；
  - 场景 4：Wails 工具关窗退到托盘时，点击按钮成功二次唤醒重新建窗；
  - 场景 5：`zedhub` 退到托盘后，点击按钮顺畅唤醒。
