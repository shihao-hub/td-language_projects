# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0", "numpy>=1.26"]
# ///
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

def render_vector_icon(size=1024, style='cyan_coral', shape='squircle') -> Image.Image:
    scale = 4
    dim = size * scale
    
    y, x = np.ogrid[:dim, :dim]
    cx, cy = dim / 2.0, dim / 2.0
    
    pad = 72 * scale
    r_corner = 200 * scale
    
    bg_img = Image.new('RGBA', (dim, dim), (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(bg_img)
    
    slate_fill = (15, 23, 42, 255)
    border_col = (30, 41, 59, 255)
    
    if shape == 'squircle':
        rect_box = [pad, pad, dim - pad, dim - pad]
        draw_bg.rounded_rectangle(rect_box, radius=r_corner, fill=slate_fill)
        draw_bg.rounded_rectangle(rect_box, radius=r_corner, outline=border_col, width=int(14 * scale))
    else:
        circle_r = (dim / 2.0) - pad
        draw_bg.ellipse([cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r], fill=slate_fill, outline=border_col, width=int(14 * scale))
        
    bg_arr = np.array(bg_img, dtype=np.float32) / 255.0
    
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    angle = np.mod(np.arctan2(x - cx, cy - y), 2 * np.pi)
    
    mid_r = 295.0 * scale
    stroke_w = 90.0 * scale
    stroke_half = stroke_w / 2.0
    
    dist_ring = np.abs(dist - mid_r)
    ring_aa = np.clip(0.5 - (dist_ring - stroke_half) / (1.5 * scale), 0.0, 1.0)
    
    track_color = np.array([30, 41, 59, 255], dtype=np.float32) / 255.0
    total_active_rad = 0.70 * 2 * np.pi
    
    cap0_dist = np.sqrt((x - cx)**2 + (y - (cy - mid_r))**2)
    cap0_mask = np.clip(0.5 - (cap0_dist - stroke_half) / (1.5 * scale), 0.0, 1.0)
    
    cap70_x = cx + mid_r * np.sin(total_active_rad)
    cap70_y = cy - mid_r * np.cos(total_active_rad)
    cap70_dist = np.sqrt((x - cap70_x)**2 + (y - cap70_y)**2)
    cap70_mask = np.clip(0.5 - (cap70_dist - stroke_half) / (1.5 * scale), 0.0, 1.0)
    
    gauge_layer = track_color * ring_aa[:, :, None]
    
    col_main = np.array([0, 240, 255, 255], dtype=np.float32) / 255.0
    col_accent = np.array([255, 92, 77, 255], dtype=np.float32) / 255.0
    split_rad = 0.52 * 2 * np.pi
    
    main_mask = ring_aa * np.clip(1.0 - (angle - split_rad) / 0.005, 0.0, 1.0) * np.clip((angle - 0) / 0.005, 0.0, 1.0)
    main_mask = np.maximum(main_mask, cap0_mask)
    
    accent_mask = ring_aa * np.clip((angle - split_rad) / 0.005, 0.0, 1.0) * np.clip(1.0 - (angle - total_active_rad) / 0.005, 0.0, 1.0)
    accent_mask = np.maximum(accent_mask, cap70_mask)
    
    gauge_layer = gauge_layer * (1.0 - main_mask[:, :, None]) + col_main * main_mask[:, :, None]
    gauge_layer = gauge_layer * (1.0 - accent_mask[:, :, None]) + col_accent * accent_mask[:, :, None]

    final_arr = bg_arr.copy()
    gauge_alpha = gauge_layer[:, :, 3:4]
    final_arr[:, :, :3] = final_arr[:, :, :3] * (1.0 - gauge_alpha) + gauge_layer[:, :, :3] * gauge_alpha
    final_arr[:, :, 3:4] = np.maximum(final_arr[:, :, 3:4], gauge_alpha)
    final_arr[:, :, 3] = final_arr[:, :, 3] * bg_arr[:, :, 3]
    
    img_large = Image.fromarray((np.clip(final_arr, 0.0, 1.0) * 255.0).astype(np.uint8), mode='RGBA')
    img_out = img_large.resize((size, size), Image.Resampling.LANCZOS)
    return img_out

def main():
    root = Path(__file__).resolve().parent.parent
    im = render_vector_icon(1024, style='cyan_coral', shape='squircle')
    im.save(root / "icon.png")

    sizes = [256, 128, 64, 48, 32, 24, 16]
    im.save(root / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    im.save(root / "internal" / "app" / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    print("[OK] 图标生成并同步完成")

if __name__ == "__main__":
    main()
