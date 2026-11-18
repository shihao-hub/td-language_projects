# Cursor YOLO 模式（免批准自动运行）调研

> 问题：Cursor 里如何开 YOLO 模式，总是让我批准很烦。
> 调研日期：2026-10-07；来源均为 Cursor 官方文档一手资料。

## 结论（先看这个）

1. 入口：`Settings > Agents > Approvals & Execution`，在 **Run Modes** 三选一：`Auto-review` / `Allowlist` / `Run Everything`。
2. 真正的 YOLO = **`Run Everything`**：所有 tool call 自动跑，无沙箱、无分类器、零弹窗，但官方明确说“你接受风险才用”。
3. 折中推荐 = **`Auto-review`**（官方默认推荐）：白名单命令直接跑，其余 shell 进沙箱，能进沙箱就直接跑，进不了才走后端分类器判定，分类器拦不住/认为有必要时才会弹批准框。
4. 即使 YOLO 了，以下三类**硬保护不受 Run Mode 控制**，照样会弹（这是“总是让我批准”最常见的坑）：
   - Browser 工具保护、文件删除保护、工作区外文件保护。

来源：https://cursor.com/docs/agent/security/run-modes（Pick a mode / Other protections 两节）；https://cursor.com/docs/agent/security（First-party tool calls 节：终端命令默认要批准，用 Run Modes 放行）。

## 三种模式对照

| 模式 | 不经批准直接跑什么 | 沙箱 | 分类器 | 适合谁 |
|---|---|---|---|---|
| Auto-review（推荐默认） | 白名单调用直接跑；其余 shell 尽量进沙箱跑；进不了沙箱的走分类器 | 对 shell 生效 | 有 | 想要少弹窗 + 高风险前有人把关 |
| Allowlist | 只有白名单里的动作免批；开沙箱后，部分 shell 可在沙箱跑 | 可选（仅 shell） | 无 | 想要确定性行为，只信几个固定重复动作 |
| Run Everything | 全部自动跑 | 无 | 无 | 接受风险、要零弹窗 |

来源：同上 Run Modes 页 `Pick a mode` 表格原文。

## 为什么开了自动还是弹？排查清单

1. **模式没切对**：留在 Auto-review/Allowlist 下，非白名单、高风险调用本来就会弹。要零弹窗必须切 Run Everything。
2. **撞上硬保护**：删文件（含 `rm`）、工作区外创建/改/删文件、Browser 工具调用，任何模式下都可能弹。来源：Run Modes 页 `Other protections`。
3. **shell 进不了沙箱**：需要完整网络、写工作区外、提权操作的命令无法用沙箱，会转分类器，分类器 block 后 agent 若坚持要做就会弹批准框。来源：`How Auto-review works`。
4. **Read Access = Workspace**：工作区外文件读取要批准（批准卡显示完整路径和原因），Grep 会跳过区外文件。Run Everything 下该设置隐藏（不生效）。来源：`Read access` 节。需 Cursor 3.23+。
5. **MCP / Fetch**：MCP 连接本身要批一次，之后每个 tool 调用默认逐个批，需另配 MCP allowlist 才能预放行；Auto-review 对 shell/MCP/Fetch 按“沙箱→分类器”顺序判定。来源：https://cursor.com/docs/agent/security（Third-party tool calls）、Run Modes（How Auto-review works）。
6. **团队策略覆盖个人**：Team dashboard 可限定可用模式、沙箱联网规则、Read 策略；定义了团队级 Auto-review 配置后，本地 `permissions.json` 被忽略。来源：`Team controls` / `Configuring Auto-review`。
7. **Auto-review 置灰**：企业版模型访问控制里把 Claude 4.5 Haiku 禁了会导致 Auto-review 不可用（分类器用 Gemini 3.5 Flash Lite，fallback 是 Claude 4.5 Haiku）。去 Team Settings → Models 放开，重开 Cursor。来源：`Auto-review classifier requirements`。

## 配置方法

### A. 切 YOLO（Run Everything）

`Settings > Agents > Approvals & Execution > Run Everything`。无额外文件可配。

### B. 半自动（Auto-review 微调，推荐）

- 不想每次都批、但高风险想留一手时用。不用配也能跑得不错；想强制某些必审，用自然语言写 `permissions.json`：
- 位置：`~/.cursor/permissions.json`（整机）或 `<project>/.cursor/permissions.json`（单项目，可提交共享）；两处并存则合并；团队有全局配置时本地文件被忽略。
- Schema：

