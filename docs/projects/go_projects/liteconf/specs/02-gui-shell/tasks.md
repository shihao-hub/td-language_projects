# Task List — liteconf Web 控制台壳子

以下命令均在子项目目录 `go_projects\liteconf` 内执行。项目零第三方依赖（`go.mod` 的 require 列表保持为空），仅用 Go 1.22 标准库与浏览器原生能力。

- [x] 1. 创建前端静态资源骨架
  - 新建 `go_projects/liteconf/internal/server/webui/static/index.html`：头部（标题「liteconf 控制台」+「新建配置」按钮）、`#error-banner` 全局错误横幅、`#list-view` 列表容器、`#editor-view` 编辑器容器、原生 `<dialog id="new-dialog">` 新建对话框；`<link rel="stylesheet" href="style.css">` + `<script src="app.js" defer>`
  - 新建 `go_projects/liteconf/internal/server/webui/static/style.css`：最小样式（横幅错误态、视图显隐 class、表格、dialog）
  - 新建 `go_projects/liteconf/internal/server/webui/static/app.js`：占位空文件（`"use strict";` 一行即可），保证后续 `//go:embed static` 目录非空可编译
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-1

- [x] 2. 实现 webui 静态托管包
  - 新建 `go_projects/liteconf/internal/server/webui/webui.go`：`package webui`；`//go:embed static` 嵌入；`fs.Sub` 取 `static` 为根 + `http.FileServerFS` 实现 `Handler() http.Handler`；外层中间件对所有响应设 `Cache-Control: no-cache`；包内不出现任何存储/校验/版本管理业务代码
  - 仅用标准库 `embed`、`io/fs`、`net/http`（`http.FileServerFS` 为 Go 1.22 新增，go.mod 已是 `go 1.22`）
  - Run and validate: `cd go_projects\liteconf; go build ./...; go vet ./...`
  - Ref: REQ-1, REQ-6
  - 实施说明：`http.FileServerFS` 按完整请求路径查文件，挂载 `/ui/` 下需包一层 `http.StripPrefix("/ui", ...)` 剥前缀，否则 `/ui/app.js` 会在子文件系统里找 `ui/app.js` 命中 404（实测发现并修复）

- [x] 3. 在 NewMux 注册 /ui/ 路由
  - 修改 `go_projects/liteconf/internal/server/handler.go`：`NewMux` 新增一行 `mux.Handle("GET /ui/", webui.Handler())`，import `github.com/shihao-hub/liteconf/internal/server/webui`；既有四条 `/api/*` 路由的注册与实现零改动
  - `/ui`（无斜杠）依赖 `ServeMux` 自带 301 补斜杠，不额外注册
  - Run and validate: `cd go_projects\liteconf; go build ./...; go vet ./...`
  - Ref: REQ-1, REQ-7

- [x] 4. app.js：API 包装与 hash 路由
  - `api(method, path, body)`：fetch → 解析统一包络 `{code,message,data}`；`code !== "ok"`、非 JSON 响应、网络异常统一归一为 `{status, code, message}` 错误对象 reject
  - hash 路由：`#/` 列表、`#/{app}/{env}` 编辑器；监听 `hashchange`；app/env 段不匹配 `[a-zA-Z0-9_-]+` 一律回列表（不向服务端发请求）
  - 全局 `showError(msg)` / `clearError()` 横幅工具，供各视图复用
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-2, REQ-6

- [x] 5. app.js：发现列表视图
  - `GET /api/discovery` → 取 `data.apps[]` 按 app 分组渲染 env 与 version；点击 env → `location.hash = "#/" + app + "/" + env`
  - `apps` 为空 → 展示空状态提示「仓库中还没有配置」，不报错
  - 请求失败 → 错误横幅，不渲染误导性空列表
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-2

