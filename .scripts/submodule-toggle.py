# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# submodule-toggle.py —— 语言子模块临时注销（deinit）/ 恢复（restore）一键脚本，
#                        带前置检查与只读体检。
# 用法（在父仓库根目录执行）：
#     uv run .scripts/submodule-toggle.py -Action status  -Name native_projects,rust_projects
#     uv run .scripts/submodule-toggle.py -Action deinit  -Name native_projects,rust_projects
#     uv run .scripts/submodule-toggle.py -Action restore -Name rust_projects
# 三动作：status=只读体检；deinit=本地注销（有未提交/未推送即整批拒绝）；
#         restore=恢复 + 切跟踪分支（gitlink 缺失时自动回溯历史重建）
# 背景与原理：docs/repo/Git 子模块临时注销（native、rust）.md
# 安全边界：不触碰远端；不改 .gitmodules；绝不自动 commit / push；
#           native 的 gitlink 重建完成后需按提示提交父仓指针。
# 退出码：0=成功（含幂等跳过）；1=参数/校验错误；2=前置检查不通过；3=执行失败。

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Windows 下 stdout 重定向到管道时默认走 locale 编码（cp936），中文会乱码；统一重配置为 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------- 输出着色（轻量 ANSI，非终端时自动退化为纯文本） ----------------

_USE_COLOR = sys.stdout.isatty()
if os.name == "nt" and _USE_COLOR:
    os.system("")  # 激活 Windows 终端的 VT 转义序列支持


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def cyan(t: str) -> str:
    return _c(t, "36")


def green(t: str) -> str:
    return _c(t, "32")


def yellow(t: str) -> str:
    return _c(t, "33")


def dark_yellow(t: str) -> str:
    return _c(t, "33;2")


def red(t: str) -> str:
    return _c(t, "31")


def dark_gray(t: str) -> str:
    return _c(t, "90")


def gray(t: str) -> str:
    return _c(t, "37;2")


def white(t: str) -> str:
    return _c(t, "97")


# ---------------- 通用工具 ----------------


def show_usage() -> None:
    print()
    print(cyan("用法示例："))
    print("  .\\.scripts\\submodule-toggle.py -Action status  -Name native_projects,rust_projects")
    print("  .\\.scripts\\submodule-toggle.py -Action deinit  -Name native_projects,rust_projects")
    print("  .\\.scripts\\submodule-toggle.py -Action restore -Name rust_projects")
    print()
    print("（也可用 uv run .scripts/submodule-toggle.py ... 执行；-Name 支持空格或逗号分隔多个子模块）")
    print()


def known_submodules(gitmodules_path: Path) -> list[str]:
    """解析 .gitmodules 中登记的全部子模块名。"""
    names: list[str] = []
    for line in gitmodules_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^\s*\[submodule\s+"([^"]+)"\]', line)
        if m:
            names.append(m.group(1))
    return names


class GitError(RuntimeError):
    """git 命令失败。"""


def git_checked(cwd: Path, *args: str) -> list[str]:
    """执行 git 命令，失败抛 GitError，成功返回 stdout 各行。"""
    r = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise GitError(f"git {' '.join(args)} 失败，退出码 {r.returncode}")
    return [line for line in r.stdout.splitlines() if line.strip()]


