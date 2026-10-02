# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow>=10.0"]
# ///
# generate_all.py：一次渲染三套风格的群头像成品图与对比页。
# 用法: uv run .scripts/group_avatars/generate_all.py（输出到脚本同目录）
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_REGULAR = r"C:\Windows\Fonts\msyh.ttc"

SIZE = 1024

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def linear_gradient(size, c1, c2, direction="vertical"):
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

def radial_glow(size, color, alpha_center=180, radius=500):
    w, h = size
    r_val, g_val, b_val = hex_to_rgb(color)
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - w/2)**2 + (y - h/2)**2)
    norm = np.clip(dist / radius, 0, 1)
    a = (alpha_center * (1 - norm**1.2)).astype(np.uint8)
    a = np.clip(a, 0, 255)
    r = np.full((h, w), r_val, dtype=np.uint8)
    g = np.full((h, w), g_val, dtype=np.uint8)
    b = np.full((h, w), b_val, dtype=np.uint8)
    arr = np.dstack([r, g, b, a])
    return Image.fromarray(arr, "RGBA")

def create_smooth_mask(size, bbox, radius):
    scale = 3
    sw, sh = size[0] * scale, size[1] * scale
    mask = Image.new("L", (sw, sh), 0)
    draw = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = [int(v * scale) for v in bbox]
    r = int(radius * scale)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)

