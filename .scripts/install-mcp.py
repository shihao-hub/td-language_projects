# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
install-mcp.py：通用多 MCP 配置给多 Agent 的强化分发与管理工具

================================================================================
一、核心心智模型：双层开关驱动 + 全量收敛
================================================================================

脚本顶部有两层对称的常量总开关：
  • PRESET_ENABLED —— 每个预设 MCP 装不装：
      True  缺省执行时同步/修复到各启用 Agent（已装且一致则跳过，缺则补装）；
      False 从各启用 Agent 卸载该 MCP（不存在则自然跳过）；
  • AGENT_ENABLED —— 每家 Agent 参不参与（省内存利器）：
      True  正常参与预设收敛；False 不再部署任何内置预设，
      缺省收敛时还会清理该 Agent 的既有预设残留。

不带任何参数运行 = 按两层开关做一次【全量收敛】：
向启用 Agent 安装已启用预设，并卸载停用预设 / 停用 Agent 上的残留；
显式点名 --mcp <name>（强制安装预设）与 --agent <name>（强制处理该 Agent）
属于对两层开关的临时覆盖，供按需场景使用。

本工具支持【全 Agent 矩阵 × 多 MCP 服务】的双向解耦与灵活调度。
底层采用原子写入（tmp + os.replace）杜绝配置损坏，并使用正则安全更新 TOML / YAML 段落保留注释。

================================================================================
二、支持的 7 大 Agent 目标与其配置映射
================================================================================

• claude          -> ~/.claude.json                                (Claude Code 全局配置)
• opencode        -> ~/.config/opencode/opencode.json              (opencode 用户级配置)
• codex           -> ~/.codex/config.toml                          (Codex CLI 用户级 TOML)
• pi              -> ~/.pi/agent/mcp.json                          (pi coding agent 用户级配置，支持 exposure: direct)
• antigravity     -> ~/.gemini/antigravity-acp/mcp.json            (Antigravity ACP 后端形态)
• antigravity-ide -> ~/.gemini/config/mcp_config.json              (Antigravity 桌面 IDE / VSCode 插件全局配置)
• dsh             -> ~/.dsh/profiles/desktop/cordis.patch.yml      (DeepSeek Harness 桌面 Profile 配置)

【深入原理解析：关于 Antigravity (agy) 的三种形态与配置收敛】
用户日常可能接触到三种 Antigravity 形态：
  形态 1：Zed ACP —— Zed 编辑器或其他外部客户端通过 ACP 协议挂载 agy 后台守护进程。
          -> 读取: ~/.gemini/antigravity-acp/mcp.json （对应目标: antigravity）
  形态 2：VS Code 插件面板 —— 在标准 VS Code 中安装 Antigravity 插件所使用的面板。
          -> 读取: ~/.gemini/config/mcp_config.json   （工具缓存落盘于 ~/.gemini/antigravity/mcp/）
  形态 3：基于 VS Code 定制的 Antigravity 独立桌面 IDE 本体。
          -> 读取: ~/.gemini/config/mcp_config.json   （工具缓存落盘于 ~/.gemini/antigravity-ide/mcp/）
因此：
• 形态 2（VS Code 插件）与 形态 3（独立定制 IDE）在架构底层共享读取【同一个全局配置】~/.gemini/config/mcp_config.json！
• 脚本中的 antigravity-ide 即可同时满足形态 2 与形态 3；
• 配合 antigravity（形态 1），全套脚本仅需维护这两处，即可 100% 完整覆盖 agy 全部三种形态。

【关于 DeepSeek Harness (dsh) 接入 MCP 客户端】
DeepSeek Harness 采用 Cordis 微内核架构，通过 @deepseek-ai/dsh-mcp-client 插件加载外部 MCP 工具：
• 目标: dsh (~/.dsh/profiles/desktop/cordis.patch.yml)
• 机制: 声明式注入 mcp-<serverName> 补丁项；其 stdio 传输基于 @modelcontextprotocol
        客户端 + cross-spawn 启动，Windows 下可直接写 npx（.cmd shim 由 cross-spawn 解析）。

================================================================================
三、内置预设（受 PRESET_ENABLED 开关控制）
================================================================================

• aoci            : 智能探测本机 aoci.exe 安装路径并自动绑定当前仓库根目录
                    （--repo <REPO_ROOT> mcp），默认启用；
• chrome-devtools : npx -y chrome-devtools-mcp@latest，浏览器自动化调试与检测，
                    默认启用（Windows 下 claude / antigravity / antigravity-ide
                    自动套 cmd /c npx 包装，规避 .cmd shim 无 shell 解析问题）；
• everything      : 业界最佳实践 uvx everything-mcp，毫秒级全盘秒搜，自带敏感
                    路径黑名单与 Token 截断保护，默认停用（每个 Agent 会话各起
                    一份常驻进程，较占内存；需要时改开关为 True 或显式点名）；
• 自定义 MCP      : 支持通过 --custom-name / --custom-cmd / --custom-args
                    自由分发任意第三方 MCP 服务（自定义模式不参与收敛）。

================================================================================
四、常用指令与实测效果
================================================================================

