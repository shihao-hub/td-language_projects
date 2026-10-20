# Task List: 知识库时序防腐与生命周期治理引擎 (kbman)

- [x] 1. 创建任务三件套 tasks.md 并初始化 Go 模块
  - Files: `docs/specs/06-kb-temporal-governance/tasks.md`, `go_projects/kbman/go.mod`
  - Verify: Go 模块初始化成功，依赖 `gopkg.in/yaml.v3` 安装就绪
  - Ref: AC-1

- [x] 2. 实现核心数据模型与 YAML Frontmatter 双向解析器
  - Files: `internal/metadata/metadata.go`, `internal/parser/frontmatter.go`
  - Verify: 单元测试覆盖带旧 frontmatter / 新 frontmatter 的 Markdown 解析与无损还原
  - Ref: AC-1

- [x] 3. 实现历史笔记批量升级服务 (Migrator)
  - Files: `internal/service/migrator.go`
  - Verify: 五段式文件名解析准确，生成标准的时序元数据并无损保留正文
  - Ref: AC-1

- [x] 4. 实现防御性前置拦截校验与状态报告 (Check/Audit)
  - Files: `internal/service/governance.go`, `cmd/kbman/main.go`
  - Verify: `kbman check <id>` 准确根据 verified / suspect / deprecated 状态返回退出码与建议
  - Ref: AC-2

- [x] 5. 实现执行期自愈回写与踩坑日志追加 (Report/Touch)
  - Files: `cmd/kbman/main.go`
  - Verify: `kbman report <id> --status suspect --append "..."` 原子回写成功
  - Ref: AC-3

- [x] 6. 编译 kbman.exe 并对 80 篇旧笔记执行全量批量升级
  - Files: `go_projects/kbman/kbman.exe`, `kb-engineering-notes/*.md`
  - Verify: 80 篇旧笔记 100% 具备标准时序防腐元数据，Git diff 正文无破坏
  - Ref: AC-1, AC-2, AC-3
- [x] 7. 复盘修正：渲染器重构为最小侵入模式并补齐 CLI 契约
  - Files: `internal/parser/frontmatter.go`, `internal/service/io.go`, `internal/contract/schema.go`, `cmd/kbman/main.go`
  - Verify: 首轮 `yaml.Marshal` 全量重排会打乱 79 篇笔记字段顺序，已回滚并改为「只追加缺失字段」；全量升级 diff 仅 921 行新增、0 正文改动（两处 BOM 顺带净化）
  - Verify: 原子写（temp + rename）、`--json` 标准包络、`--schema` 离线契约、`kbman schema` 目录均已落地
  - Ref: AC-1, AC-3
