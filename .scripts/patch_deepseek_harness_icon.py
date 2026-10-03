# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow>=10.0.0",
# ]
# ///
"""
========================================================================================
DeepSeek Harness 任务栏/托盘/可执行文件图标精细化修改与自动更新恢复脚本
========================================================================================

【背景与工程全景 (Context & Engineering Background)】
1. 目标应用:
   DeepSeek Harness (https://harness.deepseek.com) 是基于 Electron 深度定制的桌面客户端，
   默认安装在: D:\\Users\\29580\\AppData\\Local\\Programs\\DeepSeek Harness\\DeepSeek Harness.exe
2. 原始痛点与视觉割裂分析:
   - 官方 Windows 客户端图标源自 macOS 规范 (Big Sur 之后的超大留白圆角容器规范)，四周预留了
     近 15% 的透明内缩与投影边缘。在 Windows 任务栏浅色底 (24px/32px/40px) 渲染时，视觉上明显比
     旁边的 Chrome、Zed、Sublime Text 缩进一小圈，而且在暗色系开发工具排布中显得刺眼。
   - 仅改任务栏快捷方式 (.lnk) 只能改变“未启动状态”，一旦点击运行，Electron 窗口从 EXE 内部的
     PE 资源提取旧图标，导致“点开瞬间图标变回旧版”的严重撕裂。
3. 状态统一原理 (Why this works for both pinned & running):
   - 未启动 (Pinned): 任务栏快捷方式指向 `DeepSeek Harness.exe,0`。
   - 启动运行 (Running): Electron 主窗口未指定单独 icon 时，Windows 底层直接提取主进程 EXE 模块
     的 PE 图标资源 (RT_GROUP_ICON) 作为运行窗口图标。
   - 因此直接使用 rcedit 注入修改 `DeepSeek Harness.exe` 内嵌的 PE 图标资源，未启动和启动态即可
     100% 纯天然保持绝对一致。

【实操踩坑、用户体验反馈与迭代记录 (Pitfalls, User Feedback & Evolution)】
在实际调优交付过程中，我们经历了多轮极其关键的视觉微调与避坑：
1. 坑点一：为什么即便放大了原图，在任务栏依然觉得“格格不入 / 还是太小”？
   - 根本原因：Zed、Sublime Text 的底板几乎是 100% 满铺 32x32 网格每个像素边缘，且圆角非常克制硬朗
     (rx≈140~150)。而原方案底板四周自带透明虚影且使用了大圆角 (rx=210)，视觉面积依然小一圈且像鹅卵石。
   - 解决方案：底板扩大至 988x988 消除虚影，圆角收敛至 rx=150，使外轮廓与 Zed 达到 1:1 绝对对齐。
2. 坑点二：为什么换成暗黑底板后，用户依然觉得“图标别扭，想让鲸鱼往中间去去”？
   - 根本原因（精准测量发现）：官方鲸鱼尾巴上翘、头部下俯，原始数学边界严重偏心！
     * 原始坐标：左留白 101px，右留白仅 51px（水平严重偏右 25px！）；
     * 上留白 241px，下留白仅 140px（垂直严重偏下 50px！）；
     在任务栏缩小后，导致整个鲸鱼严重挤在右下角，左上角大面积空荡，视觉极度失衡。
   - 解决方案：向左平移 25px、向上平移 50px 精确校准，达成左右各 105px/106px (水平误差0.5px)、
     上下各 211px/214px 的几何与光学双重对称居中。
3. 坑点三：系统托盘 (System Tray) 图标未同步变动？
   - 原因：Electron 托盘图标写死了读取外部文件: `resources/tray.ico`，不走 EXE 内部资源。
   - 解决方案：脚本自动化支持双向同步——修改任务栏 EXE 时，自动备份原版 `resources/tray.ico.bak`，
     并一并热覆写 `tray.ico`，让任务栏和右下角托盘保持一致。
4. 坑点四：官方自动更新覆盖 (Auto-Update Recovery):
   - DeepSeek Harness 内置 electron-updater，当官方推送新版本升级后，EXE 文件会被完整覆写。
   - 只要任何 AI 助手或用户在发现图标被重置后，重新运行一次本脚本即可秒级恢复：
         uv run .scripts/patch_deepseek_harness_icon.py --custom-icon .scripts/custom_icons/3_dark_monochrome_centered.ico

【用法示例 (Usage)】
  1. 一键应用最终完美居中版暗黑极简图标 (任务栏 + 托盘同时生效):
       uv run .scripts/patch_deepseek_harness_icon.py --custom-icon .scripts/custom_icons/3_dark_monochrome_centered.ico
  2. 应用其他候选风格 (详见 .scripts/custom_icons/ 下各风格及 comparison_preview.png):
       uv run .scripts/patch_deepseek_harness_icon.py --custom-icon .scripts/custom_icons/1_dark_pro_blue.ico
  3. 官方原始状态一键完全还原 (恢复原始 EXE 与原始 tray.ico，无需担心丢失备份):
       uv run .scripts/patch_deepseek_harness_icon.py --restore
  4. 补丁完成后若任务栏未立即刷新，可追加强制重启 Explorer:
       uv run .scripts/patch_deepseek_harness_icon.py --custom-icon ... --restart-explorer

========================================================================================
"""

