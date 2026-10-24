# clictl 工具分组、树状/平铺视图与稳定排序

- 现状：WebUI 列表默认 `launch_count DESC, name ASC`，启动任意工具即跳到最前，顺序不稳定。
- 现状：dev / release 变体混排，无法按项目或用途归类。
- 目标：支持用户自定义分组（meta.group），提供树状 / 平铺视图切换，默认平铺 + 名称升序稳定排序。

## 决策（已确认）

| 议题 | 决策 |
|---|---|
| 默认视图 | 平铺 |
| 分组方式 | 用户显式分组，不做自动推断；空分组归入「未分组」 |
| 分组存储 | `meta.group`（字符串，≤32 字节，首尾空白裁剪） |
| 分组入口 | 注册对话框「分组」输入框 + 详情页「分组」编辑面板 |
| 默认排序 | 名称升序（CLI / MCP / WebUI 同步） |
| 可选排序 | 名称 / 最近启动 / 启动次数 / 添加时间 |
| 组顺序 | 恒为名称字母序，「未分组」置底，避免顺序漂移 |
| 偏好持久化 | 落盘到当前通道数据目录 `ui_preferences.json`（GUI 随机端口，localStorage 不可靠） |

## 实施

### 后端

- [x] `internal/store/meta.go`：白名单增加 `group`（string，裁剪空白，≤32 字节）。
- [x] `internal/store/store.go`：`ListTools` 默认排序改为 `t.name ASC`。
- [x] `internal/api/preferences.go`（新增）：`UIPreferences{view_mode,sort_mode,collapsed_groups}` 读写。
- [x] `internal/api/server.go`：注册 `GET/POST /api/preferences`；偏好文件与 DB 同通道目录。
- [x] 测试：偏好默认值/持久化/非法值回落；`meta.group` 校验；列表稳定排序。

### 前端

- [x] `index.html`：列表工具栏增加「树状 / 平铺」切换与排序下拉；详情页增加「分组」编辑面板；注册对话框增加分组输入。
- [x] `app.js`：
  - 偏好加载/保存（后端为准）；
  - 分组渲染（分组头可折叠、数量、运行中提示）；
  - 排序实现（组内排序，组顺序字母序）；
  - 分组保存（合并现有 meta，清空时删除 `group` 键）。
- [x] `style.css`：tree-group、视图切换、排序下拉、分组编辑行样式。

### 文档

- [x] README：排序契约、`/api/preferences`、meta 白名单增加 `group`。
- [x] `internal/cli/commands.go` 与 `internal/mcp/tools.go` 描述改为名称升序。
- [x] `docs/projects/go_projects/clictl/clictl 使用指南.md` 同步排序说明。

## 验证

- [x] `go test ./...`、`go vet ./...`、`gofmt -l` 通过。
- [x] `uv run scripts/build.py` 生成 dev 产物。
- [x] 手工验收：平铺默认；切换树状后重启仍为树状；折叠分组重启保持；切换排序重启保持；插入启动记录后列表不跳位；分组保存/清空生效。

## 风险与边界

- `meta` 采用整体替换语义：详情页分组保存会先合并当前 meta，避免冲掉 source/tags。
- 5 秒轮询刷新详情时，分组输入框正在编辑则不回填，避免输入被覆盖。
- 用户重命名分组后，旧折叠状态可能成为孤儿键，仅占少量偏好文件空间，不影响功能。

## 实施记录

- 后端：`meta.group` 白名单（≤32B）、`ListTools` 名称升序、`/api/preferences` + `<通道目录>/ui_preferences.json`。
- 前端：平铺默认、树状折叠分组、四档排序、详情页与注册弹窗分组入口；视图/排序/折叠状态服务端持久化。
- 验证：`go test ./...`、`go vet ./...`、`gofmt -l` 通过；`uv run scripts/build.py` 构建 dev 双产物成功。
- 接口验收：临时 APPDATA 下注册 beta/alpha 并给 beta 插入启动记录，列表仍为 alpha→beta；偏好默认 flat/name，保存 tree/recent 后重启保持。
- UI 验收：Edge headless 截图确认树状（含折叠、计数、未分组置底）与平铺（分组徽标、排序下拉）渲染正常；临时进程与截图已清理。
