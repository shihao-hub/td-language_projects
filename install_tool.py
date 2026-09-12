# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""按工具名把子仓构建产物安装到 ~/.local/bin。

用法：
    uv run scripts/install_tool.py <instancelock|clictl|jtree|all>
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

# 仓库根（本脚本位于 <repo>/scripts/ 下）
REPO_ROOT = Path(__file__).resolve().parent.parent

# 安装目标目录：用户级 PATH
DEST_DIR = Path.home() / ".local" / "bin"

# 固定路径类工具：参数名 -> (源文件相对路径, 目标文件名)
FIXED_TOOLS: dict[str, tuple[str, str]] = {
    "instancelock": ("go_projects/instancelock/build/instancelock.exe", "instancelock.exe"),
    "clictl": ("go_projects/clictl/clictl.exe", "clictl.exe"),
}

# jtree 特殊：release 目录下存在多个带版本号的 exe，需选版本号最大者
JTREE_RELEASE_DIR = "typescript_projects/jtree/release"
JTREE_DEST_NAME = "jtree.exe"

# 工具的完整列表与可选顺序
ALL_TOOLS: list[str] = [*FIXED_TOOLS, "jtree"]


def human_size(num: float) -> str:
    """字节数转人类可读大小。"""
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def latest_jtree_src() -> Path:
    """在 release 目录中选版本号最大的 jtree-vX.Y.Z.exe。"""
    release_dir = REPO_ROOT / JTREE_RELEASE_DIR
    if not release_dir.is_dir():
        raise FileNotFoundError(f"目录不存在：{release_dir}（typescript_projects 子模块未拉取？）")

    pattern = re.compile(r"^jtree-v(\d+(?:\.\d+)*)\.exe$")
    best: tuple[tuple[int, ...], Path] | None = None
    for path in release_dir.glob("jtree-v*.exe"):
        match = pattern.match(path.name)
        if not match:
            continue
        # 版本号转整数元组，保证语义排序（0.10.0 > 0.9.0）
        key = tuple(int(seg) for seg in match.group(1).split("."))
        if best is None or key > best[0]:
            best = (key, path)

    if best is None:
        raise FileNotFoundError(
            f"{release_dir} 下未找到 jtree-v*.exe，请先在子项目内构建（pnpm exe）"
        )
    return best[1]


def resolve_src(tool: str) -> Path:
    """根据工具名解析源文件绝对路径。"""
    if tool in FIXED_TOOLS:
        return REPO_ROOT / FIXED_TOOLS[tool][0]
    return latest_jtree_src()


def resolve_dest_name(tool: str) -> str:
    """根据工具名解析安装后的文件名。"""
    if tool in FIXED_TOOLS:
        return FIXED_TOOLS[tool][1]
    return JTREE_DEST_NAME


def install(tool: str) -> None:
    """复制单个工具的构建产物到安装目录。"""
    src = resolve_src(tool)
    if not src.is_file():
        raise FileNotFoundError(f"源文件不存在：{src}（请先在对应子项目内构建）")
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEST_DIR / resolve_dest_name(tool)
    shutil.copy2(src, dest)
    print(f"[OK] {tool}: {src.relative_to(REPO_ROOT)} -> {dest} ({human_size(src.stat().st_size)})")


def main() -> int:
    parser = argparse.ArgumentParser(description="安装子仓构建产物到 ~/.local/bin")
    parser.add_argument(
        "tool",
        choices=[*ALL_TOOLS, "all"],
        help="要安装的工具名，all 表示全部安装",
    )
    args = parser.parse_args()

    tools = ALL_TOOLS if args.tool == "all" else [args.tool]
    failed = False
    for tool in tools:
        try:
            install(tool)
        except OSError as exc:
            print(f"[FAIL] {tool}: {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
