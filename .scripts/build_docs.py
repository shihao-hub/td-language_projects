# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mkdocs-material>=9.5",
#   "mkdocs-awesome-pages-plugin>=2.9",
#   "jieba>=0.42",
# ]
# ///
# build_docs.py：docs/ 静态文档站点的构建入口（Material for MkDocs）。
# 用法:
#   uv run .scripts/build_docs.py build           # 构建 .mkdocs-site/（file:// 双击 index.html 浏览）
#   uv run .scripts/build_docs.py preview         # 构建后起一次性静态服务并自动开浏览器（只读浏览，Ctrl+C 退出）
#   uv run .scripts/build_docs.py serve           # 写作期热刷新 + 中文搜索（http://127.0.0.1:12345）
#   uv run .scripts/build_docs.py build --strict  # 严格校验（警告视为错误，断链检查）
# 说明: 依赖由 PEP 723 内联声明，uv 全局缓存解析，仓库内不产生任何 Python 工程文件；
#       .mkdocs-site/ 为构建产物，已入 .gitignore，随时删除重建。
#       本文件必须保持 UTF-8 无 BOM：uv 对带 BOM 脚本的 PEP 723 依赖识别会失效。
# 中文搜索: 依赖 mkdocs-material 内置的中文处理——搜索插件在 jieba 可导入时，会把索引里
#       的汉字按 jieba 词切分并用零宽空格（\u200b）连接，zh 语言包又把 \u200b 与空白都
#       算作分隔符，查询侧再按倒排索引词典做贪心切分，因此中文搜索开箱即用、无需后处理。
#       本脚本的 PEP 723 里声明 jieba 就是为触发这条链路（缺 jieba 时 material 会静默
#       跳过中文切分，中文搜索退化为整段匹配）。build / serve / preview 三个入口行为一致。

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / ".mkdocs-site"


def preview() -> int:
    # 构建后起本地静态服务并自动打开浏览器；只读浏览用（写作请用 serve 热刷新）
    import threading
    import webbrowser
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    code = subprocess.call(
        [sys.executable, "-m", "mkdocs", "build", "--config-file", str(ROOT / "mkdocs.yml")],
        cwd=str(ROOT),
    )
    if code != 0:
        return code

    url = "http://127.0.0.1:8766/"
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE_DIR))
    with ThreadingHTTPServer(("127.0.0.1", 8766), handler) as httpd:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        print(f"预览服务已启动：{url}（Ctrl+C 退出）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("预览服务已停止")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="docs/ 静态站点构建（Material for MkDocs）")
    parser.add_argument("command", choices=["build", "serve", "preview"], help="build=构建；serve=写作期热刷新+中文搜索；preview=构建后起静态服务（只读浏览）")
    parser.add_argument("--strict", action="store_true", help="build 时启用严格校验（警告视为错误）")
    args = parser.parse_args()

    if args.command == "preview":
        return preview()

    cmd = [sys.executable, "-m", "mkdocs", args.command, "--config-file", str(ROOT / "mkdocs.yml")]
    if args.command == "build" and args.strict:
        cmd.append("--strict")
    if args.command == "serve":
        cmd += ["--dev-addr", "127.0.0.1:12345"]

    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
