# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11.0"]
# ///
"""GLM Quota Watch 双通道构建流水线。

产物规则（严格隔离，每条通道出两个二进制，命名固定为 `glmquotawatch-<通道>[-dev].exe`）：
  - dev（默认）：glmquotawatch-gui-dev.exe（GUI 通道）+ glmquotawatch-cli-dev.exe（Console 通道）
  - release：glmquotawatch-gui.exe（GUI 通道）+ glmquotawatch-cli.exe（Console 通道）
  只有 HEAD 精确命中 v* tag 且工作区干净时才允许 release；
  dev 与 release 产物名不同，互不覆盖。

双通道设计（为何不能只出一个）：
  - GUI 通道用 -H windowsgui 构建，双击零黑框；它不承担 CLI 语义：
    不管从哪里启动（双击 / 终端 / 快捷方式 / 带任意参数）结果都是显示 GUI，
    唯一语义参数是 --hidden（开机自启的静默托盘）与 --demo，其余参数一律忽略；
  - Console 通道为 console 子系统，父 shell 正常等待，
    prompt / 光标 / 管道 / 输出重定向全合规，终端、脚本与 Agent 一律用它。

用法：
  uv run scripts/build.py              # 开发构建 (dev)
  uv run scripts/build.py --release    # 发布构建（条件不满足时直接报错退出 2）
  uv run scripts/build.py --version 0.2.0   # 仅覆盖版本基线，不改变 dev/release 判定
  uv run scripts/build.py --skip-frontend   # 跳过前端 npm run build
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 四个产物统一落 bin/；勿用 build/（Wails 资源目录）或 dist/（前端产物）。
OUT_DIR = PROJECT_ROOT / "bin"
TAG_PREFIX = ""  # 单仓项目，tag 直接为 vX.Y.Z
RSRC_EXE = shutil.which("rsrc") or r"C:\Users\29580\go\bin\rsrc.exe"

VERSION_FILE = PROJECT_ROOT / "info.json"
MANIFEST = PROJECT_ROOT / "wails.exe.manifest"
ICON_RELEASE = PROJECT_ROOT / "icon.ico"
ICON_DEV = PROJECT_ROOT / "internal" / "app" / "icon_dev.ico"
SYSO_OUT = PROJECT_ROOT / "cmd" / "glmquotawatch" / "rsrc_windows_amd64.syso"
EXE_GUI_RELEASE = OUT_DIR / "glmquotawatch-gui.exe"
EXE_GUI_DEV = OUT_DIR / "glmquotawatch-gui-dev.exe"
EXE_CLI_RELEASE = OUT_DIR / "glmquotawatch-cli.exe"
EXE_CLI_DEV = OUT_DIR / "glmquotawatch-cli-dev.exe"

# 历史产物（旧单产物与迁移前根目录双通道产物），构建后自动清理，避免与新产物混淆。
LEGACY_EXES = (
    PROJECT_ROOT / "glmquotawatch.exe",
    PROJECT_ROOT / "glmquotawatch-dev.exe",
    PROJECT_ROOT / "bin" / "glmquotawatch.exe",
    PROJECT_ROOT / "bin" / "glmquotawatch-dev.exe",
    PROJECT_ROOT / "glmquotawatch-gui.exe",
    PROJECT_ROOT / "glmquotawatch-gui-dev.exe",
    PROJECT_ROOT / "glmquotawatch-cli.exe",
    PROJECT_ROOT / "glmquotawatch-cli-dev.exe",
)
RENDER_ICON = PROJECT_ROOT / "scripts" / "render_icon.py"

GENERATED_SUFFIXES = (
    "/bin/glmquotawatch-gui.exe",
    "/bin/glmquotawatch-gui-dev.exe",
    "/bin/glmquotawatch-cli.exe",
    "/bin/glmquotawatch-cli-dev.exe",
    "/glmquotawatch.exe",
    "/glmquotawatch-dev.exe",
    "/cmd/glmquotawatch/rsrc_windows_amd64.syso",
    "/icon.ico",
    "/icon.png",
    "/internal/app/icon.ico",
)


def setup_console() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def exact_project_tag() -> str | None:
    r = run_git("tag", "--points-at", "HEAD")
    if r.returncode != 0:
        return None
    for tag in (t.strip() for t in r.stdout.splitlines()):
        if tag.startswith(f"{TAG_PREFIX}v"):
            return tag
    return None


def latest_project_tag() -> str | None:
    r = run_git("describe", "--tags", "--abbrev=0", "--match", f"{TAG_PREFIX}v*")
    if r.returncode != 0:
        return None
    tag = r.stdout.strip()
    return tag or None


def base_version() -> str:
    tag = latest_project_tag()
    if tag:
        return tag[len(TAG_PREFIX):].lstrip("v")
    return str(json.loads(VERSION_FILE.read_text(encoding="utf-8"))["fixed"]["file_version"]).strip()


def worktree_dirty() -> bool:
    r = run_git("-c", "status.relativePaths=false", "status", "--porcelain", "--untracked-files=normal")
    if r.returncode != 0:
        return True
    for line in r.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        normalized = "/" + path.replace("\\", "/").lstrip("/")
        if any(normalized.endswith(suffix) for suffix in GENERATED_SUFFIXES):
            continue
        return True
    return False


def build_resources(release: bool) -> int:
    if release and RENDER_ICON.exists():
        r = subprocess.run(["uv", "run", str(RENDER_ICON)], cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print("⚠️ 图标渲染脚本执行异常，跳过重绘", file=sys.stderr)

    icon = ICON_RELEASE if release else ICON_DEV
    if not icon.exists():
        print(f"❌ 缺少图标文件: {icon}", file=sys.stderr)
        return 4

    r = subprocess.run(
        [
            str(RSRC_EXE),
            "-manifest", str(MANIFEST),
            "-ico", str(icon),
            "-arch", "amd64",
            "-o", str(SYSO_OUT),
        ],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode != 0:
        print(f"❌ rsrc 编译 syso 失败（exit {r.returncode}）", file=sys.stderr)
        return r.returncode
    print(f"✅ 已注入 Windows PE 资源段: {SYSO_OUT} (icon: {icon.name})")
    return 0


def generate_bindings() -> int:
    """重新生成前端 bindings（Wails 调用 ID 由 Go 包路径哈希得出，
    包路径/方法签名一变旧 bindings 就会全部失配；本步是防「前端调不通后端」的唯一保障）。"""
    wails3 = shutil.which("wails3") or r"C:\Users\29580\go\bin\wails3.exe"
    if not (wails3 and Path(wails3).exists()):
        print(
            "⚠️ 未找到 wails3，跳过 bindings 重建（若改过 Go 绑定层/模块路径，前端将全部报 unknown bound method id）",
            file=sys.stderr,
        )
        return 0
    print("🔨 [Bindings] 正在重建前端 bindings (wails3 generate bindings)...")
    r = subprocess.run(
        [wails3, "generate", "bindings", "-clean=true", "-ts", "-i", "./..."],
        cwd=str(PROJECT_ROOT),
    )
    if r.returncode != 0:
        print(f"❌ bindings 生成失败（exit {r.returncode}）", file=sys.stderr)
        return r.returncode
    return 0


def build_frontend() -> int:
    frontend_dir = PROJECT_ROOT / "frontend"
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    print("🔨 [Frontend] 正在编译前端 (npm run build)...")
    r = subprocess.run([npm_cmd, "run", "build"], cwd=str(frontend_dir))
    if r.returncode != 0:
        print(f"❌ 前端构建失败（exit {r.returncode}）", file=sys.stderr)
        return r.returncode
    return 0


def main() -> int:
    setup_console()

    parser = argparse.ArgumentParser(description="构建 glmquotawatch 双通道二进制（dev / release 严格隔离）")
    parser.add_argument("--release", action="store_true", help="声明发布构建；tag 或工作区条件不满足时直接报错")
    parser.add_argument("--version", default="", help="覆盖版本基线（不改变 dev/release 判定）")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端构建")
    args = parser.parse_args()

    # 1. 判定构建类型：默认 dev，仅 精确 tag + 干净工作区 才 release
    exact_tag = exact_project_tag()
    dirty = worktree_dirty()
    release = exact_tag is not None and not dirty

    if args.release and not release:
        reason = "当前 HEAD 未命中项目 tag" if exact_tag is None else "工作区存在未提交改动"
        print(f"❌ 拒绝发布构建：{reason}（release 需同时满足 精确 tag + 工作区干净）", file=sys.stderr)
        return 2

    # 2. bindings 重建 + 前端构建（bindings 必须与当前 Go 绑定层同步，
    #    否则 dist 里的调用 ID 会全部失配，界面表现为「永久加载 + 按钮无反应」）
    dist_dir = PROJECT_ROOT / "frontend" / "dist"
    if not args.skip_frontend or not dist_dir.exists():
        rc = generate_bindings()
        if rc != 0:
            return rc
        rc = build_frontend()
        if rc != 0:
            return rc

    # 3. 图标与 PE 资源
    rc = build_resources(release)
    if rc != 0:
        return rc

    base = args.version.lstrip("v") if args.version else base_version()
    if release:
        version = f"v{base}"
    else:
        version = f"v{base}-dev" + ("-dirty" if dirty else "")
    build_mode = "release" if release else "dev"

    print(
        f"📦 构建配置: Version={version}, Mode={build_mode} "
        f"(tag={exact_tag or '-'}, dirty={dirty})"
    )

    # 4. 逐通道 go build（每通道两个产物：GUI 零黑框 + Console 终端友好）
    OUT_DIR.mkdir(parents=True, exist_ok=True)   # go build 不会自动建父目录

    targets = (
        (EXE_GUI_RELEASE if release else EXE_GUI_DEV, True),
        (EXE_CLI_RELEASE if release else EXE_CLI_DEV, False),
    )
    for out_exe, gui in targets:
        flags = ["-w", "-s"]
        if gui:
            flags.append("-H windowsgui")
        flags.append(f"-X glmquotawatch/internal/app.Version={version}")
        flags.append(f"-X glmquotawatch/internal/app.BuildMode={build_mode}")

        tags = [] if release else ["dev"]
        if not gui:
            tags.append("cli")

        go_cmd = ["go", "build", "-trimpath"]
        if tags:
            go_cmd += ["-tags", ",".join(tags)]
        go_cmd += [f"-ldflags={' '.join(flags)}", "-o", str(out_exe), "./cmd/glmquotawatch"]

        channel = "GUI" if gui else "Console"
        print(f"🔨 [{channel}] {out_exe.name}")
        r = subprocess.run(go_cmd, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print(f"❌ go build 失败（exit {r.returncode}）: {out_exe.name}", file=sys.stderr)
            return r.returncode

    # 5. 产物名守卫：dev 必须带 -dev 后缀，release 不得带
    for out_exe, _gui in targets:
        if release and "dev" in out_exe.stem:
            print(f"❌ 产物命名违规: {out_exe}", file=sys.stderr)
            return 3
        if not release and not out_exe.stem.endswith("-dev"):
            print(f"❌ 产物命名违规: {out_exe}", file=sys.stderr)
            return 3

    for out_exe, gui in targets:
        size_mb = out_exe.stat().st_size / (1024 * 1024)
        print(f"🎉 构建完成 [{'GUI' if gui else 'Console'}]: {out_exe.name} ({size_mb:.2f} MB)")

    # 6. 清理历史命名的单产物
    for legacy in LEGACY_EXES:
        if not legacy.exists():
            continue
        try:
            legacy.unlink()
        except OSError as exc:
            print(
                f"⚠️ 无法清理历史产物（可能仍在运行）: {legacy.relative_to(PROJECT_ROOT)} ({exc})",
                file=sys.stderr,
            )
            continue
        print(f"🧹 已清理历史产物: {legacy.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())