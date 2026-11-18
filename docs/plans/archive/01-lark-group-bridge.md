# lark_group_bridge.py 开发计划

## 项目概述

仓库运维脚本目录 `.scripts/` 下的单文件 Python 桥接脚本：让任何 AI agent 向飞书外部群**发文本/图片/PPT/任意文件（对外共享机器人，bot 身份）**、**读群消息（lark-cli）**。webhook 降级为文本备选通道（`--via webhook`）。

- 单脚本文件放 `.scripts/`，文档注释完备——其他 AI agent **只读这一个文件**就知道怎么用
- 文件头 docstring 按 skill-creator（SKILL.md）规范写：frontmatter（name/description）+ 使用手册
- webhook URL 等敏感配置**不入仓库**，首次 `init` 写入 `%APPDATA%\language_projects\lark_group_bridge\config.json`
- PEP 723 内联元数据，`uv run .scripts/lark_group_bridge.py <cmd>` 执行，纯标准库零第三方依赖
- 遵守 CLI 标准精神（一次性脚本豁免 MCP/schema 强制）：人读默认 + `--json`、退出码 0/1/2、JSON 包络 `{"ok":...}`

## 项目结构

```
language_projects/
└── docs/
    ├── scripts/lark_group_bridge.py    # 唯一交付物：对外共享机器人发文本/媒体 + lark-cli 读取桥接
    └── plans/01-lark-group-bridge.md   # 本计划
```

运行时数据（不在仓库内）：

```
%APPDATA%\language_projects\lark_group_bridge\config.json
```

## 核心数据结构

config.json（`init` 写入）：

```json
{
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx",
  "default_chat_id": "oc_xxx"
}
```

`--json` 统一包络（本仓约定）：

```json
{"ok": true, "data": {"chat_id": "oc_xxx", "message_id": null}}
```

```json
{"ok": false, "error": {"code": "webhook_not_configured", "message": "先执行 init 配置 webhook"}}
```

业务错误码表：

| code | 场景 |
|---|---|
| `config_unwritable` | 配置目录/文件写入失败 |
| `webhook_not_configured` | send 前未 init |
| `webhook_failed` | webhook HTTP 层失败 |
| `webhook_rejected` | 飞书返回非成功码 |
| `cli_missing` | lark-cli 不在 PATH |
| `cli_failed` | lark-cli 子进程非零退出 |
| `chat_id_required` | read 未提供且未配置 default_chat_id |

## 对外接口设计（CLI）

| 子命令 | 参数 | 说明 |
|---|---|---|
| `init` | `--webhook <url>` 必填；`--chat-id <oc_xxx>` 可选 | 非交互写入配置；已存在则覆盖（打印新旧差异摘要） |
| `send` | 三选一：`--text <str>` \| `--image <path>` \| `--file <path>`；可选 `--agent <name>`（默认「AI 助手」）、`--chat-id`、`--via webhook`（仅文本，旧通道） | 默认 **bot 身份**发（图片/文件先上传再以富文本单条发出，标注在正文）；`--via webhook` 时文本走旧 webhook 通道 |
| `groups` | 无 | 列出 lark-cli 可见的群（找 chat_id 用） |
| `read` | `--chat-id <oc_xxx>` 可选（缺省用 default_chat_id）；`--limit N` 默认 10 | 拉取群里最近 N 条消息 |

- 全局 `--json`：机器输出。send/init 输出标准包络；read/groups 的 `--json` **透传 lark-cli 原始 JSON**（输出即协议，不二次包装）
- 退出码：`0` 成功、`2` 参数错误、`1` 其他失败
- `--help` 各子命令具备；`--version` 输出版本号

## 核心模块设计

