# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# install-aoci-mcp.py：把本仓库的 AOCI MCP（aoci.exe --repo <本仓> mcp）统一配置到
# claude code / opencode / codex / antigravity（ACP 与桌面 IDE 两个形态）的用户级配置文件。
# 幂等：已存在且一致的配置跳过；不一致默认仅报告（--force 才覆盖）；缺失则写入。
# antigravity 两份配置（官方文档 docs/mcp）：
#   antigravity      -> ~/.gemini/antigravity-acp/mcp.json        （ACP 形态：Zed 等编辑器接入 agy agent）
#   antigravity-ide  -> ~/.gemini/config/mcp_config.json          （桌面 IDE / CLI / 2.0 全局）
# 用法:
#   uv run .scripts/install-aoci-mcp.py            # 检查并补齐全部五处
#   uv run .scripts/install-aoci-mcp.py --agent antigravity-ide
#   uv run .scripts/install-aoci-mcp.py --json     # 机器可读输出
#   uv run .scripts/install-aoci-mcp.py --force    # 覆盖已有不一致配置
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Windows 管道/终端统一 UTF-8 输出，防中文乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# aoci.exe 探测候选：固定安装路径优先，其次 PATH
AOCI_EXE_CANDIDATES = [
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\aoci\aoci.exe")),
    Path.home() / "AppData" / "Local" / "Programs" / "aoci" / "aoci.exe",
]


def find_aoci_exe() -> Path:
    for cand in AOCI_EXE_CANDIDATES:
        if cand.is_file():
            return cand
    found = shutil.which("aoci") or shutil.which("aoci.exe")
    if found:
        return Path(found)
    raise SystemExit("[ERROR] 未找到 aoci.exe，请用 --exe 指定路径")


def norm(p) -> str:
    """路径等价归一：统一分隔符与大小写（Windows 不敏感），用于一致性比较。"""
    return str(p).replace("/", "\\").lower()


def expected_binding(exe: Path, repo: Path):
    """期望的命令绑定：命令字符串 + 参数（--repo <仓库根> mcp）。"""
    return str(exe), ["--repo", str(repo), "mcp"]


def read_json(path: Path):
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}  # 空文件（如 antigravity-ide 的 0 字节 mcp_config.json）视为空配置
    return json.loads(text)


