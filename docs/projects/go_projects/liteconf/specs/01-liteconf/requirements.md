# Requirements Document

## Introduction

liteconf 是一个轻量配置中心，定位为 `.env` 的替代品、极简版 Apollo：单实例 Go server 托管各应用各环境的 JSON 配置文件，配套 Go client SDK 供业务项目 import，通过 HTTP 长轮询实现配置热更新，配置变化时以观察者模式回调订阅者。面向内网/本机可信环境，无鉴权，零第三方依赖（仅 Go 标准库）。

## Requirements

### Requirement 1

配置存储模型：server 以 `configs/{app}/{env}.json` 的二级目录结构存储配置，`app`（应用名）与 `env`（环境名）为任意合法名称，配置内容为任意 JSON 对象。每份配置在 server 内存中维护元数据：版本号（单调递增）、内容 hash、最后修改时间。

#### Scenario 1
- **WHEN** server 启动时扫描配置根目录
- **THE SYSTEM SHALL** 加载所有已存在的 `{app}/{env}.json` 并为每份配置初始化版本号与元数据

#### Scenario 2
- **IF** 请求的 `app` 或 `env` 不存在
- **THEN** THE SYSTEM SHALL 返回稳定的业务错误（not_found），不产生任何副作用

### Requirement 2

配置读取 API：server 提供 HTTP 接口按 `app` + `env` 读取配置内容与版本元数据，另提供发现接口列出全部应用、环境及版本，便于调试与浏览。

#### Scenario 1
- **WHEN** 客户端请求 `GET /api/{app}/{env}`
- **THE SYSTEM SHALL** 返回该配置的完整 JSON 内容及版本号元数据

#### Scenario 2
- **WHEN** 客户端请求发现接口
- **THE SYSTEM SHALL** 返回所有应用、环境与当前版本的列表

### Requirement 3

配置写入 API：server 提供HTTP 写入接口，接收 JSON 配置内容，原子写入对应文件（临时文件 + rename），版本号自增，并触发订阅者通知。

#### Scenario 1
- **WHEN** 客户端提交合法 JSON 配置到写入接口
- **THE SYSTEM SHALL** 原子更新对应文件、版本号 +1，并以新版本号响应

#### Scenario 2
- **IF** 提交的内容不是合法 JSON 或 `app`/`env` 名称不合法
- **THEN** THE SYSTEM SHALL 拒绝写入并返回业务错误，文件与版本号保持不变

### Requirement 4

外部文件编辑检测：支持绕过 API 直接编辑 server 上的配置文件。server 周期性轮询（mtime + 内容 hash 对比）检测外部修改。

#### Scenario 1
- **WHEN** server 检测到某配置文件被外部直接修改
- **THE SYSTEM SHALL** 重新加载内容、版本号自增，并按订阅通知流程通知所有订阅者

#### Scenario 2
- **IF** 被外部修改的文件内容不是合法 JSON
- **THEN** THE SYSTEM SHALL 保留旧版本继续提供服务，并记录告警日志

### Requirement 5

长轮询变更通知 API：server 提供长轮询接口，客户端携带已知版本号挂起请求；版本变化立即返回，超时未变化返回当前版本供客户端重新发起。支持多客户端并发订阅同一配置。

#### Scenario 1
- **WHEN** 客户端以版本号 N 发起长轮询且当前版本已大于 N
- **THE SYSTEM SHALL** 立即返回最新配置版本，不挂起

#### Scenario 2
- **WHEN** 挂起期间该配置版本发生变化
- **THE SYSTEM SHALL** 立即响应并返回最新版本与内容

#### Scenario 3
- **IF** 挂起超过超时上限（默认 30 秒）版本仍未变化
- **THEN** THE SYSTEM SHALL 返回当前版本，由客户端重新发起下一轮长轮询

### Requirement 6

SDK 初始化与配置获取：Go client SDK 提供初始化入口（server 地址、app、env），启动时同步拉取一次配置并缓存。

