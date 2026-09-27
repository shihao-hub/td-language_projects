# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 构建 mcp-cleanup.exe（控制台程序，内嵌清理脚本，可从任意目录执行）
# 用法：uv run build.py

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    r = subprocess.run(
        ["go", "build", "-trimpath", "-ldflags", "-s -w", "-o", "mcp-cleanup.exe", "."],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        return r.returncode
    print(f"built: {ROOT / 'mcp-cleanup.exe'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
