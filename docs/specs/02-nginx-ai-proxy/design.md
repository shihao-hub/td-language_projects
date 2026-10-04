# Design Document: Nginx AI Proxy Submodule (02-nginx-ai-proxy)

## Overview
本项目是一个用于在 Linux 服务器（如腾讯云 VPS）上裸跑部署的高性能、超轻量 AI 代理套件。项目通过自建 Nginx 作为反向代理节点，向客户端（项目内嵌 `python/nanocode`）提供自定义安全认证的 HTTP 接入端点，并在内部注入真实的智谱（GLM）API 凭证转发给官方接口。

经实测：腾讯云服务器正在运行 `dontstarve_dedi`（饥荒联机服务器），且 80 端口被占用；但系统已安装 `/usr/sbin/nginx`，且 **8088 端口完全空闲**。项目采用 **系统裸跑 Nginx + Go 编写的单二进制管理工具（`aiproxy`）** 进行服务编排与生命周期管理，总内存开销稳定在 5~10MB，对游戏服务器完全零压力。

## Context & Architecture

```
+-------------------------------------------------------------+
| 本地客户端 (Windows)                                        |
|  - 子项目 python/nanocode (uv run 单脚本运行, 无 .venv)     |
|  - API_URL: http://<tencent-ip>:8088/api/anthropic/v1/messages|
|  - Header: Authorization: Bearer <PROXY_SECRET_KEY>         |
+------------------------------+------------------------------+
                               | (公网 HTTP 请求 :8088)
                               v
+-------------------------------------------------------------+
| 腾讯云服务器 (Linux / ssh tencent / 已实测 8088 空闲)       |
|                                                             |
|  [aiproxy CLI] (Go 单二进制静态工具, 极低内存)              |
|    |- aiproxy keygen: 基于 crypto/rand 生成 sk-proxy-xxx    |
|    |- aiproxy init: 读取 .env 渲染 /etc/nginx/conf.d/aiproxy.conf |
|    |- 控制 nginx -t / nginx -s reload / 检查 8088 与 RSS内存|
|                                                             |
|  [Nginx 原生进程] (常驻内存 ~5MB)                           |
|    1. 校验 $http_authorization == "Bearer <PROXY_KEY>"      |
|       - 不匹配 -> 直接响应 401 JSON {"error": "unauthorized"} |
|    2. 匹配 -> 动态重写 Header:                              |
|       - proxy_set_header Authorization "Bearer <GLM_KEY>"   |
|       - proxy_set_header Host open.bigmodel.cn              |
|    3. 反向代理 -> proxy_pass https://open.bigmodel.cn/      |
|       - proxy_ssl_server_name on                            |
|       - proxy_buffering off (保证 SSE 打字机流式响应)       |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| 智谱清言官方 API (https://open.bigmodel.cn)                 |
|  - 验证 GLM 官方 API Key 并返回流式/非流式模型结果          |
+-------------------------------------------------------------+
```

## Goals and Non-Goals
### Goals
- **极简且安全的网络中转**：客户端只要配置腾讯云服务器 IP:8088 和自定义 Proxy Key，即可正常调用 GLM，真实 GLM 密钥永不离开云端。
- **安全 Key 生成能力**：Go CLI 提供 `keygen` 命令，用加密安全的随机数生成虚拟 API Key。
- **游戏友好型极低内存**：使用 Linux 原生已装的 `/usr/sbin/nginx`，避免 Docker 守护进程，保持内存占用在 5~10MB。
- **Go 原生运维封装**：用 Go 编写 `cmd/aiproxy`，提供 `keygen`、`init`、`start` / `stop` / `reload` / `status` 以及 `test` 命令。
- **无缝内嵌 `nanocode`**：在子项目设立 `python/nanocode` 目录，通过 `uv run` 直接执行，开箱即用。
- **全大写待办文件醒目留存**：根目录保留 `TODO_OPENRESTY_LUA.md`，完整记录未来演进。
- **规范二级 Submodule**：符合 `GUIDE-子项目拆分子模块.md`，拥有独立的 Git 历史与仓库。

### Non-Goals
- 不在当前阶段引入 OpenResty 或 Lua 动态脚本运行环境。
- 不强制申请域名与 Let's Encrypt 证书（纯 HTTP + 8088 端口访问）。

---

## Detailed Design

### 1. 目录结构设计 (`go_projects/nginx-ai-proxy`)