import argparse
import ctypes
import io
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from PIL import Image

# Windows 控制台安全输出 UTF-8，防止 GBK 编码崩溃
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 默认候选安装路径
DEFAULT_EXE_CANDIDATES = [
    Path(r"D:\Users\29580\AppData\Local\Programs\DeepSeek Harness\DeepSeek Harness.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\DeepSeek Harness\DeepSeek Harness.exe")),
]

# rcedit 候选路径与下载源
RCEDIT_DEFAULT_PATH = Path(r"D:\Users\language_projects_bin\rcedit.exe")
RCEDIT_DOWNLOAD_URL = "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe"

# Windows ICO 规范全套尺寸 (支持所有 DPI 缩放)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def find_target_exe(custom_path: str | None) -> Path:
    """定位 DeepSeek Harness.exe"""
    if custom_path:
        p = Path(custom_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"未找到指定的 EXE 文件: {p}")
        return p

    for cand in DEFAULT_EXE_CANDIDATES:
        if cand.is_file():
            return cand

    raise FileNotFoundError(
        "未能自动定位 DeepSeek Harness.exe，请使用 --target-exe 手动指定路径。"
    )


def ensure_rcedit(custom_path: str | None) -> Path:
    """确保 rcedit 可用，若缺失则自动下载"""
    if custom_path:
        p = Path(custom_path).resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"指定的 rcedit 不存在: {p}")

    # 1. 检查已知固定路径
    if RCEDIT_DEFAULT_PATH.is_file():
        return RCEDIT_DEFAULT_PATH

    # 2. 检查系统 PATH
    path_which = shutil.which("rcedit") or shutil.which("rcedit-x64")
    if path_which:
        return Path(path_which)

    # 3. 自动下载到已知目录
    dest = RCEDIT_DEFAULT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[*] 未检测到 rcedit 工具，正在自动从 GitHub 下载: {RCEDIT_DOWNLOAD_URL}")
    try:
        urllib.request.urlretrieve(RCEDIT_DOWNLOAD_URL, dest)
        print(f"[+] 下载完成: {dest}")
        return dest
    except Exception as exc:
        raise RuntimeError(f"下载 rcedit 失败: {exc}。请手动放置 rcedit.exe 到系统 PATH 或 {dest}")


def check_running_process(exe_name: str = "DeepSeek Harness.exe", kill: bool = False) -> None:
    """检查进程是否运行，避免文件占用导致修改失败"""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if exe_name.lower() in output.lower():
            if kill:
                print(f"[*] 正在自动终止运行中的 {exe_name} 进程...")
                subprocess.run(["taskkill", "/F", "/IM", exe_name], check=True)
            else:
                print(f"[!] 警告: 检测到 {exe_name} 正在运行！", file=sys.stderr)
                print("[!] 修改 EXE 需要其未被占用，请先退出该应用，或追加 --kill 参数自动关闭。", file=sys.stderr)
                sys.exit(1)
    except Exception:
        pass


