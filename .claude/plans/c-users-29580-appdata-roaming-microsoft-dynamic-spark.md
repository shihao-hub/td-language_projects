# Alt+C 行为对齐：Codex 未运行时不自动启动

## Context

用户发现 `app_switcher.ahk` 中 Alt+C 在 Codex 未启动时仍会拉起应用，与大多数热键行为不一致。

- **根因**：`ToggleCodex()`（`app_switcher.ahk:348-359`）是专用实现，未运行时显式执行
  `Run('explorer.exe shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App')`；而通用 `ToggleApp()` →
  `ToggleWin(target, runCmd := "")` 在 `runCmd` 为空时未运行即静默返回（`app_switcher.ahk:117-124`）。
- **一致性盘点**：
  - 未运行 → 静默：Alt+1/2/3（Zed、Sublime Merge、Sublime Text）、Alt+A、Alt+D、Alt+F、Alt+R、Alt+W（8 个）
  - 未运行 → 启动：Alt+X（资源管理器）、Alt+T（Tinta）、Alt+C（Codex，本次目标）
- **用户决策**：仅 Alt+C 改为静默，与主流组对齐；Alt+X、Alt+T 保留自动启动。

## 修改

文件：`C:\Users\29580\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\app_switcher.ahk`
（用 Edit 工具原地修改，保持 UTF-8 无 BOM；严禁 PowerShell 重定向/Set-Content 落盘）

1. **`ToggleCodex()` 函数体（约 348-359 行）**：删除未运行时的 Run 分支，未运行交给 `ToggleWin` 静默返回：

   ```ahk
   ToggleCodex() {
       target := 'ahk_class Chrome_WidgetWin_1 ahk_exe ChatGPT.exe'
       ToggleWin(target)
   }
   ```

2. **函数头注释（约 343-347 行）**：删除「未运行 -> 通过 shell:AppsFolder 拉起 MSIX 应用」条目，
   改为「未运行 -> 静默无反应（与 Alt+1/2/3/A/F/R/W 对齐）」。

3. **热键注册处注释（约 389 行）**：`; Alt + C -> Codex 桌面客户端 (OpenAI Codex，进程 ChatGPT.exe；未运行则自动拉起)`
   去掉「未运行则自动拉起」。

4. **不改动** `ToggleWin` 的 `runCmd` 参数（当前无调用方使用，属死参数，避免扩大 diff）。

## 验证

1. 重载脚本（会先终止旧实例再启动，属预期行为）：

   ```
   "C:\Users\29580\AppData\Local\Programs\AutoHotkey\v2\AutoHotkey64.exe" /restart "C:\Users\29580\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\app_switcher.ahk"
   ```

2. 确认脚本无语法错误启动（托盘出现 AHK 图标；若弹报错窗口则检查修改处语法）。
3. 功能测试：
   - 完全退出 Codex（托盘退出，确认无 `ChatGPT.exe` 窗口），按 Alt+C → **无任何反应**，任务管理器无新进程；
   - 手动启动 Codex 后，按 Alt+C → 正常置顶/最小化（抽屉式 Toggle 不受影响）；
   - 抽查 Alt+A / Alt+F 确认重载后其他热键正常。
4. 若热键全部失效：检查是否重载成功、托盘图标是否存在，重新执行 `/restart`。

## 未决问题与阻塞确认清单

- [x] 无——已确认：仅 Alt+C 改为静默，Alt+X / Alt+T 保持自动启动。
