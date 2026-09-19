---
name: go-exe-icon
description: go_projects 子仓产 Windows exe 的项目默认配置站标地鼠图标的四步流程（复制 go-default.ico → rsrc 生成 .syso → go build → 入库），含触发与豁免条件、验证方法与 PE 资源原理。当 go_projects 下新建项目首次构建 exe、已有项目重建或换图标，且用户未对图标提出要求时使用；用户明确指定图标或明确不要时豁免。
---

# GUIDE-GO-EXE-ICON：go_projects exe 默认图标

适用于 `go_projects` 子仓内产出 Windows exe 的项目。当用户未对图标提出任何要求时，默认为该项目的 exe 配置站标地鼠图标，直接按本文执行，无需再次询问。

## 触发与豁免

- **触发**：go_projects 下新建项目首次构建 exe，或已有项目调整构建产物，用户未提及图标。
- **豁免**（满足任一则跳过本流程）：
  - 用户明确指定了其他图标；
  - 用户明确说不要图标；
  - 构建目标不是 Windows（`GOOS != windows`）。

## 图标资源

- 权威源：父仓库根目录 `assets\projects\go_projects\go-default.ico`（go.dev 站标地鼠，含 16/24/32/48/64/128/256 共 7 帧）。
- 使用方式：把该文件**复制**一份到项目主包目录（如 `go_projects\<项目>\cmd\<工具>\icon.ico`）。复制是值拷贝，不产生项目间构建依赖，不违反仓库隔离性原则。
- 重生成：更换或更新图片时，用仓库 `docs/scripts/gen_icon.py`（PEP 723 + Pillow，`uv run` 执行）重出多帧 ico，再执行第 2 步重出 `.syso`。

## 操作步骤（四步）

1. 复制图标到新项目主包目录：

   ```powershell
   Copy-Item D:\Users\language_projects\assets\projects\go_projects\go-default.ico D:\Users\language_projects\go_projects\<项目>\cmd\<工具>\icon.ico
   ```

2. 生成 Windows 资源对象（rsrc 未安装则先 `go install`，全机只需一次）：

   ```powershell
   go install github.com/akavel/rsrc@latest
   cd D:\Users\language_projects\go_projects\<项目>
   & "$env:USERPROFILE\go\bin\rsrc.exe" -ico cmd\<工具>\icon.ico -o cmd\<工具>\rsrc_windows_amd64.syso
   ```

3. 构建：`go build` 照常（或用项目自己的构建脚本），Go 链接器自动链接主包目录下的 `*.syso`，无需改任何 Go 代码或构建参数。
4. 提交：`icon.ico` 与 `rsrc_windows_amd64.syso` 均入库，按 `<project>:feat:` 提交格式随该项目提交。

## 验证

```powershell
Add-Type -AssemblyName System.Drawing
$i = [System.Drawing.Icon]::ExtractAssociatedIcon("<exe 完整路径>")
"$($i.Width)x$($i.Height)"   # 输出 32x32 即已带图标
```

资源管理器存在图标缓存，未立刻刷新属正常现象，可换目录查看或等待缓存失效。

## 原理速记

- Windows exe 图标是 PE 资源，与 Go 代码无关；Go 工具链约定：主包目录下的 `*.syso`（COFF 资源对象）会被链接器自动链接进产物，图标、版本信息、manifest 都走这条路。
- 文件名即作用域：`rsrc_windows_amd64.syso` 仅在 `GOOS=windows`、`GOARCH=amd64` 构建时生效，交叉编译其他平台不受影响。
- 生成工具：rsrc（akavel/rsrc，纯 Go）；备选 goversioninfo（可顺带写版本信息块）、MSYS2 windres（编译 .rc）。

## 参考

- 完整实操留档（资源来源、获取命令、Wikimedia 介绍、手动 DIY 与踩坑）：
  <https://qcnpt54xm50k.feishu.cn/docx/OyMydgWowoyplVxm8Z9cyBSRn7e>
- ico 生成脚本：`docs/scripts/gen_icon.py`