```
go_projects/nginx-ai-proxy/
├── TODO_OPENRESTY_LUA.md     # 【全大写醒目】OpenResty + Lua 扩展路线详细待办
├── .env.example              # 环境变量模板 (PROXY_PORT=8088, PROXY_KEY, GLM_KEY)
├── .gitignore                # 忽略 .env, aiproxy 二进制, 日志等
├── README.md                 # 子项目使用说明与一键部署指引
├── go.mod                    # Go 模块文件 (module td-go_projects-nginx-ai-proxy)
├── configs/
│   └── nginx.conf.tmpl       # Nginx 站点配置模板 (供 Go 模板引擎渲染)
├── cmd/
│   └── aiproxy/
│       └── main.go           # CLI 入口 (命令: keygen, init, start, stop, reload, status, test)
├── internal/
│   ├── config/               # 读取与校验 .env 配置
│   │   └── config.go
│   ├── nginx/                # 封装 Nginx 模板渲染与系统命令执行 (nginx -t, nginx -s)
│   │   └── manager.go
│   └── tester/               # 发起本地与上游探针连通性测试
│       └── probe.go
├── python/
│   └── nanocode/
│       ├── .env.example      # 客户端配置示例
│       └── nanocode.py       # 直接内嵌，通过 uv run 单脚本运行 (无 .venv)
└── scripts/
    ├── deploy.ps1            # Windows 本地一键打包并 SCP 发布脚本
    └── deploy.sh             # Linux 端一键部署与重载脚本
```

### 2. Nginx 配置核心模板设计 (`configs/nginx.conf.tmpl`)

```nginx
# 由 aiproxy 自动渲染，请勿手工覆盖
server {
    listen {{ .Port }};
    server_name _;

    proxy_connect_timeout 60s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;

    location / {
        # 1. 鉴权逻辑：验证客户端 Header 是否携带匹配的自定义 Key
        set $auth_pass 0;
        if ($http_authorization = "Bearer {{ .ProxyKey }}") {
            set $auth_pass 1;
        }
        if ($http_x_api_key = "{{ .ProxyKey }}") {
            set $auth_pass 1;
        }

        if ($auth_pass = 0) {
            default_type application/json;
            return 401 '{"error":{"type":"authentication_error","message":"Invalid proxy API key"}}';
        }

        # 2. 真实上游转发与 Header 注入
        proxy_pass {{ .GlmUpstream }};
        proxy_ssl_server_name on;
        proxy_ssl_protocols TLSv1.2 TLSv1.3;

        # 重写认证头为智谱官方 Key
        proxy_set_header Authorization "Bearer {{ .GlmKey }}";
        proxy_set_header x-api-key "{{ .GlmKey }}";
        proxy_set_header Host open.bigmodel.cn;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 3. 核心：禁用缓存与缓冲，确保打字机流式 (SSE) 逐字直出
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
```

### 3. Go CLI 管理程序设计 (`aiproxy`)

1. **`aiproxy keygen`**：
   - 核心代码：`b := make([]byte, 16); rand.Read(b); key := "sk-proxy-" + hex.EncodeToString(b)`。
   - 输出安全随机 Key，并支持 `--write` 自动写入 `.env`。
2. **`aiproxy init`**：
   - 校验环境已装 `/usr/sbin/nginx`。
   - 读取同目录下的 `.env` 文件。
   - 使用 Go 标准库 `text/template` 将 `configs/nginx.conf.tmpl` 渲染生成到 `/etc/nginx/conf.d/aiproxy.conf`。
   - 执行 `nginx -t` 进行语法校验。
3. **`aiproxy start` / `stop` / `reload`**：
   - 封装 `systemctl start nginx` 或 `nginx -s reload`。
4. **`aiproxy status`**：
   - 查询 Nginx 进程状态及监听端口 8088。
   - 输出实际驻留内存（RSS），直观展示内存占用（约 4MB~8MB）。
5. **`aiproxy test`**：
   - 向 `http://127.0.0.1:8088/api/anthropic/v1/messages` 发起 401 探针和正常探针。

### 4. 客户端单脚本运行 (`python/nanocode/nanocode.py`)

- 运行方式：
  ```bash
  cd python/nanocode
  uv run nanocode.py
  ```
- 配置 `python/nanocode/.env`：
  ```ini
  OPENROUTER_API_KEY = sk-proxy-<生成的KEY>
  API_URL = http://<tencent-server-ip>:8088/api/anthropic/v1/messages
  MODEL = glm-5.3-flash
  ```

---

## 醒目待办文件设计 (`TODO_OPENRESTY_LUA.md`)

在子项目根目录创建该文件，其内容涵盖：
1. **升级背景与动机**：何时应该升级（如需精细化 Token 统计、Prompt 审查、多 Key 容灾轮询）。
2. **安装 OpenResty**：`apt install openresty` 及替换命令。
3. **Lua 模块规划**：
   - `access_by_lua_block`：连接本地 Redis 做 Key 配额校验。
   - `body_filter_by_lua_block`：解析流式 chunk 捕获 `usage.total_tokens`。
4. **架构平滑迁移步骤**：Go CLI 模板更新与服务重载。

---

## Acceptance Criteria Mapping

| AC ID | 对应设计方案 |
|---|---|
| **AC-1** | `go_projects/nginx-ai-proxy` 完整工程结构 + 全大写 `TODO_OPENRESTY_LUA.md` |
| **AC-2** | 实测 8088 端口无冲突 + Nginx 401 拦截 + Header 替换 + 流式无缓冲 |
| **AC-3** | `aiproxy` CLI 提供 `keygen` / `init` / `reload` / `status` / `test` |
| **AC-4** | `python/nanocode` 内嵌，使用 `uv run` 单脚本验证端到端流式对话 |
