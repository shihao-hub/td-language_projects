---
name: ai-agent-approval-modes
description: 当用户问「有没有插件能让 agent 每次动手前都先问我」「不要 plan 模式，我要逐步批准」「DSH/Claude Code/Codex/OpenCode/Cline 怎么开逐动作确认」时使用，也用于排查「为什么 agent 完全没弹确认窗」。
---

# AI Agent 逐动作审批（approval）能力对比与 DSH 落地

## 1. 概述

用户要的是 **human-in-the-loop gate**：agent 每要执行一个工具调用（写文件、跑命令），先停下来等人点「允许」。这不是 plan mode——plan mode 只改提示词、要求先出方案，**并不限制工具**（DSH 官方原话 `every tool remains callable`，见 `dsh-plan-mode` 包 README），所以它看起来"怪"是正常的。

决定"要不要问人"的是两件事的组合：**沙箱模式**（能做什么）+ **审批策略**（什么时候问）。下面给四家 agent 的对应开关，以及 DSH 缺"逐动作"档时怎么补。

## 2. 结论速查

| 工具 | 有无「每个动作都问」 | 开启方式 | 性质 |
|---|---|---|---|
| **DSH** | ❌ 内置没有 | 只能用 `tools/pre-execute` 插件自造，或退而用「自动授权审查」 | 需插件 |
| **Claude Code** | ✅ 有（Manual） | `--permission-mode default`，再配 `permissions.ask` | 官方内置 |
| **OpenCode** | ✅ 有 | 显式加规则 `{action:"*",resource:"*",effect:"ask"}` | 官方内置 |
| **Cline** | ✅ 默认即是 | 保持 Auto-Approve 全关，别开 YOLO | 官方内置 |
| **Codex CLI** | ⚠️ 仅逐「命令」 | `[projects."/path"] trust_level = "untrusted"` | 官方内置（能力已收缩） |
| **Cursor / Windsurf** | ⚠️ 仅 shell/MCP/终端 | Run Mode=Allowlist / 终端级别=Disabled | 官方内置 |
| **Aider** | ❌ 不能 | 无 | — |
| **通用第三方** | ❌ 无 | 没有成熟的"任意 agent 强制审批"代理层 | — |

关键前提：**除 Cline/Roo 外，绝大多数工具出厂是"放行"的**，必须显式打开才会逐步问。

## 3. DSH 现状：为什么你现在一个确认窗都看不到

DSH 的权限 = **预设（preset）** = 沙箱模式 + 审批策略的捆绑（`@deepseek-ai/dsh-permission-presets`）。审批策略只有两个值（`@deepseek-ai/dsh-user-approval`）：

- `ask`：交给已注册的 answerer（Web 端就是审批面板）决定；
- `never`：不询问，任何 ask **确定性直接拒绝**。

当前 `~/.dsh/profiles/web/cordis.patch.yml` 的 `defaultPreset` 是 `danger-full-access`，该预设为 `sandbox: danger-full-access` + `approval: never`。即 **沙箱全开 + 审批通道关闭**，连"越界要不要问"都不会发生。

内置三档（Web 界面文案）：

| 预设 | 沙箱 | 审批 | 效果 |
|---|---|---|---|
| 仅可查看 `read-only` | read-only | ask | 只读；越界会问 |
| 工作区内修改 `workspace-write` | workspace-write | ask | 工作区内自由写；越界/提权才问 |
| 完全权限 `danger-full-access` | danger-full-access | never | 什么都不问 |

审批面板是现成的（`@deepseek-ai/dsh-client-ui-approval`）：接管 composer，回车批准、Esc 拒绝，**只支持"允许一次 / 拒绝"**，没有"始终允许"。也就是说——**门槛机制齐全，缺的是"谁来产生 ask"**。

DSH 唯一的官方 ask 来源是实验性的 **「自动授权审查」（Auto review，`@deepseek-ai/dsh-experimental-auto-review`）**：每次工具调用前让当前模型判风险，`low` 直接放行、`medium` 转成 ask 问你、`high` 直接拒。它属于"随安装附带、默认关闭"的可选 bundle（`OPTIONAL_BUNDLES`）。开启：Web 侧栏 **Plugins** 页 → 打开「自动授权审查」→ 会话内 `/permission auto`（或选择器里带 `EXP` 的那项）。注意**仍是模型在审、不是你在审**，且每次调用多一轮模型请求。

## 4. 在 DSH 里实现「每个动作都问我」的三条路

