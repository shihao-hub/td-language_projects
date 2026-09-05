# Requirements Document — projstat

## Introduction

`language_projects` 总仓通过 git submodules 挂载 4 个语言 monorepo（go_projects / python_projects / rust_projects / typescript_projects），现有 23 个活跃项目；另有 5 个归档项目位于父仓 `.archived/<lang>/` 下。项目状态信息目前散落在各项目自维护的 README.md / TODO.md / NOTES.md / SPEC.md / HANDOFF.md 中，格式不统一，无法一眼回答"这个项目处于什么阶段、什么时候继续做什么、是否读过源码、是否可用、是否测试过"。

projstat 是一个运行于 Windows 的 Go CLI（源码位于 `go_projects/projstat/`），为全部项目提供统一的状态标注与追踪：每个项目目录下一个 `PROJECT.toml` 承载手工标注，命令运行时实时采集 git 元数据，二者合并输出列表 / 详情 / 待办视图。

## Requirements

### REQ-1: 项目发现

projstat SHALL 自动发现全部待标注项目：4 个 `<lang>_projects/` 下的直接子目录（深度 1）与 `.archived/<lang>/` 下的直接子目录（深度 2）；文件与非目录条目不视为项目。

#### Scenario 1.1: 完整发现
- WHEN 在总仓内任一位置运行 projstat 任一命令
- THE SYSTEM SHALL 发现 23 个活跃项目与 5 个归档项目（共 28 个）

#### Scenario 1.2: 未标注项目不遗漏
- WHEN 某项目目录尚无 PROJECT.toml
- THE SYSTEM SHALL 仍将其纳入结果并标记为未标注（stage 显示 "-"）

### REQ-2: 根目录定位

projstat SHALL 从当前工作目录逐级向上自动定位总仓根（同时包含 `.git` 与 `go_projects` 的目录），无需配置；定位失败时 SHALL 以退出码 1 报错并提示可用 `--root` 显式指定。

#### Scenario 2.1: 子目录内运行
- WHEN 在 `python_projects/zedhub` 内运行 projstat
- THE SYSTEM SHALL 自动定位总仓根并正常工作

