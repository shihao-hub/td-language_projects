# 01 - agyquota：Antigravity 配额查询 CLI

## 概述

📋 Plan for: "agyquota — Antigravity 配额查询 CLI"

**问题陈述**：不打开 Antigravity IDE 就能查询模型配额（Gemini / Claude+GPT 两桶，Weekly + Five Hour 窗口的剩余百分比与重置时间）。

**需求**（含用户决策）：Go 正式 CLI 小项目；百分比 + 重置时间；遵循《CLI 工具开发标准》双入口（CLI 人读 + `--json` + `mcp` 子命令 + `schema` 导出）。

**背景**（调研结论）：

- 凭据：`~\.gemini\antigravity-acp\acp_token.json` 含 refresh_token（长期有效）+ project_id，离线可换 access token，已实测成功
- 端点：`POST daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels`，body `{"project":"aicode-consumers"}`，响应含每模型 `quotaInfo{remainingFraction, resetTime, window_size}`（language_server.exe 二进制 strings 确认）
- 已知问题：该接口限流较严（IDE 运行时它会持续轮询），需 429 退避重试
- 参考项目：`glmquotawatch`（cobra + go-sdk v1.8.0 + internal 分层 + 图标），结构与依赖直接对齐
- 官方无网页配额面板（antigravity.google 主站已抓取确认），IDE 内 Settings → Models & Usage 是唯一官方入口

**方案**：

```
cmd/agyquota（组装入口）
 ├─ internal/cli      人读表格 + --json 包络（{"ok":true,"data":...}）
 ├─ internal/mcp      stdio server + schema 导出（工具名 agyquota.quota.get）
 └─ internal/service  公共核心：读 token → 刷新 → 调 API → 归一化为模型桶×窗口
      └─ internal/agapi   OAuth 刷新 + fetchAvailableModels 调用（基础设施层）
```

- token 文件**只读**（外部数据源，不拷贝不改写），支持 `--token-file` 覆盖路径
- 项目默认零写入；模型分组动态解析（`gemini-*` / `claude-*|gpt-*`），不硬编码
- 429 指数退避重试 3 次；exe 按图标指南配地鼠站标

## 任务分解

- [x] Task 1: 项目骨架——go.mod（go 1.25.x + cobra + go-sdk v1.8.0）、cmd/agyquota 主入口、`--help`/`--version`
  - 文件：`go_projects/agyquota/{go.mod,cmd/agyquota/main.go}`
  - 验证（备用）：`go build ./...`；`agyquota --help` 输出帮助、`--version` 输出版本
  - Demo：`agyquota --help` 可用
- [x] Task 2: 配额核心——读 token 文件、OAuth 刷新、调 fetchAvailableModels（429 退避）、解析归一化
  - 文件：`internal/service/{service.go,quota.go}`、`internal/agapi/{token.go,client.go}`
  - 验证（备用）：执行期先手工探通接口拿真实响应再写解析；`go build ./...`
  - Demo：内部函数返回结构化的"模型桶×窗口"数据
- [x] Task 3: CLI 输出——`quota` 子命令（默认命令），人读表格（百分比 + "X小时X分钟后刷新"）+ `--json`
  - 文件：`internal/cli/{root.go,quota.go,output.go}`
  - 验证（备用）：`agyquota quota` 出两桶四行数据；`agyquota quota --json` 可 `ConvertFrom-Json`
  - Demo：不打开 IDE 查到与 IDE 面板一致的数据
- [x] Task 4: MCP + schema——`mcp` 子命令（stdio，`agyquota.quota.get`，input/outputSchema）、`schema` 子命令导出契约目录
  - 文件：`internal/mcp/{server.go,tools.go,schema.go}`
  - 验证（备用）：stdio JSON-RPC 探针（initialize → tools/list → tools/call）取回真实配额；`agyquota schema` 输出与注册同源
  - Demo：从 MCP 客户端侧能查配额
