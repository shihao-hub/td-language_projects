# Walkthrough：glmquotawatch-gui 托盘图标对齐自定义用量图标

## 变更内容

- 将生成首选的 `build/glmquotawatch.ico` 覆盖到 Wails 构建入口使用的 `build/windows/icon.ico`。
- 删除项目根冗余的 Go 地鼠 `icon.ico`。
- 将托盘嵌入路径从项目根 `icon.ico` 改为 `build/windows/icon.ico`，使托盘、exe、任务栏和开始菜单共用同一图标源。
- 更新 `RunOptions.Icon` 与 `main.go` 的注释，并修正 README 图标来源说明。

对应 Go 子仓提交：`5bae4c6 glmquotawatch-gui:feat: 更换应用与托盘图标`。

## 验证

### 构建

- 命令：`wails3 task windows:build`
- 结果：成功，产物位于 `go_projects/glmquotawatch-gui/bin/glmquotawatch-gui.exe`。
- 警告：日志提示部分依赖声明需要 Go 1.26，当前构建工具链报告 Go 1.25；本次构建未失败。

### 图标资源

- `build/windows/icon.ico` 覆盖后包含 16/24/32/48/64/128/256px 七层，均为 32bpp。
- 从生产 exe 抽取关联图标为 32x32、32bpp；采样像素确认为青色弧 `RGB(0,255,255)`、珊瑚弧 `RGB(164,66,64)`、深色底 `RGB(15,23,42)`。

### 运行收尾

- 以 `--demo` 启动生产 exe，PID `21172` 正常存活。
- 按 PID 终止验证进程，最终没有 `glmquotawatch-gui.exe` 残留。
- 自动桌面截图未返回有效画面，因此托盘最终外观需要用户在自己系统托盘中做一次目视确认。

## 未做与遗留

- 未运行 `go test`；本次仅按用户要求执行生产构建和图标资源验证。
- Go 子仓仍保留用户此前 `internal/guiapp/app.go` 窗口尺寸/背景色改动，以及多个前端文件改动；本次提交已用局部 staging 隔离。
- 图标比稿与生成过程文件仍未入库：`build/appicon.svg`、`build/glmquotawatch.ico`、其他候选 PNG、`render_icon.py`、`tray_legibility_test.png`。