### 路线 A：先恢复审批通道（纯配置，0 风险）

预设表可自定义。在 `~/.dsh/profiles/web/cordis.patch.yml` 的 `permission` 条目加一档：

```yaml
- id: permission
  name: "@deepseek-ai/dsh-permission-presets"
  config:
    presets:
      read-only:          { sandbox: read-only,          approval: ask }
      workspace-write:    { sandbox: workspace-write,    approval: ask }
      danger-full-access: { sandbox: danger-full-access, approval: never }
      full-ask:                       # 新增：全权限 + 有审批通道
        sandbox: danger-full-access
        approval: ask
        name: 完全权限+逐次确认
        description: 保留全部权限，但任何 ask 都会弹窗等人批准
    defaultPreset: danger-full-access
```

之后 `/permission full-ask`。**这一步只是"把门打开"，还没有人敲门**——默认没有任何工具会产生 ask。

### 路线 B：开「自动授权审查」（官方实验特性）

适合"不想被小事打断、但高风险必须我点头"。代价：额外 token + 模型可能误判（官方明确写了可能放行危险动作、也可能误拒正常动作）。

### 路线 C：自己写 40 行插件，做真正的逐动作确认

机制是工具执行管线的 `tools/pre-execute` waterfall（`@deepseek-ai/dsh-tools`）：监听器返回 `{ kind: 'ask', reason, displayReason }` 就进审批流程，`allowed-once` 才真执行；返回 `allow` 放行、`deny` 拒绝。参考 `dsh-experimental-auto-review` 的 `apply()`：

```js
export const name = 'per-call-approval'
export const inject = ['tools', 'approval']

// 只拦"会改东西"的工具；读类放行，否则每轮对话都会被弹窗淹没
const GATED = new Set(['pwsh', 'bash', 'write', 'edit', 'run_code'])

export function apply(ctx) {
  return ctx.on('tools/pre-execute', async (exec, next) => {
    if (!GATED.has(exec.name)) return next()
    return {
      kind: 'ask',
      reason: `per-call approval for "${exec.name}"`,
      displayReason: {
        en: `Allow "${exec.name}"?`,
        zh: `是否允许执行「${exec.name}」？`,
      },
    }
  })
}
```

打包成 profile 插件（与 `dsh-experimental-auto-review` 同构）：目录内 `package.json` 声明

```json
{ "name": "dsh-per-call-approval", "type": "module", "main": "index.js",
  "dsh": { "bundle": { "patch": "./cordis.patch.yml" } } }
```

`cordis.patch.yml` 写 `- insert: [{ id: per-call-approval, name: 'dsh-per-call-approval' }]`，再 `dsh plugin --profile web add <该目录>`。

**必须配套路线 A**：`approval: never` 下 ask 会被判成"用户拒绝"，你会看到命令全失败而不是弹窗。另外 in-process 子 agent 委派时会被钉成 `never`，子 agent 的动作不会弹窗。

## 5. 其他工具怎么开（一手文档）

### Claude Code
`default` 模式（UI 显示 **Manual**）：只有读取免问，改文件、跑 shell、访问网络都停下来问。要覆盖到"每个 Bash/Edit"，再加 `ask` 规则（求值顺序 deny → ask → allow，ask 命中即弹窗）：

```json
// ~/.claude/settings.json
{ "permissions": { "defaultMode": "default",
                   "ask": ["Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"] } }
```

