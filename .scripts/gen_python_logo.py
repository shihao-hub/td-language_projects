# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.0"]
# ///
# gen_python_logo.py：生成 Python 双蛇标志高分辨率透明 PNG（exe 默认图标源图）。
# 用法: uv run .scripts/gen_python_logo.py [输出.png]（默认 python-logo-1024.png）
# 说明: path 数据内嵌自 Wikimedia 官方 Python-logo-notext.svg（110x110 viewBox），
#       贝塞尔展平后用 Pillow 多边形填充，填充 PSF 官方扁平品牌色，
#       眼睛子路径挖洞保持透明；产物再交给 gen_icon.py 出多帧 ico：
#       uv run .scripts/gen_python_logo.py logo.png && uv run .scripts/gen_icon.py logo.png <输出.ico>

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# viewBox="0.21 -0.077 110 110"
VX, VY, VW = 0.21, -0.077, 110.0
SIDE = 1024
BLUE = (55, 118, 171, 255)    # #3776AB（PSF 官方扁平蓝）
YELLOW = (255, 212, 59, 255)  # #FFD43B（PSF 官方扁平黄）

BLUE_PATH = (
    "M55.023,-0.077c-25.971,0-26.25,10.081-26.25,12.156c0,3.148,0,12.594,0,12.594"
    "h26.75v3.781c0,0-27.852,0-37.375,0c-7.949,0-17.938,4.833-17.938,26.25"
    "c0,19.673,7.792,27.281,15.656,27.281c2.335,0,9.344,0,9.344,0s0-9.765,0-13.125"
    "c0-5.491,2.721-15.656,15.406-15.656c15.91,0,19.971,0,26.531,0"
    "c3.902,0,14.906-1.696,14.906-14.406c0-13.452,0-17.89,0-24.219"
    "C82.054,11.426,81.515,-0.077,55.023,-0.077z "
    "M40.273,8.392c2.662,0,4.813,2.15,4.813,4.813c0,2.661-2.151,4.813-4.813,4.813"
    "s-4.813-2.151-4.813-4.813C35.46,10.542,37.611,8.392,40.273,8.392z"
)
YELLOW_PATH = (
    "M55.397,109.923c25.959,0,26.282-10.271,26.282-12.156c0-3.148,0-12.594,0-12.594"
    "H54.897v-3.781c0,0,28.032,0,37.375,0c8.009,0,17.938-4.954,17.938-26.25"
    "c0-23.322-10.538-27.281-15.656-27.281c-2.336,0-9.344,0-9.344,0s0,10.216,0,13.125"
    "c0,5.491-2.631,15.656-15.406,15.656c-15.91,0-19.476,0-26.532,0"
    "c-3.892,0-14.906,1.896-14.906,14.406c0,14.475,0,18.265,0,24.219"
    "C28.366,100.497,31.562,109.923,55.397,109.923z "
    "M70.148,101.454c-2.662,0-4.813-2.151-4.813-4.813s2.15-4.813,4.813-4.813"
    "c2.661,0,4.813,2.151,4.813,4.813S72.809,101.454,70.148,101.454z"
)

TOKEN_RE = re.compile(r"([MmCcHhVvSsZz])|(-?\d*\.?\d+(?:e-?\d+)?)", re.I)


def parse_path(d: str) -> list[list[tuple[float, float]]]:
    """解析 path 为若干子路径（转绝对坐标，三次贝塞尔按 24 段展平）。"""
    seq: list[tuple[str, str | None]] = [
        (cmd, None) if cmd else ("num", num) for cmd, num in TOKEN_RE.findall(d)
    ]
    subs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = sx = sy = px = py = 0.0
    i = 0
    last_cmd = ""

    def nums(count: int) -> list[float]:
        nonlocal i
        vals = [float(seq[i + j][1]) for j in range(count)]
        i += count
        return vals

    while i < len(seq):
        cmd, _ = seq[i]
        if cmd != "num":
            last_cmd = cmd
            i += 1
            if cmd in "Zz" and cur:
                subs.append(cur)
                cur = []
            continue
        c = last_cmd
        if c in "Mm":
            dx, dy = nums(2)
            x, y = (x + dx, y + dy) if c == "m" else (dx, dy)
            sx, sy = x, y
            if cur:
                subs.append(cur)
            cur = [(x, y)]
            last_cmd = "L"
        elif c in "Ll":
            dx, dy = nums(2)
            x, y = (x + dx, y + dy) if c == "l" else (dx, dy)
            cur.append((x, y))
        elif c in "Hh":
            (dx,) = nums(1)
            x = x + dx if c == "h" else dx
            cur.append((x, y))
        elif c in "Vv":
            (dy,) = nums(1)
            y = y + dy if c == "v" else dy
            cur.append((x, y))
        elif c in "Cc":
            p = nums(6)
            if c == "c":
                p = [p[0] + x, p[1] + y, p[2] + x, p[3] + y, p[4] + x, p[5] + y]
            c1x, c1y, c2x, c2y, ex, ey = p
            for t in [j / 24 for j in range(1, 25)]:
                mt = 1 - t
                cur.append((
                    mt**3 * x + 3 * mt**2 * t * c1x + 3 * mt * t**2 * c2x + t**3 * ex,
                    mt**3 * y + 3 * mt**2 * t * c1y + 3 * mt * t**2 * c2y + t**3 * ey,
                ))
            px, py, x, y = c2x, c2y, ex, ey
        elif c in "Ss":
            p = nums(4)
            if c == "s":
                p = [p[0] + x, p[1] + y, p[2] + x, p[3] + y]
            c1x, c1y = 2 * x - px, 2 * y - py
            c2x, c2y, ex, ey = p
            for t in [j / 24 for j in range(1, 25)]:
                mt = 1 - t
                cur.append((
                    mt**3 * x + 3 * mt**2 * t * c1x + 3 * mt * t**2 * c2x + t**3 * ex,
                    mt**3 * y + 3 * mt**2 * t * c1y + 3 * mt * t**2 * c2y + t**3 * ey,
                ))
            px, py, x, y = c2x, c2y, ex, ey
        else:
            raise ValueError(f"未支持的命令: {c}")
    if cur:
        subs.append(cur)
    return subs


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("python-logo-1024.png")
    k = SIDE / VW
    img = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for d, color in ((BLUE_PATH, BLUE), (YELLOW_PATH, YELLOW)):
        subs = [
            [((px - VX) * k, (py - VY) * k) for px, py in sub]
            for sub in parse_path(d)
        ]
        mask = Image.new("L", (SIDE, SIDE), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.polygon(subs[0], fill=255)
        for hole in subs[1:]:  # 眼睛子路径挖洞
            mdraw.polygon(hole, fill=0)
        img.paste(color, (0, 0), mask)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"已生成: {out} ({out.stat().st_size} bytes), {SIDE}x{SIDE} 透明底 PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
