# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 构建 exe-launcher.exe（GUI，隐藏控制台）
# 用法：uv run scripts/build.py

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    r = subprocess.run(
        ["go", "build", "-trimpath", "-ldflags", "-s -w -H windowsgui",
         "-o", "exe-launcher.exe", "./cmd/exe-launcher"],
        cwd=str(ROOT),
    )
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
