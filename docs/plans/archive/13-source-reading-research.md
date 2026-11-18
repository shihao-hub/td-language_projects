# 源代码阅读方法调研计划

**问题陈述**：用户希望了解 `python_projects/archery-mcp` 的用途，并通过 `/skill:research` 调研一套可复用、可验证的源代码阅读方法。项目本身是小型 Python 单模块工具，适合作为方法落地示例。

**需求**：
- 只读分析 `python_projects/archery-mcp`，总结其定位、入口、主要数据流、边界与当前状态。
- 以官方文档、协议规范、Git/Python 工具文档及原始研究论文为优先依据，调研如何阅读源代码。
- 将调研结果写入父仓库 `docs/repo/` 下的单个中文 Markdown 文件；不修改业务代码。
- 给出一条适用于本项目的实际阅读路线，而不是只罗列抽象原则。

**背景**：
- 项目主要源码集中在 `archery_sql_mcp/__init__.py`，同时提供 CLI 与 MCP stdio 两种入口。
- `README.md`、`pyproject.toml`、`TODO.md` 已完成初步阅读；项目当前没有测试目录。
- 已确认可使用的主要一手资料包括 Python `ast`/`pdb`/`trace` 文档、Git `log`/`blame`/`bisect` 文档、Python `pyproject.toml` 规范、MCP 基础协议规范，以及 retrieval practice 原始研究论文。

**方案**：
1. 继续只读核对项目入口、配置、认证、查询、CLI/MCP 适配器和 Git 历史，形成项目摘要。
2. 从一手资料提炼源代码阅读中的五个动作：先建立外部契约、再画数据流、按调用链追踪、用工具验证假设、用主动回忆固化理解。
3. 在 `docs/repo/源码阅读方法调研.md` 写入：结论、证据来源、适用于 `archery-mcp` 的分步练习、风险审查清单和参考链接。
4. 写入后只做 Markdown 内容与 Git 状态核对，不运行会接触生产 Archery/Redis 的命令。

**任务分解**
- [x] Task 1: 完成 `archery-mcp` 的只读架构梳理 完成
  - 文件：`python_projects/archery-mcp/README.md`、`pyproject.toml`、`TODO.md`、`archery_sql_mcp/__init__.py`、相关 Git 历史
  - 实现：确认入口、配置优先级、认证与会话恢复、SQL/Redis 只读约束、查询状态机、CLI/MCP 工具映射及当前限制
  - 验证：只读使用 `rg`、Git 查询和文件阅读；预期能从入口一路解释到远程请求和结果返回
  - Demo：用一条 `query` 调用和一条 `get_token` 调用分别画出调用链
- [x] Task 2: 汇总一手资料并形成源代码阅读方法 完成
  - 文件：拟写 `docs/repo/源码阅读方法调研.md`
  - 实现：为每条方法绑定官方文档、协议规范或原始研究来源，并明确“证据支持什么、不能推出什么”
  - 验证：逐条检查参考链接可访问、主张与来源对应；预期文档不依赖无出处的二手总结
  - Demo：读者可按文档步骤分析本项目，而不必从 944 行单文件逐行通读
- [x] Task 3: 写入并核对调研文档 完成
  - 文件：`docs/repo/源码阅读方法调研.md`
  - 实现：写入方法论、项目实操路线、练习题、风险检查和参考资料；不改业务代码
  - 验证：读取文档并检查 `git diff --check`；预期 Markdown 完整、引用清晰、无空白错误
  - Demo：用户可直接打开文档，按“契约 → 数据流 → 调用链 → 分支 → 验证 → 回忆”的顺序阅读 `archery-mcp`

---

**最后更新**：2026-09-23
**作者**：AI
**版本**：v1

## 执行记录

- 已完成 `archery-mcp` 的只读架构梳理。
- 已基于 Python、Git、MCP 官方文档和原始研究论文完成方法调研。
- 已写入 `docs/repo/源码阅读方法调研.md`。
- 已检查 Markdown 相对链接、尾随空白和 `git diff --check`；未调用生产 Archery/Redis。