# -------------------------------------------------------------
# STYLE 1: 暗黑微光科技质感徽章 (Dark Luminescence Badges)
# -------------------------------------------------------------
def generate_style1():
    themes = [
        {
            "id": "notes",
            "name": "随笔记",
            "en": "QUICK NOTES",
            "c_grad1": "#FFB300",
            "c_grad2": "#F57C00",
            "glow": "#FFB300",
            "icon_type": "notes"
        },
        {
            "id": "todo",
            "name": "待办项",
            "en": "TODO LIST",
            "c_grad1": "#00E5FF",
            "c_grad2": "#00B0FF",
            "glow": "#00E5FF",
            "icon_type": "todo"
        },
        {
            "id": "temp",
            "name": "临时区",
            "en": "TEMP BUFFER",
            "c_grad1": "#C084FC",
            "c_grad2": "#A855F7",
            "glow": "#C084FC",
            "icon_type": "temp"
        },
        {
            "id": "archive",
            "name": "归档区",
            "en": "ARCHIVE BOX",
            "c_grad1": "#34D399",
            "c_grad2": "#059669",
            "glow": "#34D399",
            "icon_type": "archive"
        }
    ]

    for item in themes:
        # 1. 底图：深黑微渐变底
        bg = linear_gradient((SIZE, SIZE), "#0D1117", "#161B22", direction="vertical")
        
        # 2. 居中微光扩散
        glow_layer = radial_glow((SIZE, SIZE), item["glow"], alpha_center=110, radius=520)
        bg.alpha_composite(glow_layer)

        # 3. 核心容器：现代 Squircle 圆角矩形卡片
        card_size = 720
        margin = (SIZE - card_size) // 2
        card_bbox = [margin, margin - 15, margin + card_size, margin + card_size - 15]
        
        # 卡片深色半透明玻璃层
        card_mask = create_smooth_mask((SIZE, SIZE), card_bbox, radius=180)
        card_surface = Image.new("RGBA", (SIZE, SIZE), (24, 30, 42, 235))
        
        # 卡片边缘微发光描边
        border_img = linear_gradient((SIZE, SIZE), item["c_grad1"], item["c_grad2"], direction="diagonal")
        border_mask_outer = create_smooth_mask((SIZE, SIZE), [card_bbox[0]-4, card_bbox[1]-4, card_bbox[2]+4, card_bbox[3]+4], radius=184)
        border_mask_inner = create_smooth_mask((SIZE, SIZE), card_bbox, radius=180)
        border_diff = Image.new("L", (SIZE, SIZE), 0)
        b_outer = np.array(border_mask_outer)
        b_inner = np.array(border_mask_inner)
        b_diff = np.clip(b_outer.astype(np.int32) - b_inner.astype(np.int32), 0, 255).astype(np.uint8)
        border_mask = Image.fromarray(b_diff, "L")
        
        bg.paste(border_img, (0, 0), border_mask)
        bg.paste(card_surface, (0, 0), card_mask)

        # 4. 图标绘制区（超采样绘制高清几何图标）
        canvas = Image.new("RGBA", (SIZE * 2, SIZE * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        
        cx = SIZE
        cy = (margin + card_size // 2 - 60) * 2

        # 渐变彩球/微标背衬
        icon_grad = linear_gradient((SIZE*2, SIZE*2), item["c_grad1"], item["c_grad2"], direction="diagonal")
        
        if item["icon_type"] == "notes":
            # 笔记本 + 笔
            # 本子底板
            bx0, by0, bx1, by1 = cx - 180, cy - 200, cx + 180, cy + 200
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=40, fill=(255, 255, 255, 240))
            # 装订条
            d.rectangle([bx0, by0, bx0 + 60, by1], fill=hex_to_rgb(item["c_grad2"]) + (255,))
            # 书页横线
            for ly in [by0 + 100, by0 + 170, by0 + 240, by0 + 310]:
                d.rounded_rectangle([bx0 + 100, ly, bx1 - 60, ly + 20], radius=10, fill=(220, 226, 235, 255))
            # 顶部灵感小闪光星
            sx, sy = bx1 - 10, by0 - 20
            d.polygon([(sx, sy-40), (sx+12, sy-12), (sx+40, sy), (sx+12, sy+12), (sx, sy+40), (sx-12, sy+12), (sx-40, sy), (sx-12, sy-12)], fill=(255, 215, 0, 255))

        elif item["icon_type"] == "todo":
            # 待办对勾盾牌 / 圆盘
            r = 220
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 245))
            d.ellipse([cx - r + 30, cy - r + 30, cx + r - 30, cy + r - 30], fill=hex_to_rgb(item["c_grad1"]) + (220,))
            # 对勾
            check_pts = [(cx - 90, cy + 10), (cx - 30, cy + 80), (cx + 100, cy - 60)]
            d.line(check_pts, fill=(255, 255, 255, 255), width=48, joint="curve")
            d.ellipse([check_pts[0][0]-24, check_pts[0][1]-24, check_pts[0][0]+24, check_pts[0][1]+24], fill=(255,255,255,255))
            d.ellipse([check_pts[2][0]-24, check_pts[2][1]-24, check_pts[2][0]+24, check_pts[2][1]+24], fill=(255,255,255,255))

        elif item["icon_type"] == "temp":
            # 循环中转双弧线 + 闪电/瞬时
            r = 210
            # 循环箭头外环
            d.arc([cx - r, cy - r, cx + r, cy + r], start=30, end=150, fill=hex_to_rgb(item["c_grad1"]) + (255,), width=40)
            d.arc([cx - r, cy - r, cx + r, cy + r], start=210, end=330, fill=hex_to_rgb(item["c_grad2"]) + (255,), width=40)
            # 中间沙盒托盘 / 纸飞机
            px, py = cx, cy
            d.polygon([(px - 100, py - 40), (px + 100, py), (px - 100, py + 40), (px - 40, py)], fill=(255, 255, 255, 245))
            d.line([(px - 40, py), (px + 100, py)], fill=hex_to_rgb(item["c_grad2"]) + (255,), width=16)

        elif item["icon_type"] == "archive":
            # 档案整理盒
            bx0, by0, bx1, by1 = cx - 190, cy - 140, cx + 190, cy + 180
            # 盒体
            d.rounded_rectangle([bx0, by0 + 60, bx1, by1], radius=30, fill=(255, 255, 255, 245))
            # 盒盖
            d.rounded_rectangle([bx0 - 20, by0, bx1 + 20, by0 + 80], radius=24, fill=hex_to_rgb(item["c_grad1"]) + (255,))
            # 把手槽 / 标签卡
            d.rounded_rectangle([cx - 70, cy + 20, cx + 70, cy + 80], radius=16, fill=(220, 230, 242, 255))
            d.rounded_rectangle([cx - 40, cy + 40, cx + 40, cy + 60], radius=10, fill=hex_to_rgb(item["c_grad2"]) + (255,))

        canvas_resized = canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        bg.alpha_composite(canvas_resized)

        # 5. 文字排版
        draw_txt = ImageDraw.Draw(bg)
        font_title = ImageFont.truetype(FONT_BOLD, 78)
        font_sub = ImageFont.truetype(FONT_REGULAR, 26)

        # 标题居中
        txt = item["name"]
        bbox = draw_txt.textbbox((0, 0), txt, font=font_title)
        tw = bbox[2] - bbox[0]
        tx = (SIZE - tw) // 2
        ty = margin + card_size - 170
        draw_txt.text((tx, ty), txt, font=font_title, fill=(255, 255, 255, 250))

        # 英文副标
        sub = item["en"]
        sbbox = draw_txt.textbbox((0, 0), sub, font=font_sub)
        sw = sbbox[2] - sbbox[0]
        sx = (SIZE - sw) // 2
        sy = ty + 90
        # 英文副标背景小胶囊
        capsule_pad = 18
        draw_txt.rounded_rectangle([sx - capsule_pad, sy - 4, sx + sw + capsule_pad, sy + 32], radius=16, fill=(255, 255, 255, 25))
        draw_txt.text((sx, sy), sub, font=font_sub, fill=hex_to_rgb(item["c_grad1"]) + (230,))

        # 保存
        out_path = os.path.join(OUTPUT_DIR, f"avatar_style1_{item['id']}.png")
        bg.save(out_path, "PNG")
        print(f"Generated Style 1: {out_path}")