① 查看所有 Agent 的 MCP 挂载状态矩阵（含各预设开关与漂移标记）：
   $ uv run .scripts/install-mcp.py --status
   -----------------------------------------------------------------------------
   Agent            aoci[开]   chrome-devtools[开]  everything[关]  Config Path
   -----------------------------------------------------------------------------
   antigravity      [✔ 已装]   [✔ 已装]             [· 未装]        ...
   -----------------------------------------------------------------------------

② 全量收敛（缺省行为，完全按 PRESET_ENABLED × AGENT_ENABLED 两层开关执行）：
   # 向启用 Agent 安装已启用预设；卸载停用预设与停用 Agent 上的残留
   $ uv run .scripts/install-mcp.py
   # 停用某家 Agent（如不用 pi 了）：AGENT_ENABLED 中置 False，
   # 缺省收敛会清空其内置预设；再置回 True 即按预设开关重新补装

③ 显式安装/恢复某预设到指定 Agent（覆盖开关，供按需临时使用）：
   $ uv run .scripts/install-mcp.py --mcp everything --agent dsh claude

④ 强制覆盖已有但不一致的配置：
   $ uv run .scripts/install-mcp.py --force

⑤ 卸载指定 MCP 服务：
   $ uv run .scripts/install-mcp.py --remove everything

⑥ 机器可读 JSON 输出：
   $ uv run .scripts/install-mcp.py --json

⑦ 兼容老入口：
   $ uv run .scripts/install-aoci-mcp.py  # 内部已重构为本脚本的转发代理
"""
import argparse
import errno
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows 终端输出 UTF-8 编码防乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# 用户开关区（打开文件即见；以下两层总开关是收敛行为的唯一修改入口）
# ===========================================================================
# 第一层：PRESET_ENABLED —— 每个预设 MCP 装不装：
#   True  = 缺省执行时同步/修复到各启用 Agent（已装且一致则跳过，缺则补装）；
#   False = 从各启用 Agent 卸载该 MCP（不存在则自然跳过）。
PRESET_ENABLED: Dict[str, bool] = {
    "aoci": True,
    "chrome-devtools": False,  # 每 Agent 一份常驻 node（调工具还会起 Chrome），占内存，默认关闭
    "everything": False,   # 每个 Agent 会话各起一份常驻进程，较占内存，默认关闭
}

# 第二层：AGENT_ENABLED —— 每家 Agent 参不参与（省内存利器）：
#   True  = 该 Agent 正常参与预设收敛（具体装哪些由 PRESET_ENABLED 决定）；
#   False = 该 Agent 不再部署任何内置预设，缺省收敛时会清理其既有预设残留；
#           显式 --agent 点名可临时覆盖本开关（会打印提示）。
AGENT_ENABLED: Dict[str, bool] = {
    "claude": True,
    "opencode": True,
    "codex": True,
    "pi": True,
    "antigravity": True,
    "antigravity-ide": True,
    "dsh": True,
}


def agent_is_enabled(name: str) -> bool:
    """Agent 开关查询（未列出的 Agent 默认按启用处理）。"""
    return AGENT_ENABLED.get(name, True)


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def norm(p: Any) -> str:
    """路径与命令等价归一化（统一反斜杠与小写，用于跨平台/Windows一致性比对）。"""
    if p is None:
        return ""
    return str(p).replace("/", "\\").lower()


def read_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}  # 空文件视为空字典
    try:
        return json.loads(text)
    except Exception:
        return None


def write_text_atomic(path: Path, text: str) -> None:
    """尽力原子写入文本：临时文件 + os.replace，杜绝半写中断破坏配置。

    Windows 下目标文件可能被运行中的 Agent（如 opencode）持有句柄，
    导致 os.replace 报拒绝访问；此时降级为原地覆写并清理临时文件。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError as e:
        if e.errno not in (errno.EACCES, errno.EPERM):
            raise
        # 目标被占用无法替换，降级原地覆写；失败时尽力恢复原内容
        old = path.read_text(encoding="utf-8") if path.is_file() else None
        try:
            path.write_text(text, encoding="utf-8")
        except OSError:
            if old is not None:
                try:
                    path.write_text(old, encoding="utf-8")
                except OSError:
                    pass
            raise
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass


def write_json_atomic(path: Path, data: dict) -> None:
    """原子写入 JSON：临时文件 + os.replace，杜绝半写中断破坏配置。"""
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------------------
# MCP Server 定义模型
# ---------------------------------------------------------------------------
@dataclass
class MCPSpec:
    name: str
    description: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    type: str = "stdio"
    extra_by_agent: Dict[str, dict] = field(default_factory=dict)  # 特定 agent 附加字段，如 pi: {"exposure": "direct"}
    command_by_agent: Dict[str, str] = field(default_factory=dict)  # 特定 agent 覆盖启动命令（如 Windows 需要 cmd /c 包装）
    args_by_agent: Dict[str, List[str]] = field(default_factory=dict)  # 特定 agent 覆盖启动参数（需与 command 覆写配套）


def spec_for_agent(spec: MCPSpec, agent: str) -> MCPSpec:
    """返回套用 agent 专属 command/args 覆写后的规格（无覆写时原样返回）。"""
    cmd = spec.command_by_agent.get(agent)
    args = spec.args_by_agent.get(agent)
    if cmd is None and args is None:
        return spec
    return replace(
        spec,
        command=cmd if cmd is not None else spec.command,
        args=args if args is not None else spec.args,
    )


