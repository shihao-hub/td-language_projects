# Requirements Document — liteconf Web 控制台壳子

## Introduction

liteconf 是轻量配置中心（单实例 Go server + Go client SDK），当前"控制台"即编辑器：管理配置全靠 curl 或直接改文件。本功能为其新增一个 **Web GUI 壳子**（最小控制台）：嵌入现有 server 进程，浏览器访问 `/ui/` 即可完成配置的浏览、编辑与创建。

已与用户确认的决策：

- **技术栈**：Web 控制台，纯 Go 标准库 + `go:embed` 内嵌静态页 + 原生 JS，**保持项目零第三方依赖**
- **集成方式**：嵌入现有 `liteconf-server` 进程（新增 `/ui/` 路由），不新增 cmd 入口
- **功能范围**：发现列表、查看配置、双模式编辑保存（JSON 文本 + 键值表）、新建配置
- **架构约束**：遵循《CLI 工具开发标准》第 2/7 章——GUI 入口只做渲染与交互，业务一律复用既有 `/api/*` 接口，不另写一套存储/校验逻辑

## Requirements

### Requirement 1 — 控制台页面托管

系统提供内嵌的 Web 控制台，静态资源随二进制分发，不依赖外部文件与第三方前端依赖。

#### Scenario 1.1
- **WHEN** 用户以浏览器访问 `GET /ui/` 或 `GET /ui`
- **THE SYSTEM SHALL** 返回控制台首页 HTML（经 `go:embed` 内嵌编译进二进制）

#### Scenario 1.2
- **WHEN** server 启动
- **THE SYSTEM SHALL** 注册 `/ui/` 路由且不引入任何第三方依赖（`go.mod` 的 require 列表保持为空）

### Requirement 2 — 发现列表

控制台首页展示全部配置的概览，数据来自既有 `GET /api/discovery` 接口。

#### Scenario 2.1
- **WHEN** 用户打开控制台首页
- **THE SYSTEM SHALL** 调用 `/api/discovery` 并按应用分组展示全部 app / env / version

#### Scenario 2.2
- **WHEN** 配置仓库为空（无任何 app/env）
- **THE SYSTEM SHALL** 展示明确的空状态提示，不报错

#### Scenario 2.3
- **WHEN** `/api/discovery` 请求失败（如网络异常）
- **THE SYSTEM SHALL** 在页面展示错误提示，不展示误导性的空列表

### Requirement 3 — 查看配置

用户可查看任一 app/env 的完整配置内容。

#### Scenario 3.1
- **WHEN** 用户在列表中选择某个 app/env
- **THE SYSTEM SHALL** 调用 `GET /api/{app}/{env}` 并展示该配置的 JSON 内容与当前版本号

#### Scenario 3.2
- **WHEN** 目标配置返回 `not_found`（如查看期间被删除）
- **THE SYSTEM SHALL** 展示"配置不存在"的错误提示

### Requirement 4 — 双模式编辑保存

用户可在控制台内编辑配置 JSON 并保存，提供 JSON 文本与键值表两种编辑模式。

#### Scenario 4.1 — JSON 文本模式
- **WHEN** 用户切换到 JSON 文本编辑模式
- **THE SYSTEM SHALL** 以可编辑文本形式载入当前配置内容，保存动作由用户显式触发（无自动保存）

#### Scenario 4.2 — 保存前本地校验
- **IF** JSON 文本模式下提交的内容无法通过前端本地 `JSON.parse` 校验
- **THEN THE SYSTEM SHALL** 立即拦截并展示校验错误，不发起保存请求

#### Scenario 4.3 — 一键格式化
- **WHEN** 用户在 JSON 文本模式点击格式化
- **THE SYSTEM SHALL** 对当前文本内容做缩进美化后回填；内容非法时提示且不改动原文

#### Scenario 4.4 — 键值表模式
- **WHEN** 用户切换到键值表编辑模式
- **THE SYSTEM SHALL** 将当前配置对象递归扁平化为点路径（如 `db.host`）的键值表格，叶子值可直接编辑，保存时重组为 JSON 提交

#### Scenario 4.5 — 复杂值整体编辑
- **WHEN** 某键的值为数组或其他非原始类型
- **THE SYSTEM SHALL** 将该值作为整体 JSON 文本片段在表格单元格中编辑，不为数组提供专门编辑器

#### Scenario 4.6 — 模式切换
- **WHEN** 用户在两种编辑模式间切换
- **THE SYSTEM SHALL** 以当前编辑缓冲内容为准互转（JSON ↔ 键值表），不静默丢弃未保存的修改

#### Scenario 4.7 — 保存
- **WHEN** 用户提交保存
- **THE SYSTEM SHALL** 调用 `PUT /api/{app}/{env}` 写入，成功后展示新版本号

#### Scenario 4.8 — 服务端校验失败
- **IF** 服务端返回 `invalid_json`（前端校验被绕过或时序差异）
- **THEN THE SYSTEM SHALL** 展示校验失败提示，且原配置不被覆盖

### Requirement 5 — 新建配置

用户可在控制台直接创建新配置，无需 curl 或手动建文件。

#### Scenario 5.1
- **WHEN** 用户在列表页发起"新建配置"并输入合法的 app/env 与初始 JSON
- **THE SYSTEM SHALL** 调用 `PUT /api/{app}/{env}` 创建配置，成功后新条目出现在列表中并展示其版本号（首版为 1）

#### Scenario 5.2
- **IF** 输入的 app/env 含 `[a-zA-Z0-9_-]` 之外的字符（服务端返回 `invalid_name`）
- **THEN THE SYSTEM SHALL** 展示命名规则提示，不创建

#### Scenario 5.3
- **IF** 目标 app/env 已存在
- **THEN THE SYSTEM SHALL** 在新建确认时向用户明示"该配置已存在，提交将覆盖现有内容"，由用户显式确认后执行

### Requirement 6 — GUI 入口不承载业务规则

GUI 层（静态页与 `/ui/` 路由）只负责资源托管与页面渲染。

#### Scenario 6.1
- **WHEN** 控制台执行读、写、枚举、新建任一业务操作
- **THE SYSTEM SHALL** 通过既有 `/api/*` 接口完成（页面用 fetch 调用），GUI 路由层不新增存储、校验或版本管理等业务实现

#### Scenario 6.2
- **WHEN** 页面发起针对 app/env 的请求
- **THE SYSTEM SHALL** 仅对合法名称（`[a-zA-Z0-9_-]+`）发起请求；服务端既有校验继续兜底，前端本地校验不替代也不削弱服务端校验

### Requirement 7 — 现有行为不受影响

新增 `/ui/` 路由不得改变既有 server 行为。

#### Scenario 7.1
- **WHEN** server 启动后
- **THE SYSTEM SHALL** 保持既有 `/api/discovery`、`GET/PUT /api/{app}/{env}`、`GET /api/watch/{app}/{env}` 的路径、包络与错误码不变

#### Scenario 7.2
- **WHEN** 请求路径为 `/api/*` 下的任意路径
- **THE SYSTEM SHALL** 不被 `/ui/` 路由拦截或改写

### Requirement 8 — 文档一致性

交付后项目文档与实现保持一致。

#### Scenario 8.1
- **WHEN** 本功能交付
- **THE SYSTEM SHALL**（交付物要求）更新子项目 `README.md`：项目结构加入 GUI 部分，"定位与边界"中原"无 Web 控制台"的例外声明改写为现状描述