# 读取单个子模块的完整状态（只读，不产生任何修改）
class SmState:
    def __init__(self, repo_root: Path, name: str) -> None:
        self.name = name
        self.modules_dir = (repo_root / ".git" / "modules" / name).exists()

        # index 中是否有 160000 gitlink
        self.gitlink_sha: str | None = None
        ls_lines = git_checked(repo_root, "ls-files", "-s", "--", name)
        if ls_lines:
            m = re.match(r"^160000\s+([0-9a-f]{40})", ls_lines[0])
            if m:
                self.gitlink_sha = m.group(1)

        self.initialized = False
        self.branch = ""
        self.dirty = False
        self.dirty_count = 0
        self.unpushed_count = 0
        self.stash_count = 0
        sm_path = repo_root / name
        if (sm_path / ".git").exists():
            self.initialized = True
            branch_lines = git_checked(sm_path, "branch", "--show-current")
            if branch_lines:
                self.branch = branch_lines[0].strip()
            dirty_lines = git_checked(sm_path, "status", "--porcelain")
            self.dirty_count = len(dirty_lines)
            self.dirty = self.dirty_count > 0
            unpushed_lines = git_checked(sm_path, "log", "--all", "--not", "--remotes", "--oneline")
            self.unpushed_count = len(unpushed_lines)
            stash_lines = git_checked(sm_path, "stash", "list")
            self.stash_count = len(stash_lines)


# ---------------- status：只读体检 ----------------


def action_status(repo_root: Path, names: list[str]) -> int:
    print(cyan(f"======== submodule-toggle 状态体检（共 {len(names)} 个目标）========"))
    for n in names:
        s = SmState(repo_root, n)
        print()
        print(white(f"[{n}]"))
        print("  登记(.gitmodules) : 已登记")
        if s.modules_dir:
            print(f"  本地 git 库       : .git/modules/{n} 存在（本地即可恢复）")
        else:
            print(yellow("  本地 git 库       : 缺失（恢复时需从远端重新拉取）"))
        if s.gitlink_sha:
            print(f"  index gitlink     : {s.gitlink_sha[:7]}（index 中存在）")
        else:
            print(yellow("  index gitlink     : 缺失（不能直接 update --init，restore 时脚本会自动重建）"))
        if not s.initialized:
            print(yellow("  工作区            : 未初始化（已注销）"))
            print("  判定              : 已注销（无数据丢失，随时可 restore）")
            print(f"  建议              : 需要恢复时运行 -Action restore -Name {n}")
        else:
            if s.branch:
                print(f"  工作区            : 已初始化；分支 {s.branch}")
            else:
                print("  工作区            : 已初始化；detached HEAD（无本地分支）")
            if s.dirty:
                dirty_desc = f"有未提交改动（{s.dirty_count} 处，含未跟踪）"
            else:
                dirty_desc = "工作区干净"
            print(f"  变更状态          : {dirty_desc}；未推送提交 {s.unpushed_count}；stash {s.stash_count}")
            if s.dirty or s.unpushed_count > 0:
                print(yellow("  判定              : 暂不能 deinit（请先在子模块内处理 commit / push）"))
            else:
                print("  判定              : 可安全 deinit")
            print(f"  建议              : 注销运行 -Action deinit -Name {n}")
    print()
    print(green("体检完成（status 为只读操作，未做任何修改）。"))
    return 0


# ---------------- deinit：本地注销（带前置检查） ----------------


