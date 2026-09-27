# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 构建 file-sync-native（wails）
# 用法：uv run build.py

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAILS = Path(os.environ.get("USERPROFILE", "")) / "go" / "bin" / "wails.exe"


def main() -> int:
    r = subprocess.run([str(WAILS), "build"], cwd=str(ROOT))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