# ---------------------------------------------------------------------------
# 预设 MCP 探测与构建
# ---------------------------------------------------------------------------
AOCI_EXE_CANDIDATES = [
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\aoci\aoci.exe")),
    Path.home() / "AppData" / "Local" / "Programs" / "aoci" / "aoci.exe",
]


def resolve_aoci_spec(repo_root: Path = REPO_ROOT, explicit_exe: Optional[str] = None) -> MCPSpec:
    exe_path: Optional[Path] = None
    if explicit_exe:
        exe_path = Path(explicit_exe).resolve()
    else:
        for cand in AOCI_EXE_CANDIDATES:
            if cand.is_file():
                exe_path = cand
                break
        if not exe_path:
            found = shutil.which("aoci") or shutil.which("aoci.exe")
            if found:
                exe_path = Path(found)

    if not exe_path or not exe_path.exists():
        exe_path = AOCI_EXE_CANDIDATES[0]

    return MCPSpec(
        name="aoci",
        description="AOCI 索引感知（本仓库代码上下文）",
        command=str(exe_path),
        args=["--repo", str(repo_root), "mcp"],
        extra_by_agent={"pi": {"exposure": "direct"}}
    )


def resolve_chrome_devtools_spec() -> MCPSpec:
    """Chrome DevTools MCP（浏览器自动化调试）。

    Windows 兼容说明：npx 是 .cmd shim，部分 Agent（claude / antigravity 系）
    的 stdio 传输不带 shell 解析，故对这些 Agent 自动套 `cmd /c npx` 包装；
    opencode / pi / codex / dsh 的启动器可自行解析 .cmd（dsh 底层为 cross-spawn），
    直接使用 npx 即可。
    """
    base_args = ["-y", "chrome-devtools-mcp@latest"]
    wrap_agents = ("claude", "antigravity", "antigravity-ide")
    return MCPSpec(
        name="chrome-devtools",
        description="Chrome DevTools MCP（浏览器自动化调试：导航、截图、console/network）",
        command="npx",
        args=list(base_args),
        command_by_agent={a: "cmd" for a in wrap_agents},
        args_by_agent={a: ["/c", "npx", *base_args] for a in wrap_agents},
        extra_by_agent={"pi": {"exposure": "direct"}},
    )


def resolve_everything_spec() -> MCPSpec:
    cmd = "uvx"
    env = {}
    return MCPSpec(
        name="everything",
        description="Voidtools Everything 全盘秒级文件发现（带安全黑名单与 Token 保护）",
        command=cmd,
        args=["everything-mcp"],
        env=env,
        extra_by_agent={"pi": {"exposure": "direct"}}
    )


# ---------------------------------------------------------------------------
# 预设 MCP 总开关已上移至文件顶部「用户开关区」，此处仅保留预设构建入口
# ---------------------------------------------------------------------------
def build_preset_spec(name: str, aoci_exe: Optional[str] = None) -> Optional[MCPSpec]:
    """按预设名构建 MCPSpec；未知预设返回 None。"""
    if name == "aoci":
        return resolve_aoci_spec(REPO_ROOT, aoci_exe)
    if name == "chrome-devtools":
        return resolve_chrome_devtools_spec()
    if name == "everything":
        return resolve_everything_spec()
    return None


# ---------------------------------------------------------------------------
# 各 Agent 配置处理器
# ---------------------------------------------------------------------------
class AgentHandler:
    def __init__(self, name: str, config_path: Path, description: str):
        self.name = name
        self.config_path = config_path
        self.description = description

    def get_server(self, mcp_name: str) -> Optional[dict]:
        raise NotImplementedError

    def upsert_server(self, spec: MCPSpec, force: bool) -> str:
        """返回状态：ok / written / written_new / skipped_mismatch / error:*"""
        raise NotImplementedError

    def remove_server(self, mcp_name: str) -> str:
        """返回状态：removed / not_found / error:*"""
        raise NotImplementedError