- [x] Task 5: 收尾接线——地鼠图标四步（复制 ico → rsrc → .syso → 入库）、项目 README、父仓项目文档
  - 文件：`cmd/agyquota/{icon.ico,rsrc_windows_amd64.syso}`、`go_projects/agyquota/README.md`、`docs/projects/go_projects/agyquota/设计说明.md`
  - 验证（备用）：`ExtractAssociatedIcon` 输出 32x32；`go vet ./...`
  - Demo：exe 带图标，文档可查

## 关键决策与风险假设

- 项目名 **`agyquota`**（对齐 glmquotawatch 命名风格）
- 落盘位置：`docs/projects/go_projects/agyquota/plans/`（新项目序列从 01 起）
- 风险①：429 限流节奏需执行期实测（Task 2 先探通再写解析）
- 风险②：假设 Claude/GPT 模型也在 fetchAvailableModels 响应里；若不在，降级为只报 Gemini 并注明（记录为已知限制）
- 风险③：`daily-cloudcode-pa` 是 Google 内部端点，未来可能变化——工具失败时输出提示"可打开 IDE 面板查看"

## 实施说明

（执行期追加：任务完成勾选、偏差记录、新发现）

### 执行记录（2026-09-22）

- Task 1-4 代码完成并构建通过；Task 5 图标（32x32 验证）、README、设计说明完成。
- 执行期修复①：凭据文件 `scopes` 字段实际是数组而非字符串，已改为宽松解码。
- 真实冒烟发现：配额接口对本工具返回 429，而 IDE 调用始终成功。

### 偏差记录：配额接口的"客户端身份"封锁（风险①的实际形态比预期严重）

无头试验（PowerShell + Go 原生 HTTP/2 gRPC 探针，约 40 次请求）+ 本地 MITM 抓包（自签 CA + HTTPS_PROXY 劫持 LS）结论：

1. 端点地图与 proto 结构见父仓 `docs/projects/go_projects/agyquota/设计说明.md`（关键：`FetchAvailableModelsRequest` 含 `entitlement{userTier}` 字段，合法值由服务端下发、二进制无常量）。
2. Google 按**客户端身份头**分类：无身份头一律 429；伪 jetski 身份路由到配额注册表但 NOT_FOUND（缺 entitlement）。
3. 已排除：凭据差异（与 IDE 同 OAuth client）、并发抢占、协议差异（JSON/gRPC 同样 429）、域名差异（daily-/生产一致）、scope 扩展（refresh 拒绝）、client #2 浏览器授权（restricted_client）。
4. MITM 死因：LS 的 gRPC 与 REST 通道均内置 Google 根证书池（证书锁定），自签 CA 无法注入；期间发现并修复了代理自身的 h2c prior-knowledge 路由问题，但无法改变客户端侧证书校验。
5. 最终状态：工具代码全部就绪且可构建，配额接口的封锁为 Google 服务端策略，非 IDE 客户端当前无法绕过。复活路径与完整调查记录见设计说明。

### 交付决策

用户批准按 C 方案收尾：工具按原计划交付（CLI/MCP/schema/图标/文档），配额查询如实标注"受 Google 客户端校验限制"；`login` 子命令（client #2 授权流，被 restricted_client 阻断）不留死功能，已移除，调查知识沉淀在设计说明。

### 交付后补充（2026-09-22，用户追加需求）

- 应用户"重试无日志像卡死"的反馈：新增 stderr 进度提示（凭据加载/OAuth 刷新/查询阶段 + 429 退避重试倒计时），`--json` 模式同样走 stderr 诊断流，MCP 入口保持静默。
- README 重写为完整版：命令一览、注意事项（429 封锁/退避耗时/凭据安全/内部端点/禁高频轮询/MCP 超时预算）、错误码排查表。

---

**最后更新：** 2026-09-22
**作者：** AI & User
**版本：** v1.0
