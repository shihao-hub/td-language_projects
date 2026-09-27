# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.0"]
# ///
# make-icon.py — 生成 winres\icon.png（256x256 源图标）
#
# 视觉：深靛蓝渐变圆角底 + 2x2 彩色圆角方块网格（应用启动器隐喻），
# 右下角白色方块内嵌靛蓝播放三角，点出「启动」。16px 托盘尺寸下四色网格仍可辨。
# 改完重新生成本图后，需再执行（在仓库根目录）：
#   go-winres make --arch amd64 --out cmd\exe-launcher\rsrc
# 把各尺寸（16/32/48/256）打包进 cmd\exe-launcher\rsrc_windows_amd64.syso 并重新 scripts\build.py。
# 用法：uv run winres/make-icon.py（原 PS 版基于 System.Drawing，此处用 Pillow 直译）

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256    # 画布边长
RADIUS = 58   # 外框圆角半径
OUT = Path(__file__).resolve().parent / "icon.png"

# 2x2 彩色方块网格参数
TILE = 84.0   # 方块边长
GAP = 12.0    # 间隙
MARGIN = (SIZE - (TILE * 2 + GAP)) / 2   # 38
TR = 18.0     # 方块圆角
# 右下角先画白方块，其余三块用彩色（靛蓝/青/琥珀）
TL_COLOR = (0x81, 0x8C, 0xF8)   # 靛蓝 300
TR_COLOR = (0x22, 0xD3, 0xEE)   # 青 400
BL_COLOR = (0xFB, 0xBF, 0x24)   # 琥珀 400
TRI_COLOR = (0x4F, 0x46, 0xE5)  # 白方块里的播放三角（靛蓝）


def main() -> int:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 1. 外底：对角线渐变 深靛蓝 → 藏蓝（逐行插值填充后按圆角裁剪）
    c1 = (0x37, 0x30, 0xA3)
    c2 = (0x1E, 0x1B, 0x4B)
    grad = Image.new("RGBA", (SIZE, SIZE))
    gd = ImageDraw.Draw(grad)
    for i in range(SIZE):
        t = i / (SIZE - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
        gd.line([(0, i), (SIZE, i)], fill=color)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # 2. 2x2 彩色方块网格
    x1, x2 = MARGIN, MARGIN + TILE + GAP
    y1, y2 = MARGIN, MARGIN + TILE + GAP
    d.rounded_rectangle([x1, y1, x1 + TILE, y1 + TILE], radius=TR, fill=TL_COLOR)
    d.rounded_rectangle([x2, y1, x2 + TILE, y1 + TILE], radius=TR, fill=TR_COLOR)
    d.rounded_rectangle([x1, y2, x1 + TILE, y2 + TILE], radius=TR, fill=BL_COLOR)
    d.rounded_rectangle([x2, y2, x2 + TILE, y2 + TILE], radius=TR, fill=(255, 255, 255))

    # 3. 白方块里的播放三角（光学上右移）
    cx, cy = x2 + TILE / 2 + 3, y2 + TILE / 2
    tw, th = 16.0, 22.0
    d.polygon(
        [(cx - tw / 2, cy - th / 2), (cx - tw / 2, cy + th / 2), (cx + tw / 2, cy)],
        fill=TRI_COLOR,
    )

    img.save(OUT, "PNG")
    print(f"saved: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
