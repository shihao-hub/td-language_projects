# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# link-submodule-agents.py —— 将父仓 AGENTS.md 以 NTFS 硬链接同步到各子模块/子仓库根目录
#
# 背景与用途：
#   Antigravity (AGY)、Claude Code、Codex 等 Agent 工具在向上遍历规则文件（AGENTS.md / GEMINI.md）时，
#   遇到子模块的 .git（无论是独立仓库目录还是 submodule 的 .git 文件）就会判定到达仓库顶层并停止向上查找。
#   本脚本利用 Windows NTFS 硬链接（Hard Link），将父仓的 AGENTS.md 0 成本、0 延迟物理同步至各子模块根目录：
#     1. 零维护：两处实际指向同一磁盘 Inode，修改任何一处，所有子模块实时同步；
#     2. 零权限门槛：NTFS 硬链接无需 Windows 开发者模式或管理员特权；
#     3. 规则穿透：让 Agent 在任何子项目开发时，都能直接读到父仓的开发与 Git 提交规范。
#
# 用法：
#   uv run .scripts/link-submodule-agents.py             # 默认：为所有子仓库建立硬链接
#   uv run .scripts/link-submodule-agents.py --status    # 检查各子仓库链接状态与 Inode
#   uv run .scripts/link-submodule-agents.py --unlink    # 清理所有子仓库中的链接
#   uv run .scripts/link-submodule-agents.py --add-gitignore  # 将 /AGENTS.md 追加至各子仓库 .gitignore

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


def get_repo_root() -> Path:
    """获取父仓库根目录（即 .scripts 的上级目录）。"""
    return Path(__file__).resolve().parent.parent


def discover_submodule_roots(root: Path, include_thirdparty: bool = False) -> list[Path]:
    """发现当前仓库下的所有 Git 子模块与独立 Git 仓库根目录。"""
    sub_roots: list[Path] = []
    ignored_names = {".git", "node_modules", ".venv", "vendor", "dist", "bin", "build", ".idea", ".vscode"}
    if not include_thirdparty:
        ignored_names.add(".thirdparty")

    for dirpath_str, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_str)
        # 排除父仓库根目录本身
        if dirpath == root:
            # 过滤不需要深入遍历的目录
            dirnames[:] = [d for d in dirnames if d not in ignored_names]
            continue

        # 如果当前目录下存在 .git（可能是文件夹，也可能是 submodule 的 gitdir 文件）
        has_git = (dirpath / ".git").exists()
        if has_git:
            sub_roots.append(dirpath)

        # 过滤子目录，避免扫描大型构建产物
        dirnames[:] = [d for d in dirnames if d not in ignored_names]

    # 按路径长度排序输出，更直观
    sub_roots.sort(key=lambda p: (len(p.parts), str(p)))
    return sub_roots


def cmd_link(root: Path, source_file: Path, targets: list[Path], force: bool = False) -> int:
    """为各子模块创建硬链接。"""
    if not source_file.is_file():
        print(f"[ERROR] 源规则文件不存在: {source_file}")
        return 1

    print(f"[INFO] 源文件: {source_file.relative_to(root)} (Inode: {source_file.stat().st_ino})")
    print(f"[INFO] 扫描到 {len(targets)} 个子仓库/模块\n")

    success_count = 0
    for target_dir in targets:
        dest_file = target_dir / "AGENTS.md"
        rel_target = target_dir.relative_to(root)

        if dest_file.exists():
            try:
                if os.path.samefile(source_file, dest_file):
                    print(f"  [OK] 已存在硬链接 (同一 Inode): {rel_target / 'AGENTS.md'}")
                    success_count += 1
                    continue
                elif force:
                    print(f"  [WARN] 覆盖现有不同文件 (--force): {rel_target / 'AGENTS.md'}")
                    dest_file.unlink()
                else:
                    print(f"  [SKIP] 存在非链接的独立文件 (使用 --force 可覆盖): {rel_target / 'AGENTS.md'}")
                    continue
            except Exception as e:
                print(f"  [FAIL] 检查现有文件失败 {rel_target}: {e}")
                continue

        try:
            os.link(source_file, dest_file)
            print(f"  [LINKED] 成功创建硬链接: {rel_target / 'AGENTS.md'}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] 创建硬链接失败 {rel_target}: {e}")

    print(f"\n[DONE] 完成: {success_count}/{len(targets)} 个目标已就绪。")
    return 0


def cmd_unlink(root: Path, source_file: Path, targets: list[Path]) -> int:
    """清理子模块中的 AGENTS.md。"""
    print(f"[INFO] 清理子仓库中的硬链接 AGENTS.md...\n")
    cleaned_count = 0

    for target_dir in targets:
        dest_file = target_dir / "AGENTS.md"
        rel_target = target_dir.relative_to(root)

        if not dest_file.exists():
            continue

        try:
            # 严格防止误删根目录源文件
            if dest_file.resolve() == source_file.resolve() and target_dir == root:
                continue

            dest_file.unlink()
            print(f"  [REMOVED] 已删除: {rel_target / 'AGENTS.md'}")
            cleaned_count += 1
        except Exception as e:
            print(f"  [ERROR] 删除失败 {rel_target}: {e}")

    print(f"\n[DONE] 共清理 {cleaned_count} 个子模块文件。")
    return 0


