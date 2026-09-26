# Design Document

## Overview

本设计把 typeai 从“单线消息 + 单个 active turn”扩展为“一个 session 内包含多条对话分支的树”。首版只渲染一个区域，通过 Tab 切换分支，不创建第二个进程，也不实现左右双 Pane 或鼠标选区。

分支只保存自己的新增消息，并通过父分支 ID 与 Fork 消息位置解析继承上下文。流式事件携带 branch ID 和 turn ID，确保隐藏分支的响应不会污染当前分支。

## Context

当前实现的关键事实：

- `internal/session/store.go` 的 `Session` 使用 `schema_version: 2` 与线性 `Messages []Message`。
- `internal/tui/model.go` 直接持有单一 `messages`、`active`、`running`、`viewport` 和输入状态。
- `internal/tui/stream.go` 的流式消息目前没有分支身份；事件默认只服务当前唯一回合。
- `internal/tui/view.go` 只渲染一个 transcript、一个输入框和状态栏。
- `Store.Save` 已使用临时文件、`Sync` 与原子替换，分支持久化应复用该边界。

## Goals and Non-Goals

- **Goals**
  - 在一个进程和一个 session 中创建、切换、继续多个对话分支。
  - 让每个分支拥有独立的消息追加、流式状态、取消操作和错误状态。
  - 用共享父历史避免复制完整上下文。
  - 将 session JSON 升级到 schema version 3，并兼容读取 version 2。
  - 在纯键盘终端中通过 Tab、键盘快捷键和命令完成分支操作。

- **Non-Goals**
  - 首版不实现鼠标拖选、右键菜单、选区坐标映射。
  - 首版不实现左右并排双 Pane。
  - 首版不支持从 AI 消息中间字符切断上下文。
  - 首版不改变 LLM API、配置结构、图片传输协议或 CLI 外部契约。

## Detailed Design

### 1. Session 分支模型

- `UPDATED` `internal/session/store.go`
  - **Purpose**：把线性 session 扩展为可持久化的分支树，并保留 version 2 的读取兼容。
  - **Changes**：新增 `Branch` 持久化结构，至少包含 `id`、`parent_id`、`fork_message_index`、`messages`、`created_at`；`Session` 增加 `root_branch_id`、`active_branch_id` 与 `branches`，当前写入版本改为 3。
  - **Complexity**：Medium

建议的 schema version 3 结构：

```json
{
  "schema_version": 3,
  "id": "session-id",
  "model": "model-name",
  "created_at": "time",
  "updated_at": "time",
  "root_branch_id": "main",
  "active_branch_id": "fork-01",
  "branches": [
    {
      "id": "main",
      "parent_id": "",
      "fork_message_index": 0,
      "messages": [],
      "created_at": "time"
    },
    {
      "id": "fork-01",
      "parent_id": "main",
      "fork_message_index": 2,
      "messages": [],
      "created_at": "time"
    }
  ]
}
```

`fork_message_index` 表示父分支对外可见历史中的消息数量，采用半开区间语义：子分支继承父分支 `[0, fork_message_index)`。

schema version 2 读取时，把原 `Messages` 转换为 `main` 分支的本地消息，`root_branch_id` 和 `active_branch_id` 都设为 `main`。写盘时使用 version 3，不再同时写一份重复的顶层线性消息。

### 2. 分支历史解析

- `CREATED` `internal/session/branch.go`
  - **Purpose**：集中处理分支创建、父历史解析、拓扑校验和 branch ID 生成。
  - **Changes**：提供 `CreateBranch`、`ResolveMessages`、`ValidateBranches` 等纯逻辑能力；解析时递归获取父分支历史前缀，再拼接当前分支本地消息。
  - **Complexity**：Medium

核心不变量：

1. 根分支的 `parent_id` 为空，且只能有一个根分支。
2. 非根分支的 `parent_id` 必须存在。
3. `fork_message_index` 不得大于父分支解析后的消息数。
4. 分支 ID 在同一个 session 内唯一。
5. 分支创建后父关系和 Fork 位置不可变；只能追加本地消息。
6. 检测到环、悬空父分支或非法索引时拒绝加载/保存，不猜测修复。

### 3. TUI 分支状态

- `UPDATED` `internal/tui/model.go`
  - **Purpose**：把单一 `messages` 与 `activeTurn` 拆为按 branch ID 索引的运行时状态，同时维持当前 Tab 的渲染投影。
  - **Changes**：增加 branch map、`activeBranchID`、每分支的 messages/active/running/status/cancel 状态；输入框和 viewport 继续作为当前 Tab 的单一渲染资源，切换 Tab 时从目标分支重建 transcript。
  - **Complexity**：High

推荐的运行时结构：

```go
type branchState struct {
    ID          string
    ParentID    string
    ForkAt      int
    Messages    []uiMessage
    Active      *activeTurn
    Running     bool
    Status      string
    OperationErr error
    Cancel      context.CancelFunc
}
```

切换分支时：

1. 保存当前输入框的临时文本到当前分支 UI 状态。
2. 更新 `activeBranchID`。
3. 将目标分支的消息、active turn、状态和输入草稿装载到当前模型。
4. 重新计算 viewport 内容，但不发起网络请求。
5. 更新 `active_branch_id`，在 session 已经落盘后立即原子保存。

### 4. Fork 命令和 Tab 交互

- `UPDATED` `internal/tui/model.go`
  - **Purpose**：提供无鼠标的首版分支创建和切换入口。
  - **Changes**：新增 `/fork`、`/branch <id>`、分支列表/切换命令；新增 `Ctrl+Shift+F` 创建分支；使用 `Ctrl+PageUp` / `Ctrl+PageDown` 循环切换 Tab。
  - **Complexity**：Medium

