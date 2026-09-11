# clictl 使用指南

> 项目位置：`go_projects/clictl`（子仓内）。本文为父仓镜像文档，与项目内 `README.md` 保持同步。
> CLI + JSON 输出的通用实现模式（供其他 CLI 项目参考）：见同目录 `cli-json-pattern.md`。

## 定位

Windows 单文件 CLI 工具注册器/启动器：注册任意 exe，`clictl run <名>` 透传启动，启动过程被接管并记录。所有管理命令**永远输出 JSON**，存储用 SQLite（`%AppData%\clictl\clictl.db`）。

## 快速上手

```powershell
# 构建（产出单文件 clictl.exe，版本号注入）
cd go_projects/clictl
./scripts/build.ps1 -Version 1.0.0

# 注册（name 默认=文件名去 .exe 小写化）
clictl add "D:\Program Files\Go\bin\go.exe" --desc "Go toolchain" --meta '{\"source\":\"go\",\"tags\":[\"dev\"]}'

# 查看全部（launch_count 降序），--pretty 缩进输出
clictl list --pretty

# 透传启动：与直接执行 go version 完全一致，退出码直通
clictl run go version

# 详情：最近 10 条启动 + 累计耗时
clictl info go

# 更新/清空 meta
clictl set go --meta '{\"tags\":[\"cli\"]}'
clictl set go --meta '{}'

# 删除注册（级联删其 launches）
clictl rm go
```

## JSON 包络

- 成功：`{"ok":true,"data":...}`
- 失败：`{"ok":false,"error":{"code":"...","message":"..."}}`
- 管理命令错误走 stdout；`run` 的前置错误（未注册/文件失效）走 **stderr**，保证 `run` 的 stdout 只属于子进程

常用错误码：`conflict`（name/path 重复）、`not_found`、`meta_unknown_key`、`meta_invalid`、`meta_too_large`、`not_exe`（v1 仅支持 .exe）、`file_not_found`、`db_error`。

## 退出码约定

- 管理命令：0 成功 / 1 失败
- `clictl run`：透传子进程退出码；未注册/文件失效 = 127
- `help` / `-h` / `--help` / 无参数：输出帮助（JSON），exit 0；子命令级 `-h`（如 `clictl add -h`）同样输出帮助

## meta 白名单

`--meta` 仅允许 `source`（string ≤64B）与 `tags`（[]string ≤8 项、每项 ≤32B、去重小写存储），白名单外 key 直接拒绝；序列化后 ≤ 4KB 硬限。

## 启动记账

每次 `run` 落一条 launches 记录（started_at / duration_ms / exit_code）。父进程吞掉 Ctrl+C，同控制台的子进程照常退出，父进程回写记录后再退——异常终止也有完整记录（duration_ms 为 NULL 表示未正常结束）。

## status 机制

落库 `status` 记录"上次校验结论"；list/info/run 触碰时一律现场 `os.Stat` 刷新并回写，JSON 输出的 status 永远是实时结论，`list --status invalid` 可过滤出失效条目。

## 二期规划

`scan` 批量收编、`.cmd/.bat/.ps1` shim、`clictl rpc` JSON-RPC 模式（stdin NDJSON，GUI/AI 客户端接入）、标签体系、全局统计。详见项目内 `PLAN.md`。
