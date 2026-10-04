# Task List: Nginx AI Proxy Submodule (02-nginx-ai-proxy)

- [ ] 1. 创建子模块目录骨架与全大写演进文档
  - Files: `go_projects/nginx-ai-proxy/go.mod`, `go_projects/nginx-ai-proxy/.gitignore`, `go_projects/nginx-ai-proxy/.env.example`, `go_projects/nginx-ai-proxy/TODO_OPENRESTY_LUA.md`
  - 实现细节：在 `go_projects/nginx-ai-proxy` 下初始化 `go.mod` (module `td-go_projects-nginx-ai-proxy`)；配置 `.gitignore` 排除真实 `.env` 和构建产物；提供包含 `PROXY_PORT=8088`、`PROXY_KEY=...`、`GLM_KEY=...` 的 `.env.example`；创建全大写文件 `TODO_OPENRESTY_LUA.md` 详尽记录后续升级 OpenResty + Lua 的架构演进方案。
  - Verify: `cd D:\Users\language_projects\go_projects\nginx-ai-proxy; go env GOMOD` 输出正确的 go.mod 路径，且 `TODO_OPENRESTY_LUA.md` 文件存在。
  - Ref: AC-1

- [ ] 2. 编写 Nginx 代理配置模板与纯 Nginx 语法验证
  - Files: `go_projects/nginx-ai-proxy/configs/nginx.conf.tmpl`
  - 实现细节：编写完整的 8088 server 块模板，包含自定义 Key 校验（401 拦截）、Header 注入（替换为智谱真实 Key）、`proxy_pass`、`proxy_ssl_server_name on`、`proxy_buffering off` 及长超时配置。
  - Verify: 检查模板包含所有的占位符，且符合标准 Nginx 语法。
  - Ref: AC-2

- [ ] 3. 实现 Go 管理工具 `aiproxy` 核心包（含 Keygen 与 Nginx 控制）
  - Files: `go_projects/nginx-ai-proxy/internal/config/config.go`, `go_projects/nginx-ai-proxy/internal/nginx/manager.go`, `go_projects/nginx-ai-proxy/internal/tester/probe.go`
  - 实现细节：
    - `internal/config`: 使用内置轻量解析读取 `.env`；提供 `GenerateKey()` 基于 `crypto/rand` 生成 `sk-proxy-<hex>` 高熵安全 Key 并支持写回 `.env`。
    - `internal/nginx`: 使用 `text/template` 将 `nginx.conf.tmpl` 渲染生成到 `/etc/nginx/conf.d/aiproxy.conf`；封装 `nginx -t`、`nginx -s reload`、`systemctl` 调用；通过 `ps` 或 procfs 读取 Nginx 进程的 RSS 内存消耗。
    - `internal/tester`: 封装 HTTP 探测，测试 401 拦截和合法 Key 转发通路。
  - Verify: `cd D:\Users\language_projects\go_projects\nginx-ai-proxy; go vet ./internal/...` 无报错。
  - Ref: AC-3

- [ ] 4. 组装 `aiproxy` CLI 入口并交叉编译测试
  - Files: `go_projects/nginx-ai-proxy/cmd/aiproxy/main.go`
  - 实现细节：实现子命令 `keygen`、`init`、`start`、`stop`、`reload`、`status`、`test`。支持交叉编译 Linux amd64 二进制：`$env:GOOS="linux"; $env:GOARCH="amd64"; go build -o bin/aiproxy-linux-amd64 ./cmd/aiproxy`。
  - Verify: `cd D:\Users\language_projects\go_projects\nginx-ai-proxy; go build -o bin/aiproxy.exe ./cmd/aiproxy` 编译成功并运行 `bin\aiproxy.exe keygen` 能生成有效 Key。
  - Ref: AC-3

- [ ] 5. 整合客户端 `python/nanocode` 零依赖单脚本
  - Files: `go_projects/nginx-ai-proxy/python/nanocode/nanocode.py`, `go_projects/nginx-ai-proxy/python/nanocode/.env.example`
  - 实现细节：将本地 `nanocode.py` 单文件拷贝并收拢进 `python/nanocode/`，提供客户端配置范本。支持通过 `uv run python/nanocode/nanocode.py` 零依赖单脚本执行，不依赖 `.venv`。
  - Verify: 检查 `python/nanocode/nanocode.py` 文件完整性，检查其对 `OPENROUTER_API_KEY` 和 `API_URL` 的解析逻辑。
  - Ref: AC-4

- [ ] 6. 编写一键发布脚本与子项目使用文档
  - Files: `go_projects/nginx-ai-proxy/README.md`, `go_projects/nginx-ai-proxy/scripts/deploy.ps1`, `go_projects/nginx-ai-proxy/scripts/deploy.sh`
  - 实现细节：
    - 编写一键打包与 SCP 推送脚本（支持 Windows 本地直接一条命令打包 Linux 二进制和配置模板，`scp` 至 `ssh tencent` 服务器并触发 `aiproxy init && aiproxy reload`）。
    - 编写详细的 `README.md`，包含服务器端环境准备、配置方式、管理命令、内存监控方法，以及引用 `TODO_OPENRESTY_LUA.md`。
  - Verify: 检查部署脚本语法，检查 README 中的指引完整性。
  - Ref: AC-1, AC-3

- [ ] 7. 按照 GUIDE 手册建立独立 Git 仓库与 Submodule 挂载
  - Files: `language_projects/.gitmodules`
  - 实现细节：参考 `docs/guides/GUIDE-子项目拆分子模块.md`，通过 `gh repo create shihao-hub/td-go_projects-nginx-ai-proxy` 建立远端仓库；提交本地代码并推送远端 `main` 分支；配置父级 `.gitmodules` 的 `ignore = all` 与 `branch = main`。
  - Verify: `git submodule status` 输出正常且父级 `git status` 干净无噪音。
  - Ref: AC-1

- [ ] 8. 服务器端部署、启动与客户端真机联调验证
  - Files: `go_projects/nginx-ai-proxy/python/nanocode/.env`
  - 实现细节：将代理部署至腾讯云服务器，通过 `aiproxy` 启动 Nginx 8088 端口；配置本地 `python/nanocode/.env`，运行 `uv run python/nanocode/nanocode.py` 进行真机流式对话测试，确认返回正常且服务器 Nginx 内存稳定在 10MB 内。
  - Verify: 客户端终端呈现打字机流式回答，腾讯云 Nginx 访问日志记录 200。
  - Ref: AC-2, AC-4
