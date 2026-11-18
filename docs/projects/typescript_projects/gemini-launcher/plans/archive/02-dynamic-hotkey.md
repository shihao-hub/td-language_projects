# Plan: gemini-launcher 动态获取 Chrome Gemini 快捷键

## 概述

**问题陈述**：`host/host.py` 硬编码模拟 `Alt + G`；用户在 `chrome://settings/ai/gemini` 改快捷键后扩展即失效。目标：host 动态读取 Chrome 实际配置的热键并按其模拟，扩展侧顺带展示当前生效热键。

**需求**（澄清确认）：
- 读取失败 / `launcher_enabled=false` / 热键值解析失败时：回退硬编码 Alt+G 并记日志（用户决策 1=a）
- 解析范围：修饰键（Alt/Ctrl/Shift/Win）+ 字母/数字/F1-F24，超出范围回退 Alt+G（用户决策 2=a）
- 扩展侧展示当前生效热键（tooltip 方式），host 协议新增消息（用户决策 3=b）

**背景**（本机只读调研实证）：
- 热键存储位置：`%LOCALAPPDATA%\Google\Chrome\User Data\Local State`（浏览器级 JSON），键 `glic.launcher_enabled: true`、`glic.launcher_hotkey: "Alt+G"`；值为 Chromium accelerator 记法（`修饰键+键名`，`+` 分隔）
- 两个 profile 的 `Preferences` 中 `glic` 节均无 `launcher_hotkey`，无 profile 级覆盖
- Chrome 修改设置后 Local State 非即时落盘（ImportantFileWriter 有约 10s 时滞），按次触发读取 + mtime 缓存即可覆盖
- 现有时序机制（`press_alt_g` 的扫描码 + 0.02/0.03s 间隔）与修饰键无关，泛化即可复用
- SendInput 注入事件同样经过 Chrome 的全局热键处理路径，换组合键行为不变

**方案**：
```
[扩展点击] → {action:"trigger"} → host 读 Local State(mtime 缓存)
    → glic.launcher_hotkey 解析成功 → press_hotkey(修饰键VK[], 键VK)
    → 任一环节失败 → 回退 press_hotkey([VK_MENU], VK_G) + 记日志
[响应] 带 enabled/hotkey/source → 扩展 chrome.action.setTitle 展示
[SW 启动/新端口] → {action:"get_hotkey"} 预热刷新 tooltip
```

## 任务分解

- [x] Task 1: host 增加 Local State 读取与热键解析纯函数
  - 文件：`typescript_projects/gemini-launcher/host/host.py`
  - 实现：`read_glic_config()` 读 Local State 并 json 解析，返回 `(enabled, hotkey_str)`，mtime 缓存避免每次点击重解析，异常返回 None；`parse_accelerator(s)` 按 `+` 拆分，Alt/Ctrl/Shift/Win→0x12/0x11/0x10/0x5B，末段字母 A-Z→0x41 起、数字 0-9→0x30 起、F1-F24→0x70-0x87，无法解析返回 None
  - 验证：项目根运行 `uv run python -c "import sys; sys.path.insert(0, 'host'); import host; print(host.parse_accelerator('Alt+G')); print(host.parse_accelerator('Ctrl+Shift+K')); print(host.parse_accelerator('Alt+F5')); print(host.parse_accelerator('Alt+Foo')); print(host.read_glic_config())"`，预期依次 `([18], 71)`、`([17, 16], 75)`、`([18], 116)`、`None`、`(True, 'Alt+G')`
  - Demo：能在 REPL 中看到本机真实配置被正确解析出来

- [x] Task 2: host 泛化按键模拟并接入 trigger/get_hotkey 协议（依赖 Task 1）
  - 文件：`typescript_projects/gemini-launcher/host/host.py`
  - 实现：`press_alt_g` 改造为通用 `press_hotkey(modifier_vks, key_vk)`（修饰键依次按下→键按下/抬起→修饰键逆序抬起，沿用现有扫描码与时序常量）；trigger 处理改为「read_glic_config → parse_accelerator → 成功用动态值，任一失败回退 [VK_MENU]+VK_G」，日志记录动态值或回退原因；新增 `get_hotkey` action；两种响应统一携带 `enabled`（bool）、`hotkey`（实际生效值或 null）、`source`（`dynamic`|`fallback`）
  - 验证：`uv run build_exe.py` 编译通过并生成 `host/gemini_host.exe`；重载 Native Host 后点扩展图标，Gemini 面板弹出且 `host.log` 出现 `using dynamic hotkey Alt+G`
  - Demo：点击扩展图标 → 面板照常弹出，日志显示读取到的动态热键与来源

- [x] Task 3: 扩展 tooltip 显示当前生效热键（依赖 Task 2 的协议）
  - 文件：`typescript_projects/gemini-launcher/extension/background.js`
  - 实现：`getPort()` 新建端口后发送 `{action:"get_hotkey"}`；新增 `chrome.runtime.onStartup` 预连接（tooltip 的 setTitle 不跨浏览器会话持久，会话启动时刷新）；`port.onMessage` 统一处理：`enabled && source==="dynamic"` → title `Gemini (Alt+G)`；`enabled && source==="fallback"` → `Gemini (Alt+G，默认回退)`；`enabled===false` → `Gemini（未启用快捷键）`；trigger 响应同样带热键信息，每次点击顺带刷新
  - 验证：`chrome://extensions` 重载扩展后悬停图标，tooltip 显示 `Gemini (Alt+G)`
  - Demo：悬停扩展图标即可看到当前生效热键

- [x] Task 4: manifest 版本号与 README 文档同步
  - 文件：`typescript_projects/gemini-launcher/extension/manifest.json`、`typescript_projects/gemini-launcher/README.md`
  - 实现：manifest `version` → `1.1.0`；README 架构节补动态热键流程（Local State 路径、`glic.launcher_hotkey`、回退策略、tooltip 行为、「修改热键后约 10s 内落盘」的时滞说明）；「快速安装与配置」第 4 步改为「快捷键任意组合均可，扩展自动适配，默认/回退值为 Alt+G」
  - 验证：manifest 为合法 JSON（重载扩展无报错）；按 README 步骤可完整走通新流程
  - Demo：文档与实际行为一致

**端到端验收**（需用户配合，执行完 Task 1-4 后询问）：在 `chrome://settings/ai/gemini` 把「键盘快捷键」改为 `Alt + K`，等约 15s 后点扩展图标：面板弹出、`host.log` 显示 `Alt+K`、tooltip 变为 `Gemini (Alt+K)`，随后改回 `Alt + G`。

## 实施说明（2026-10-02 执行）

- Task 1/2/4 的验证均已在执行中完成：解析函数输出与预期完全一致；`get_hotkey` 协议经管道喂帧实测，响应 `{'enabled': True, 'hotkey': 'Alt+G', 'source': 'dynamic'}`；manifest 1.1.0 合法。
- 编译时旧 exe 被两个 Chrome 常驻 host 进程锁定，已终止（扩展下次点击自动重连）后重建成功。
- Task 3 实际实现额外加了 `chrome.runtime.onInstalled` 预取（扩展重载即刷新 tooltip，`onStartup` 只覆盖浏览器会话启动）。
- 点击触发的端到端验证（含改键 Alt+K 实测）需在用户 Chrome 中重载扩展后进行，待用户执行。

---

**最后更新**：2026-10-02
**作者**：AI & User
**版本**：v1.1
