# Requirements Document: Anatomy Manager

## Summary
开发一个 Go 语言编写的 `anatomy` 技能产物管理程序（Anatomy Manager）。程序提供 CLI、HTTP API、单文件轻量嵌入式 WebUI，并预留 Wails 桌面端复用层。核心数据基于 SQLite 单文件全量持久化，支持其他 Agent 在执行完 anatomy 生成任务后，将产物（HTML、MJS、PNG、MD 原理文档）无缝移交给本程序归档、索引并支持交互式可视化渲染。

以会话 `6970a9e0-1c38-4f75-bd66-ec8a26d10e6a`（精密限流定标仪 `rate-limiter`）为真实基准用例。

## Functional Requirements
- **FR-1 [产物摄取与归档 Ingest]**：
  - 支持指定生成目录、原理解析文档路径、Agent 会话 ID、标签与标题。
  - 将生成的交互 HTML、Node 脚本（build.mjs）、预览图（PNG）、原理解释（Markdown）作为完整 Project/Artwork 实体入库。
  - 数据模型包含主入口 HTML 判定、日间/夜间版本识别。
- **FR-2 [SQLite 单文件存储]**：
  - 基于纯 Go SQLite 驱动，零 CGO 编译依赖。
  - 所有关联产物文件采用 BLOB 二进制快照存储入库，脱离源码目录后依然具备独立渲染能力。
- **FR-3 [CLI 接口与 Schema 契约]**：
  - 提供 `ingest`, `list`, `get`, `schema`, `export`, `serve` 等命令。
  - 支持 `--json` 机器可读输出；
  - 提供 `schema ingest` 和 `schema artwork` 输出标准 JSON Schema，供上游 Agent 自省工具输入规范。
- **FR-4 [HTTP 服务与流式分发]**：
  - 提供 RESTful API 查阅图谱列表与元数据详情。
  - 提供静态文件流式直接访问（`/api/artworks/:id/files/:filename`），支持 Content-Type 自动嗅探与沙箱 iframe 载入。
- **FR-5 [单文件原生 WebUI 交互]**：
  - 纯原生 HTML/CSS/JS 实现，无任何 npm/webpack 依赖，编译期通过 `//go:embed` 打包进二进制。
  - 左侧展示作品卡片流、缩略图与即时检索；
  - 中间视窗支持安全沙箱 iframe 交互渲染，支持暗黑/明亮渲染一键切换、全屏/新标签页独立预览；
  - 标签页抽屉支持 Markdown 原理与机械映射文档预览、零件构建脚本源码浏览、关联资产清单下载。
- **FR-6 [Wails 桌面端解耦预留]**：
  - WebUI 资产与业务核心解耦，预留 Go struct binding 接口，便于未来无缝升级为 Wails 原生桌面应用。

## Non-Functional Requirements
- **NFR-1 [零 CGO 编译便携性]**：采用纯 Go 驱动，Windows 下直接 `go build` 产出单文件 `.exe`。
- **NFR-2 [离线自治]**：不依赖外部 CDN，不依赖远程网络，WebUI 与 SVG 渲染完全本地离线可用。

## Acceptance Criteria
### AC-1: 产物摄取正确性
- **WHEN** 执行 `anatomymanager ingest --dir <rate-limiter-dir> --doc <doc-path> --name rate-limiter --json`；
- **THEN** 返回包含 `status: success` 的 JSON，归档 6 个核心文件入库，SQLite 生成记录。

### AC-2: CLI 格式自描述
- **WHEN** 执行 `anatomymanager schema ingest`；
- **THEN** 标准输出符合 JSON Schema 规范的参数描述，退出码为 0。

### AC-3: 离线沙箱渲染
- **WHEN** 启动 `anatomymanager serve` 并在浏览器打开 `http://127.0.0.1:8765`；
- **THEN** 正常展示左侧卡片，点击 `rate-limiter` 能在 iframe 中流畅运行 SVG 动效与点击交互。
