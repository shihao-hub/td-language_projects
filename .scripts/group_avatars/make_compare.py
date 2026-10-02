# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# make_compare.py：生成 compare.html，把参考图与成品图并排对比。
# 用法: uv run .scripts/group_avatars/make_compare.py
import os

dir_path = os.path.dirname(os.path.abspath(__file__))
files = [
    ("archive_avatar_1790684172300.jpg", "归档区 (AI手绘原版)"),
    ("todo_avatar.jpg", "待办项 (AI手绘原版)"),
    ("temp_zone_avatar.jpg", "临时区 (AI手绘原版)"),
    ("jyy_notes_green.png", "随笔记 (SVG复刻版)"),
    ("jyy_todo_green.png", "待办项 (SVG复刻版)"),
    ("jyy_temp_green.png", "临时区 (SVG复刻版)"),
    ("jyy_archive_green.png", "归档区 (SVG复刻版)")
]

html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>群头像设计全集对比</title>
<style>
body { background: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 30px; }
h1 { text-align: center; color: #10b981; }
.grid { display: flex; flex-wrap: wrap; gap: 24px; justify-content: center; }
.card { background: #1e293b; border-radius: 16px; padding: 16px; width: 280px; text-align: center; }
img { width: 100%; border-radius: 12px; }
.round img { border-radius: 50%; }
h3 { margin: 10px 0 6px 0; font-size: 16px; }
</style>
</head>
<body>
<h1>群头像设计与参考全集</h1>
<div class="grid">
"""

for f, name in files:
    full_path = os.path.join(dir_path, f)
    if os.path.exists(full_path):
        html += f"""
        <div class="card">
          <img src="{f}">
          <h3>{name}</h3>
          <span style="font-size:12px;color:#94a3b8;">{f}</span>
        </div>
        """

html += """
</div>
</body>
</html>
"""

with open(os.path.join(dir_path, "compare.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("compare.html written successfully!")