class JsonAgentHandler(AgentHandler):
    def __init__(self, name: str, config_path: Path, description: str, key_path: Tuple[str, ...]):
        super().__init__(name, config_path, description)
        self.key_path = key_path

    def _locate_servers_table(self, data: dict, create: bool = False) -> Optional[dict]:
        node = data
        for key in self.key_path[:-1]:
            child = node.get(key)
            if not isinstance(child, dict):
                if create:
                    child = {}
                    node[key] = child
                else:
                    return None
            node = child
        table_key = self.key_path[-1]
        child = node.get(table_key)
        if not isinstance(child, dict):
            if create:
                child = {}
                node[table_key] = child
            else:
                return None
        return node[table_key]

    def get_server(self, mcp_name: str) -> Optional[dict]:
        data = read_json(self.config_path)
        if not data:
            return None
        servers = self._locate_servers_table(data, create=False)
        if servers and mcp_name in servers and isinstance(servers[mcp_name], dict):
            return servers[mcp_name]
        return None

    def _match_server(self, existing: dict, spec: MCPSpec, extra: dict) -> bool:
        """判断已有条目的 command/args/env 与附加字段是否与目标 spec 一致。"""
        cmd = existing.get("command")
        args = existing.get("args") or []
        if isinstance(cmd, list):
            cmd_args, cmd = cmd[1:], cmd[0]
        else:
            cmd_args = args

        cmd_match = norm(cmd) == norm(spec.command)
        args_match = [norm(a) for a in cmd_args] == [norm(a) for a in spec.args]
        extra_match = all(existing.get(k) == v for k, v in extra.items())
        env_match = existing.get("env", {}) == spec.env if spec.env else True
        return cmd_match and args_match and extra_match and env_match

    def _build_entry(self, spec: MCPSpec, extra: dict) -> dict:
        """按该 Agent 的配置格式构建 MCP 条目。"""
        entry = {
            "type": spec.type,
            "command": spec.command,
            "args": spec.args,
        }
        if spec.env:
            entry["env"] = spec.env
        if extra:
            entry.update(extra)
        return entry

    def upsert_server(self, spec: MCPSpec, force: bool) -> str:
        data = read_json(self.config_path)
        created = data is None
        if created:
            data = {}

        servers = self._locate_servers_table(data, create=True)
        if servers is None:
            return "error: 配置文件结构异常，无法定位 MCP 服务器表"

        extra = spec.extra_by_agent.get(self.name, {})

        # 一致性校验
        if spec.name in servers and isinstance(servers[spec.name], dict):
            if self._match_server(servers[spec.name], spec, extra):
                return "ok"
            if not force:
                return "skipped_mismatch"

        # 写入条目
        servers[spec.name] = self._build_entry(spec, extra)
        write_json_atomic(self.config_path, data)
        return "written_new" if created else "written"

    def remove_server(self, mcp_name: str) -> str:
        data = read_json(self.config_path)
        if not data:
            return "not_found"
        servers = self._locate_servers_table(data, create=False)
        if not servers or mcp_name not in servers:
            return "not_found"
        del servers[mcp_name]
        write_json_atomic(self.config_path, data)
        return "removed"


class OpencodeJsonHandler(JsonAgentHandler):
    """opencode 专用处理器（条目格式与其他 Agent 不同）。

    opencode 的 MCP 条目要求：
    • type 必须为 "local"（而非 "stdio"）；
    • command 为数组 [命令, 参数...]，无独立 args 字段；
    • 必须显式声明 enabled 字段；
    • 环境变量字段名为 environment（而非 env）。
    参考: https://opencode.ai/docs/mcp-servers/
    """

    def _match_server(self, existing: dict, spec: MCPSpec, extra: dict) -> bool:
        if existing.get("type") != "local":
            return False
        cmd = existing.get("command")
        if not isinstance(cmd, list) or not cmd:
            return False

        cmd_match = norm(cmd[0]) == norm(spec.command)
        args_match = [norm(a) for a in cmd[1:]] == [norm(a) for a in spec.args]
        enabled_match = existing.get("enabled") is True
        env_match = existing.get("environment", {}) == spec.env if spec.env else True
        return cmd_match and args_match and enabled_match and env_match

    def _build_entry(self, spec: MCPSpec, extra: dict) -> dict:
        entry = {
            "type": "local",
            "command": [spec.command] + list(spec.args),
            "enabled": True,
        }
        if spec.env:
            entry["environment"] = spec.env
        if extra:
            entry.update(extra)
        return entry


class CodexTomlHandler(AgentHandler):
    """专门处理 ~/.codex/config.toml 配置。采用精准正则保留其它段落与注释。"""

    def __init__(self, name: str = "codex", config_path: Optional[Path] = None, description: str = "Codex CLI 用户级配置"):
        super().__init__(name, config_path or (Path.home() / ".codex" / "config.toml"), description)

    def _get_section_block(self, text: str, mcp_name: str) -> Optional[List[str]]:
        target_section = f"[mcp_servers.{mcp_name}]"
        lines = text.splitlines()
        in_sec = False
        sec_lines = []
        for line in lines:
            stripped = line.strip()
            if re.fullmatch(r"\[[^\]]+\]", stripped):
                if in_sec:
                    break
                in_sec = (stripped == target_section)
                continue
            if in_sec:
                sec_lines.append(line)
        return sec_lines if in_sec else None

    def get_server(self, mcp_name: str) -> Optional[dict]:
        if not self.config_path.is_file():
            return None
        text = self.config_path.read_text(encoding="utf-8")
        sec_lines = self._get_section_block(text, mcp_name)
        if sec_lines is None:
            return None
        res = {"command": "", "args": []}
        for l in sec_lines:
            s = l.strip()
            if s.startswith("command"):
                parts = s.split("=", 1)
                if len(parts) == 2:
                    res["command"] = parts[1].strip().strip("'\"")
            elif s.startswith("args"):
                parts = s.split("=", 1)
                if len(parts) == 2:
                    try:
                        res["args"] = json.loads(parts[1].strip().replace("'", '"'))
                    except Exception:
                        pass
        return res

    def upsert_server(self, spec: MCPSpec, force: bool) -> str:
        text = self.config_path.read_text(encoding="utf-8") if self.config_path.is_file() else ""
        sec_lines = self._get_section_block(text, spec.name)
        target_section = f"[mcp_servers.{spec.name}]"

        if sec_lines is not None:
            cmd_ok = any(norm(line.split("=", 1)[1].strip().strip("'\"")) == norm(spec.command)
                         for line in sec_lines if line.strip().startswith("command"))
            args_str = " ".join([norm(a) for a in spec.args])
            sec_joined = " ".join([norm(l) for l in sec_lines])
            args_ok = all(norm(a) in sec_joined for a in spec.args)

            if cmd_ok and args_ok:
                return "ok"
            if not force:
                return "skipped_mismatch"

            self.remove_server(spec.name)
            text = self.config_path.read_text(encoding="utf-8") if self.config_path.is_file() else ""

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        args_json = json.dumps(spec.args, ensure_ascii=False)
        block = f"\n{target_section}\ncommand = '{spec.command}'\nargs = {args_json}\n"
        if spec.env:
            env_json = json.dumps(spec.env, ensure_ascii=False)
            block += f"env = {env_json}\n"

        with open(self.config_path, "a", encoding="utf-8") as f:
            f.write(block if text.endswith("\n") or not text else "\n" + block)
        return "written"

    def remove_server(self, mcp_name: str) -> str:
        if not self.config_path.is_file():
            return "not_found"
        text = self.config_path.read_text(encoding="utf-8")
        target_section = f"[mcp_servers.{mcp_name}]"
        if target_section not in text:
            return "not_found"

        lines = text.splitlines(keepends=True)
        new_lines = []
        in_sec = False
        for line in lines:
            stripped = line.strip()
            if re.fullmatch(r"\[[^\]]+\]", stripped):
                if in_sec:
                    in_sec = False
                elif stripped == target_section:
                    in_sec = True
                    continue
            if not in_sec:
                new_lines.append(line)

        self.config_path.write_text("".join(new_lines), encoding="utf-8")
        return "removed"