def cmd_status(root: Path, source_file: Path, targets: list[Path]) -> int:
    """查看子模块中 AGENTS.md 链接状态。"""
    if not source_file.is_file():
        print(f"[ERROR] 源规则文件不存在: {source_file}")
        return 1

    src_ino = source_file.stat().st_ino
    print(f"[INFO] 父仓源文件: {source_file.relative_to(root)} (Inode: {src_ino})\n")
    print(f"{'子仓库路径':<45} | {'状态':<12} | {'详情'}")
    print("-" * 80)

    for target_dir in targets:
        dest_file = target_dir / "AGENTS.md"
        rel_target = str(target_dir.relative_to(root))

        if not dest_file.exists():
            status = "未建立"
            detail = "无 AGENTS.md"
        else:
            try:
                dest_ino = dest_file.stat().st_ino
                if dest_ino == src_ino:
                    status = "已链接"
                    detail = f"Inode: {dest_ino} (与源文件一致)"
                else:
                    status = "独立文件"
                    detail = f"Inode: {dest_ino} (内容不同)"
            except Exception as e:
                status = "异常"
                detail = str(e)

        print(f"{rel_target:<45} | {status:<12} | {detail}")

    print("-" * 80)
    return 0


def cmd_gitignore(root: Path, targets: list[Path], remove: bool = False) -> int:
    """向各子模块的 .gitignore 添加或移除 /AGENTS.md。"""
    rule_line = "/AGENTS.md\n"
    tag = "# 忽略父仓硬链接规则文件"

    for target_dir in targets:
        gi_file = target_dir / ".gitignore"
        rel_target = target_dir.relative_to(root)

        content = ""
        if gi_file.is_file():
            content = gi_file.read_text(encoding="utf-8", errors="replace")

        if remove:
            if "/AGENTS.md" in content:
                new_lines = [
                    l for l in content.splitlines(keepends=True)
                    if l.strip() not in ("/AGENTS.md", "AGENTS.md", tag)
                ]
                gi_file.write_text("".join(new_lines), encoding="utf-8")
                print(f"  [UPDATED] 已从 .gitignore 移除: {rel_target / '.gitignore'}")
            else:
                print(f"  [SKIP] 未包含规则: {rel_target / '.gitignore'}")
        else:
            if "/AGENTS.md" in content or "\nAGENTS.md" in content:
                print(f"  [OK] 已存在忽略规则: {rel_target / '.gitignore'}")
            else:
                sep = "\n" if content and not content.endswith("\n") else ""
                new_content = content + f"{sep}\n{tag}\n{rule_line}"
                gi_file.write_text(new_content, encoding="utf-8")
                print(f"  [ADDED] 已追加忽略规则: {rel_target / '.gitignore'}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="将父仓库 AGENTS.md 规则文件以 NTFS 硬链接同步至各个子模块根目录。"
    )
    parser.add_argument(
        "--status", action="store_true", help="查看所有子仓库的 AGENTS.md 链接状态"
    )
    parser.add_argument(
        "--unlink", action="store_true", help="清理移除所有子仓库中的 AGENTS.md 硬链接"
    )
    parser.add_argument(
        "--add-gitignore", action="store_true", help="向所有子仓库的 .gitignore 追加 /AGENTS.md"
    )
    parser.add_argument(
        "--remove-gitignore", action="store_true", help="从所有子仓库的 .gitignore 移除 /AGENTS.md"
    )
    parser.add_argument(
        "--include-thirdparty", action="store_true", help="包含 .thirdparty 目录下的第三方子模块"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="当目标存在非链接文件时强制覆盖"
    )
    parser.add_argument(
        "--source", type=str, default=None, help="自定义源规则文件路径（默认: <repo>/AGENTS.md）"
    )

    args = parser.parse_args()

    repo_root = get_repo_root()
    source_file = Path(args.source) if args.source else (repo_root / "AGENTS.md")

    # 发现所有子仓库目标
    targets = discover_submodule_roots(repo_root, include_thirdparty=args.include_thirdparty)

    if args.status:
        return cmd_status(repo_root, source_file, targets)
    elif args.unlink:
        return cmd_unlink(repo_root, source_file, targets)
    elif args.add_gitignore:
        return cmd_gitignore(repo_root, targets, remove=False)
    elif args.remove_gitignore:
        return cmd_gitignore(repo_root, targets, remove=True)
    else:
        # 默认操作：建立硬链接
        return cmd_link(repo_root, source_file, targets, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