```json
{
  "autoRun": {
    "allow_instructions": [],
    "block_instructions": [
      "Every AWS CLI command should go through approval first."
    ]
  }
}
```

- 偷懒写法：直接跟 Cursor agent 说“以后所有 AWS CLI 命令先过审批”，让它帮你改这个文件。来源：`Configuring Auto-review`。
- 分类器是跑在 Cursor 后端的，判定时可在本机做只读 `ReadFile/Grep/Glob/ListDir`（如读你要跑的脚本）。来源：`How Auto-review works`。

### C. 沙箱网络（`sandbox.json`，和 permissions.json 分工不同）

- `permissions.json` 管“自动跑还是送审”；`sandbox.json` 管“沙箱里能碰什么”（网络域名、额外可读写路径、临时目录、构建缓存）。来源：`permissions.json and sandbox.json do different jobs`。
- 位置：`~/.cursor/sandbox.json`（整机）或 `<project>/.cursor/sandbox.json`（单项目，项目优先，团队策略和硬规则在其上）。
- 沙箱默认：工作区内可读写；`.git/config`、`.git/hooks`、`.vscode`、`.cursorignore` 等受保护；网络默认 blocked，按 Network 模式 + `sandbox.json` allowlist 放行；默认模式是 `sandbox.json + Defaults`（常用包管理器域名已内置，约上百个如 `*.githubusercontent.com、registry.npmjs.org、pypi.org、proxy.golang.org` 等）。来源：`Sandboxing / Network access`。

### D. Windows 用户注意

- 沙箱实现细节官方只写了 macOS（Seatbelt via `sandbox-exec`，需 Cursor v2.0+）和 Linux（user namespace，沙箱内 `id -u` 变 0，用 `CURSOR_ORIG_UID/GID` 取真实用户）；Windows 行为文档未展开，PowerShell 下“总是批准”多半是命令走不了沙箱 → 只能走分类器/弹窗。来源：`How sandboxing works on your platform / Environment variables`。
- 终端主题太花（如 p10k）会截断内联输出，`CURSOR_AGENT` 环境变量可用来在 Cursor 会话里降级 prompt。来源：https://cursor.com/docs/agent/terminal。

## 版本变迁

- 3.5（2026-05-22）：`Ask Every Time` 废弃，新用户不可选（用空 Allowlist 等效）；`Run in Sandbox` 并入 Allowlist+沙箱。
- 3.6（2026-05-29）：Auto-review 上线，成为推荐默认。
- 3.23（2026-10-01）：Read Access 新增 Workspace 模式 + Read Allowlist + 团队 Read 策略。
- Cloud Agents 不用 Run Modes（独占机器，不问你）。来源：Run Modes 页 `Changelog` 及文末说明。

## 附：网络访问能否修改（2026-10-07 追加）

> 来源：https://cursor.com/docs/reference/sandbox（sandbox.json Reference）、https://cursor.com/docs/agent/security/run-modes（Network access）。

- 能改，但**只对“进沙箱的命令”生效**，改法是写 `sandbox.json` 的 `networkPolicy`，不是改 Run Mode 下拉框。
- 你截图已是 `Run Everything`：官方写明“without sandboxing”，即**无沙箱、网络全开**，`sandbox.json` 的网络限制此时不生效。想在 YOLO 的同时限网，得退回 `Allowlist + 开沙箱`（或 Auto-review），再用 `networkPolicy` 收紧。
- 三档网络模式（Settings 或 sandbox.json）：`sandbox.json Only`（仅 allowlist 域名）/ `sandbox.json + Defaults`（默认，allowlist + Cursor 内置上百个包管理器域名）/ `Allow All`（沙箱内也不限网）。
- `networkPolicy` 写法：`default: deny|allow` + `allow[] / deny[]`，支持精确域名、`*.example.com` 通配、CIDR；`deny` 永远优先；内网段（10/172.16/192.168/127、169.254.169.254、::1/fe80/fc00）默认防 SSRF blocked；只匹配域名/IP，URL 路径忽略。
- 全放行示例：`{ "networkPolicy": { "default": "allow" } }`；白名单示例：`{ "networkPolicy": { "default": "deny", "allow": ["registry.npmjs.org", "pypi.org", "*.githubusercontent.com"] } }`。
- 文件位置：`~/.cursor/sandbox.json`（整机）/ `<project>/.cursor/sandbox.json`（单项目优先）；allow 合并（团队有 allowlist 则团队替换本地），deny 恒合并，`default` 取更严的 `deny`。