class DshAgentHandler(AgentHandler):
    """DeepSeek Harness (dsh) 专用处理器。
    目标配置文件：~/.dsh/profiles/desktop/cordis.patch.yml
    通过 @deepseek-ai/dsh-mcp-client 插件接入 stdio MCP 服务。
    """

    def __init__(self, name: str = "dsh", config_path: Optional[Path] = None, description: str = "DeepSeek Harness 桌面 Profile 配置"):
        super().__init__(name, config_path or (Path.home() / ".dsh" / "profiles" / "desktop" / "cordis.patch.yml"), description)

    def _find_entry_bounds(self, lines: List[str], mcp_name: str) -> Optional[Tuple[int, int]]:
        """定位 mcp-{mcp_name} 条目的起始行和结束行。

        支持两种位置：
        1. insert 列表内（正确写法）：`    - id: mcp-xxx`（4 空格缩进）；
        2. 顶层补丁项（历史遗留错误写法）：`- id: mcp-xxx`，仅用于识别并迁移。
        结束边界为下一条同级条目 / 顶级 `- ` 条目 / 文件尾。
        """
        target_ids = (f"id: mcp-{mcp_name}",)
        start_idx = -1
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("- id:") and any(t in stripped for t in target_ids):
                start_idx = idx
                break
        if start_idx == -1:
            return None

        # 同级条目的缩进（"- id:" 前的空格数）
        indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        end_idx = len(lines)
        for idx in range(start_idx + 1, len(lines)):
            line = lines[idx]
            stripped = line.strip()
            # 同级或更高级的新条目边界
            cur_indent = len(line) - len(line.lstrip())
            if stripped.startswith("- ") and cur_indent <= indent:
                end_idx = idx
                break
        return (start_idx, end_idx)

    def get_server(self, mcp_name: str) -> Optional[dict]:
        if not self.config_path.is_file():
            return None
        text = self.config_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        bounds = self._find_entry_bounds(lines, mcp_name)
        if bounds is None:
            return None
        cmd = ""
        args = []
        for line in lines[bounds[0]:bounds[1]]:
            stripped = line.strip()
            if stripped.startswith("command:"):
                cmd = stripped.split(":", 1)[1].strip().strip("'\"")
            elif stripped.startswith("- ") and "command:" not in stripped and "name:" not in stripped:
                args.append(stripped[2:].strip().strip("'\""))
        return {"command": cmd, "args": args}

    def _find_insert_range(self, lines: List[str]) -> Optional[Tuple[int, int]]:
        """定位顶级 `- insert:` 列表的行范围 [列表头行, 列表结束边界行)。"""
        for idx, line in enumerate(lines):
            if re.match(r"^-\s+insert:\s*$", line):
                end = len(lines)
                for j in range(idx + 1, len(lines)):
                    if lines[j].startswith("- ") or (lines[j].strip() and not lines[j][0].isspace()):
                        end = j
                        break
                return (idx, end)
        return None

    def _render_insert_block(self, spec: MCPSpec) -> str:
        """渲染 insert 列表内的条目块（`- id:` 缩进 4 空格）。"""
        args_yaml = "\n".join([f"          - '{a}'" if (":" in a or "\\" in a or " " in a) else f"          - {a}" for a in spec.args])
        cmd_val = f"'{spec.command}'" if ("\\" in spec.command or " " in spec.command) else spec.command
        block = (
            f"    - id: mcp-{spec.name}\n"
            f"      name: '@deepseek-ai/dsh-mcp-client'\n"
            f"      config:\n"
            f"        serverName: {spec.name}\n"
            f"        transport: stdio\n"
            f"        command: {cmd_val}\n"
        )
        if spec.args:
            block += f"        args:\n{args_yaml}\n"
        if spec.env:
            block += "        env:\n"
            for k, v in spec.env.items():
                block += f"          {k}: '{v}'\n"
        return block

    def upsert_server(self, spec: MCPSpec, force: bool) -> str:
        if not self.config_path.is_file():
            base_text = "# Your patch layer for this dsh profile.\n\n- insert:\n"
        else:
            base_text = self.config_path.read_text(encoding="utf-8")
        lines = base_text.splitlines(keepends=True)
        lines_no_ends = [l.rstrip("\r\n") for l in lines]
        bounds = self._find_entry_bounds(lines_no_ends, spec.name)

        if bounds is not None:
            old_block = "".join(lines[bounds[0]:bounds[1]])
            cmd_ok = norm(spec.command) in norm(old_block)
            args_ok = all(norm(a) in norm(old_block) for a in spec.args)
            already_in_insert = lines[bounds[0]].startswith("    - id:")
            if cmd_ok and args_ok and already_in_insert:
                return "ok"
            if not force and not already_in_insert:
                # 历史遗留的顶层写法不生效，直接视为需要迁移修复
                pass
            if (cmd_ok and args_ok) or force:
                del lines[bounds[0]:bounds[1]]
            elif not force:
                return "skipped_mismatch"

        new_block = self._render_insert_block(spec)

        # 追加到顶级 `- insert:` 列表末尾；不存在则新建
        ins_range = self._find_insert_range([l.rstrip("\r\n") for l in lines])
        if ins_range is None:
            clean_lines = "".join(lines).rstrip() + "\n\n- insert:\n" + new_block
        else:
            pos = ins_range[1]
            lines.insert(pos, new_block)
            clean_lines = "".join(lines)
        write_text_atomic(self.config_path, clean_lines)
        return "written"

    def remove_server(self, mcp_name: str) -> str:
        if not self.config_path.is_file():
            return "not_found"
        text = self.config_path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        lines_no_ends = [l.rstrip("\r\n") for l in lines]
        bounds = self._find_entry_bounds(lines_no_ends, mcp_name)
        if bounds is None:
            return "not_found"
        del lines[bounds[0]:bounds[1]]
        clean_lines = "".join(lines).rstrip() + "\n"
        write_text_atomic(self.config_path, clean_lines)
        return "removed"


