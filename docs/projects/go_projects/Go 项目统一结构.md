# Go 项目统一结构

> 状态：现行结构入口。新建 Go 项目、增加 GUI、调整入口或构建方式前先读本文；存量项目按本次任务范围维护，不自动迁移。
> 本文路径以父仓 `language_projects` 为根；职责约定集中于此，CLI 契约与桌面实施细节按下表加载。

## 先确定任务，再读对应材料

| 任务 | 阅读路径与边界 |
|---|---|
| 新 CLI、修改 CLI/MCP 契约 | 本文 → [CLI 工具开发标准](<CLI 工具开发标准.md>)；纯 CLI 不引入 GUI |
| 新 GUI、修改桌面入口/构建 | 本文 → [双通道技能入口](../../../.agents/skills/sh-user-skills/sh-desktop-dual-channel/README.md) 的 Go 分支 → [Go SOP](../../../.agents/skills/sh-user-skills/sh-desktop-dual-channel/references/go-wails.md)；涉及 CLI 契约再读 CLI 标准 |
| 已有 Wails v2 故障 | 先核对目标项目依赖，再读 [114：存量 v2 排障](../../../.agents/skills/kb-engineering-notes/114_dev_wails_fix_WailsV2托盘图标与退出拦截.md)；修复不自动升级框架 |
| 存量局部修改 | 先读项目实现与 README，只加载本次涉及的标准；架构迁移另行确定范围 |

读取桌面参考文件是仓库规定的前置阅读，不依赖 skill 自动触发，也无需用户另行点名命令门面。

## 默认结构与职责

- **CLI**：默认人读；管理/查询命令必须支持 `--json`，独立工具提供 `schema` 子命令。导出契约不初始化数据库、网络或业务文件；本约定不新增 `--schema` 别名。MCP 交付政策继续以 CLI 标准为准。
- **GUI**：新项目默认 Wails v3 + 内嵌 HTML/CSS/JS。GUI 与 CLI 各一个 exe，分别承担窗口和终端职责；纯 CLI 工具无需桌面壳。
- **公共核心**：CLI 与 HTTP 适配器复用同一业务用例，入口负责参数、展示与渠道生命周期。WebUI 通过 HTTP 调业务，实时更新按需用 SSE；Wails 仅提供窗口、托盘等宿主能力。
- **同一 WebUI**：GUI 和 CLI `serve` 使用同一个 Handler，`/` 返回内嵌页面，`/api/*` 提供业务 API。普通 CLI 子命令可直接调用公共用例；不默认改造成 daemon 薄客户端。

```text
CLI 子命令 ───────────────────────→ 公共用例 → 持久层（按需）
CLI serve ─┐                            ↑
           ├→ 同一 Handler：WebUI + HTTP API ┘
Wails 壳 ──┘  页面通过 HTTP 调用 API
```

新桌面项目按 Go SOP 的骨架落位；已有结构满足职责边界时保留命名：

```text
cmd/<app>/       GUI main.go（!cli）与 CLI cli.go（cli），分别编译
internal/cli/    CLI 参数与结果适配
internal/service/ 公共业务用例
internal/api/    GUI 与 serve 共用的 Handler
internal/web/    go:embed 的 HTML/CSS/JS
internal/app/    Wails 宿主、版本与运行配置
internal/storage/ 持久层（按需）
scripts/        单一 build.py；图标生成脚本按需
bin/            构建产物，不入库
```

## 桌面交付边界

- **两种入口 × 两种构建形态**：一次构建选择 dev 或 release，产出 CLI、GUI 两份 exe；不是每次构建四份。GUI 使用 Windows GUI 子系统，CLI 使用 Console 子系统。
- **dev/prod 隔离**：产物名、版本、数据目录、单实例标识与图标按 Go SOP 分离；数据只写仓规自有目录。单一 `scripts/build.py` 根据精确 tag + 干净工作区判定 release，默认不把开发产物覆盖到正式名。
- **窗口生命周期**：关窗销毁 WebView，进程留托盘；再次显示重建窗口，恢复位置、尺寸与最大化状态。GUI 日志落盘，开发版禁止注册开机自启。
- **依赖基线**：沿用 Go SOP 已验证的 Wails v3 `v3.0.0-beta.33` 作为参考基线；升级时核对目标版本 API 并验证，不将历史示例当作最新版文档。
- **条件材料**：有持久层才读数据库章节；存在多进程写入才检查并发治理；有数据迁移才设计迁移。示例中的 SQLite、业务命令和只读 GUI 都不是所有项目的强制选型。

## 资料权威与最小验收

现行结构看本文；CLI 契约看 CLI 标准；桌面实施看 Go SOP；知识库用于匹配版本的专项排障。[daemon v2](<CLI 工具开发标准 v2.md>) 是试点方案，采用需有明确需求。归档 `file-sync-native` 等项目和在用项目都只是局部参考，不作为整项目复制模板，也不覆盖当前约定。

交付时按实际改动验证：CLI 的人读/JSON/schema；GUI 与 `serve` 的同一页面/API；双 exe 子系统；关窗释放与重建；dev/prod 隔离。纯 CLI 或局部修复不运行无关桌面验收，存量偏差在项目 README 记录。
