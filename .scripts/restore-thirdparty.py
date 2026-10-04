# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# restore-thirdparty.py —— 检查并恢复 .thirdparty 外部依赖项目
# 用法：在仓库根目录下执行
#     uv run .scripts/restore-thirdparty.py
#     uv run .scripts/restore-thirdparty.py --check
#     uv run .scripts/restore-thirdparty.py --name mini-swe-agent

import argparse
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPOSITORIES = [
    {
        "name": "Antigravity-Hans",
        "url": "https://github.com/yuexps/Antigravity-Hans.git",
        "branch": "main",
        "desc": "Google Antigravity 汉化工具与 GUI 构建流水线",
    },
    {
        "name": "claude-code-transcripts",
        "url": "https://github.com/simonw/claude-code-transcripts.git",
        "branch": "main",
        "desc": "Simon Willison 的 Claude Code 会话历史记录工具",
    },
    {
        "name": "ClaudeScope",
        "url": "https://github.com/Liuziyu77/ClaudeScope.git",
        "branch": "main",
        "desc": "Claude Code 会话执行轨迹与思维链可视化 UI",
    },
    {
        "name": "codex",
        "url": "https://github.com/openai/codex.git",
        "branch": "main",
        "desc": "OpenAI 官方开源本地终端编程 Agent CLI",
    },
    {
        "name": "commerce-agents",
        "url": "https://github.com/anthropics/commerce-agents.git",
        "branch": "main",
        "desc": "Anthropic 官方开源 Claude 商业/电商 Agent 范式",
    },
    {
        "name": "ContextMenuManager",
        "url": "https://github.com/BluePointLilac/ContextMenuManager.git",
        "branch": "master",
        "desc": "Windows 纯粹右键菜单管理程序",
    },
    {
        "name": "deepseek-harness",
        "url": "https://github.com/deepseek-ai/deepseek-harness.git",
        "branch": "master",
        "tag": "dsh-v0.2.0-rc.1",
        "desc": "DeepSeek 官方评测框架与 Harness 工具",
    },
    {
        "name": "dive-into-llms",
        "url": "https://github.com/Lordog/dive-into-llms.git",
        "branch": "main",
        "desc": "《动手学大模型》系列编程实践教程",
    },
    {
        "name": "FerretDB",
        "url": "https://github.com/FerretDB/FerretDB.git",
        "branch": "main",
        "desc": "Go 实现的开源 MongoDB 替代方案（转译 PG/SQLite）",
    },
    {
        "name": "mini-swe-agent",
        "url": "https://github.com/SWE-agent/mini-swe-agent.git",
        "branch": "main",
        "desc": "SWE-agent 极简软件工程智能体（含中英双语文档）",
    },
    {
        "name": "minimax-code",
        "url": "https://github.com/MiniMax-AI/minimax-code.git",
        "branch": "main",
        "desc": "MiniMax 官方开源代码编程助手与 Agent CLI",
    },
    {
        "name": "nanocode",
        "url": "https://github.com/1rgs/nanocode.git",
        "branch": "master",
        "desc": "极简命令行 AI 编程 Agent 原型",
    },
    {
        "name": "opencode",
        "url": "https://github.com/anomalyco/opencode.git",
        "branch": "dev",
        "desc": "全功能开源终端 AI 辅助编程系统",
    },
    {
        "name": "pi-mono",
        "url": "https://github.com/badlogic/pi-mono.git",
        "branch": "main",
        "desc": "Mario Zechner 的 pi 智能体生态 Monorepo",
    },
    {
        "name": "QwenPaw",
        "url": "https://github.com/agentscope-ai/QwenPaw.git",
        "branch": "main",
        "tag": "v2.2.1-beta.1",
        "desc": "基于 AgentScope 与 Qwen 的智能体个人助手",
    },
    {
        "name": "screenshot-to-code",
        "url": "https://github.com/abi/screenshot-to-code.git",
        "branch": "main",
        "desc": "截图一键生成 HTML/Tailwind/React/Vue 前端页面",
    },
    {
        "name": "ZCode",
        "url": "https://github.com/zai-org/ZCode.git",
        "branch": "main",
        "tag": "v3.14.3",
        "desc": "智谱 AI (ZAI) 开源的代码生成提效工具套件",
    },
]

SPECIAL_DIRS = [
    {
        "name": "antigravity-acp-src",
        "desc": "Google Antigravity ACP 核心源码（官方二进制解包）",
    },
    {
        "name": "docs",
        "desc": "离线参考文档（包含 cli_debugging_guide.md 终端调试实战指南）",
    },
    {
        "name": "nanocode-acl-recovery",
        "desc": "nanocode 目录 Windows ACL 权限恢复备份脚本套件",
    },
]


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="检查与恢复 .thirdparty 外部依赖项目")
    parser.add_argument("--check", action="store_true", help="只做状态检查，不执行 clone")
    parser.add_argument("--name", type=str, default="", help="仅针对指定项目执行恢复或检查")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    tp_dir = repo_root / ".thirdparty"

    if not tp_dir.exists():
        if args.check:
            print(f"[!] .thirdparty 目录不存在: {tp_dir}")
            return 1
        print(f"[+] 创建 .thirdparty 目录: {tp_dir}")
        tp_dir.mkdir(parents=True, exist_ok=True)

    items = REPOSITORIES
    if args.name:
        items = [r for r in REPOSITORIES if r["name"].lower() == args.name.lower()]
        if not items:
            print(f"[-] 未找到登记的第三方项目: {args.name}")
            return 1

    print(f"=== .thirdparty 状态盘点 ({len(items)} 个 Git 仓库) ===")
    missing_count = 0

    for r in items:
        target = tp_dir / r["name"]
        if not target.exists():
            missing_count += 1
            if args.check:
                print(f"[-] [缺失] {r['name']:<25} 远端: {r['url']}")
                continue

            print(f"[+] 正在克隆 {r['name']}...")
            branch = r.get("branch", "main")
            clone_cmd = ["clone", "--depth", "50", "--branch", branch, r["url"], str(target)]
            res = run_git(clone_cmd)
            if res.returncode != 0:
                fallback_cmd = ["clone", "--depth", "50", r["url"], str(target)]
                res2 = run_git(fallback_cmd)
                if res2.returncode != 0:
                    print(f"    [X] 克隆失败: {res.stderr.strip()}")
                    continue

            tag = r.get("tag")
            if tag:
                run_git(["checkout", tag], cwd=target)

            print(f"    [√] {r['name']} 恢复完成")
        else:
            is_git = (target / ".git").exists()
            if is_git:
                branch_out = run_git(["branch", "--show-current"], cwd=target).stdout.strip()
                head_out = run_git(["rev-parse", "--short", "HEAD"], cwd=target).stdout.strip()
                dirty = bool(run_git(["status", "--porcelain"], cwd=target).stdout.strip())
                dirty_flag = " (有本地修改)" if dirty else ""
                print(f"[√] [正常] {r['name']:<25} [{branch_out or 'detached'} @ {head_out}]{dirty_flag}")
            else:
                print(f"[?] [非Git] {r['name']:<24}")

    if not args.name:
        print("\n=== 非 Git 归档目录 ===")
        for s in SPECIAL_DIRS:
            target = tp_dir / s["name"]
            status = "[存在]" if target.exists() else "[缺失]"
            print(f"{status} {s['name']:<25} {s['desc']}")

    print("\n盘点完毕。详情可阅读根目录下的 THIRDPARTY.md 了解远端地址与定制细节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())