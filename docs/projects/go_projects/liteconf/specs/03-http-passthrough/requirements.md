# Requirements Document

## Introduction

liteconf（`go_projects/liteconf`）当前形态为"轻量配置中心"：server（`liteconf-server.exe`，纯 flag 风格，非 CLI）+ Go client SDK，HTTP API 调试依赖手敲 curl。本功能为其新增**独立 CLI 入口** `liteconf.exe`（server 二进制一行不动），首个子命令 `http [args...]` 把全部参数原样透传给 curlie（Go 生态的 HTTPie 等价物：HTTPie 语法 + curl 引擎），作为配置中心 HTTP API 的轻量调试入口。

遵循《CLI 工具开发标准》v1.0 的相关条款：

- 透传命令不强制 JSON 包络（标准 4.1），`http` 子命令为纯透传；
- 不提供 MCP 入口：纯终端透传、无自身数据面与状态，无合理 MCP 操作，按标准 0.1 节例外处理并在项目文档记录；
- 必须提供 `--help` / `--version` / `schema`（标准 0.1）；无 MCP 的独立 CLI 的 `schema` 导出自身命令契约并声明 `interface: "cli"`（标准 5.5）。

**前置依赖（环境）**：目标机器需安装 curlie：`go install github.com/rs/curlie@latest`（本机 `C:\Users\<user>\go\bin` 已在 PATH，安装后即可解析）。

## Requirements

### Requirement 1
curlie 依赖就绪（环境前提）

#### Scenario 1
- **WHEN** 在 PATH 中解析 `curlie` 可执行文件
- **THE SYSTEM SHALL** 能够成功找到（经 `go install github.com/rs/curlie@latest` 安装），且 `curlie --version` 正常输出版本号

### Requirement 2
独立 CLI 入口与自描述能力

liteconf 项目应包含独立 CLI 程序入口（`cmd/liteconf`），构建产出 `liteconf.exe`；`liteconf-server.exe` 的代码、启动参数与行为不受任何影响。

#### Scenario 1
- **WHEN** 用户执行 `liteconf --help`（或 `-h`、`help`、无任何参数）
- **THE SYSTEM SHALL** 向 stdout 输出人读帮助（用法与子命令列表，至少含 `http` 与 `schema`），退出码 0，且不解析 PATH、不启动任何外部程序

#### Scenario 2
- **WHEN** 用户执行 `liteconf --version`（或 `version`）
- **THE SYSTEM SHALL** 输出版本号（与构建注入一致），退出码 0

#### Scenario 3
- **IF** 用户执行了未知子命令（如 `liteconf foo`）
- **THEN THE SYSTEM SHALL** 向 stderr 输出人读错误说明，退出码 2（调用参数错误）

### Requirement 3
`http` 子命令：参数原样透传给 curlie

`liteconf http [args...]` 将 args 原样透传给 PATH 中的 curlie：stdin/stdout/stderr 直通、不经任何 shell 包裹；liteconf 自身不解析、不消费、不改写任何 args（`--help`、`--version`、`--` 之后的参数等全部属于 curlie）。

#### Scenario 1
- **WHEN** 用户执行 `liteconf http <args...>` 且 curlie 存在于 PATH
- **THE SYSTEM SHALL** 以 args 为参数数组启动 curlie 并直通三条标准流；curlie 退出后，THE SYSTEM SHALL 以 curlie 的退出码作为 liteconf 的退出码

#### Scenario 2
- **IF** PATH 中找不到 curlie
- **THEN THE SYSTEM SHALL** 仅向 stderr 输出人读错误（说明未找到 curlie，并附安装命令 `go install github.com/rs/curlie@latest`），退出码 1，stdout 不产生任何输出

#### Scenario 3
- **WHEN** 用户执行 `liteconf http`（不带任何参数）
- **THE SYSTEM SHALL** 原样透传空参数集启动 curlie（由 curlie 自行输出其用法并决定退出码），liteconf 不做前置拦截

### Requirement 4
`schema` 子命令：CLI 契约导出

#### Scenario 1
- **WHEN** 用户执行 `liteconf schema`
- **THE SYSTEM SHALL** 向 stdout 输出一个 JSON 对象，声明 `interface: "cli"`，包含 `http` 子命令的输入/输出契约描述（与帮助信息同源的手工维护目录），退出码 0，且不解析 PATH、不启动任何外部程序

### Requirement 5
构建集成

#### Scenario 1
- **WHEN** 执行项目构建脚本（`scripts/build.ps1`）
- **THE SYSTEM SHALL** 同时产出 `build/liteconf-server.exe` 与 `build/liteconf.exe`，两者版本号注入方式一致

### Requirement 6
MCP 例外与文档记录

#### Scenario 1
- **WHERE** liteconf CLI 仅包含纯终端透传子命令（无自身数据面、状态与记账）
- THE SYSTEM SHALL 不提供 MCP 入口；项目 README 应记录该例外理由与 CLI 用法（安装前提、使用示例、退出码约定），并同步改写现有"定位与边界"一节中"不配套 CLI 与 MCP"的过期例外记录

### Requirement 7
质量验证

#### Scenario 1
- **WHEN** 执行 `go build ./...`、`go vet ./...`、`go test ./...`（在 `go_projects/liteconf` 目录内）
- **THE SYSTEM SHALL** 全部通过；单元测试至少覆盖：未知子命令返回退出码 2、`schema` 输出可解析且含 `interface: "cli"`、curlie 缺失时的错误路径（通过注入可执行文件查找函数模拟）、透传启动编排对参数的原样传递
