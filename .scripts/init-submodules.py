# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# init-submodules.py —— 克隆后初始化子模块并切换到跟踪分支
# 用法：git clone --recurse-submodules <URL> 后，在父仓库根目录执行一次
#     uv run .scripts/init-submodules.py
# 说明：git 子模块默认以 detached HEAD checkout 父仓库记录的 commit，
#       本脚本在初始化后按 .gitmodules 中各子模块的 branch 字段切到对应本地分支。

import re
import subprocess
import sys

# Windows 下 stdout 重定向到管道时默认走 locale 编码（cp936），中文会乱码；
# 统一重配置为 UTF-8 并开行缓冲（保证与子进程透传输出的顺序一致）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    """执行 git 命令并返回结果（输出按 UTF-8 解码）。"""
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def main() -> int:
    # 1. 仅初始化尚未拉取的子模块（status 输出前缀 '-' 表示未初始化）；
    #    已存在的 checkout 保持原样，不把领先指针的子模块拽回旧 commit
    status = run_git("submodule", "status")
    if status.returncode != 0:
        sys.stderr.write(status.stderr)
        return status.returncode
    for line in status.stdout.splitlines():
        m = re.match(r"^-[0-9a-f]+ (\S+)", line)
        if not m:
            continue
        sm_path = m.group(1)
        print(f"init: {sm_path}")
        r = subprocess.run(["git", "submodule", "update", "--init", "--", sm_path])
        if r.returncode != 0:
            return r.returncode

    # 2. 按各子模块在 .gitmodules 中声明的 branch 切换本地分支；
    #    未声明 branch 时回退 master，再回退 main
    #    （git switch 在本地无同名分支时会自动创建并跟踪 origin/<branch>）
    foreach_cmd = (
        'branch=$(git config -f $toplevel/.gitmodules submodule.$name.branch); '
        'if [ -z "$branch" ]; then branch=master; fi; '
        'git switch "$branch" 2>/dev/null || git switch main'
    )
    r = subprocess.run(["git", "submodule", "foreach", "--recursive", foreach_cmd])
    if r.returncode != 0:
        return r.returncode

    print("OK: 子模块已初始化并全部切换到跟踪分支。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
