# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# check-agy-upstream.py —— Google Antigravity ACP 上游监控检测
# 用法：
#     uv run .scripts/check-agy-upstream.py                  # 检查 Registry 版本 + 搜索 GitHub 社区仓库
#     uv run .scripts/check-agy-upstream.py --only-registry  # 仅检查官方 ACP Registry 版本
#     uv run .scripts/check-agy-upstream.py --query "xxx"    # 自定义 GitHub 搜索关键词
# 说明：对比 Zed 本地已装 antigravity-acp 版本与官方 ACP Registry 最新版本并提示升级路径；
#       全部走标准库 urllib，零三方依赖。

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

USER_AGENT = "Py-AGY-Checker"
REGISTRY_URL = "https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json"
LOCAL_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Zed" / "external_agents" / "registry" / "antigravity-acp"
DEFAULT_QUERY = "antigravity acp"
HTTP_TIMEOUT = 10  # 秒

# Windows 下 stdout 重定向到管道时默认走 locale 编码（cp936），中文会乱码；统一重配置为 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def http_get_json(url: str, headers: dict[str, str]) -> dict | None:
    """GET 一个 JSON 接口，失败时打印警告并返回 None（不中断整体流程）。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 —— 网络/解析失败统一降级为警告
        print(f"WARNING: 请求 {url} 失败: {exc}")
        return None


def local_version() -> str:
    """读取 Zed 本地已安装的 antigravity-acp 版本（v_* 目录名）。"""
    if not LOCAL_INSTALL_DIR.is_dir():
        return "未知(未安装)"
    dirs = sorted(p.name for p in LOCAL_INSTALL_DIR.iterdir() if p.is_dir() and p.name.startswith("v_"))
    if not dirs:
        return "未知(未安装)"
    first = dirs[0]
    # 目录名形如 v_<version>_<hash>，取第一段下划线前的版本号
    if first.startswith("v_"):
        rest = first[2:]
        version = rest.split("_", 1)[0]
        return version if version else first
    return first


def main() -> int:
    parser = argparse.ArgumentParser(description="检测 Google Antigravity ACP 上游 Registry 版本与 GitHub 社区仓库动态")
    parser.add_argument("--only-registry", action="store_true",
                        help="仅检测官方 ACP Registry 版本，不调用 GitHub 搜索 API")
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help=f"自定义 GitHub 搜索关键词（默认为 {DEFAULT_QUERY!r}）")
    args = parser.parse_args()

    print("=" * 50)
    print("       Google Antigravity ACP 上游监控检测        ")
    print("=" * 50)
    print()

    # ----------------------------------------------------
    # 1. 检查官方 ACP Registry 与本地已安装版本
    # ----------------------------------------------------
    print("[1/2] 正在检查 ACP 官方注册表与本地版本...")

    installed = local_version()
    remote_version: str | None = None
    remote_dist: str | None = None

    resp = http_get_json(REGISTRY_URL, {})
    if resp is not None:
        for agent in resp.get("agents", []):
            if agent.get("id") == "antigravity-acp":
                remote_version = agent.get("version")
                remote_dist = (agent.get("distribution", {}).get("binary", {})
                               .get("windows-x86_64", {}).get("archive"))
                break

    print(f"  * 本地已安装版本 : {installed}")
    if remote_version:
        print(f"  * 上游 Registry 版本: {remote_version}")
        if remote_dist:
            print(f"  * 上游分发包 URL  : {remote_dist}")
        if installed == remote_version:
            print("  ✔ 当前本地版本与上游 Registry 一致 (最新版)。")
        else:
            print(f"  ▲ 检测到版本差异！本地: {installed} -> 上游: {remote_version}")
            print("    可在 Zed 命令面板运行 'agent: update' 或重启 Zed 触发自动升级。")
    else:
        print("  * 未能获取到远端版本。")

    print()

    if args.only_registry:
        return 0

    # ----------------------------------------------------
    # 2. 检索 GitHub 社区活跃仓库
    # ----------------------------------------------------
    print(f"[2/2] 正在搜索 GitHub 社区仓库 (关键词: '{args.query}')...")

    search_url = (
        "https://api.github.com/search/repositories?q="
        + urllib.parse.quote(args.query)
        + "&sort=updated&order=desc&per_page=6"
    )
    gh_resp = http_get_json(search_url, {"Accept": "application/vnd.github.v3+json"})
    if gh_resp is not None:
        items = gh_resp.get("items", [])
        if items:
            print(f"  找到 {len(items)} 个相关仓库：")
            print()
            for repo in items:
                updated = "-"
                if repo.get("updated_at"):
                    try:
                        updated = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
                    except ValueError:
                        updated = str(repo["updated_at"])[:10]
                print(f"  - {repo.get('full_name', '?')}"
                      f" (⭐ {repo.get('stargazers_count', 0)} | 更新于 {updated})")
                if repo.get("description"):
                    print(f"    {repo['description']}")
                print(f"    {repo.get('html_url', '')}")
        else:
            print("  未找到匹配的相关仓库。")

    print()
    print("检测完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