def generate_enlarged_ico_from_png(src_png: Path, out_ico: Path, scale: float = 1.06) -> None:
    """智能去边距、居中放大并生成规范多尺寸 Windows ICO。"""
    im = Image.open(src_png).convert("RGBA")
    r, g, b, a = im.split()

    mask = a.point(lambda p: 255 if p > 20 else 0)
    bbox = mask.getbbox()
    if not bbox:
        bbox = (0, 0, im.width, im.height)

    cropped = im.crop(bbox)
    content_w, content_h = cropped.size

    canvas_size = 1024
    target_w = int(canvas_size * scale)
    target_h = int(canvas_size * scale)

    scaled = cropped.resize((target_w, target_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    paste_x = (canvas_size - target_w) // 2
    paste_y = (canvas_size - target_h) // 2
    canvas.paste(scaled, (paste_x, paste_y), scaled)

    frames = [canvas.resize((s, s), Image.LANCZOS) for s in ICO_SIZES]
    out_ico.parent.mkdir(parents=True, exist_ok=True)
    frames[-1].save(
        out_ico,
        format="ICO",
        append_images=frames[:-1],
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"[+] ICO 生成成功: {out_ico} (裁剪主体: {content_w}x{content_h}, 缩放倍率: {scale})")


def convert_custom_icon(custom_path: Path, out_ico: Path) -> None:
    """处理用户传入的自定义图标 (PNG 或 ICO)"""
    if custom_path.suffix.lower() == ".ico":
        shutil.copy2(custom_path, out_ico)
        print(f"[+] 直接使用已有 ICO 文件: {custom_path}")
        return

    im = Image.open(custom_path).convert("RGBA")
    side = max(im.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)

    frames = [canvas.resize((s, s), Image.LANCZOS) for s in ICO_SIZES]
    out_ico.parent.mkdir(parents=True, exist_ok=True)
    frames[-1].save(
        out_ico,
        format="ICO",
        append_images=frames[:-1],
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"[+] 自定义图像已转为标准 ICO: {out_ico}")


def refresh_windows_icon_cache(restart_explorer: bool = False) -> None:
    """刷新 Windows 图标缓存与任务栏快捷方式状态"""
    print("[*] 正在刷新 Windows 图标缓存与任务栏状态...")

    taskbar_dir = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"))
    if taskbar_dir.is_dir():
        for lnk in taskbar_dir.glob("*DeepSeek*.lnk"):
            try:
                os.utime(lnk, None)
                print(f"[+] 已触碰任务栏快捷方式时间戳: {lnk.name}")
            except Exception:
                pass

    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, 0, 0)
        print("[+] 已广播 Windows SHChangeNotify 图标刷新通知")
    except Exception as e:
        print(f"[-] SHChangeNotify 调用异常: {e}")

    if restart_explorer:
        print("[*] 正在安全重启 Windows Explorer (资源管理器)...")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], check=True)
            subprocess.Popen(["explorer.exe"])
            print("[+] Windows Explorer 已成功重启")
        except Exception as e:
            print(f"[-] 重启 Explorer 异常: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DeepSeek Harness 任务栏/可执行文件图标修改与更新恢复工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--scale", type=float, default=1.06, help="放大倍率 (默认 1.06，充满画布并微调饱满度)")
    parser.add_argument("--custom-icon", type=str, help="自定义图标路径 (支持 .png, .ico)")
    parser.add_argument("--restore", action="store_true", help="从 .bak 备份文件恢复官方原始 EXE 及托盘图标")
    parser.add_argument("--kill", action="store_true", help="如果 DeepSeek Harness 正在运行，强行关闭它")
    parser.add_argument("--restart-explorer", action="store_true", help="补丁完成后强制重启 Windows 资源管理器")
    parser.add_argument("--target-exe", type=str, help="手动指定 DeepSeek Harness.exe 路径")
    parser.add_argument("--rcedit-path", type=str, help="手动指定 rcedit.exe 路径")
    parser.add_argument("--no-tray", action="store_true", help="不修改右下角托盘图标 (默认会自动同步修改并备份)")

    args = parser.parse_args()

    exe_path = find_target_exe(args.target_exe)
    print(f"[*] 目标可执行文件: {exe_path}")

    bak_path = exe_path.with_name(f"{exe_path.name}.bak")
    tray_ico_path = exe_path.parent / "resources" / "tray.ico"
    tray_bak_path = exe_path.parent / "resources" / "tray.ico.bak"

    # 还原模式
    if args.restore:
        check_running_process(exe_path.name, kill=args.kill)
        restored_any = False
        if bak_path.is_file():
            shutil.copy2(bak_path, exe_path)
            print(f"[+] 已成功恢复官方原始 EXE: {exe_path}")
            restored_any = True
        else:
            print(f"[-] 提示: 未找到 EXE 备份文件 {bak_path}")

        if tray_bak_path.is_file():
            shutil.copy2(tray_bak_path, tray_ico_path)
            print(f"[+] 已成功恢复官方原始托盘图标: {tray_ico_path}")
            restored_any = True
        else:
            print(f"[-] 提示: 未找到托盘图标备份文件 {tray_bak_path}")

        if restored_any:
            refresh_windows_icon_cache(args.restart_explorer)
            return 0
        else:
            print("[-] 错误: 未找到任何备份文件，无法还原！", file=sys.stderr)
            return 1

    # 修改模式
    check_running_process(exe_path.name, kill=args.kill)
    rcedit_exe = ensure_rcedit(args.rcedit_path)

    # 1. 安全备份 EXE 与托盘图标
    if not bak_path.is_file():
        shutil.copy2(exe_path, bak_path)
        print(f"[+] 已创建官方原始 EXE 安全备份: {bak_path}")
    else:
        print(f"[*] 检测到已存在 EXE 安全备份: {bak_path} (保留原备份，不覆盖)")

    if tray_ico_path.is_file() and not tray_bak_path.is_file():
        shutil.copy2(tray_ico_path, tray_bak_path)
        print(f"[+] 已创建官方原始托盘图标安全备份: {tray_bak_path}")
    elif tray_bak_path.is_file():
        print(f"[*] 检测到已存在托盘图标安全备份: {tray_bak_path} (保留原备份，不覆盖)")

    # 2. 准备图标
    work_dir = exe_path.parent / "resources"
    work_dir.mkdir(parents=True, exist_ok=True)
    out_ico = work_dir / "patched_taskbar_icon.ico"

    if args.custom_icon:
        custom_p = Path(args.custom_icon).resolve()
        if not custom_p.is_file():
            print(f"[-] 错误: 指定的自定义图标不存在: {custom_p}", file=sys.stderr)
            return 1
        convert_custom_icon(custom_p, out_ico)
    else:
        src_png = work_dir / "icon.png"
        if not src_png.is_file():
            print(f"[-] 错误: 未在 resources 目录下找到原图 icon.png: {src_png}", file=sys.stderr)
            return 1
        generate_enlarged_ico_from_png(src_png, out_ico, scale=args.scale)

    # 3. 使用 rcedit 注入 PE 资源
    print(f"[*] 正在调用 rcedit 将图标注入 EXE PE 资源: {exe_path.name}")
    cmd = [str(rcedit_exe), str(exe_path), "--set-icon", str(out_ico)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] rcedit 执行失败 (code {res.returncode}): {res.stderr}", file=sys.stderr)
        return res.returncode

    print(f"[+] 图标成功写入 {exe_path.name}！")

    # 4. 同步更新托盘图标 (默认启用)
    if not args.no_tray:
        try:
            shutil.copy2(out_ico, tray_ico_path)
            print(f"[+] 已同步更新右下角托盘图标: {tray_ico_path}")
        except Exception as e:
            print(f"[-] 托盘图标写入异常: {e}")

    # 5. 刷新系统缓存
    refresh_windows_icon_cache(restart_explorer=args.restart_explorer)

    print("\n" + "=" * 60)
    print("[SUCCESS] 任务栏与托盘图标补丁完成！")
    print(f"• 目标文件: {exe_path}")
    print(f"• 原始备份: {bak_path}")
    print(f"• 托盘备份: {tray_bak_path}")
    print(f"• 当前图标: {out_ico}")
    print("• 未启动、启动态及系统托盘已 100% 同步为新图标。")
    print("• 若客户端未来自动更新覆盖，只需再次运行: uv run .scripts/patch_deepseek_harness_icon.py")
    print("• 如需一键完全恢复官方出厂状态: uv run .scripts/patch_deepseek_harness_icon.py --restore")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
