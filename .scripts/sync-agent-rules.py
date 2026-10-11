# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""sync-agent-rules.py —— 同步本地 GLOBAL.md 到跨 Agent 全局配置

设计与架构说明：
  1. 单一真理来源（SSOT）：
     跨项目、跨 Agent 通用的基线约束在仓库根目录以单个单词命名的 `GLOBAL.md` 统一维护，
     由当前项目 Git 全程纳管。
  2. 消除二次导入（Zero Double Import）：
     仓库专有的 `AGENTS.md` 不再重复包含 `GLOBAL.md` 中的通用条款，模型在会话启动时：
       - 全局系统 prompt 加载：`GLOBAL.md`（通用交互、PowerShell 5.1/7 安全、文件防御等）
       - 仓库级别 context 加载：`AGENTS.md`（本仓 Monorepo、子模块、文档布局、Matt Pocock 规划等）
     杜绝两份通用规则叠加产生的 Double Context Tax（每次交互节约大量静态 Token）。
  3. 涵盖 6 大 Agent 与 AGY 三大形态：
     - Codex (@openai/codex):             ~/.codex/AGENTS.md
     - Claude Code (@anthropic-ai):       ~/.claude/CLAUDE.md
     - OpenCode (opencode-ai):            ~/.config/opencode/AGENTS.md
     - Pi (@earendil-works):              ~/.pi/agent/AGENTS.md
     - DSH (DeepSeek Harness):            ~/.dsh/AGENTS.md
     - AGY (Antigravity)：覆盖三大形态（agy cli、agy acp、agy ide）：
      - ~/.gemini/AGENTS.md              (Gemini 根级通用注入)
        - ~/.gemini/config/AGENTS.md       (跨形态共享配置目录，覆盖 CLI/ACP/IDE)

用法：
  uv run .scripts/sync-agent-rules.py           # 默认：将 GLOBAL.md 以软链接映射至各 Agent
  uv run .scripts/sync-agent-rules.py --copy    # 以物理文件复制方式同步（免 Windows 特权）
  uv run .scripts/sync-agent-rules.py --status  # 查看各 Agent 全局约束文件当前状态
  uv run .scripts/sync-agent-rules.py --unlink  # 清理所有 Agent 全局目录中的链接/文件
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Windows 终端统一配置 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_repo_root() -> Path:
    """获取仓库根目录（即 .scripts 的上级目录）。"""
    return Path(__file__).resolve().parent.parent


def get_agent_targets() -> dict[str, list[Path]]:
    """返回 6 大 Agent 工具所识别的全局约束文件目标路径列表。"""
    home = Path.home()
    return {
        "Codex (@openai/codex)": [
            home / ".codex" / "AGENTS.md",
        ],
        "Claude Code (@anthropic-ai/claude-code)": [
            home / ".claude" / "CLAUDE.md",
        ],
        "OpenCode (opencode-ai)": [
            home / ".config" / "opencode" / "AGENTS.md",
        ],
        "Pi Coding Agent (@earendil-works/pi-coding-agent)": [
            home / ".pi" / "agent" / "AGENTS.md",
        ],
        "DeepSeek Harness (dsh)": [
            home / ".dsh" / "AGENTS.md",
        ],
        "Antigravity (覆盖 agy cli / agy acp / agy ide 三大形态)": [
            home / ".gemini" / "AGENTS.md",
            home / ".gemini" / "config" / "AGENTS.md",
        ],
    }