# -------------------------------------------------------------
# STYLE 2: 极简单字·超高辨识度徽标 (Bold Mono Glyph)
# -------------------------------------------------------------
def generate_style2():
    chars = [
        {
            "id": "notes",
            "char": "记",
            "sub": "随笔记 · NOTES",
            "c1": "#FF6B00",
            "c2": "#FFA000",
            "accent": "#FFF3E0"
        },
        {
            "id": "todo",
            "char": "待",
            "sub": "待办项 · TODO",
            "c1": "#0072FF",
            "c2": "#00C6FF",
            "accent": "#E1F5FE"
        },
        {
            "id": "temp",
            "char": "临",
            "sub": "临时区 · TEMP",
            "c1": "#7928CA",
            "c2": "#FF0080",
            "accent": "#FCE7F3"
        },
        {
            "id": "archive",
            "char": "档",
            "sub": "归档区 · ARCHIVE",
            "c1": "#0BA360",
            "c2": "#3CBA92",
            "accent": "#E8F5E9"
        }
    ]

    for item in chars:
        # 底图直接是饱满有张力的高级渐变
        bg = linear_gradient((SIZE, SIZE), item["c1"], item["c2"], direction="diagonal")
        
        # 柔和四角微光与同心环几何点缀
        deco = Image.new("RGBA", (SIZE * 2, SIZE * 2), (0, 0, 0, 0))
        d_deco = ImageDraw.Draw(deco)
        cx, cy = SIZE, SIZE
        
        # 优雅的同心大圆环
        for r_ring in [750, 850]:
            d_deco.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], outline=(255, 255, 255, 30), width=6)
        
        # 四角小光点
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle)
            px = int(cx + 800 * math.cos(rad))
            py = int(cy + 800 * math.sin(rad))
            d_deco.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(255, 255, 255, 120))

        deco_resized = deco.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        bg.alpha_composite(deco_resized)

        # 核心巨大文字（采用 460px 超大号粗体，即使缩小到 32px 也能清晰识别）
        font_big = ImageFont.truetype(FONT_BOLD, 440)
        font_sub = ImageFont.truetype(FONT_BOLD, 46)

        # 绘制微投影提升立体感
        d = ImageDraw.Draw(bg)
        txt = item["char"]
        bbox = d.textbbox((0, 0), txt, font=font_big)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (SIZE - tw) // 2
        ty = (SIZE - th) // 2 - 60

        # 投影
        d.text((tx, ty + 12), txt, font=font_big, fill=(0, 0, 0, 45))
        # 主字
        d.text((tx, ty), txt, font=font_big, fill=(255, 255, 255, 255))

        # 底部精致胶囊标签
        sub_txt = item["sub"]
        sbbox = d.textbbox((0, 0), sub_txt, font=font_sub)
        stw = sbbox[2] - sbbox[0]
        sth = sbbox[3] - sbbox[1]
        stx = (SIZE - stw) // 2
        sty = SIZE - 180

        pad_x, pad_y = 36, 16
        d.rounded_rectangle([stx - pad_x, sty - pad_y, stx + stw + pad_x, sty + sth + pad_y], radius=32, fill=(255, 255, 255, 235))
        # 标签文字颜色使用对应深主色
        d.text((stx, sty - 4), sub_txt, font=font_sub, fill=hex_to_rgb(item["c1"]) + (255,))

        out_path = os.path.join(OUTPUT_DIR, f"avatar_style2_{item['id']}.png")
        bg.save(out_path, "PNG")
        print(f"Generated Style 2: {out_path}")