Fork 行为：

- 只允许从当前分支最近一条已完成 AI 消息之后创建。
- 子分支继承当前分支完整已完成历史，创建后输入框为空。
- 不自动发起请求；用户在新 Tab 输入后才发送。
- AI 正在流式输出时拒绝 Fork，并保留原分支运行状态。
- branch ID 使用稳定的短 ID；显示名称可为 `main`、`fork-01`、`fork-01-01`。

- `UPDATED` `internal/tui/view.go`
  - **Purpose**：渲染 Tab 条和当前分支状态。
  - **Changes**：在 transcript 上方新增 Tab 条，突出当前 branch；状态栏显示当前分支 ID 和运行状态；窄终端仍只渲染一个内容区域。
  - **Complexity**：Medium

### 5. 流式事件路由

- `UPDATED` `internal/tui/stream.go`
  - **Purpose**：让网络流事件携带分支身份。
  - **Changes**：为 `streamDeltaMsg`、`streamResultMsg` 增加 `BranchID` 与 `TurnID`；启动请求时闭包捕获二者；回调只向同一 TUI event loop 投递带身份事件。
  - **Complexity**：Medium

- `UPDATED` `internal/tui/model.go`
  - **Purpose**：按 branch ID 与 turn ID 更新正确分支。
  - **Changes**：`applyDelta`、`finishStream`、取消和错误处理先解析目标分支，再更新对应分支状态；只有目标分支是当前 Tab 时才刷新可见 viewport。
  - **Complexity**：High

- `UPDATED` `internal/tui/render_job.go`
  - **Purpose**：防止 Markdown 缓存和异步渲染结果串到其他分支。
  - **Changes**：渲染 key 增加 branch/turn 身份或等价的内容身份；异步结果应用前校验 generation、branch ID 和 source key。
  - **Complexity**：Medium

### 6. 持久化边界与迁移

- `UPDATED` `internal/session/store.go`
  - **Purpose**：安全保存分支树。
  - **Changes**：复用现有原子写盘；分支创建、成功回答完成、激活分支变更在已存在 session 文件时触发保存；保存失败保留内存状态并显示错误，不覆盖旧文件。
  - **Complexity**：Medium

- `UPDATED` `internal/service/chat.go`
  - **Purpose**：继续让业务层收到一个有序的当前分支请求上下文。
  - **Changes**：不改变 LLM 协议；调用方在发送前解析当前分支历史并传入现有发送接口，避免 service 层持有 TUI 分支状态。
  - **Complexity**：Low

数据流：

```text
Fork command
  -> branch graph validates parent and fork index
  -> TUI creates branchState
  -> activeBranchID changes
  -> session.Store saves schema v3

Send in active tab
  -> ResolveMessages(activeBranchID)
  -> existing Chat.SendWithImages(...)
  -> streamDeltaMsg{BranchID, TurnID}
  -> branchState update
  -> render only when branch is active
  -> completed turn appended and session saved atomically
```

### 7. 错误处理与边界

- Fork 发生在流式中：返回本地状态错误，不取消原请求。
- 当前分支不存在：回退到 `main` 仅限内存初始化阶段；已加载的损坏 session 必须报错而不是静默重建。
- 分支数量过多：首版不设置人为低上限，但 Tab 文本必须截断显示，完整 ID 保留在命令/错误信息中。
- 当前 Tab 切换时后台分支完成：只更新后台 branchState；用户切回时显示已完成内容。
- 保存失败：保留当前内存分支，状态栏显示保存错误；下一次成功回答或显式保存再次尝试。

### Module Collaboration and Data Flow

`session` 负责持久化结构、迁移和分支历史解析；`tui` 负责当前 Tab、输入焦点、分支运行时状态和事件路由；`service.Chat` 只接收解析后的有序请求上下文，不感知分支树；`stream.go` 把网络回调转换为带身份的 Bubble Tea 消息；`view.go` 只投影当前分支与 Tab 状态。

依赖方向必须保持：

```text
session branch model -> tui branch state -> service.Chat request
                                      <- stream events with identity
```

禁止让 `service.Chat` 反向依赖 TUI branch state，也禁止让隐藏分支直接写当前 viewport。

## Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | Fork 命令和 Tab 交互、分支历史解析 |
| AC-2 | 分支历史解析、TUI 分支状态 |
| AC-3 | Tab 交互、`view.go` Tab 条、当前输入投影 |
| AC-4 | 流式事件路由、异步渲染身份校验 |
| AC-5 | schema v3、持久化边界与迁移 |
| AC-6 | schema v2 读取迁移 |
| AC-7 | 错误处理与边界不变量 |
| AC-8 | 当前单分支投影与 service 外部契约保持不变 |

## Design Review Notes

### Findings

- **HIGH：0**
- **MEDIUM：0**
- **NIT：1** —— `Ctrl+Shift+F` 是否被终端完整传递需要在实现阶段用实际 Windows Terminal 验证；同时保留 `/fork` 作为确定性回退入口。

### 已验证假设

- 当前 session 写盘已经具备临时文件、`Sync`、权限设置和原子替换能力，可以复用。
- 当前 TUI 的流式更新通过 Bubble Tea 消息进入单一 event loop，增加身份字段可以保持同一并发模型。
- 当前 LLM 发送接口接收有序消息/输入，不需要改变外部协议即可由调用方提供分支解析后的上下文。

### 未验证或错误假设

- 尚未验证 `Ctrl+Shift+F` 在目标 Windows Terminal 配置中的具体 KeyMsg 表达；`/fork` 必须始终保留。
- 尚未实现鼠标选区，因此“选中文字作为引用草稿”的行为保留到后续需求，不作为本首版验收项。