def cmd_sync(
    repo_root: Path,
    source_filename: str = "GLOBAL.md",
    copy_mode: bool = False,
    force: bool = False,
) -> int:
    """将 GLOBAL.md 同步/链接至各大 Agent 全局配置。"""
    source_file = repo_root / source_filename
    if not source_file.is_file():
        print(f"[ERROR] 基线文件不存在: {source_file}")
        return 1

    print(f"[1/2] 读取本地纳管的通用基线: {source_file.name} ({source_file.stat().st_size} bytes)")

    agent_targets = get_agent_targets()
    mode_desc = "文件复制 (Copy)" if copy_mode else "Windows 软链接 (Symlink)"
    print(f"[2/2] 正在分发全局约束 [{mode_desc}]...\n")

    success_count = 0
    total_targets = 0
    symlink_privilege_error = False

    for agent_name, paths in agent_targets.items():
        print(f"  ● {agent_name}:")
        for dest_path in paths:
            total_targets += 1
            dest_dir = dest_path.parent
            dest_dir.mkdir(parents=True, exist_ok=True)

            rel_dest = str(dest_path)
            if dest_path.is_symlink():
                try:
                    resolved_target = dest_path.resolve()
                    if resolved_target == source_file.resolve():
                        print(f"    - [OK] 软链接已有效指向目标: {rel_dest}")
                        success_count += 1
                        continue
                    else:
                        print(f"    - [UPDATE] 软链接指向其他文件，重新链接: {rel_dest}")
                        dest_path.unlink()
                except Exception:
                    dest_path.unlink()
            elif dest_path.exists():
                if force:
                    print(f"    - [FORCE] 覆盖现有文件: {rel_dest}")
                    dest_path.unlink()
                else:
                    print(f"    - [SKIP] 已存在独立文件（使用 --force 允许覆盖或重新创建）: {rel_dest}")
                    continue

            if copy_mode:
                try:
                    shutil.copy2(source_file, dest_path)
                    print(f"    - [COPIED] 复制成功: {rel_dest}")
                    success_count += 1
                except Exception as e:
                    print(f"    - [ERROR] 复制失败: {rel_dest} ({e})")
            else:
                try:
                    os.symlink(source_file.resolve(), dest_path)
                    print(f"    - [LINKED] 软链接创建成功: {rel_dest} -> {source_file.name}")
                    success_count += 1
                except OSError as e:
                    if getattr(e, "winerror", None) == 1314:
                        symlink_privilege_error = True
                        print(f"    - [NO PRIVILEGE] 客户端没有特权（WinError 1314）: {rel_dest}")
                    else:
                        print(f"    - [ERROR] 软链接创建失败: {rel_dest} ({e})")

    print(f"\n[DONE] 同步完成: {success_count}/{total_targets} 个目标就绪。")

    if symlink_privilege_error:
        print("\n" + "=" * 70)
        print("【重要提示：Windows 软链接特权说明】")
        print("创建符号链接报错 [WinError 1314] 客户端没有特权。在 Windows 上有两种解决途径：")
        print("  1. 开启开发者模式（推荐，一次性配置）：")
        print("     进入「Windows 设置」->「系统」或「隐私和安全性」->「开发者选项」-> 将「开发者模式」开启。")
        print("     开启后普通用户身份无需提权即可自由创建跨驱动器软链接（D: -> C:）。")
        print("  2. 使用免特权复制模式（立即生效）：")
        print("     运行命令：uv run .scripts/sync-agent-rules.py --copy --force")
        print("=" * 70)

    return 0


def cmd_status(repo_root: Path, source_filename: str = "GLOBAL.md") -> int:
    """查看各大 Agent 的全局约束文件状态。"""
    source_file = repo_root / source_filename
    print(f"[INFO] 本地基线文件: {source_file} (存在: {source_file.exists()})\n")
    print(f"{'Agent 工具 / 形态':<50} | {'全局目标路径':<40} | {'状态'}")
    print("-" * 115)

    agent_targets = get_agent_targets()
    for agent_name, paths in agent_targets.items():
        for dest_path in paths:
            if not dest_path.exists() and not dest_path.is_symlink():
                status = "未配置 (缺失)"
            elif dest_path.is_symlink():
                try:
                    resolved = dest_path.resolve()
                    if resolved == source_file.resolve():
                        status = "已链接 (有效软链接)"
                    else:
                        status = f"已链接 (指向其它: {resolved.name})"
                except Exception as e:
                    status = f"无效链接 ({e})"
            else:
                status = f"普通文件 ({dest_path.stat().st_size} bytes)"

            # 显示较短路径
            display_path = str(dest_path).replace(str(Path.home()), "~")
            print(f"{agent_name:<50} | {display_path:<40} | {status}")

    print("-" * 115)
    return 0


def cmd_unlink() -> int:
    """清理各大 Agent 的全局规则链接/文件。"""
    agent_targets = get_agent_targets()
    removed_count = 0
    print("[INFO] 正在清理各大 Agent 的全局约束文件...")

    for agent_name, paths in agent_targets.items():
        for dest_path in paths:
            if dest_path.is_symlink() or dest_path.exists():
                try:
                    dest_path.unlink()
                    display_path = str(dest_path).replace(str(Path.home()), "~")
                    print(f"  [REMOVED] {agent_name}: {display_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"  [ERROR] 清理失败 {dest_path}: {e}")

    print(f"\n[DONE] 共清理 {removed_count} 个全局配置文件。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="将本地单一真理文件 GLOBAL.md 软链接或同步到 6 大 Agent 全局配置。"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="GLOBAL.md",
        help="本地通用规则文件名（默认: GLOBAL.md）",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="采用物理文件复制模式（避免无开发者模式时的软链接特权错误）",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="当目标位置已存在同名普通文件时强制覆盖",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看所有 Agent 全局约束配置的链接与文件状态",
    )
    parser.add_argument(
        "--unlink",
        action="store_true",
        help="清理移除所有 Agent 全局配置中的规则链接与文件",
    )

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.status:
        return cmd_status(repo_root, args.file)
    elif args.unlink:
        return cmd_unlink()
    else:
        return cmd_sync(
            repo_root=repo_root,
            source_filename=args.file,
            copy_mode=args.copy,
            force=args.force,
        )


if __name__ == "__main__":
    sys.exit(main())