#### Scenario 1
- **WHEN** 业务项目初始化 SDK
- **THE SYSTEM SHALL** 从 server 拉取指定 app/env 的最新配置并缓存，供同步读取

#### Scenario 2
- **IF** 初始化时 server 不可达
- **THEN** THE SYSTEM SHALL 返回明确的错误（含重试建议），不返回空配置伪装成功

### Requirement 7

SDK 变更订阅回调（观察者模式）：SDK 提供 `OnChange` 注册入口，配置版本变化时以新旧配置调用所有已注册回调。

#### Scenario 1
- **WHEN** SDK 通过长轮询感知到配置版本变化
- **THE SYSTEM SHALL** 将新配置更新到缓存，并以旧配置与新配置调用所有已注册回调

#### Scenario 2
- **IF** 某个回调执行 panic 或阻塞
- **THEN** THE SYSTEM SHALL 不影响其他回调的执行与后续变更通知（回调异步派发）

### Requirement 8

SDK 容错：长轮询断开后自动重连（指数退避）；网络故障期间保留最后可用配置继续提供读服务，恢复后自动追上最新版本。

#### Scenario 1
- **IF** 长轮询连接失败或超时
- **THEN** THE SYSTEM SHALL 按退避策略自动重试，期间 `Get` 等读取方法继续返回最后缓存的可用配置

#### Scenario 2
- **WHEN** server 恢复可达
- **THE SYSTEM SHALL** 无需人工干预自动恢复订阅并刷新到最新配置

### Requirement 9

SDK 读取方法：SDK 提供同步读取能力——按键读取（支持点路径）、读取完整配置对象、反序列化到业务 struct。

#### Scenario 1
- **WHEN** 业务代码调用按键读取
- **THE SYSTEM SHALL** 从当前缓存返回对应值，键不存在时返回明确的存在性标识而非静默零值

#### Scenario 2
- **WHEN** 业务代码调用反序列化方法
- **THE SYSTEM SHALL** 将当前缓存配置解码到调用方提供的 struct 并返回错误信息

### Requirement 10

部署定位与数据目录：liteconf 定位内网/本机可信环境，HTTP 明文、无鉴权；server 自身运行数据（日志等）与默认配置根目录遵循仓库数据目录约定。

#### Scenario 1
- **WHEN** server 启动
- **THE SYSTEM SHALL** 从启动参数读取配置根目录（未指定时默认使用 `%APPDATA%\language_projects\liteconf\configs\`，取不到 `APPDATA` 时回退 `~/.language_projects/liteconf/configs/`），自身运行数据写入 `%APPDATA%\language_projects\liteconf\`

#### Scenario 2
- **WHEN** 部署者将 server 暴露到不可信网络
- **THE SYSTEM SHALL** 在文档中明确警告：本工具无鉴权，仅限内网/本机使用

## Assumptions（假设与补全）

以下为基于上下文的假设，若有出入请在评审时指出：

1. **单实例部署**：不做集群、主备、多副本一致性；文件即数据库，无额外持久化存储。
2. **无鉴权**：内网/本机可信环境使用，HTTP 明文传输。
3. **名称约束**：`app`、`env` 限制为 `[a-zA-Z0-9_-]+`，作为路径段防目录穿越。
4. **配置结构**：配置内容为 JSON 对象（顶层 map），支持任意嵌套；不限制业务字段 schema。
5. **发现接口**（REQ-2 Scenario 2）为调试便利补全的需求，非用户明确提出。
6. **版本号语义**：版本号在 server 运行期间单调递增，重启后从文件状态重建（不承诺跨重启连续），长轮询以「版本号不相等」为变化依据。
7. **技术栈**：Go 标准库 `net/http` 实现全部 HTTP 能力，零第三方依赖；文件监听用轮询实现而非 fsnotify。
8. **本仓库新项目**：本次只交付 server（常驻服务）+ SDK（Go 库），不提供 CLI 管理入口与 MCP（按《CLI 工具开发标准》记录例外：本项目形态为服务 + 库，无管理命令面）。