### config 读写
- `_config_dir()`：`%APPDATA%` 取得到 → `%APPDATA%\language_projects\lark_group_bridge\`；否则回退 `~/.language_projects/lark_group_bridge/`
- 写入前 `mkdir(parents=True, exist_ok=True)` 创建完整目录链（仓库强约束）
- 读取失败/不存在 → 返回空配置，不抛异常

### send（webhook 单通道，自动附加代发标注）
- **标注规则**：`--agent <name>` 指定发送方 AI agent 名（缺省「AI 助手」），标注文案：`—— 本条由 AI 助手「<name>」代发，非本人发送`；不同 agent 传不同名字即可区分
- **文本通道（webhook）**：POST JSON `{"msg_type":"text","content":{"text":"<text>\n\n<标注>"}}`；超时 15s；成功判定**兼容两种响应格式**：`{"StatusCode":0}` 与 `{"code":0}`；其余响应 → `webhook_rejected`，附带原始响应片段（截断 200 字符）
- **媒体通道已砍**：实测平台三连拒（详见关键技术点 7），`send` 不再提供 `--image/--file`

### read / groups（lark-cli 子进程）
- `subprocess.run(["lark-cli", ...], capture_output=True, text=True, timeout=60)`，参数数组传递、不经 shell
- `read` 底层：`lark-cli im +chat-messages-list --chat-id <id> --as user --json --page-size <N>`（实测无 `--limit` 参数，用 `--page-size`（1-50）+ 默认 desc 排序取最新 N 条）
- `groups` 底层：`lark-cli im +chat-list --as user --json`，人读模式解析出 `名称 + chat_id` 表格
- FileNotFoundError → `cli_missing`；非零退出 → `cli_failed`（带 stderr 片段）
- docstring 中向 AI agent 说明：lark-cli 的登录态是前置条件，token 过期需 `lark-cli auth login`

### 文件头 docstring（skill-creator 风格）
- YAML frontmatter：`name`、`description`（含触发场景描述）
- 正文小节：何时用 / 前置条件 / 快速开始 / 子命令参考 / 配置与数据位置 / 安全注意事项 / 常见问题
- 全中文注释；标识符英文

## 实现步骤（分阶段）

### Phase 1：脚本主体
- [x] 1.1 PEP 723 头 + skill 风格 docstring 使用手册（先把"给人看的手册"写完）
- [x] 1.2 config 模块：路径解析、目录链创建、读写函数
- [x] 1.3 `init` 与 `send`：webhook 双格式判定 + `--agent` 标注注入
- [x] 1.4 `groups` 与 `read`：lark-cli 子进程封装、错误映射、人读渲染
- [x] 1.5 `--json` 包络、退出码（0/1/2）、UTF-8 输出统一收口
- [x] 1.6 `--version`、`--help` 全覆盖

**验收标准**：
- `uv run .scripts/lark_group_bridge.py --help` 及各子命令 `--help` 正常，`--version` 输出版本
- 未 init 时 `send --text x` 报 `webhook_not_configured`，退出码 1，`--json` 输出可被 `json.loads` 解析
- `init --webhook <url>` 后 config.json 出现在约定目录且含 URL；重复 init 覆盖并提示
- `groups` 能列出群列表（人读表格 + `--json` 透传）
- `read --chat-id <id> --limit 5` 返回最近 5 条消息

### Phase 2：端到端验证与收尾
- [x] 2.1 用真实 webhook 发一条文本测试消息（用户在群里确认收到）
- [x] 2.2 媒体通道平台限制实测（已完成于编码期：230027/11221/10208 三连拒，结论记入关键技术点 7）
- [x] 2.3 用 `read` 读回发送的消息，验证双向链路
- [x] 2.4 删除根目录 `lark-auth-qr.png`
- [x] 2.5 输出改动摘要与 git commit 命令（仅含 `lark_group_bridge.py` 与 `docs/plans/01-lark-group-bridge.md`）

**验收标准**：
- 群里真实收到脚本发出的文本（机器人身份，含标注）（用户确认）
- `read --limit 5` 能看到刚发的消息
- `git status` 确认 webhook URL 未出现在任何入库文件中

### Phase 3：bot 通道改造（对外共享解锁后）
- [x] 3.1 实测 bot 三连（文本/图片/文件进外部群）——已通过，结论记入关键技术点 8
- [x] 3.2 `send` 改造：默认 bot 身份；文本拼标注；图片/文件上传（bot）+ 富文本单条（标注在正文）；`--via webhook` 保留旧通道
- [x] 3.3 docstring 手册同步重写（bot 优先、webhook 降级为备选、媒体支持恢复）
- [x] 3.4 端到端验收：脚本发三类消息 + read 读回 + `--json` 抽查

**验收标准**：
- `send --text/--image/--file` 三类消息到达群里（bot 身份，标注正确）
- `read --limit 8` 能读回三类消息
- `send --text x --via webhook` 仍走旧通道成功

## 技术依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Python 标准库（argparse/json/urllib/subprocess/pathlib/os/sys） | 全部功能 | PEP 723 `dependencies = []` |
| lark-cli（外部） | read/groups | 本机已装且 user 身份已授权 |
| uv（外部） | 执行方式 | 仓库约定 `uv run` |

## 关键技术点

1. **webhook 成功判定双格式**：飞书自定义机器人新旧响应格式并存，`StatusCode==0 || code==0` 才算成功
2. **read 透传不包装**：`--json` 时原样转发 lark-cli stdout（CLI 标准：输出即协议的命令不强制 JSON 包络）
3. **Windows 控制台编码**：脚本入口 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`，避免 PowerShell 5.1 GBK 控制台中文乱码
4. **敏感信息隔离**：webhook URL 只存 %APPDATA%，脚本与计划文件中仅出现占位符；本计划同样不写入真实 URL
5. **lark-cli 参数数组传递**：不经 shell，避免引号/空格注入问题
6. **双身份与代发标注**：webhook 消息天然显示为机器人；靠 `--agent` 把标注写进消息正文，不同 AI agent 传自己的名字即可区分
7. **媒体发送的平台硬限制（未开对外共享时，实测）**：① user 身份向外部群发消息 → `230027`（scope 齐全仍被 external-chat 策略拦截）；② webhook 使用 user 上传的 image_key → `11221`（image_key 归属校验）；③ webhook 发 file 类型 → `10208`（不支持）
8. **对外共享解锁（实测全通）**：在开发者后台「应用发布 → 版本管理与发布 → 创建版本」开启「对外共享」（个人实名认证即可），bot 加进外部群后：文本 `im:message:send_as_bot` ✅、图片/文件 `im:resource` + 发送 ✅、进群方式为 user 调 `chat.members create` 且 `member_id_type=app_id` 填应用 ID。bot 在外部群可「响应群成员消息」→ 事件监听（`lark-cli event consume`）由死路变为可行（二期）
9. **lark-cli 的 .CMD 垫片陷阱**：Windows 下 lark-cli 是 npm 垫片（`node.exe run.js %*`），以 .CMD 直接作子进程时 cmd.exe 会二次解析参数，**含换行的参数被截断/串位**（实测：多行 `--text` 导致 `--as bot` 丢失、回落 user 身份触发 230027）。修复：脚本解析垫片内容取出 node.exe + run.js 直调 node，绕开 cmd.exe

