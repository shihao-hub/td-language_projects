# /// script
# requires-python = ">=3.10"
# dependencies = ["radon>=6"]
# ///
# calc_crap.py：按 CRAP 公式（CC^2 * (1-cov)^3 + CC）统计 Python 代码的
# 复杂度与覆盖率复合风险，供 Zed 任务「CRAP: Python」调用。
# 用法: coverage run -m pytest && coverage json -o coverage.json &&
#       uv run .scripts/calc_crap.py --cov coverage.json --threshold 30
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from radon.complexity import cc_visit
except ImportError:
    print("[ERROR] 缺少 radon 依赖，请运行: uv run .scripts/calc_crap.py（PEP 723 会自动装）", file=sys.stderr)
    sys.exit(1)


def calculate_crap(cc: int, cov: float) -> float:
    """CRAP = CC^2 * (1 - cov)^3 + CC"""
    return (cc**2) * ((1.0 - cov) ** 3) + cc


def normalize_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/").lower()


def main():
    parser = argparse.ArgumentParser(description="Calculate CRAP score for Python code.")
    parser.add_argument("--src", default=".", help="Source directory to analyze (default: current directory)")
    parser.add_argument("--cov", default="coverage.json", help="Path to coverage.json (default: coverage.json)")
    parser.add_argument("--threshold", type=float, default=30.0, help="CRAP threshold (default: 30.0)")
    parser.add_argument("--all", action="store_true", help="Display all functions, not just those over threshold")
    args = parser.parse_args()

    cov_file = Path(args.cov)
    if not cov_file.is_file():
        print(f"[ERROR] 找不到覆盖率文件: {cov_file}", file=sys.stderr)
        print("请先运行单元测试生成 coverage.json:", file=sys.stderr)
        print("  coverage run -m pytest", file=sys.stderr)
        print("  coverage json -o coverage.json", file=sys.stderr)
        sys.exit(1)

    with open(cov_file, "r", encoding="utf-8") as f:
        try:
            cov_data = json.load(f).get("files", {})
        except Exception as e:
            print(f"[ERROR] 解析 {cov_file} 失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 规范化 coverage 键路径以支持跨平台匹配
    normalized_cov = {}
    for file_path, data in cov_data.items():
        norm_key = Path(file_path).resolve().as_posix().lower()
        normalized_cov[norm_key] = set(data.get("executed_lines", []))

    src_path = Path(args.src).resolve()
    results = []
    ignored_dirs = {".venv", "venv", "__pycache__", ".git", ".pytest_cache", ".tox", "build", "dist"}

    for root, dirs, files in os.walk(src_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for file in files:
            if not file.endswith(".py") or file.startswith("test_") or file.endswith("_test.py"):
                continue

            file_p = Path(root) / file
            norm_file_key = file_p.as_posix().lower()
            rel_path = file_p.relative_to(src_path).as_posix()

            try:
                code_content = file_p.read_text(encoding="utf-8")
            except Exception:
                continue

            # 获取该文件的执行覆盖行
            executed_lines = None
            if norm_file_key in normalized_cov:
                executed_lines = normalized_cov[norm_file_key]
            else:
                for cov_k, lns in normalized_cov.items():
                    if cov_k.endswith(rel_path.lower()):
                        executed_lines = lns
                        break
            if executed_lines is None:
                executed_lines = set()

            try:
                blocks = cc_visit(code_content)
            except Exception:
                continue

            for block in blocks:
                # 只分析函数与方法
                if getattr(block, "is_method", False) or getattr(block, "name", None):
                    func_lines = set(range(block.lineno, block.endline + 1))
                    total_lines = len(func_lines)
                    if total_lines == 0:
                        cov_ratio = 1.0
                    else:
                        cov_ratio = len(func_lines & executed_lines) / total_lines

                    crap = calculate_crap(block.complexity, cov_ratio)
                    results.append({
                        "name": block.name,
                        "file": rel_path,
                        "line": block.lineno,
                        "cc": block.complexity,
                        "cov": cov_ratio,
                        "crap": crap,
                    })

    results.sort(key=lambda x: x["crap"], reverse=True)

    header = f"{'CRAP':>6} | {'CC':>4} | {'Cov%':>6} | {'Location':<45} | {'Function'}"
    divider = "-" * len(header)
    print(header)
    print(divider)

    high_risk_count = 0
    displayed_count = 0
    for r in results:
        is_risky = r["crap"] >= args.threshold
        if is_risky:
            high_risk_count += 1

        if is_risky or args.all:
            displayed_count += 1
            flag = " [CRAP]" if is_risky else ""
            loc = f"{r['file']}:{r['line']}"
            print(f"{r['crap']:>6.1f} | {r['cc']:>4} | {r['cov']*100:>5.1f}% | {loc:<45} | {r['name']}{flag}")

    if displayed_count == 0:
        print(f"恭喜！所有函数 CRAP 分数均低于设定阈值 ({args.threshold})。")

    print(divider)
    print(f"总计检测到 {len(results)} 个函数，其中高风险函数 (CRAP >= {args.threshold}): {high_risk_count} 个。")
    if high_risk_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
