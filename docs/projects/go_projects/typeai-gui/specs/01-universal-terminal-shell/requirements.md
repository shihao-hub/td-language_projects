# Requirements Document

## Summary

`typeai-gui` 当前是 typeai 专属的 Wails 终端窗口壳（xterm.js + ConPTY，单会话、typeai.exe 硬定位）。本次将其泛化为**通用 CLI/TUI 桌面终端**：窗口内支持多标签页，每个标签页运行一个由用户配置的 CLI exe（TUI 或交互式 CLI），typeai 作为预置默认 profile。配置采用运行时 UI（打开应用后即可管理 profile，含 exe 存在探测），不依赖配置文件手工编辑，也不与 clictl 产生任何数据耦合。现有 ConPTY 桥接层（含 EOF 死锁与堆损坏规避）原样复用。

## Functional Requirements

- FR-1（profile 管理 UI）：应用内提供 profile 管理界面，可新增、编辑、删除 profile；字段为：名称（必填、去重）、exe 路径（必填）、启动参数（可选，原样拼接在 exe 后）。
- FR-2（exe 存在探测）：添加/编辑 profile 时，输入 exe 路径后即时探测并反馈：存在（显示绝对路径）或缺失（明确提示），缺失的 profile 不允许用于新建标签页。
- FR-3（多标签页）：主界面为标签页容器；从 profile 列表新建标签页后在标签页内以 ConPTY 运行该 exe；同一 profile 可开多个标签页；标签页可切换、可关闭。
- FR-4（标签页生命周期）：关闭单个标签页即终止该标签页的子进程并释放其 ConPTY，其余标签页不受影响；子进程自行退出时该标签页显示退出状态覆盖层。
- FR-5（窗口级清理）：关闭窗口终止全部标签页的子进程，无任何后台残留。
- FR-6（预置 typeai）：内置名为 `typeai` 的默认 profile，exe 路径沿用现有三级定位（`TYPEAI_GUI_TYPEAI_PATH` → 同目录 → PATH）；首次启动且无用户 profile 时直接以该 profile 打开第一个标签页。
- FR-7（配置持久化）：profile 持久化为 JSON 文件，位于 `%APPDATA%\language_projects\<项目名>\{dev|prod}\profiles.json`（取不到 APPDATA 回退 `~/.language_projects/`），写入前自动创建完整目录链；dev 与 prod 构建的数据目录相互隔离。
- FR-8（错误呈现）：任何标签页内 exe 启动失败（路径失效等）时，该标签页显示已尝试信息与修复指引，不闪退、不影响其他标签页。

## Non-Functional Requirements

- 标签页切换时各终端的屏幕状态与滚动历史完整保留（不重绘丢失）。
- 标签页切换、新建、关闭操作不阻塞 UI 主线程。
- 沿用现有构建规范：单一 build.py、dev/release 自动判定、GUI 专属图标。

## Acceptance Criteria

### AC-1
WHEN 首次启动（无用户 profile 且预置 typeai 可定位），THEN 应用直接打开一个运行 typeai TUI 的标签页，交互与现状一致。

### AC-2
WHEN 在 profile 管理界面录入 exe 路径后，THEN 界面即时显示该路径的存在性探测结果；路径不存在时无法保存为可用 profile。

### AC-3
WHEN 从 profile A 新建标签页并再次从 profile A 新建另一标签页，THEN 两个标签页独立运行各自的子进程，切换时终端状态完整保留，窗口缩放对当前标签页即时生效。

### AC-4
WHEN 关闭一个标签页，THEN 仅该标签页的子进程被终止且进程列表中无残留，其余标签页继续正常运行。

### AC-5
WHEN 关闭应用窗口，THEN 全部标签页的子进程被终止，`Get-Process` 确认无任何对应 exe 残留。

### AC-6
WHEN dev 与 prod 构建先后运行，THEN 二者读写 `profiles.json` 的目录不同（`dev/` 与 `prod/` 子目录），互不可见。

### AC-7
WHEN 某 profile 对应的 exe 在启动前已失效，THEN 该标签页显示含路径与修复建议的错误覆盖层，应用不闪退。

## Out of Scope

- 与 clictl 的任何集成（不读写其数据库、不依赖其注册表）
- 多窗口（多显示器各开一窗）；一个窗口多标签页已满足
- 远程会话（SSH/容器内终端）
- profile 的工作目录、环境变量覆盖等高级启动属性
- 标签页拆分（split pane）、终端配色自定义
- 项目更名（本期保持 `typeai-gui` 名称与 module 名不变；如需更名单独成期）

## 开放问题（批准时确认）

1. **项目更名**：泛化后 `typeai-gui` 这个名字不再准确（如 `termdeck`/`termshell`）。更名涉及目录、module、exe 产物名、README 一并调整，成本一次性。本期是否顺带更名？
