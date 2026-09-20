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
#   uv run .scripts/build_docs.py preview         # 构建+分词后起静态服务并自动开浏览器（搜索用，Ctrl+C 退出）
#   uv run .scripts/build_docs.py serve           # 写作期热刷新（http://127.0.0.1:8765，不做分词）
#   uv run .scripts/build_docs.py build --strict  # 严格校验（警告视为错误，断链检查）
# 说明: 依赖由 PEP 723 内联声明，uv 全局缓存解析，仓库内不产生任何 Python 工程文件；
#       .mkdocs-site/ 为构建产物，已入 .gitignore，随时删除重建。
#       本文件必须保持 UTF-8 无 BOM：uv 对带 BOM 脚本的 PEP 723 依赖识别会失效。
# 中文搜索: mkdocs 内置搜索的 worker 无中文分词器，且 lunr tokenizer 按单字符
#       match separator（零宽断言恒失败），无法在配置层切分汉字。本脚本在 build
#       完成后用 jieba 对 search_index.json 的 title/text 做预分词（空格分隔），
#       浏览器端按默认空格 separator 建出词级索引；中文查询串（无空格）作为
#       整词恰好命中预分出的词。serve 模式不做后处理，中文搜索以 build 产物为准。

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / ".mkdocs-site"
INDEX_PATH = SITE_DIR / "search" / "search_index.json"

TAG_RE = re.compile(r"<[^>]+>")
CJK_RE = re.compile(r"[\u4e00-\u9fa5]")
CJK_RUN_RE = re.compile(r"([\u4e00-\u9fa5]+)")


def segment_search_index() -> int:
    # 对索引中的中文文本做 jieba 预分词；HTML 标签原样保留，只处理标签外文本；
    # 仅对连续中文段分词，非中文片段（代码标识符、URL 等）原样保留
    import jieba

    jieba.setLogLevel(60)  # 关闭 jieba 初始化日志
    # 常用专名补词：jieba 默认词典缺仓库高频术语，补上可提升索引与查询切分精度
    for word in ("飞书", "子模块", "多维表格"):
        jieba.add_word(word)

    def seg_plain(chunk: str) -> str:
        if not CJK_RE.search(chunk):
            return chunk
        parts = CJK_RUN_RE.split(chunk)
        out = [p if i % 2 == 0 else " ".join(jieba.cut(p)) for i, p in enumerate(parts)]
        return " ".join(out)

    def seg(text: str) -> str:
        if not CJK_RE.search(text):
            return text
        parts: list[str] = []
        pos = 0
        for m in TAG_RE.finditer(text):
            parts.append(seg_plain(text[pos : m.start()]))
            parts.append(m.group(0))
            pos = m.end()
        parts.append(seg_plain(text[pos:]))
        return "".join(parts)

    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    count = 0
    for doc in data.get("docs", []):
        for field in ("title", "text"):
            if doc.get(field):
                doc[field] = seg(doc[field])
                count += 1
    INDEX_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return count


def preview() -> int:
    # 构建 + jieba 分词后起本地静态服务并自动打开浏览器，供 file:// 下不可用的搜索场景使用
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
    if INDEX_PATH.is_file():
        fields = segment_search_index()
        print(f"中文分词后处理完成：{fields} 个字段已 jieba 预分词")

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
    parser.add_argument("command", choices=["build", "serve", "preview"], help="build=构建；preview=构建+分词+静态服务（搜索用）；serve=写作热刷新")
    parser.add_argument("--strict", action="store_true", help="build 时启用严格校验（警告视为错误）")
    args = parser.parse_args()

    if args.command == "preview":
        return preview()

    cmd = [sys.executable, "-m", "mkdocs", args.command, "--config-file", str(ROOT / "mkdocs.yml")]
    if args.command == "build" and args.strict:
        cmd.append("--strict")
    if args.command == "serve":
        cmd += ["--dev-addr", "127.0.0.1:8765"]

    code = subprocess.call(cmd, cwd=str(ROOT))
    if code == 0 and args.command == "build" and INDEX_PATH.is_file():
        fields = segment_search_index()
        print(f"中文分词后处理完成：{fields} 个字段已 jieba 预分词")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
