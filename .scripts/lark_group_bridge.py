# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
r"""---
name: lark-group-bridge
description: >-
  飞书外部群消息桥：send 以「对外共享机器人」身份向外部群发文本、图片、PPT/任意文件
  （自动上传，富文本单条携带 AI 代发标注），read 用 lark-cli 读群里最近消息，
  groups 列出群找 chat_id，init 写配置。当 AI agent 需要「给飞书外部群发消息
  （含图片/文件）、看群里对方的回复」时使用本工具。--agent 区分不同 AI agent 的署名。
---

# lark-group-bridge 使用手册（供 AI agent 与人阅读）

## 何时使用

- 要向飞书**外部群**（含跨租户成员的群）发文本、图片、PPT/任意文件
- 要看外部群里**对方的回复**（主动轮询读取）
- 背景知识：消息以应用的「对外共享机器人」身份发出（群里显示为机器人，不是群主本人），
  不同 AI agent 用 `--agent` 署名区分

## 通道说明

| 内容 | 通道 | 身份 | 依赖 |
|---|---|---|---|
| 文本 | bot（默认） | 机器人 | lark-cli + bot 已在目标群 |
| 图片/文件 | bot | 机器人 | 同上 |
| 文本（旧通道） | `--via webhook` | 自定义机器人 | 配置了 webhook_url |

- bot 的 tenant token 由 lark-cli 用 appId/appSecret 自动获取，**不依赖用户登录态**，
  比 user token（7 天刷新）更稳
- webhook 仅支持文本：发图片报 11221（key 归属校验）、发文件报 10208（不支持该类型）
- user 身份向外部群发消息被平台策略禁止（230027，外部聊天策略，与 scope 无关），勿尝试

## 前置条件

| 依赖 | 用途 | 缺失时的表现 |
|---|---|---|
| uv | 执行脚本 | 统一用 `uv run .scripts/lark_group_bridge.py <子命令>` |
| lark-cli | 全部发送、read、groups | 报 `cli_missing`；bot token 自动获取，无需 auth login |
| bot 已在目标群 | 所有 bot 通道发送 | lark-cli 报群成员相关错误；用 `groups` 确认群，客户端手动加 bot |
| webhook 已配置 | 仅 `--via webhook` 时 | 报 `webhook_not_configured` |

## 快速开始

```powershell
# 1. 一次性配置（chat_id 用 groups 查；webhook 可选，仅旧通道需要）
uv run .scripts/lark_group_bridge.py init --chat-id oc_xxx

# 2. 发文本 / 图片 / PPT文件（均为机器人身份，消息内自动带代发标注）
uv run .scripts/lark_group_bridge.py send --text "构建完成了" --agent opencode
uv run .scripts/lark_group_bridge.py send --image D:\shots\a.png --agent opencode
uv run .scripts/lark_group_bridge.py send --file D:\docs\技术方案.pptx --agent Claude

# 3. 读群里最近 10 条消息（看对方的回复，时间正序）
uv run .scripts/lark_group_bridge.py read
```

## 子命令参考

| 子命令 | 参数 | 说明 |
|---|---|---|
| `init` | `--webhook <url>` 可选；`--chat-id <oc_xxx>` 可选 | 写入配置；重复执行覆盖旧值 |
| `send` | `--text` / `--image` / `--file` 三选一；`--agent <名>`；`--chat-id`；`--via webhook` | 默认 bot 通道；webhook 仅支持文本 |
| `groups` | 无 | 列出 lark-cli 可见的群（含外部群标记），用于查 chat_id |
| `read` | `--chat-id`（缺省用配置）、`--limit N`（默认 10，上限 50） | 按时间正序显示最近 N 条 |

### 代发标注（重要）

- 文本消息：标注拼在文本尾部
- 图片/文件消息：与图片/文件在**同一条**富文本消息内（先上传拿 key，再发富文本，不追发第二条）
- 标注文案：`—— 本条由 AI 助手「<name>」代发，非本人发送`
- 不同 AI agent 发送时**必须**传 `--agent <自己的名字>`（如 opencode、Codex、Claude），
  群里的人靠它区分消息来自哪个 agent

### 机器输出

每个子命令支持 `--json`（放在子命令名之后）：

- `init` / `send`：本工具标准包络 `{"ok": true, "data": {...}}` / `{"ok": false, "error": {"code": "...", "message": "..."}}`
- `read` / `groups`：**透传 lark-cli 的原始 JSON**（输出即协议，不二次包装）
- 退出码：`0` 成功；`2` 参数错误；`1` 其他失败（错误码见源码 `BridgeError` 各调用点）

## 配置与数据位置

| 项 | 值 |
|---|---|
| 配置文件 | `%APPDATA%\language_projects\lark_group_bridge\config.json`（无 APPDATA 时回退 `~\.language_projects\lark_group_bridge\`） |
| `webhook_url` | 仅 `--via webhook` 通道使用（机密，可选） |
| `default_chat_id` | `send` 与 `read` 的缺省群 |

## 安全注意事项

1. **bot 的发送权 = lark-cli 配置里的 appId/appSecret**：不要把 lark-cli 凭据交给不可信的人
2. webhook URL 等于群的文本发送权：泄露后到 群设置-群机器人 里重置，再 `init` 写入新 URL
3. 凭据与 webhook 都**禁止**写进任何仓库文件、日志、聊天记录、代码
4. 消息标注是身份透明机制：所有代发消息必须携带 `--agent` 标注

## 常见问题

- **bot 发送报群成员/可见性错误**：bot 还没被加进目标群。在群里 客户端-设置-群机器人
  手动添加，或用 lark-cli：
  `im chat.members create --params '{"chat_id":"oc_xxx","member_id_type":"app_id"}' --data '{"id_list":["<appId>"]}' --as user`
- **发图片/文件报 230027 / 11221 / 10208**：说明你在用 user 身份或 webhook 发媒体——
  这两条路被平台封死，必须走默认的 bot 通道
- **报 cli_missing / cli_failed**：lark-cli 未安装或不在 PATH
- **不知道 chat_id**：跑 `groups`，找目标群的 `oc_` 开头 ID
- **为什么不做实时推送**：bot 在外部群理论上可订阅消息事件（`lark-cli event consume`），
  但需要常驻进程，脚本暂未封装（见文件头 roadmap）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROG = "lark_group_bridge"
VERSION = "2.0.0"
APP_DIR = "lark_group_bridge"

DEFAULT_AGENT = "AI 助手"
ANNOTATION = "—— 本条由 AI 助手「{name}」代发，非本人发送"

# 文件后缀 -> files.create 的 file_type（飞书枚举），未识别的后缀一律 stream
FILE_TYPES = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "doc",
    ".xls": "xls",
    ".xlsx": "xls",
    ".ppt": "ppt",
    ".pptx": "ppt",
    ".mp4": "mp4",
    ".opus": "opus",
}


class BridgeError(Exception):
    """业务错误：携带稳定错误码，可对外展示。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------- 配置读写 ----------


