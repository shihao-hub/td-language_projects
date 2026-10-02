# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow>=10.0"]
# ///
# avatar_engine.py：群头像徽章的共用绘制引擎（圆徽章、道具、标题排版）。
# 用法: uv run .scripts/group_avatars/avatar_engine.py（成品图输出到脚本同目录）
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_REGULAR = r"C:\Windows\Fonts\msyh.ttc"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def linear_gradient(size, c1, c2, direction="vertical"):
    """Creates a 2D linear gradient array of RGBA"""
    w, h = size
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    
    if direction == "vertical":
        y = np.linspace(0, 1, h)[:, None]
        r = r1 + (r2 - r1) * y
        g = g1 + (g2 - g1) * y
        b = b1 + (b2 - b1) * y
        arr = np.dstack([np.broadcast_to(r, (h, w)),
                         np.broadcast_to(g, (h, w)),
                         np.broadcast_to(b, (h, w)),
                         np.full((h, w), 255, dtype=np.uint8)])
    elif direction == "diagonal":
        x = np.linspace(0, 1, w)[None, :]
        y = np.linspace(0, 1, h)[:, None]
        d = (x + y) / 2.0
        r = r1 + (r2 - r1) * d
        g = g1 + (g2 - g1) * d
        b = b1 + (b2 - b1) * d
        arr = np.dstack([r, g, b, np.full((h, w), 255, dtype=np.uint8)])
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def radial_gradient(size, c_center, c_edge, radius=None):
    w, h = size
    if radius is None:
        radius = math.hypot(w/2, h/2)
    r1, g1, b1 = hex_to_rgb(c_center)
    r2, g2, b2 = hex_to_rgb(c_edge)
    
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - w/2)**2 + (y - h/2)**2)
    norm = np.clip(dist / radius, 0, 1)
    
    r = r1 + (r2 - r1) * norm
    g = g1 + (g2 - g1) * norm
    b = b1 + (b2 - b1) * norm
    arr = np.dstack([r, g, b, np.full((h, w), 255, dtype=np.uint8)])
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def draw_rounded_rect_mask(size, bbox, radius):
    """Draw a smooth anti-aliased rounded rectangle mask using supersampling"""
    scale = 2
    sw, sh = size[0] * scale, size[1] * scale
    mask = Image.new("L", (sw, sh), 0)
    draw = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = [int(v * scale) for v in bbox]
    r = int(radius * scale)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)

def draw_squircle_mask(size, margin, corner_radius):
    w, h = size
    return draw_rounded_rect_mask(size, [margin, margin, w - margin, h - margin], corner_radius)

print("Base graphics engine loaded")
