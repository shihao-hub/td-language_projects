# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 构建 aiquick 双产物：bin\aiquickd.exe（控制台守护）+ bin\aiquick.exe（GUI）
# 用法：uv run build.py

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = ROOT / "bin"
# MSYS2 ucrt64 的 gcc（CGO 需要）
GCC = Path(r"C:\msys64\ucrt64\bin")

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    if GCC.is_dir():
        os.environ["PATH"] = f"{GCC};{os.environ.get('PATH', '')}"

    BIN.mkdir(parents=True, exist_ok=True)

    r1 = subprocess.run(["go", "build", "-o", str(BIN / "aiquickd.exe"), "./cmd/aiquickd"], cwd=str(ROOT))
    if r1.returncode != 0:
        return r1.returncode
    r2 = subprocess.run(
        ["go", "build", "-ldflags", "-H windowsgui -s -w", "-o", str(BIN / "aiquick.exe"), "./cmd/aiquick"],
        cwd=str(ROOT),
    )
    if r2.returncode != 0:
        return r2.returncode
    print("build OK: bin\\aiquick.exe + bin\\aiquickd.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