## 预计时间

| Phase | 估时 |
|---|---|
| Phase 1 脚本主体 | ~1.5h |
| Phase 2 验证收尾 | ~0.5h |
| **总计** | **~2h** |

## 后续扩展（二期）

- **媒体发送二期方案（已被 Phase 3 提前实现）**：~~云盘链接~~ → 对外共享机器人直发
- **`watch` 事件监听子命令**：对外共享后 bot 可「响应群成员消息」，用 `lark-cli event consume` 订阅 `im.message.receive_v1`，实时接收她的回复（此前死路已通）
- `send --markdown`（post 富文本）、interactive 卡片
- webhook 加签支持（`--secret` + HMAC-SHA256）
- `watch` 轮询子命令
- 自建「对外共享」机器人 + 事件监听（若飞书放开权限，彻底替代 webhook 与轮询）
- 使用频率高的话，升级为标准 CLI 项目（补 MCP/schema 双入口）

## 注意事项

- **webhook URL 等于群的发送权**：已在前序对话暴露，建议在群设置里重置后再 `init` 新 URL
- **lark-cli 登录态是 read/groups 的前置条件**：user token 过期（refresh 截止 2026-09-26）需重新授权
- **风险已实测落地**：user 身份向外部群发消息确认被拦（230027），媒体发送一期放弃，文本通道不受影响；P2P 跨租户限制（230038）同样存在
- **不做的事**：不加动画/多消息类型/加签（二期）；不碰其他脚本；不改 .gitignore（config 在 %APPDATA%，不入仓库）

---
**最后更新：** 2026-09-19
**作者：** AI & User
**版本：** v2.0
