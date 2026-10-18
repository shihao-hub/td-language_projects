# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""link-subproject-agents.py —— 将各级子模块及子项目的 AGENTS.md / CLAUDE.md 软链接至父仓根目录

功能说明：
  1. 动态自动发现父仓下所有的语言子仓（匹配 *_projects 目录，包括 java_projects、go_projects 等）。
  2. 一级语言子仓：
     - AGENTS.md -> ..\\AGENTS.md
     - CLAUDE.md -> ..\\CLAUDE.md
  3. 二级具体子项目：
     - AGENTS.md -> ..\\..\\AGENTS.md
     - CLAUDE.md -> ..\\..\\CLAUDE.md
  4. 强制覆盖已有实体文件或旧软链：
     - 遇到原有的实体文件或旧软链，直接 unlink 移除并重新建立标准相对符号链接。
  5. Windows 兼容性：
     - Windows NTFS 内核要求相对符号链接目标必须使用反斜杠 '\\'。

用法：
  uv run .scripts/link-subproject-agents.py          # 批量创建/覆盖软链接
  uv run .scripts/link-subproject-agents.py --check  # 体检各处软链接状态
  uv run .scripts/link-subproject-agents.py --dry-run# 预览将要进行的软链操作
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Windows 终端统一配置 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 忽略扫描的目录名称
IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".zed",
    ".zcode",
    "node_modules",
    "target",
    "build",
    "dist",
    "bin",
    "__pycache__",
    ".venv",
    "venv",
    ".scratch",
    "temp",
}

TARGET_FILES = ["AGENTS.md", "CLAUDE.md"]


def get_repo_root() -> Path:
    """获取父仓库根目录。"""
    return Path(__file__).resolve().parent.parent


def get_lang_submodules(repo_root: Path) -> list[str]:
    """动态探测父仓下的所有语言子仓（以 _projects 结尾的目录）。"""
    langs: list[str] = []
    for d in sorted(repo_root.iterdir()):
        if d.is_dir() and d.name.endswith("_projects") and not d.name.startswith("."):
            langs.append(d.name)
    return langs


def get_subprojects(submodule_dir: Path) -> list[Path]:
    """探测语言子仓下的所有独立子项目目录。"""
    subprojects: list[Path] = []
    if not submodule_dir.is_dir():
        return subprojects

    for child in sorted(submodule_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name in IGNORED_DIRS or child.name.startswith("."):
            continue
        markers = [
            "go.mod", "main.go",
            "pom.xml", "build.gradle", "settings.gradle",
            "pyproject.toml", "requirements.txt", "setup.py",
            "package.json", "tsconfig.json",
            "Cargo.toml",
            "CMakeLists.txt",
            "README.md",
        ]
        has_marker = any((child / m).exists() for m in markers)
        if has_marker:
            subprojects.append(child)

    return subprojects


def get_platform_relative_target(levels: int, fname: str) -> str:
    """根据层级和操作系统，构造合法的相对目标路径。
    Windows NTFS 内核对符号链接目标要求使用反斜杠 '\\'。
    """
    sep = "\\" if os.name == "nt" else "/"
    parts = [".."] * levels + [fname]
    return sep.join(parts)


def ensure_symlink(link_path: Path, relative_target_str: str, dry_run: bool, check_only: bool) -> bool:
    """确保 link_path 软链接指向 relative_target_str 且目标可正常读取。"""
    is_correct_symlink = False
    if link_path.is_symlink():
        try:
            raw_target = os.readlink(link_path)
            # 标准化路径比对
            if Path(raw_target).as_posix() == Path(relative_target_str).as_posix() and link_path.exists():
                is_correct_symlink = True
        except OSError:
            is_correct_symlink = False

    if is_correct_symlink:
        return True

    if check_only:
        state = "NOT_A_SYMLINK (EXISTING_FILE)" if link_path.exists() and not link_path.is_symlink() else "BROKEN/INVALID"
        if not link_path.exists() and not link_path.is_symlink():
            state = "MISSING"
        print(f"  [MISMATCH] {link_path} ({state} -> 应为 {relative_target_str})")
        return False

    if dry_run:
        action = "覆盖实体文件并创建软链" if link_path.exists() and not link_path.is_symlink() else "链接"
        print(f"  [DRY-RUN] 将{action}: {link_path} -> {relative_target_str}")
        return True

    # 实际创建/覆盖软链接
    try:
        # 如果存在旧实体文件、旧软链或破损软链，强制移除
        if link_path.is_symlink():
            link_path.unlink()
        elif link_path.exists():
            os.remove(link_path)

        # 确保父目录存在
        link_path.parent.mkdir(parents=True, exist_ok=True)
        # 创建符号链接
        link_path.symlink_to(relative_target_str, target_is_directory=False)
        print(f"  [LINKED] {link_path} -> {relative_target_str}")
        return True
    except OSError as e:
        print(f"  [ERROR] 创建软链接失败 {link_path}: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="批量将子仓及子项目的 AGENTS.md / CLAUDE.md 软链至根目录")
    parser.add_argument("--check", action="store_true", help="仅体检状态，不实际修改")
    parser.add_argument("--dry-run", action="store_true", help="预览变更，不实际写盘")
    args = parser.parse_args()

    repo_root = get_repo_root()
    print(f"=== 正在扫描与建立全局 AGENTS.md / CLAUDE.md 软链接 (Root: {repo_root.name}) ===")

    for fname in TARGET_FILES:
        if not (repo_root / fname).is_file():
            print(f"[FATAL] 根目录基准文件不存在: {repo_root / fname}")
            return 1

    lang_submodules = get_lang_submodules(repo_root)
    print(f"发现语言子仓: {', '.join(lang_submodules)}")

    total_links = 0
    mismatches = 0

    for lang in lang_submodules:
        submodule_path = repo_root / lang
        if not submodule_path.is_dir():
            continue

        print(f"\n📂 处理一级子仓: {lang}")
        # 1. 一级子仓: 目标是 1 级相对路径 (..\AGENTS.md)
        for fname in TARGET_FILES:
            link_path = submodule_path / fname
            target_str = get_platform_relative_target(1, fname)
            total_links += 1
            if not ensure_symlink(link_path, target_str, args.dry_run, args.check):
                mismatches += 1

        # 2. 二级子项目: 目标是 2 级相对路径 (..\..\AGENTS.md)
        subprojects = get_subprojects(submodule_path)
        for proj in subprojects:
            for fname in TARGET_FILES:
                link_path = proj / fname
                target_str = get_platform_relative_target(2, fname)
                total_links += 1
                if not ensure_symlink(link_path, target_str, args.dry_run, args.check):
                    mismatches += 1

    print("\n" + "=" * 50)
    if args.check:
        if mismatches > 0:
            print(f"❌ 体检发现: 共检查 {total_links} 处软链接，其中 {mismatches} 处未就绪或非软链。")
            return 1
        print(f" 全部就绪: 共 {total_links} 处软链接完全指向根目录基准文件且可正常穿透！")
        return 0

    print(f" 运行完成: 共核查/建立 {total_links} 处软链接。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
