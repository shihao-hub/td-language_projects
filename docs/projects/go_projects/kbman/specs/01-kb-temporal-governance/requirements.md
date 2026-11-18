# Requirements Document: 知识库时序防腐与生命周期治理引擎 (kbman)

## Summary
构建一个用 Go 语言编写的高性能轻量 CLI/库程序 `kbman`（位于 `go_projects/kbman`），用于对 `kb-engineering-notes`（及类似知识库）实现工业级的时序元数据防腐治理。涵盖两大核心能力：
1. **自动升级与元数据回填**：扫描既有 80 篇旧格式知识库笔记（仅有 name/description），安全平滑注入标准的时序防腐 YAML Frontmatter（id, status: verified, created, last_verified, falsification_signals 等），无损保留正文与 BOM 规范；
2. **检索期防御性拦截与执行期自愈回写闭环**：
   - 提供 `kbman check <id|file>`：在 AI 执行某 SOP 前快速校验状态，若为 `deprecated` 或超期立即告警防御；
   - 提供 `kbman report <id> --status <suspect|deprecated|verified> [--reason "..."] [--append-log "..."]`：执行期若被工具报错证伪，一键原子回写 Frontmatter 与追加排障日志，形成自愈闭环。

## Functional Requirements
- **FR-1 [历史文件平滑升级 (Migrate)]**：
  - 读取五段式文件名中的 `<id>`, `<domain>`, `<scope>`, `<type>`, `<slug>`；
  - 解析旧 frontmatter，在保持原有 description 关键词的前提下，注入结构化时序元数据；
  - 默认状态设为 `verified`，时间戳从文件 git log 或文件系统自动推导，生成标准无 BOM UTF-8 文件。
- **FR-2 [前置检索防御拦截 (Check/Inspect)]**：
  - 命令 `kbman check <id>` 输出标准 JSON/Text 状态报告；
  - 若 `status == deprecated`，明确返回不可执行警示并指明 `superseded_by`。
- **FR-3 [执行期自愈回写 (Update/Rectify)]**：
  - 命令 `kbman update <id> --status <status> [--reason <reason>]` 快速原子改写 Frontmatter；
  - 命令 `kbman append <id> --log <log-text>` 在文档末尾追加当前会话的踩坑补充。
- **FR-4 [全量审计与健康度体检 (Audit/Lint)]**：
  - 校验知识库所有文件的 YAML 合规性、ID 单调递增与死链检查；
  - 统计过期未验证条目（如超过 180 天未验证）。

## Non-Functional Requirements
- **NFR-1 [零外部依赖与单文件二进制]**：纯 Go 标准库与轻量依赖，Windows 下一键编译生成 `kbman.exe`。
- **NFR-2 [无损幂等性]**：批量迁移与回写操作必须具备严格的幂等性，严禁破坏正文 Markdown 语法与代码块。

## Acceptance Criteria
### AC-1: 历史文件 100% 格式无损升级
- **WHEN** 运行 `kbman migrate --dir "C:\Users\29580\.gemini\config\skills\kb-engineering-notes"`；
- **THEN** 现存所有 80 篇 `.md` 全部升级为标准时序元数据，Git diff 正确，正文无损。

### AC-2: 防御性拦截判定
- **WHEN** 对标记为 `deprecated` 的条目执行 `kbman check <id>`；
- **THEN** 退出码非 0 或输出拦截告警，明确提示替代方案。

### AC-3: 自愈回写原子操作
- **WHEN** 运行 `kbman update 002 --status suspect --reason "Git 2.45 下报错行为变更"`；
- **THEN** 002 号条目的 Frontmatter 中 `status` 变为 `suspect`，更新时间自动刷新。