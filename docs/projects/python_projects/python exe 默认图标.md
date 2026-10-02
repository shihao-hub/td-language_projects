---
name: python-exe-icon
description: python_projects 子仓打包 Windows exe 时默认配置 Python 双蛇标志图标的流程（python-default.ico → Nuitka --windows-icon-from-ico），含触发与豁免条件、重生成方法与验证方法。当 python_projects 下项目打包 exe 且用户未对图标提出要求时使用；用户明确指定图标或明确不要时豁免。
---

# python_projects exe 默认图标

适用于 `python_projects` 子仓内打包 Windows exe 的项目（Nuitka 等方案）。当用户未对图标提出任何要求时，默认为该项目的 exe 配置 Python 双蛇标志图标（Python 社区事实上的吉祥物形象，Python 没有类似 Go gopher 的官方吉祥物），直接按本文执行，无需再次询问。

## 触发与豁免

- **触发**：python_projects 下项目首次打包 exe，或重新打包/换图标，用户未提及图标。
- **豁免**（满足任一则跳过本流程）：
  - 用户明确指定了其他图标；
  - 用户明确说不要图标；
  - 打包目标不是 Windows。

## 图标资源

- 权威源：父仓库 `docs\assets\projects\python_projects\python-default.ico`（官方 Python 双蛇标志，含 16/24/32/48/64/128/256 共 7 帧，透明底）。
- 使用方式：Nuitka 构建时直接以**绝对路径**引用（`--windows-icon-from-ico=<ico 绝对路径>`），**不需要复制到项目目录**——构建期一次性写进 PE 资源，产物运行不依赖源文件；这是与 Go 侧（rsrc 要求 `.syso` 放主包目录）的差异。
- 项目打包脚本可内置默认定位逻辑：`<仓库根>/docs/assets/projects/python_projects/python-default.ico`（从脚本位置向上两级推算），图标缺失时跳过并告警，不阻断构建。参考实现：`python_projects\douyin_downloader\scripts\build_exe.py`。

## 打包脚本接入（Nuitka）

在项目打包命令/脚本中追加一个参数即可：

```
--windows-icon-from-ico=<python-default.ico 绝对路径>
```

版本信息资源顺带由 `--product-version` / `--file-version` / `--file-description` 写入 VS_VERSION_INFO。

## 重生成

1. 出高分辨率源图（path 数据内嵌，不依赖网络与 SVG 渲染库）：

   ```powershell
   cd D:\Users\language_projects
   uv run .scripts\gen_python_logo.py C:\Users\29580\AppData\Local\Temp\opencode\python-logo-1024.png
   ```

2. 出多帧 ico（仓库通用脚本）：

   ```powershell
   uv run .scripts\gen_icon.py <上一步 png> D:\Users\language_projects\docs\assets\projects\python_projects\python-default.ico
   ```

## 验证

```powershell
Add-Type -AssemblyName System.Drawing
$i = [System.Drawing.Icon]::ExtractAssociatedIcon("<exe 完整路径>")
"$($i.Width)x$($i.Height)"   # 输出 32x32 即已带图标
```

资源管理器存在图标缓存，未立刻刷新属正常现象，可换目录查看或等待缓存失效。

## 原理速记

- Windows exe 图标是 PE 资源；Nuitka 的 `--windows-icon-from-ico` 在链接产物阶段直接把 ico 写入资源段（内部经 rcedit 同源机制），与 Go 的 `*.syso` 链接方案殊途同归，均无需改任何业务代码。
- 官方标志 SVG 为渐变填色，图标帧尺寸下差异不可感知，统一用 PSF 官方扁平品牌色 `#3776AB`（蓝）与 `#FFD43B`（黄）；眼睛挖洞保持透明底。
- 商标提示：Python 双蛇标志是 PSF 商标，仓库内部工具使用无碍；若对外分发修改版并保留该标志，注意 PSF 商标政策的非误导性要求。

## 参考

- Go 侧同类流程：`docs\projects\go_projects\go exe 默认图标.md`
- ico 多帧生成脚本：`.scripts\gen_icon.py`；双蛇标志源图生成脚本：`.scripts\gen_python_logo.py`
- 官方标志来源：Wikimedia `Python-logo-notext.svg`