def action_deinit(repo_root: Path, names: list[str]) -> int:
    # 第一轮：全量前置检查，任一不通过则整批拒绝、一个都不动
    to_deinit: list[str] = []
    skipped: list[str] = []
    rejected: list[tuple[str, list[str]]] = []
    for n in names:
        s = SmState(repo_root, n)
        if not s.initialized:
            skipped.append(n)
            continue
        problems: list[str] = []
        if s.dirty:
            problems.append(f"    存在未提交改动（{s.dirty_count} 处，含未跟踪文件），请先在子模块内 commit")
        if s.unpushed_count > 0:
            problems.append(f"    存在 {s.unpushed_count} 个未推送到任何远端的提交，请先在子模块内 push")
        if problems:
            rejected.append((n, problems))
        else:
            if s.stash_count > 0:
                print(dark_yellow(f"提示：{n} 存在 {s.stash_count} 条 stash（保存在 .git/modules/{n}，deinit 不会丢失）。"))
            to_deinit.append(n)

    if rejected:
        print(red("前置检查未通过，整批拒绝（未修改任何子模块）："))
        for name, problems in rejected:
            print(red(f"  [{name}]"))
            for p in problems:
                print(red(p))
        print(yellow("请先在上述子模块内处理 commit / push，然后重新运行本脚本。"))
        return 2

    for n in skipped:
        print(dark_gray(f"[{n}] 已处于注销状态，跳过（幂等）。"))

    # 第二轮：执行 deinit + 清理残留 + 验证
    failed: list[str] = []
    for n in to_deinit:
        print(cyan(f"[{n}] 正在本地注销 ..."))
        try:
            git_checked(repo_root, "submodule", "deinit", "-f", "--", n)
        except GitError as exc:
            print(red(f"  出错：{exc}"))
            failed.append(n)
            continue

        # 清理残留空目录（deinit 只清空内容、保留目录本身）
        sm_path = repo_root / n
        if sm_path.exists():
            leftovers = [p for p in sm_path.iterdir()]
            if not leftovers:
                sm_path.rmdir()
            else:
                print(yellow(f"  警告：deinit 后目录仍残留 {len(leftovers)} 项，未自动删除，请人工确认。"))

        # 验证三项：status 前缀 '-'、本地 git 库保留、config 注册已移除
        ok = True
        r = subprocess.run(
            ["git", "-C", str(repo_root), "submodule", "status", "--", n],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        status_line = r.stdout.splitlines()[:1]
        if not (status_line and status_line[0].startswith("-")):
            ok = False
            print(red("  验证失败：git submodule status 未显示 '-' 前缀。"))
        if not (repo_root / ".git" / "modules" / n).exists():
            ok = False
            print(red(f"  验证失败：本地 git 库 .git/modules/{n} 不在了（不应删除）。"))
        r = subprocess.run(
            ["git", "-C", str(repo_root), "config", "--local", "--get-regexp",
             f"^submodule\\.{re.escape(n)}\\."],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if [line for line in r.stdout.splitlines() if line.strip()]:
            ok = False
            print(red("  验证失败：.git/config 中注册条目未移除。"))

        if ok:
            print(green("  完成：已注销；本地 git 库与 .gitmodules 完好；父仓库无需提交。"))
        else:
            failed.append(n)

    if failed:
        print(red(f"以下子模块注销过程出错：{', '.join(failed)}"))
        return 3
    print()
    print(green("deinit 完成。未触碰：.gitmodules、远端、父仓库 index；恢复请运行 -Action restore。"))
    return 0


# ---------------- restore：本地恢复（普通 + gitlink 重建） ----------------


def action_restore(repo_root: Path, names: list[str]) -> int:
    failed: list[str] = []
    for n in names:
        print(cyan(f"[{n}] 正在恢复 ..."))
        s = SmState(repo_root, n)
        sm_path = repo_root / n
        if s.initialized:
            print(dark_gray("  已处于初始化状态，跳过（幂等）。"))
            continue

        rebuild_gitlink = False
        branch = "main"
        try:
            if s.gitlink_sha:
                print(f"  index gitlink 存在（{s.gitlink_sha[:7]}），执行 update --init ...")
                git_checked(repo_root, "submodule", "update", "--init", "--", n)
            else:
                print(yellow("  index gitlink 缺失（历史遗留），自动回溯历史提交重建 ..."))
                found: str | None = None
                commits = git_checked(repo_root, "rev-list", "HEAD", "--", n)
                for c in commits:
                    tree_lines = git_checked(repo_root, "ls-tree", c, "--", n)[:1]
                    if tree_lines:
                        m = re.match(r"^160000\s+([0-9a-f]{40})", tree_lines[0])
                        if m:
                            found = c
                            break
                if not found:
                    raise GitError(f"在 HEAD 历史中未找到任何包含 {n} gitlink 的提交，无法自动重建")
                print(f"  找到包含 gitlink 的历史提交 {found[:7]}，取回 index 条目 ...")
                git_checked(repo_root, "checkout", found, "--", n)
                git_checked(repo_root, "submodule", "update", "--init", "--", n)
                rebuild_gitlink = True

            # 切换到 .gitmodules 声明的跟踪分支（缺省回退 main）
            branch_lines = git_checked(
                repo_root, "config", "-f", str(repo_root / ".gitmodules"), f"submodule.{n}.branch"
            )
            if branch_lines and branch_lines[0].strip():
                branch = branch_lines[0].strip()
            git_checked(sm_path, "switch", branch)

            if rebuild_gitlink:
                # ignore=all 拦截普通 add，必须 --force；把 index 指针更新为分支最新
                git_checked(repo_root, "add", "--force", "--", n)
        except GitError as exc:
            print(red(f"  出错：{exc}"))
            print(yellow("  提示：恢复中断不会丢失数据；可修复问题后重新运行 restore。"))
            failed.append(n)
            continue

        # 验证：已初始化 + 分支正确
        new_state = SmState(repo_root, n)
        ok = True
        if not new_state.initialized:
            ok = False
            print(red("  验证失败：工作区仍未初始化。"))
        if new_state.branch != branch:
            ok = False
            print(red(f"  验证失败：当前分支 '{new_state.branch}' 与目标分支 '{branch}' 不一致。"))

        if ok:
            if rebuild_gitlink:
                print(green(f"  完成：gitlink 已重建，工作区已切到 {branch} 分支最新。"))
                print(yellow("  注意：父仓库 index 已更新（gitlink 指向分支最新），需要提交父仓库指针，建议命令："))
                print(f"    git add --force {n}")
                print(f'    git commit -m "fix: 重建 {n} 子模块 gitlink"')
            else:
                print(green(f"  完成：已恢复并切到 {branch} 分支；父仓库指针未变化，无需提交。"))
        else:
            failed.append(n)

    if failed:
        print(red(f"以下子模块恢复过程出错：{', '.join(failed)}"))
        return 3
    print()
    print(green("restore 完成。全程未触碰远端，未自动提交任何父仓库变更。"))
    return 0


# ---------------- 入口 ----------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    # 参数形态沿用原 PowerShell 版：-Action / -Name（-Name 支持空格与逗号分隔多个）
    parser = argparse.ArgumentParser(
        prog="submodule-toggle",
        description="语言子模块临时注销（deinit）/ 恢复（restore）一键脚本，带前置检查与只读体检",
    )
    parser.add_argument("-Action", dest="action", required=True,
                        choices=["status", "deinit", "restore"],
                        help="动作：status=只读体检 | deinit=本地注销 | restore=恢复+切跟踪分支")
    parser.add_argument("-Name", dest="names", required=True, nargs="+",
                        help="子模块名称（空格或逗号分隔多个；必须显式给出，防止误伤主力子模块）")
    args = parser.parse_args(argv)
    # 逗号分隔展开（兼容原 -Name native_projects,rust_projects 写法）
    expanded: list[str] = []
    for item in args.names:
        expanded.extend(part.strip() for part in item.split(",") if part.strip())
    args.names = expanded
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not (REPO_ROOT / ".gitmodules").exists():
        print(red(f"错误：{REPO_ROOT} 不是父仓库根（未找到 .gitmodules），请在父仓库内运行。"))
        return 1

    known = known_submodules(REPO_ROOT / ".gitmodules")
    invalid = [n for n in args.names if n not in known]
    if invalid:
        print(red(f"错误：以下名称未在 .gitmodules 登记：{', '.join(invalid)}"))
        print(f"已登记的子模块：{', '.join(known)}")
        show_usage()
        return 1

    try:
        if args.action == "status":
            return action_status(REPO_ROOT, args.names)
        if args.action == "deinit":
            return action_deinit(REPO_ROOT, args.names)
        return action_restore(REPO_ROOT, args.names)
    except GitError as exc:
        print(red(f"执行失败：{exc}"))
        return 3


if __name__ == "__main__":
    sys.exit(main())