# ---------------------------------------------------------------------------
# 全局 Agent 目标注册表（支持 7 大 Agent）
# ---------------------------------------------------------------------------
TARGET_AGENTS: Dict[str, AgentHandler] = {
    "claude": JsonAgentHandler("claude", Path.home() / ".claude.json", "Claude Code 用户级全局配置", ("mcpServers",)),
    "opencode": OpencodeJsonHandler("opencode", Path.home() / ".config" / "opencode" / "opencode.json", "opencode 用户级配置", ("mcp",)),
    "codex": CodexTomlHandler("codex", Path.home() / ".codex" / "config.toml", "Codex CLI 用户级配置"),
    "pi": JsonAgentHandler("pi", Path.home() / ".pi" / "agent" / "mcp.json", "pi coding agent 用户级配置", ("mcpServers",)),
    "antigravity": JsonAgentHandler("antigravity", Path.home() / ".gemini" / "antigravity-acp" / "mcp.json", "Antigravity ACP 形态（Zed 接入）", ("mcpServers",)),
    "antigravity-ide": JsonAgentHandler("antigravity-ide", Path.home() / ".gemini" / "config" / "mcp_config.json", "Antigravity 桌面 IDE / VSCode 插件全局", ("mcpServers",)),
    "dsh": DshAgentHandler("dsh", Path.home() / ".dsh" / "profiles" / "desktop" / "cordis.patch.yml", "DeepSeek Harness 桌面 Profile 配置"),
}


# Agent 级总开关已上移至文件顶部「用户开关区」（AGENT_ENABLED / agent_is_enabled）