坑：开了 sandbox 时 `autoAllowBashIfSandboxed` 默认 `true`，沙箱内 Bash 会绕过 `ask` 直接跑，要严格逐条问需置 `false`。另：v2.1.283+ 内置默认已改成 `auto`（分类器代审），所以"逐动作"要显式设回 `default`。PreToolUse hook 与 mods 的 `tool.check` 也能返回 `ask`，但那是"自己写插件"的活。来源：[Choose a permission mode](https://code.claude.com/docs/en/permission-modes)、[Configure permissions](https://code.claude.com/docs/en/permissions)。

### OpenCode
规则数组 `{action, resource, effect}`，`effect ∈ allow|deny|ask`，**last match wins**。**注意内置 base policy 第一条是 `{"action":"*","resource":"*","effect":"allow"}`，即默认全放行**；要全部 ask 必须显式覆盖：

```jsonc
{
  "permissions": [
    { "action": "*", "resource": "*", "effect": "ask" }   // 或只对 shell/edit 提 ask
  ]
}
```

审批可选 `once` / `always`（存为项目级 allow 规则）/ `reject`。来源：[Permissions](https://opencode.ai/docs/permissions)。

### Codex CLI
`approval_policy` 现只有 `on-request` / `never` / `{ granular = {...} }`，**`untrusted` 已被移除**。预设 `Auto`（`workspace-write` + `on-request`）只对"写到工作区外 / 要联网"发问。最接近"逐条问"的是工程信任级别：

```toml
# ~/.codex/config.toml
[projects."/path/to/project"]
trust_level = "untrusted"   # 命令默认需批准，除非执行策略规则放行；且禁用项目本地配置
```

它只管命令，不管文件编辑。另有 `approvals_reviewer = "auto_review"`（模型代审）。来源：[Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security)。

### Cline / Roo Code
Auto-Approve 是**分项开关**，出厂/推荐配置就是全关 = 每个编辑与命令都要点批准；开 YOLO Mode 才全自动。**这两家是唯一"默认即逐步确认"的**。Roo Code 扩展已于 2026-05-15 停服，官方建议转 Cline 或 ZooCode fork。来源：[Cline Auto Approve](https://docs.cline.bot/features/auto-approve)、[Roo Code](https://roocodeinc.github.io/Roo-Code/features/auto-approving-actions)。

### Cursor / Windsurf / Aider
Cursor 只有 Auto-review / Allowlist / Run Everything 三类 Run Mode，且只覆盖 shell、MCP、Fetch，**不含文件编辑**；要尽量多问选 Allowlist 并清空 allowlist。Windsurf 终端自动执行设为 **Disabled** 即每条终端命令都问，但不管编辑。Aider 没有逐编辑确认，只能 `--dry-run` 演练。来源：[Cursor Run Modes](https://cursor.com/docs/agent/security/run-modes)、[Windsurf 终端](https://docs.windsurf.com/zh/windsurf/terminal)、[Aider options](https://aider.chat/docs/config/options.html)。

### 通用生态（给任意 agent 挂审批）
未找到成熟的强制型方案。现有件都是 MCP 工具式（`request_approval` 之类），**靠模型自愿调用**，提示注入或模型忽略规则即绕过；或事后批量批准。真正能"强制"的只有各 agent 自己的权限系统与 hook。

## 6. 陷阱速查

| 现象 | 原因 |
|---|---|
| 设了 `ask` 却从不弹窗 | 没有任何工具产生 ask；`ask` 只是"允许被问"，不是"强制问" |
| 弹不出窗、命令直接报失败 | 会话策略是 `never`，ask 被确定性拒绝；先切带 `approval: ask` 的预设 |
| 子 agent 怎么都不问 | 委派时子会话被钉成 `never`，其拒绝是终态 |
| plan mode 里 agent 照样动手 | plan mode 不限制工具，只改提示词 |
| 想要"始终允许" | DSH 审批面板只有 `allowed-once` / 拒绝，无持久授权 |
| 开了逐动作后每轮弹十几次 | 拦截范围要收敛到写/执行类工具，读类放行 |
| OpenCode 配了 ask 仍不问 | 内置 base policy 先 allow-all，必须把自己规则排到后面覆盖 |
| Claude Code 沙箱内 Bash 不问 | `autoAllowBashIfSandboxed` 默认 true，需置 false |

## 7. 信源

- DSH 源码（本机安装）：`@deepseek-ai/dsh-user-approval`、`dsh-permission-presets`、`dsh-tools`（`PreToolDecision` / `serviceAsk`）、`dsh-experimental-auto-review`、`dsh-client-ui-approval`、`dsh-plan-mode`、`dsh-app-boot`（`OPTIONAL_BUNDLES`）；上游 <https://github.com/deepseek-ai/deepseek-harness>
- Claude Code：<https://code.claude.com/docs/en/permission-modes>、<https://code.claude.com/docs/en/permissions>、<https://code.claude.com/docs/en/hooks>
- Codex：<https://learn.chatgpt.com/docs/agent-approvals-security>
- OpenCode：<https://opencode.ai/docs/permissions>
- Cline：<https://docs.cline.bot/features/auto-approve>；Roo Code：<https://roocodeinc.github.io/Roo-Code/features/auto-approving-actions>
- Cursor：<https://cursor.com/docs/agent/security/run-modes>；Windsurf：<https://docs.windsurf.com/zh/windsurf/terminal>；Aider：<https://aider.chat/docs/config/options.html>
