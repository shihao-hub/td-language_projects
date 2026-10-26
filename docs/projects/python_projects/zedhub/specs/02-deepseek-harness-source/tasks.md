# 任务清单

- [ ] 1. 将 `zstandard` 提升为运行时依赖并更新锁文件
  - Files: `pyproject.toml`, `uv.lock`
  - 实现细节：在 `[project].dependencies` 加入 `"zstandard>=0.22"`；从
    `[dependency-groups].dev` 移除同名项；执行 `uv lock` 刷新 `uv.lock`。
  - Verify: `uv sync --locked` 成功，`uv run python -c "import zstandard; print(zstandard.__version__)"` 输出版本号。
  - Ref: AC-3, AC-4, AC-6

- [ ] 2. 在 `agent_paths.py` 增加 DSH 数据根解析
  - Files: `src/zedhub/core/agent_paths.py`
  - 实现细节：新增 `dsh_root(home: Path | None = None) -> Path`——显式 `home` 时返回
    `home/".dsh"`（忽略环境变量），否则 `DSH_DATA` 优先、回退 `Path.home()/".dsh"`；
    `_DATA_ROOT_NAMES` 增加 `"deepseek-harness": ".dsh"`；`agent_data_root` 对
    `deepseek-harness` 委托 `dsh_root(home)`。不修改 `FILE_SOURCES` /
    `SOURCE_AGENT_IDS` / `locate_session_files`。
  - Verify: `uv run python -c "from pathlib import Path; from zedhub.core.agent_paths import dsh_root; print(dsh_root(Path('C:/tmp')))"` 输出 `C:\tmp\.dsh`。
  - Ref: AC-1, AC-2

- [ ] 3. 实现 DSH 解析层
  - Files: `src/zedhub/core/deepseek_harness.py`
  - 实现细节：按设计实现 `DSH_SESSION_FILENAME` / `HEAD_LINE_LIMIT=400` /
    `TITLE_MAX=80`、`DshSessionMeta`、`iter_session_files`、
    `load_archived_ids`、`scan_session`、`extract_dsh_messages`、`title_fallbacks`。
    解析要点：zstd `stream_reader` + `TextIOWrapper` 逐行；首行 `type=session` 取
    `id/createdAt/cwd`；`session/title` 命中即 break；`user/message` 记录首条文本兜底；
    正文只收 `type=text`，丢弃 `reasoning`；所有异常按单文件吞掉并 warning。
  - Verify: `uv run pytest tests/test_deepseek_harness_source.py -q -k "scan or extract"` 通过（任务 8 提供用例）。
  - Ref: AC-3, AC-4

- [ ] 4. 实现 `DeepseekHarnessSource` 适配器
  - Files: `src/zedhub/core/sources/deepseek_source.py`
  - 实现细节：继承 `AgentSource`；`info` 声明
    `capabilities=[SESSIONS, CONTENT, DISCOVERY]`、`display_name="DeepSeek Harness"`；
    元数据缓存 `dict[Path, tuple[int, int, DshSessionMeta]]`（mtime_ns + size）与
    `workspace.json` 同样缓存；`list_sessions` 实现 project/agent/archived/limit 与
    updated 倒序；`get_session` 未命中抛 `NotFoundError`；`get_content` 调用
    `extract_dsh_messages`。
  - Verify: `uv run python -c "from pathlib import Path; from zedhub.core.sources.deepseek_source import DeepseekHarnessSource; s=DeepseekHarnessSource(); print(s.info.source_id, s.info.availability)"` 输出 `deepseek-harness` 与可用性。
  - Ref: AC-1, AC-2, AC-3, AC-4

- [ ] 5. 注册源与别名
  - Files: `src/zedhub/core/sources/__init__.py`, `src/zedhub/core/sources/base.py`
  - 实现细节：`SOURCES["deepseek-harness"] = DeepseekHarnessSource()` 并导出；
    `SOURCE_ALIASES["dsh"] = "deepseek-harness"`。
  - Verify: `uv run python -c "from zedhub.core.sources import get_source, list_source_infos; print(get_source('dsh').info.source_id); print([i.source_id for i in list_source_infos()])"` 输出含 `deepseek-harness`。
  - Ref: AC-1, AC-5

- [ ] 6. Web 检索页适配 DSH
  - Files: `src/zedhub/webui/app.js`
  - 实现细节：新增 `SOURCE_LABELS` 与 `hitKindLabel(hit)`；`openHit` 类型行改用该函数；
    `agentSource` 推断追加 `deepseek-harness`；`hasContentSupport` 加入
    `"deepseek-harness"`；「查看轨迹」按钮在 `agentSource === "deepseek-harness"` 时
    不渲染。不改 HTML/CSS。
  - Verify: `uv run zedhub serve` 后打开 `/ui`，搜索命中 DSH 时详情面板文案正确、可加载正文、无轨迹按钮（开发构建需先起 daemon）。
  - Ref: AC-7

- [ ] 7. 更新契约、CLI 帮助与项目文档
  - Files: `src/zedhub/contract.py`, `src/zedhub/cli.py`, `README.md`, `docs/projects/python_projects/zedhub/zedhub 对接协议.md`
  - 实现细节：`sessions list/show/content` 的 `--source` help 补
    `deepseek-harness`；`sessions` 摘要补该源；trajectory 摘要注明
    `deepseek-harness` 不支持；README「数据源边界」增加只读源说明与示例
    `uv run zedhub sessions list --source deepseek-harness`；协议文档数据源清单同步。
  - Verify: `uv run zedhub schema` 正常输出且摘要含 `deepseek-harness`（离线命令，无需 daemon）。
  - Ref: AC-1, AC-8

- [ ] 8. 补充 DSH 源测试
  - Files: `tests/test_deepseek_harness_source.py`
  - 实现细节：用 `tmp_path` 构造 `<root>/sessions/--proj--/<sid>/session.v4.jsonl.zstd`
    （`zstandard.ZstdCompressor` 压缩 JSONL）与 `storages/workspace.json`；覆盖：
    正常元数据与标题、title 缺失回退首条 user、archived 命中、`project`/`archived`
    过滤与排序、正文只含 text、损坏文件跳过、数据根缺失返回空、`dsh` 别名解析、
    `export/link` 能力不存在。直接实例化源，不依赖全局注册表单例缓存。
  - Verify: `uv run pytest tests/test_deepseek_harness_source.py -q` 全通过；`uv run pytest -q` 无回归。
  - Ref: AC-1, AC-2, AC-3, AC-4, AC-5, AC-8
  - [test]
