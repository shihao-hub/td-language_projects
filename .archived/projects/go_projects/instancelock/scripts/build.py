# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# instancelock 构建脚本：注入版本号并生成 SHA256SUMS
# 用法：uv run scripts/build.py [--version X.Y.Z]（默认 dev）

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
OUT_REL = r"build\instancelock-windows-amd64.exe"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 instancelock 并生成 SHA256SUMS")
    parser.add_argument("--version", default="dev", help="版本号（默认 dev）")
    args = parser.parse_args()

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_DIR / "instancelock-windows-amd64.exe"

    r = subprocess.run(
        ["go", "build", "-ldflags", f"-X main.version={args.version}",
         "-o", str(out), "./cmd/instancelock"],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode != 0:
        print(f"go build 失败（exit {r.returncode}）", file=sys.stderr)
        return r.returncode

    digest = hashlib.sha256(out.read_bytes()).hexdigest().lower()
    (BUILD_DIR / "SHA256SUMS.txt").write_text(f"{digest}  {out.name}\n", encoding="ascii")
    print(f"{OUT_REL} (version={args.version}) 构建完成，SHA256SUMS.txt 已生成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
