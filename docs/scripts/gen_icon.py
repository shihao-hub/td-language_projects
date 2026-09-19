# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.0"]
# ///
# gen_icon.py：把一张 PNG 源图转成多尺寸 Windows .ico 图标。
# 用法: uv run gen_icon.py <input.png> <output.ico>
# 说明: 非方形源图会等比缩放并居中放到透明方形画布上；
#       输出帧: 16/24/32/48/64/128/256。

import argparse
import sys
from pathlib import Path

from PIL import Image

SIZES = [16, 24, 32, 48, 64, 128, 256]


def main() -> int:
    parser = argparse.ArgumentParser(description="PNG 转多尺寸 Windows ico")
    parser.add_argument("input", help="源图路径（建议 >=256px、透明底 PNG）")
    parser.add_argument("output", help="输出 .ico 路径")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.is_file():
        print(f"错误: 源图不存在: {src}", file=sys.stderr)
        return 1

    img = Image.open(src).convert("RGBA")

    # 等比缩放并居中到透明方形画布
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)

    # 逐帧 LANCZOS 重采样，保证小尺寸清晰度
    frames = [canvas.resize((s, s), Image.LANCZOS) for s in SIZES]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[-1].save(out, format="ICO", append_images=frames[:-1], sizes=[(s, s) for s in SIZES])

    print(f"已生成: {out} ({out.stat().st_size} bytes), 帧: {', '.join(str(s) for s in SIZES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