- [x] 6. app.js：查看配置（编辑器载入）
  - 进入 `#/{app}/{env}`：`GET /api/{app}/{env}` → 展示 content 与当前 version；编辑器缓冲初始化 `text = JSON.stringify(content, null, 2)`
  - 返回 `not_found` → 展示「配置不存在」提示与返回列表链接
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-3

- [x] 7. app.js：JSON 文本编辑模式
  - textarea 绑定权威缓冲 `text`；「格式化」按钮 = `JSON.parse` → `JSON.stringify(obj, null, 2)` 回填，parse 失败提示且不改动原文
  - 「保存」：先前端 `JSON.parse` 本地校验，失败立即拦截并展示错误，不发请求；通过则 `PUT /api/{app}/{env}`，成功展示返回的新版本号；服务端 `invalid_json` 等错误 → 错误横幅，本地缓冲不动
  - 无自动保存，保存仅由显式按钮触发
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-4

- [x] 8. app.js：键值表编辑模式
  - flatten：递归下钻普通对象生成点路径行（如 `db.host`）；键名含 `.` 不下钻、数组与其他非原始值 → 该键整行按「复杂值」处理，单元格内容为值的 JSON 文本片段
  - rebuild：叶子单元格先尝试 `JSON.parse` 识别数字/布尔/null 字面量，失败按字符串；复杂值单元格整体 `JSON.parse`，失败标红该行并阻止保存
  - 键值表保存走与任务 7 相同的 PUT 流程（保存前 rebuild 回写 `text`）
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-4

- [x] 9. app.js：双模式互转
  - text→table：当前 `text` 可 `JSON.parse` 才切换并渲染表格，失败报错并停留原模式；table→text：rebuild 结果回写 `text`，总是可行
  - 切换不重置缓冲，未保存修改一律保留（`text` 为唯一权威缓冲）
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-4

- [x] 10. app.js：新建配置对话框
  - `<dialog>` 内输入 app、env 与初始 JSON（默认 `{}`）；app/env 前端按 `^[a-zA-Z0-9_-]+$` 预校验，不合法直接提示不提交
  - 提交前先 `GET /api/{app}/{env}` 探测存在性：已存在 → 明示「该配置已存在，提交将覆盖现有内容」，用户显式确认后才 `PUT /api/{app}/{env}`；返回 `invalid_name` → 展示命名规则提示
  - 成功 → 跳转 `#/{app}/{env}`、刷新列表、展示首版版本号 1
  - Run and validate: `cd go_projects\liteconf; go build ./...`
  - Ref: REQ-5, REQ-6

- [x] 11. 更新子项目 README
  - 修改 `go_projects/liteconf/README.md`：特性列表增加控制台条目；「快速开始」补浏览器访问 `http://localhost:8646/ui/`；HTTP API 表后补 `/ui/` 静态托管说明；「项目结构」树加入 `internal/server/webui/`（webui.go + static/ 三文件）；「定位与边界」中原「无 Web 控制台（编辑器就是控制台）」改写为现状描述
  - Run and validate: 人工通读核对与实现一致
  - Ref: REQ-8

- [ ] 12. 端到端手工验证（浏览器全流程）[test]
  - 起服：`cd go_projects\liteconf; go build -o build\liteconf-server.exe ./cmd/liteconf-server; .\build\liteconf-server.exe`
  - 浏览器访问 `http://localhost:8646/ui/`（另验 `/ui` 301 跳转）：空仓库空态提示 → curl PUT 一条配置 → 刷新列表可见；查看配置展示 content+version；JSON 模式非法内容保存被本地拦截、格式化、合法保存版本号递增；键值表编辑含数组/嵌套对象配置、复杂值 JSON 片段编辑；双模式互转不丢未保存修改；新建对话框非法名拦截、已存在覆盖确认、成功后首版 1；既有 API 冒烟（discovery/GET/PUT 路径包络不变）
  - Run and validate: 人工按上述步骤逐项过一遍
  - Ref: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5, REQ-7