#### Scenario 2.2: 定位失败
- WHEN 在总仓外（如 `C:\`）运行且未提供 --root
- THE SYSTEM SHALL 以退出码 1 报错，错误信息包含 --root 用法

### REQ-3: 元数据文件 PROJECT.toml

每个项目的手工标注 SHALL 存储于该项目根目录的 `PROJECT.toml`（TOML 格式），字段为：`name`、`lang`、`stage`、`source_read`、`usable`、`tested`、`summary`、`next_action`、`next_due`、`notes`、`updated_at`。三个布尔字段（source_read / usable / tested）省缺 SHALL 表示"未标注"，区别于显式 true/false。

#### Scenario 3.1: 布尔三态
- WHEN PROJECT.toml 中未写 tested 字段
- THE SYSTEM SHALL 显示 tested 为 "-"，而非 false

#### Scenario 3.2: 阶段枚举校验
- WHEN stage 取值不在 idea | learning | wip | mvp | usable | paused | archived | dropped 之内
- THE SYSTEM SHALL 以退出码 1 拒绝并指出合法取值

#### Scenario 3.3: 日期格式校验
- WHEN next_due 不符合 YYYY-MM-DD 格式
- THE SYSTEM SHALL 以退出码 1 拒绝

### REQ-4: init 命令

`projstat init` SHALL 为所有缺 PROJECT.toml 的项目生成骨架文件（name=目录名、lang 按所属子仓推导、其余留空），且幂等；`.archived/` 下项目默认 stage=archived。

#### Scenario 4.1: 幂等
- WHEN 某项目已有 PROJECT.toml 且再次执行 init
- THE SYSTEM SHALL 跳过该目录，不改动现有文件

#### Scenario 4.2: 归档默认阶段
- WHEN init 处理 `.archived/python_projects/lele`
- THE SYSTEM SHALL 生成 stage="archived" 的骨架

### REQ-5: list 命令

`projstat list`（亦为无参数时的默认行为）SHALL 以表格输出项目：name、lang、stage、源码/可用/测试三列标记（✓/✗/-）、最后提交相对时间、next_due（逾期标红）；默认按 name 排序、隐藏归档项目；支持 `--lang`、`--stage` 过滤，`--all` 含归档，`--sort name|commit|due`，`--json`。

#### Scenario 5.1: 默认隐藏归档
- WHEN 运行 projstat list
- THE SYSTEM SHALL 输出 23 行，不含 .archived 项目

#### Scenario 5.2: 组合过滤
- WHEN 运行 projstat list --lang go --stage wip
- THE SYSTEM SHALL 仅输出 lang=go 且 stage=wip 的项目

### REQ-6: show 命令

`projstat show <name>` SHALL 输出单个项目全部手工字段与自动采集详情（最后提交时间、dirty、提交数、存在的 TODO/NOTES/SPEC/HANDOFF.md）。name 按目录名全局唯一解析；歧义或无匹配时 SHALL 以退出码 1 报错，歧义时列出候选项并提示 `lang/name` 形式。

#### Scenario 6.1: 详情输出
- WHEN 运行 projstat show zedhub
- THE SYSTEM SHALL 输出 zedhub 全部字段、git 采集信息与文档文件列表

#### Scenario 6.2: 无匹配
- WHEN 运行 projstat show nosuchproj
- THE SYSTEM SHALL 以退出码 1 报错

### REQ-7: set 命令

`projstat set <name> --<field> <value>` SHALL 更新指定字段并维护 updated_at；目标文件不存在时 SHALL 先创建骨架再更新；布尔 flag SHALL 同时支持 `--usable` 与 `--usable=false` 两种写法；非法取值 SHALL 以退出码 2 报错且不写文件。

#### Scenario 7.1: 更新单字段
- WHEN 运行 projstat set zedhub --stage usable
- THE SYSTEM SHALL 仅改写 stage 与 updated_at，其余字段原样保留

#### Scenario 7.2: 非法值拒绝
- WHEN 运行 projstat set zedhub --due 2026-13-99
- THE SYSTEM SHALL 以退出码 2 报错，PROJECT.toml 内容不变

### REQ-8: next 命令

`projstat next` SHALL 输出所有填有 next_action 的项目，按 next_due 升序排列：逾期置顶且标红，无 due 者最后；`--all` 含归档，支持 `--json`。

#### Scenario 8.1: 逾期优先
- WHEN 存在 next_due 已逾期与未到期的项目
- THE SYSTEM SHALL 逾期项目排在最前并标红

#### Scenario 8.2: 无待办
- WHEN 没有任何项目填写 next_action
- THE SYSTEM SHALL 输出空结果提示且退出码为 0

### REQ-9: git 元数据自动采集

执行 list / show / next 时 projstat SHALL 以并发方式（信号量 8）对每个项目目录运行 `git log -1`、`git status --porcelain`、`git rev-list --count HEAD`，采集最后提交时间、dirty 状态、提交数；采集结果仅存在于本次运行，SHALL NOT 落盘。

#### Scenario 9.1: 归档项目采集
- WHEN 项目位于 .archived（父仓库的子目录）
- THE SYSTEM SHALL 仍能采集到其 git 信息

### REQ-10: git 缺失降级

IF git 不在 PATH 或目录不在任何 git 仓库内 THEN THE SYSTEM SHALL 将该项目 git 字段置空并继续输出，不报错不中断。

### REQ-11: JSON 输出契约

当指定 `--json` 时，projstat SHALL 在 stdout 输出单行 JSON 信封：成功 `{"status":"ok","data":…,"count":n,"elapsed_ms":x}`，失败 `{"status":"error","message":…}`；JSON 输出 SHALL NOT 含 ANSI 颜色码。

#### Scenario 11.1: 成功信封
- WHEN 运行 projstat list --json
- THE SYSTEM SHALL 输出合法 JSON，count=23，elapsed_ms 为非负整数

### REQ-12: 退出码

projstat SHALL 使用退出码：0 = 成功（含空结果）、1 = 运行错误、2 = 用法/参数错误。

### REQ-13: Windows 控制台兼容

projstat SHALL 在启动时于 Windows 平台调用 SetConsoleOutputCP(65001) 保证 UTF-8 中文输出；表格对齐 SHALL 按 CJK 显示宽度计算；当 stdout 为管道/文件（非 TTY）时 SHALL 自动去除 ANSI 颜色码。

### REQ-14: 依赖约束

projstat 的直接依赖 SHALL 仅限 BurntSushi/toml 与 golang.org/x/text；子命令分发 SHALL 采用手写 switch + flag.FlagSet，不引入 cobra 等命令行框架。

### REQ-15: 注释保留策略

projstat 重写 PROJECT.toml 时 SHALL 按固定字段顺序输出并生成组头注释；README 中 SHALL 明示 `set` 重写会丢弃用户手写注释。