# -------------------------------------------------------------
# STYLE 3: 清新马卡龙·极简立体插画 (Pastel Minimal)
# -------------------------------------------------------------
def generate_style3():
    items = [
        {
            "id": "notes",
            "name": "随笔记",
            "en": "Notes",
            "bg_color": "#FFFBEB",
            "box_c1": "#FDE68A",
            "box_c2": "#F59E0B",
            "text_color": "#92400E",
            "icon_type": "notes"
        },
        {
            "id": "todo",
            "name": "待办项",
            "en": "Todo",
            "bg_color": "#F0FDF4",
            "box_c1": "#A7F3D0",
            "box_c2": "#10B981",
            "text_color": "#065F46",
            "icon_type": "todo"
        },
        {
            "id": "temp",
            "name": "临时区",
            "en": "Temp",
            "bg_color": "#FAF5FF",
            "box_c1": "#E9D5FF",
            "box_c2": "#A855F7",
            "text_color": "#6B21A8",
            "icon_type": "temp"
        },
        {
            "id": "archive",
            "name": "归档区",
            "en": "Archive",
            "bg_color": "#F0F9FF",
            "box_c1": "#BAE6FD",
            "box_c2": "#0284C7",
            "text_color": "#075985",
            "icon_type": "archive"
        }
    ]

    for item in items:
        # 明亮素雅浅底色
        bg = Image.new("RGBA", (SIZE, SIZE), hex_to_rgb(item["bg_color"]) + (255,))

        # 中央温润马卡龙色圆角卡片
        c_size = 700
        margin = (SIZE - c_size) // 2
        card_bbox = [margin, margin - 20, margin + c_size, margin + c_size - 20]
        
        # 柔和阴影
        shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        d_sh = ImageDraw.Draw(shadow)
        d_sh.rounded_rectangle([card_bbox[0], card_bbox[1] + 24, card_bbox[2], card_bbox[3] + 24], radius=160, fill=(0, 0, 0, 18))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
        bg.alpha_composite(shadow)

        # 卡片渐变本体
        card_mask = create_smooth_mask((SIZE, SIZE), card_bbox, radius=160)
        card_grad = linear_gradient((SIZE, SIZE), item["box_c1"], item["box_c2"], direction="diagonal")
        bg.paste(card_grad, (0, 0), card_mask)

        # 内部图标绘制 (2x 超采样)
        canvas = Image.new("RGBA", (SIZE * 2, SIZE * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        cx = SIZE
        cy = (margin + c_size // 2 - 70) * 2

        if item["icon_type"] == "notes":
            # 极简便签 + 铅笔
            d.rounded_rectangle([cx - 160, cy - 180, cx + 160, cy + 180], radius=40, fill=(255, 255, 255, 245))
            for y_line in [cy - 80, cy, cy + 80]:
                d.rounded_rectangle([cx - 100, y_line, cx + 100, y_line + 16], radius=8, fill=hex_to_rgb(item["text_color"]) + (140,))
        elif item["icon_type"] == "todo":
            # 圆形大对勾
            d.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], fill=(255, 255, 255, 245))
            pts = [(cx - 80, cy), (cx - 20, cy + 60), (cx + 90, cy - 60)]
            d.line(pts, fill=hex_to_rgb(item["box_c2"]) + (255,), width=40, joint="curve")
        elif item["icon_type"] == "temp":
            # 沙漏 / 闪电几何
            d.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], fill=(255, 255, 255, 245))
            pts = [(cx + 20, cy - 130), (cx - 70, cy + 10), (cx + 10, cy + 10), (cx - 20, cy + 130), (cx + 70, cy - 10), (cx - 10, cy - 10)]
            d.polygon(pts, fill=hex_to_rgb(item["box_c2"]) + (255,))
        elif item["icon_type"] == "archive":
            # 几何档案整理箱
            d.rounded_rectangle([cx - 170, cy - 110, cx + 170, cy + 160], radius=32, fill=(255, 255, 255, 245))
            d.rounded_rectangle([cx - 190, cy - 160, cx + 190, cy - 90], radius=24, fill=(255, 255, 255, 255))
            d.rounded_rectangle([cx - 60, cy + 10, cx + 60, cy + 50], radius=16, fill=hex_to_rgb(item["box_c2"]) + (180,))

        canvas_resized = canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        bg.alpha_composite(canvas_resized)

        # 文字排版
        draw_txt = ImageDraw.Draw(bg)
        font_title = ImageFont.truetype(FONT_BOLD, 74)
        font_sub = ImageFont.truetype(FONT_REGULAR, 28)

        txt = item["name"]
        bbox = draw_txt.textbbox((0, 0), txt, font=font_title)
        tw = bbox[2] - bbox[0]
        tx = (SIZE - tw) // 2
        ty = margin + c_size - 180
        draw_txt.text((tx, ty), txt, font=font_title, fill=hex_to_rgb(item["text_color"]) + (255,))

        sub = item["en"]
        sbbox = draw_txt.textbbox((0, 0), sub, font=font_sub)
        sw = sbbox[2] - sbbox[0]
        sx = (SIZE - sw) // 2
        sy = ty + 86
        draw_txt.text((sx, sy), sub, font=font_sub, fill=hex_to_rgb(item["text_color"]) + (180,))

        out_path = os.path.join(OUTPUT_DIR, f"avatar_style3_{item['id']}.png")
        bg.save(out_path, "PNG")
        print(f"Generated Style 3: {out_path}")

if __name__ == "__main__":
    generate_style1()
    generate_style2()
    generate_style3()
    print("All 12 high-resolution avatars generated successfully!")
