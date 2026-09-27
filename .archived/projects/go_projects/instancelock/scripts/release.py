# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# instancelock 一键发布脚本：构建 -> tag -> push -> GitHub Release
# 用法：uv run scripts/release.py --version 1.0.0 [--notes "说明"]
# 前提: gh CLI 已登录；工作区干净（instancelock/ 内无未提交变更）

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="instancelock 一键发布：构建 → tag → push → GitHub Release")
    parser.add_argument("--version", required=True, help="版本号（X.Y.Z）")
    parser.add_argument("--notes", default="", help="Release 说明")
    args = parser.parse_args()
    version = args.version

    # 1. semver 校验
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"版本号需为 X.Y.Z 形式，实际: {version}", file=sys.stderr)
        return 1
    tag = f"instancelock/v{version}"

    # 2. tag 重复检查
    r = run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"])
    if r.returncode == 0:
        print(f"tag {tag} 已存在", file=sys.stderr)
        return 1

    # 3. 工作区干净检查（仅限本项目目录；instancelock 归档后位于 .archived 内）
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", "instancelock"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.stdout.strip():
        print(f"instancelock/ 存在未提交变更，请先提交:\n{r.stdout.strip()}", file=sys.stderr)
        return 1

    # 4. 构建（注入版本号 + 生成 SHA256SUMS）
    r = subprocess.run(["uv", "run", str(SCRIPTS_DIR / "build.py"), "--version", version], cwd=str(PROJECT_ROOT))
    if r.returncode != 0:
        return r.returncode

    # 5. 打 tag 并推送
    r = run(["git", "tag", tag])
    if r.returncode != 0:
        return r.returncode
    r = run(["git", "push", "origin", tag])
    if r.returncode != 0:
        return r.returncode

    # 6. 创建 GitHub Release 并上传附件
    notes = args.notes or f"instancelock v{version}"
    r = run(
        ["gh", "release", "create", tag,
         r"build\instancelock-windows-amd64.exe", r"build\SHA256SUMS.txt",
         "--title", f"instancelock v{version}", "--notes", notes],
    )
    if r.returncode != 0:
        return r.returncode

    print(f"发布完成: {tag}")
    print(f"验证: gh release view {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