def config_dir() -> Path:
    """配置目录：%APPDATA%\\language_projects\\<name>，无 APPDATA 回退 ~/。"""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "language_projects" / APP_DIR
    return Path.home() / ".language_projects" / APP_DIR


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    """读取配置；文件缺失或损坏一律返回空配置（不抛异常，让业务层给可读错误）。"""
    try:
        obj = json.loads(config_path().read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(cfg: dict) -> None:
    # 仓库强约束：写入前自动创建完整目录链
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ---------- 输出辅助 ----------


def print_envelope(data=None, error: BridgeError | None = None) -> None:
    if error is not None:
        env = {"ok": False, "error": {"code": error.code, "message": error.message}}
    else:
        env = {"ok": True, "data": data}
    print(json.dumps(env, ensure_ascii=False))


def mask_url(url: str) -> str:
    """webhook 脱敏：保留前缀与末 4 位，中间全遮。"""
    m = re.match(r"(.*/hook/)(.+)$", url)
    if not m:
        return url[:8] + "***"
    return m.group(1) + "***" + m.group(2)[-4:]


# ---------- lark-cli 子进程 ----------


def resolve_cli() -> list[str]:
    """解析 lark-cli 的真实调用入口，返回进程参数前缀。

    Windows 上 lark-cli 是 npm 的 .CMD 垫片（内部执行 node.exe run.js %*）。
    直接以 .CMD 作为子进程时，cmd.exe 会对参数做二次解析，含换行等特殊字符的
    参数会被截断/串位（实测：多行 --text 的 `--as bot` 丢失后回落 user 身份，
    触发 230027）。因此解析出 node.exe 与 run.js 直接调用 node，绕开 cmd.exe；
    解析失败时退回原 exe。
    """
    exe = shutil.which("lark-cli")
    if exe is None:
        raise BridgeError("cli_missing", "lark-cli 不在 PATH；所有通道都依赖它")
    if exe.lower().endswith((".cmd", ".bat")):
        shim_dir = Path(exe).parent
        try:
            shim = Path(exe).read_text(encoding="utf-8", errors="replace")
            m = re.search(r'"%dp0%\\([^"]+\.js)"', shim)
            if m:
                node = shim_dir / "node.exe"
                if not node.is_file():
                    node = shutil.which("node")
                if node:
                    return [str(node), str(shim_dir / m.group(1))]
        except OSError:
            pass
    return [exe]


def run_cli(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [*resolve_cli(), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise BridgeError("cli_failed", f"lark-cli 执行超时（>{timeout}s）")


def cli_json(args: list[str], timeout: int = 120) -> dict:
    """运行 lark-cli（自动加 --json），非零退出或非 JSON 输出按业务错误处理。"""
    proc = run_cli([*args, "--json"], timeout=timeout)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        raise BridgeError("cli_failed", f"lark-cli 退出码 {proc.returncode}：{detail}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise BridgeError("cli_failed", f"lark-cli 输出不是 JSON：{proc.stdout[:200]}")


def find_key(obj, key: str):
    """在任意嵌套结构里 BFS 查找指定键的第一个值（兼容 lark-cli 输出形状变化）。"""
    queue = [obj]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def fail_if_cli_error(proc: subprocess.CompletedProcess) -> None:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        raise BridgeError("cli_failed", f"lark-cli 退出码 {proc.returncode}：{detail}")


# ---------- webhook（旧通道，仅文本） ----------


def webhook_post(webhook_url: str, payload: dict) -> dict:
    """POST 到自定义机器人；成功判定兼容 StatusCode/code 两种新旧响应格式。"""
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise BridgeError("webhook_failed", f"HTTP {e.code}：{e.read().decode('utf-8', 'replace')[:200]}")
    except urllib.error.URLError as e:
        raise BridgeError("webhook_failed", f"网络错误：{e.reason}")
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        raise BridgeError("webhook_rejected", f"响应不是 JSON：{body[:200]}")
    if obj.get("StatusCode") == 0 or obj.get("code") == 0:
        return obj
    raise BridgeError("webhook_rejected", json.dumps(obj, ensure_ascii=False)[:200])


# ---------- 子命令：init ----------


def cmd_init(args, json_mode: bool):
    old = load_config()
    cfg: dict = {}
    # 显式传 --webhook ""（或 --clear-webhook）可清除已存的 webhook；不传则保留旧值
    if getattr(args, "clear_webhook", False):
        webhook = ""
    else:
        webhook = (args.webhook if args.webhook is not None else old.get("webhook_url")) or ""
    webhook = webhook.strip()
    if webhook:
        cfg["webhook_url"] = webhook
    chat_id = (args.chat_id or old.get("default_chat_id") or "").strip()
    if chat_id:
        cfg["default_chat_id"] = chat_id
    save_config(cfg)
    data = {
        "config_path": str(config_path()),
        "webhook_url": mask_url(cfg["webhook_url"]) if cfg.get("webhook_url") else None,
        "default_chat_id": cfg.get("default_chat_id"),
    }
    if not json_mode:
        print(f"已写入配置：{data['config_path']}")
        print(f"webhook：{data['webhook_url'] or '（未设置，仅 --via webhook 时需要）'}")
        print(f"default_chat_id：{data['default_chat_id'] or '（未设置）'}")
    return data


# ---------- 子命令：send ----------


def resolve_chat_id(args) -> str:
    chat_id = (args.chat_id or load_config().get("default_chat_id") or "").strip()
    if not chat_id:
        raise BridgeError(
            "chat_id_required",
            "未提供 --chat-id 且配置里没有 default_chat_id；先跑 groups 查询再用 init --chat-id 写入",
        )
    return chat_id


def send_text_bot(text: str, annotation: str, chat_id: str) -> dict:
    """bot 通道文本：消息体 = 正文 + 标注。"""
    sent = cli_json(
        ["im", "+messages-send", "--chat-id", chat_id, "--text", f"{text}\n\n{annotation}", "--as", "bot"]
    )
    return {"channel": "bot", "sender_identity": "对外共享机器人", "message_id": find_key(sent, "message_id")}


def send_media_bot(kind: str, path: Path, annotation: str, chat_id: str) -> dict:
    """bot 通道媒体：先上传拿 key，再发单条富文本（图片内嵌 / 文件附件区），标注在正文。"""
    name = path.name
    old_cwd = os.getcwd()
    try:
        # lark-cli 的 --file/--image 只接受 cwd 相对路径，chdir 后传文件名
        os.chdir(path.parent)
        if kind == "image":
            up = cli_json(
                ["im", "images", "create", "--data", json.dumps({"image_type": "message"}), "--file", name, "--as", "bot"]
            )
            img_key = find_key(up, "image_key")
            if not img_key:
                raise BridgeError("upload_failed", f"上传完成但未取到 image_key：{json.dumps(up, ensure_ascii=False)[:200]}")
            body = f"![img]({img_key})\n\n{annotation}"
            sent = cli_json(["im", "+messages-send", "--chat-id", chat_id, "--markdown", body, "--as", "bot"])
        else:
            ftype = FILE_TYPES.get(path.suffix.lower(), "stream")
            # file_name 必须显式传：服务端默认用 UUID 命名附件
            up = cli_json(
                ["im", "files", "create", "--data", json.dumps({"file_type": ftype, "file_name": name}), "--file", name, "--as", "bot"]
            )
            file_key = find_key(up, "file_key")
            if not file_key:
                raise BridgeError("upload_failed", f"上传完成但未取到 file_key：{json.dumps(up, ensure_ascii=False)[:200]}")
            # 附件区必须挂在 post 消息上：--markdown（post）+ --attachment
            sent = cli_json(
                ["im", "+messages-send", "--chat-id", chat_id, "--markdown", annotation, "--attachment", file_key, "--as", "bot"]
            )
        return {
            "channel": "bot",
            "sender_identity": "对外共享机器人",
            "message_id": find_key(sent, "message_id"),
        }
    finally:
        os.chdir(old_cwd)


def cmd_send(args, json_mode: bool):
    annotation = ANNOTATION.format(name=args.agent)
    if args.via_webhook == "webhook":
        # 旧通道：仅文本，走 webhook（自定义机器人身份）
        if args.image or args.file:
            raise BridgeError("channel_mismatch", "webhook 通道仅支持 --text；图片/文件请走默认 bot 通道")
        cfg = load_config()
        url = cfg.get("webhook_url")
        if not url:
            raise BridgeError("webhook_not_configured", "--via webhook 需要先 init --webhook <url>")
        webhook_post(url, {"msg_type": "text", "content": {"text": f"{args.text}\n\n{annotation}"}})
        data = {"channel": "webhook", "sender_identity": "自定义机器人", "annotation": annotation}
    else:
        chat_id = resolve_chat_id(args)
        if args.text:
            data = send_text_bot(args.text, annotation, chat_id)
        else:
            path = Path(args.image or args.file)
            if not path.is_file():
                raise BridgeError("file_not_found", f"文件不存在：{path}")
            data = send_media_bot("image" if args.image else "file", path, annotation, chat_id)
        data["annotation"] = annotation
    if not json_mode:
        print(f"已发送（通道：{data['channel']}，身份：{data['sender_identity']}）")
        if data.get("message_id"):
            print(f"message_id：{data['message_id']}")
    return data


# ---------- 子命令：groups ----------


def cmd_groups(args, json_mode: bool):
    proc = run_cli(["im", "+chat-list", "--as", "user", "--json"], timeout=60)
    fail_if_cli_error(proc)
    if json_mode:  # 输出即协议：原样透传 lark-cli 的 JSON
        print(proc.stdout)
        return None
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        return None
    data = obj.get("data") or {}
    items = next((v for v in data.values() if isinstance(v, list)), [])
    for it in items:
        if not isinstance(it, dict):
            continue
        tag = "（外部群）" if it.get("external") else ""
        print(f"{it.get('name', '?')}{tag}  {it.get('chat_id', '?')}")
    return None


# ---------- 子命令：read ----------


def render_messages(obj: dict) -> None:
    """人读渲染。lark-cli 已把 content 抽成纯文本、create_time 格式化好，直接用。"""
    data = obj.get("data") or {}
    messages = data.get("messages")
    if not isinstance(messages, list):
        messages = next((v for v in data.values() if isinstance(v, list)), [])
    if not messages:
        print("（群里没有消息）")
        return
    # 接口按 desc 返回（最新在前），人读习惯时间正序，反转显示
    for m in reversed(messages):
        if not isinstance(m, dict):
            continue
        sender = m.get("sender") or {}
        name = sender.get("name") or sender.get("id") or "?"
        content = str(m.get("content") or "").replace("\n", " ")[:120]
        print(f"[{m.get('create_time', '?')}] {name}（{m.get('msg_type', '?')}）：{content}")


def cmd_read(args, json_mode: bool):
    chat_id = (args.chat_id or load_config().get("default_chat_id") or "").strip()
    if not chat_id:
        raise BridgeError(
            "chat_id_required",
            "未提供 --chat-id 且配置里没有 default_chat_id；先跑 groups 查询再用 init --chat-id 写入",
        )
    limit = max(1, min(args.limit, 50))  # 接口单页上限 50
    proc = run_cli(
        ["im", "+chat-messages-list", "--chat-id", chat_id, "--as", "user", "--json", "--page-size", str(limit)],
        timeout=60,
    )
    fail_if_cli_error(proc)
    if json_mode:  # 输出即协议：原样透传
        print(proc.stdout)
        return None
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        return None
    render_messages(obj)
    return None


# ---------- 入口 ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="飞书外部群消息桥：对外共享机器人发文本/媒体 + lark-cli 读消息（详见文件头手册）",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # --json 定义在每个子命令上（SUPPRESS 避免子解析器默认值覆盖全局取值）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="机器可读 JSON 输出")

    p = sub.add_parser("init", parents=[common], help="写入配置（webhook 可选，chat_id 推荐配置）")
    p.add_argument("--webhook", help='群自定义机器人 webhook 地址（仅 --via webhook 旧通道需要）；PowerShell 下传空串会被吞，请用 --clear-webhook')
    p.add_argument("--clear-webhook", action="store_true", help="从配置中移除已存的 webhook_url")
    p.add_argument("--chat-id", help="缺省群会话 ID（oc_ 开头，可用 groups 查询）")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("send", parents=[common], help="发文本/图片/文件（默认 bot 身份，自动带 AI 代发标注）")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="文本内容")
    group.add_argument("--image", help="图片文件路径")
    group.add_argument("--file", help="任意文件路径，如 PPT")
    p.add_argument("--agent", default=DEFAULT_AGENT, help=f"AI agent 署名，用于代发标注（默认：{DEFAULT_AGENT}）")
    p.add_argument("--chat-id", help="目标群（缺省读配置 default_chat_id）")
    p.add_argument("--via", choices=["bot", "webhook"], default="bot", dest="via_webhook",
                   help="发送通道：bot（默认，支持全部类型）| webhook（旧通道，仅文本）")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("groups", parents=[common], help="列出可见群，查 chat_id 用")
    p.set_defaults(func=cmd_groups)

    p = sub.add_parser("read", parents=[common], help="读取群里最近 N 条消息（时间正序）")
    p.add_argument("--chat-id", help="缺省用配置里的 default_chat_id")
    p.add_argument("--limit", type=int, default=10, help="条数，1-50（默认 10）")
    p.set_defaults(func=cmd_read)
    return parser


def main(argv=None) -> int:
    # Windows 控制台默认 GBK，显式切 UTF-8 防中文乱码
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    json_mode = bool(getattr(args, "json", False))
    try:
        data = args.func(args, json_mode)
        if json_mode and data is not None:
            print_envelope(data=data)
        return 0
    except BridgeError as e:
        if json_mode:
            print_envelope(error=e)  # 业务错误 JSON 走 stdout
        else:
            print(f"错误 [{e.code}]：{e.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