def write_json_atomic(path: Path, data) -> None:
    """原子写 JSON：临时文件 + os.replace，避免半写损坏目标配置。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def check_json_server(existing: dict, exe: Path) -> bool:
    """校验 Claude/Antigravity/opencode 形态里已有的 aoci 条目是否与期望一致。"""
    cmd = existing.get("command")
    args = existing.get("args") or []
    if isinstance(cmd, list):  # opencode 形态：command 为数组
        cmd_args, cmd = cmd[1:], cmd[0]
    else:
        cmd_args = args
    want_cmd, want_args = expected_binding(exe, REPO_ROOT)
    if norm(cmd) != norm(want_cmd):
        return False
    got = [norm(a) for a in cmd_args]
    want = [norm(a) if "\\" in a or "/" in a else a for a in want_args]
    return got == want


def upsert_json(path: Path, exe: Path, force: bool, server_lens: dict, key_path: tuple) -> str:
    """通用 JSON 合并：按 key_path 深入定位 server 映射表，写入/校验 aoci 条目。

    server_lens: 各层级缺省容器构造器（dict），如 {"mcpServers": dict} 或 {"mcp": dict}
    返回状态：written / ok / skipped_mismatch
    """
    data = read_json(path)
    created = data is None
    if created:
        data = {}
    node = data
    for key in key_path[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            if child is None:
                child = {}
                node[key] = child
            else:
                return "error: 配置结构异常（{} 不是对象）".format("/".join(key_path[:-1]))
        node = child
    table = key_path[-1]
    if not isinstance(node.get(table), dict):
        if node.get(table) is None:
            node[table] = {}
        else:
            return "error: 配置结构异常（{} 不是对象）".format("/".join(key_path))
    servers = node[table]
    want_cmd, want_args = expected_binding(exe, REPO_ROOT)
    if "aoci" in servers:
        if check_json_server(servers["aoci"], exe):
            return "ok"
        if not force:
            return "skipped_mismatch"
    servers["aoci"] = {"type": "stdio", "command": want_cmd, "args": want_args}
    write_json_atomic(path, data)
    return "written" + ("_new" if created else "")


def upsert_codex(path: Path, exe: Path, force: bool) -> str:
    """codex 的 config.toml：无 aoci 段则按现有风格在末尾追加（避免整文件重写丢注释）。"""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if "[mcp_servers.aoci]" in text:
        # 已有段：粗校验命令与 --repo 是否指向当前绑定。
        # 段边界按行识别节标题（^\[section]$），不能按 "[" 切分——
        # TOML 数组字面量 args = [...] 的方括号会被误判为下一个节。
        want_cmd, want_args = expected_binding(exe, REPO_ROOT)
        want_repo = norm(want_args[1])
        seg_lines = []
        in_seg = False
        for line in text.splitlines():
            stripped = line.strip()
            if re.fullmatch(r"\[[^\]]+\]", stripped):
                in_seg = stripped == "[mcp_servers.aoci]"
                continue
            if in_seg:
                seg_lines.append(line)
        seg = "\n".join(seg_lines)
        cmd_ok = any(norm(line.split("=", 1)[1].strip().strip("'\"")) == norm(want_cmd)
                     for line in seg_lines if line.strip().startswith("command"))
        repo_ok = want_repo in norm(seg)
        return "ok" if (cmd_ok and repo_ok) else ("skipped_mismatch" if not force else "force_unsupported")
    path.parent.mkdir(parents=True, exist_ok=True)
    block = (
        "\n[mcp_servers.aoci]\n"
        "command = '{exe}'\n"
        "args = [\"--repo\", '{repo}', \"mcp\"]\n"
    ).format(exe=str(exe), repo=str(REPO_ROOT))
    with open(path, "a", encoding="utf-8") as f:
        f.write(block if text.endswith("\n") or not text else "\n" + block)
    return "written"


TARGETS = {
    # agent 名 -> (配置文件, 处理器, 说明)
    "claude": (Path.home() / ".claude.json",
               lambda p, exe, force: upsert_json(p, exe, force, {}, ("mcpServers",)),
               "Claude Code 用户级全局配置"),
    "opencode": (Path.home() / ".config" / "opencode" / "opencode.json",
                 lambda p, exe, force: upsert_json(p, exe, force, {}, ("mcp",)),
                 "opencode 用户级配置"),
    "codex": (Path.home() / ".codex" / "config.toml", upsert_codex,
              "Codex CLI 用户级配置"),
    "antigravity": (Path.home() / ".gemini" / "antigravity-acp" / "mcp.json",
                    lambda p, exe, force: upsert_json(p, exe, force, {}, ("mcpServers",)),
                    "Antigravity ACP 形态（Zed 等编辑器接入）"),
    "antigravity-ide": (Path.home() / ".gemini" / "config" / "mcp_config.json",
                        lambda p, exe, force: upsert_json(p, exe, force, {}, ("mcpServers",)),
                        "Antigravity 桌面 IDE / CLI / 2.0 全局"),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把 AOCI MCP（aoci.exe --repo 本仓 mcp）配置到 claude/opencode/codex/antigravity。")
    parser.add_argument("--agent", choices=sorted(TARGETS), help="只处理指定 agent（默认全部）")
    parser.add_argument("--exe", default=None, help="显式指定 aoci.exe 路径（默认自动探测）")
    parser.add_argument("--force", action="store_true", help="覆盖已有不一致的配置")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args()

    exe = Path(args.exe).resolve() if args.exe else find_aoci_exe()
    want_cmd, want_args = expected_binding(exe, REPO_ROOT)
    names = [args.agent] if args.agent else list(TARGETS)
    results = []
    for name in names:
        path, handler, desc = TARGETS[name]
        try:
            status = handler(path, exe, args.force)
        except Exception as exc:  # 单目标失败不影响其余目标
            status = "error: {}".format(exc)
        results.append({"agent": name, "path": str(path), "desc": desc, "status": status})

    if args.json:
        print(json.dumps({"aoci_exe": str(exe), "repo": str(REPO_ROOT),
                          "args": want_args, "results": results}, ensure_ascii=False, indent=2))
        return 0 if all(not r["status"].startswith("error") for r in results) else 1

    print("aoci.exe : {}".format(want_cmd))
    print("repo     : {}".format(REPO_ROOT))
    print("args     : {}".format(" ".join(want_args)))
    print("-" * 72)
    failed = False
    for r in results:
        mark = {"ok": "[OK]", "written": "[写入]", "written_new": "[新建]"}.get(r["status"], "[注意]")
        if r["status"].startswith("error"):
            mark, failed = "[失败]", True
        print("{} {:<12} {} ({})".format(mark, r["agent"], r["path"], r["status"]))
    print("-" * 72)
    print("提示：antigravity 需重启（或重新打开工作区）后 MCP 生效；其余 agent 下次会话自动生效。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
