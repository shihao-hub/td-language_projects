# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# install-aoci-mcp.py：把本仓库的 AOCI MCP（aoci.exe --repo <本仓> mcp）统一配置到
# claude code / opencode / codex / pi / antigravity（ACP 与桌面 IDE 两个形态）的用户级配置文件。
#
# 注意：本脚本已接入通用的多 MCP 分发框架 .scripts/install-mcp.py。
# 若需分发或管理更多 MCP（如 Everything、自定义工具等），推荐直接使用：
#   uv run .scripts/install-mcp.py --status
#   uv run .scripts/install-mcp.py --mcp everything
import subprocess
import sys
from pathlib import Path

INSTALL_MCP = Path(__file__).resolve().parent / "install-mcp.py"


def main() -> int:
    cmd = [sys.executable, str(INSTALL_MCP), "--mcp", "aoci"]
    # 转发命令行参数，映射 --exe 到 --aoci-exe
    idx = 1
    argv = sys.argv[1:]
    while idx <= len(argv):
        arg = argv[idx - 1]
        if arg == "--exe" and idx < len(argv):
            cmd.extend(["--aoci-exe", argv[idx]])
            idx += 2
            continue
        elif arg.startswith("--exe="):
            cmd.append("--aoci-exe=" + arg.split("=", 1)[1])
            idx += 1
            continue
        cmd.append(arg)
        idx += 1

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
