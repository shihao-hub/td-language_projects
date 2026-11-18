# Requirements Document: Nginx AI Proxy Submodule (02-nginx-ai-proxy)

## Summary
在 `language_projects` 的 `go_projects` 一级子仓下，按照 `GUIDE-子项目拆分子模块.md` 规范新建一个独立的二级子模块项目 `nginx-ai-proxy`（代码独立建仓 `td-go_projects-nginx-ai-proxy` 并挂载）。该项目旨在以极度轻量、低内存占用（裸跑系统已装 Nginx + Go CLI 封装，不额外占用常驻容器内存，保障腾讯云服务器上运行的游戏服不受影响）的方式，在 Linux 云服务器上部署并管理一个专为 AI 请求设计的高性能反向代理。它对外暴露自定义的 API Key 和经过实测空闲的 HTTP 端口（8088），接收来自本地客户端（子项目自带 `python/nanocode`，通过 `uv run` 零依赖单脚本运行）的请求，做鉴权校验后，将请求原样转发至智谱清言（GLM）官方接口，并注入真实的 GLM API Key，同时保证 SSE 流式输出零缓冲。

## Functional Requirements
- **FR-1: 独立子模块与代码工程结构**：
  - 子项目位于 `go_projects/nginx-ai-proxy`，按照规范独立建仓、提交，并在父仓以二级 Submodule（配置 `ignore = all` 与 `branch = main`）挂载。
- **FR-2: Nginx 反向代理与请求安全中转**：
  - 监听指定 HTTP 端口（已在腾讯云服务器实测确认 8088 端口空闲，默认采用 8088）。
  - 支持虚拟 API Key 鉴权：客户端请求头携带自定义 `Authorization: Bearer <PROXY_API_KEY>`，不匹配时返回 401 Unauthorized。
  - 鉴权通过后，Nginx 自动将请求头重写为智谱官方的真实凭证（`Authorization: Bearer <GLM_API_KEY>`）。
  - 原样反向代理至智谱接口（`https://open.bigmodel.cn/api/anthropic/`），配置 `proxy_ssl_server_name on`。
  - 关闭响应缓冲（`proxy_buffering off`、`proxy_cache off`），支持打字机 SSE 流式无卡顿输出。
- **FR-3: Go 管理 CLI 工具（`aiproxy`）**：
  - 用 Go 语言实现轻量命令行工具，封装 Linux 原生服务操作。
  - 支持 `aiproxy keygen`：利用 `crypto/rand` 生成高熵安全 Key（格式形如 `sk-proxy-<hex>`）。
  - 支持 `aiproxy init`：根据模板和 `.env`（含自动生成或指定的 Key）渲染并生成 `nginx.conf`。
  - 支持 `aiproxy start` / `stop` / `reload` / `status`：封装系统服务管理（直接调用 `nginx -s` 或 `systemctl`），并能报告当前 Nginx 进程的运行状态与实际 RSS 内存占用。
  - 支持 `aiproxy test`：向本地或远端代理发送探针请求，校验 401 拦截与真实请求转发是否正常。
- **FR-4: 客户端整合（`python/nanocode` 零依赖运行）**：
  - 将 `nanocode.py` 整合至子项目的 `python/nanocode/` 目录中。
  - 支持直接通过 `uv run python/nanocode/nanocode.py` 单脚本执行，无需创建本地 `.venv`。
  - 配置同级 `.env` 将 `API_URL` 指向腾讯云代理地址，使用生成的自定义虚拟 Key。
- **FR-5: OpenResty + Lua 扩展性独立预留文件**：
  - 在子项目根目录下创建全大写文件 `TODO_OPENRESTY_LUA.md`，醒目记录升级至 OpenResty + Lua 的演进方案（包含 Redis 动态鉴权、Token 统计、Prompt 过滤等），供未来扩展参考。

## Non-Functional Requirements
- **低内存开销**：Nginx 宿主机裸跑 + Go 单二进制管理工具，常驻内存占用严格控制在 10MB 以内，绝对不干扰游戏服运行。
- **配置与凭证隔离**：真实 GLM API Key 仅保留在服务器端 `.env` 或渲染后的配置文件中，不随 Git 仓库提交；提供 `.env.example`。
- **单步部署与迁移便捷性**：通过 `scp` 或 `git pull` 后，可在服务器上一键编译或运行 `aiproxy` 完成启动。

## Acceptance Criteria
### AC-1: 子模块规范与结构就绪
- [ ] 按照 `GUIDE-子项目拆分子模块.md` 完成 `go_projects/nginx-ai-proxy` 目录初始化，拥有自包含的 `go.mod`、配置模板、管理代码及全大写的 `TODO_OPENRESTY_LUA.md`。

### AC-2: Nginx 裸跑配置与鉴权测试通过
- [ ] 未带 Key 或带错误 Key 请求 `http://<server-ip>:8088/api/anthropic/v1/messages` 时，Nginx 返回 HTTP 401；
- [ ] 携带正确自定义 `PROXY_API_KEY` 时，Nginx 成功将请求转发至智谱并返回 200，且客户端能正常逐字接收流式响应。

### AC-3: Go CLI 工具可用性
- [ ] `aiproxy` 支持 `keygen` 生成随机 Key，能够执行配置生成、Nginx 启动/停止/状态检测，且内存开销极小。

### AC-4: nanocode 整合与端到端验证
- [ ] 在子目录下执行 `uv run python/nanocode/nanocode.py`（无 `.venv`），能通过腾讯云代理成功与 GLM-5.3-flash 交互。

## Out of Scope
- 本期暂不引入 OpenResty 及 Lua 动态模块（已作为待办记录在 `TODO_OPENRESTY_LUA.md` 中）。
- 本期暂不强制配置公网域名与 HTTPS/SSL 证书（默认走 HTTP + 8088 端口）。
- 本期不实现用户计费与多租户配额系统。