# ---------------------------------------------------------------------------
# CLI 主逻辑
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="通用多 MCP 配置给多 Agent 的强化分发与管理工具（PRESET_ENABLED / AGENT_ENABLED 双层开关驱动：缺省全量收敛，显式点名临时覆盖）"
    )
    parser.add_argument("--mcp", nargs="+", default=None,
                        help="显式点名要强制安装的预设 MCP（aoci / chrome-devtools / everything）；"
                             "all 或省略 = 按 PRESET_ENABLED 全量收敛（启用则安装、停用则卸载）")
    parser.add_argument("--agent", nargs="+", choices=sorted(TARGET_AGENTS.keys()),
                        help="只处理指定的 Agent（显式点名=临时覆盖 AGENT_ENABLED；缺省处理全部）")
    parser.add_argument("--status", "--list", dest="show_status", action="store_true",
                        help="打印所有 Agent 当前各 MCP 服务的配置状态矩阵")
    parser.add_argument("--remove", metavar="MCP_NAME",
                        help="从选定的 Agent 中卸载指定的 MCP 服务")
    parser.add_argument("--force", action="store_true",
                        help="覆盖已有但不一致的配置")
    parser.add_argument("--json", action="store_true",
                        help="以结构化 JSON 输出结果")
    # 自定义 MCP 参数
    parser.add_argument("--custom-name", help="自定义 MCP 名称")
    parser.add_argument("--custom-cmd", help="自定义 MCP 启动命令")
    parser.add_argument("--custom-args", nargs="*", default=[], help="自定义 MCP 启动参数")
    # 针对 aoci 的特别参数
    parser.add_argument("--aoci-exe", default=None, help="显式指定 aoci.exe 路径")

    args = parser.parse_args()

    # 1. 确定目标 Agents（--agent 显式点名 = 临时覆盖 AGENT_ENABLED）
    explicit_agents = args.agent is not None
    if explicit_agents:
        agent_keys = list(args.agent)
        for a_key in agent_keys:
            if not agent_is_enabled(a_key):
                print(f"[提示] Agent [{a_key}] 开关为关闭（AGENT_ENABLED=False），本次因显式点名仍会处理"
                      f"（缺省收敛时会清理其预设）。", file=sys.stderr)
    else:
        agent_keys = sorted(TARGET_AGENTS.keys())

    # 2. 构建待操作的 MCPSpec 清单与执行模式
    #    显式点名（--mcp 且不含 all） = 对开关的临时覆盖（强制安装）；
    #    缺省 / --mcp all            = 按 PRESET_ENABLED 全量收敛（启用安装 / 停用卸载）。
    custom_mode = bool(args.custom_name and args.custom_cmd)
    explicit_install = args.mcp is not None and not custom_mode and "all" not in args.mcp
    specs: List[MCPSpec] = []
    if custom_mode:
        specs.append(MCPSpec(
            name=args.custom_name,
            description="自定义 MCP",
            command=args.custom_cmd,
            args=args.custom_args
        ))
    else:
        mcp_names = args.mcp if explicit_install else list(PRESET_ENABLED.keys())
        for name in mcp_names:
            spec = build_preset_spec(name, args.aoci_exe)
            if spec is None:
                print(f"[WARN] 未知 MCP 预设: {name}（跳过）", file=sys.stderr)
            else:
                specs.append(spec)

    # -----------------------------------------------------------------------
    # 操作分支 A: 查看状态矩阵 (--status / --list)
    # -----------------------------------------------------------------------
    if args.show_status:
        preset_names = list(PRESET_ENABLED.keys())
        matrix = []
        for a_key in agent_keys:
            handler = TARGET_AGENTS[a_key]
            agent_on = agent_is_enabled(a_key)
            row = {"agent": a_key, "enabled": agent_on, "path": str(handler.config_path), "presets": {}}
            for m_name in preset_names:
                installed = handler.get_server(m_name) is not None
                row["presets"][m_name] = {
                    "enabled": PRESET_ENABLED[m_name] and agent_on,  # 有效状态 = 预设开关 × Agent 开关
                    "installed": installed,
                }
            matrix.append(row)

        if args.json:
            print(json.dumps(matrix, ensure_ascii=False, indent=2))
            return 0

        def drift_mark(enabled: bool, installed: bool) -> str:
            """状态标记：漂移（有效开关与现状不一致）一眼可见。"""
            if enabled and installed:
                return "[✔ 已装]"
            if enabled:
                return "[- 未装]"
            if installed:
                return "[! 待卸载]"
            return "[· 未装]"

        headers = [f"{m}[{'开' if PRESET_ENABLED[m] else '关'}]" for m in preset_names]
        col_w = [max(len(h) + 2, 10) for h in headers]
        agent_w = max(16, max(len(r["agent"]) + (5 if not r["enabled"] else 0) for r in matrix))
        title = f"{'Agent':<{agent_w}} " + " ".join(h.ljust(w) for h, w in zip(headers, col_w)) + "Config Path"
        width = max(84, len(title) + 8)
        print("=" * width)
        print(title)
        print("-" * width)
        for r in matrix:
            cells = " ".join(
                drift_mark(r["presets"][m]["enabled"], r["presets"][m]["installed"]).ljust(w)
                for m, w in zip(preset_names, col_w)
            )
            agent_label = r["agent"] if r["enabled"] else f"{r['agent']}[停用]"
            print(f"{agent_label:<{agent_w}} {cells}{r['path']}")
        print("=" * width)
        print("提示：预设开关 PRESET_ENABLED：True=收敛安装 / False=收敛卸载；")
        print("      Agent 开关 AGENT_ENABLED：True=参与收敛 / False=不部署并清理残留（[停用] 行）。")
        return 0

    # -----------------------------------------------------------------------
    # 操作分支 B: 移除 MCP (--remove)
    # -----------------------------------------------------------------------
    if args.remove:
        remove_results = []
        for a_key in agent_keys:
            handler = TARGET_AGENTS[a_key]
            status = handler.remove_server(args.remove)
            remove_results.append({"agent": a_key, "mcp": args.remove, "status": status, "path": str(handler.config_path)})

        if args.json:
            print(json.dumps(remove_results, ensure_ascii=False, indent=2))
            return 0

        print(f"[-] 正在从各 Agent 中移除 MCP 服务 [{args.remove}]:")
        for r in remove_results:
            mark = "[已移除]" if r["status"] == "removed" else "[未配置]"
            print(f"  {mark:<8} {r['agent']:<16} {r['path']}")
        return 0

    # -----------------------------------------------------------------------
    # 操作分支 C: 安装 / 全量收敛配置 (默认)
    # -----------------------------------------------------------------------
    if custom_mode:
        mode_desc = "显式安装（自定义 MCP）"
    elif explicit_install:
        mode_desc = "显式安装（临时覆盖 PRESET_ENABLED 开关）"
    else:
        mode_desc = "全量收敛（按 PRESET_ENABLED：安装已启用 / 卸载已停用）"

    if explicit_install:
        for spec in specs:
            if not PRESET_ENABLED.get(spec.name, False):
                print(f"[提示] 预设 [{spec.name}] 开关为关闭，本次因显式点名仍会安装（缺省收敛时会将其卸载）。",
                      file=sys.stderr)

    # 3. 计划化：逐 (预设, Agent) 决定 install / remove
    #    - 停用 Agent 不接收任何内置预设，缺省收敛会清理其残留；
    #    - 显式安装（自定义 / --mcp 点名）默认跳过停用 Agent，--agent 点名可强制覆盖。
    jobs: List[Tuple[str, MCPSpec, str]] = []
    if custom_mode or explicit_install:
        skipped_agents = []
        for a_key in agent_keys:
            if not explicit_agents and not agent_is_enabled(a_key):
                skipped_agents.append(a_key)
                continue
            for spec in specs:
                jobs.append(("install", spec, a_key))
        if skipped_agents:
            print(f"[提示] Agent 开关为关闭，显式安装已跳过: {', '.join(skipped_agents)}"
                  f"（如需强制请用 --agent 点名）。", file=sys.stderr)
    else:
        for spec in specs:
            preset_on = PRESET_ENABLED.get(spec.name, False)
            for a_key in agent_keys:
                if not explicit_agents and not agent_is_enabled(a_key):
                    jobs.append(("remove", spec, a_key))  # 停用 Agent：清理全部内置预设
                else:
                    jobs.append(("install" if preset_on else "remove", spec, a_key))

    results = []
    failed = False
    for action, spec, a_key in jobs:
        handler = TARGET_AGENTS[a_key]
        eff = spec_for_agent(spec, a_key)
        try:
            if action == "install":
                status = handler.upsert_server(eff, args.force)
            else:
                status = handler.remove_server(spec.name)
        except Exception as e:
            status = f"error: {e}"
            failed = True
        results.append({
            "mcp": spec.name,
            "agent": a_key,
            "action": action,
            "path": str(handler.config_path),
            "desc": handler.description,
            "status": status,
            "command": eff.command,
            "args": eff.args
        })

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1 if failed else 0

    print("=" * 84)
    print("多 MCP -> 多 Agent 通用配置管理工具（覆盖 7 大 Agent 目标）")
    print(f"工作区仓库 : {REPO_ROOT}")
    print(f"执行模式   : {mode_desc}")
    if not (custom_mode or explicit_install):
        print("预设开关   : " + "  ".join(f"{n}={'开' if e else '关'}" for n, e in PRESET_ENABLED.items()))
        if explicit_agents:
            print("Agent 范围 : 显式点名（临时覆盖 AGENT_ENABLED）")
        else:
            disabled = [a for a in agent_keys if not agent_is_enabled(a)]
            print("Agent 开关 : " + ("全部开启" if not disabled else "停用 " + ", ".join(disabled) + "（其预设将被清理）"))
    elif explicit_agents:
        print("Agent 范围 : 显式点名（临时覆盖 AGENT_ENABLED）")
    for spec in specs:
        args_display = " ".join(spec.args) if spec.args else "(none)"
        print(f"• MCP [{spec.name}]: {spec.command} {args_display} ({spec.description})")
    print("-" * 84)

    for r in results:
        if r["action"] == "install":
            mark = {
                "ok": "[OK-存在]",
                "written": "[写入成功]",
                "written_new": "[新建配置]",
                "skipped_mismatch": "[跳过-冲突]"
            }.get(r["status"], "[异常]")
            if r["status"].startswith("error"):
                mark = "[失败]"
        else:
            mark = {"removed": "[已卸载]", "not_found": "[无需卸载]"}.get(r["status"], "[异常]")
            if r["status"].startswith("error"):
                mark = "[失败]"

        print(f"{mark:<11} {r['mcp']:<16} -> {r['agent']:<15} {r['path']}")

    print("-" * 84)
    print("提示：")
    print("1. antigravity 需重启或重新打开工作区后生效；")
    print("2. pi 已运行的会话可输入 /reload 立即生效；")
    print("3. dsh (DeepSeek Harness) 重启桌面应用或命令行后生效；")
    print("4. 其余 Agent（Claude Code、Codex、opencode）在下次启动或新建会话时自动载入；")
    print("5. 预设开关 PRESET_ENABLED（装不装）与 Agent 开关 AGENT_ENABLED（参不参与）在脚本顶部修改。")
    print("=" * 84)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
