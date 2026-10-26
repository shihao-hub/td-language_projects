# 方案实施计划：TypeAI 会话重命名与标题持久化支持

> 计划编号：57
> 关联需求：TypeAI 桌面端（WebUI）与终端（TUI）会话支持自定义重命名（Title）、持久化存储与多端即时同步呈现

---

## 目标描述

当前 TypeAI 在桌面端 WebUI（`bin/typeai-gui.exe`）与终端 TUI（`bin/typeai-cli.exe`）中，左侧会话列表与恢复弹窗均**仅能使用首条用户消息（`first_user`）或会话 ID 截断作为显示标题**。这在日常使用中存在以下痛点：
1. **标题不可控且语义散乱**：首条消息经常包含测试语句（如截图中的“你是谁？”、“你好”）、超长命令或带有格式噪声的提问，无法反映对话的核心主题与价值；
2. **缺乏会话重命名机制**：分支（Branch）已支持单击切换、双击重命名（`/api/branch/rename`），但会话（Session）层缺少标题属性与改名交互；
3. **多端缺乏统一标题呈现**：持久化 JSON 文件中缺少 `title` 字段，无法对已保存会话进行人工语义归纳与个性化分类。

**本次变更目标**：
- **数据与存储层**：在 `Session` 与 `SessionSummary` 中引入结构化 `title` 字段，保持与旧版本 Schema 完全向后兼容（缺失时优雅回退至 `first_user`）；
- **服务与 API 层**：提供 `Chat.RenameSession` 业务逻辑，并暴露 `POST /api/sessions/rename` 接口，支持重命名当前会话及指定的历史会话；
- **WebUI 交互层**：
  - 侧边栏列表优先渲染自定义 `title`；
  - 提供直观便捷的改名交互（会话项支持双击编辑、悬停快捷编辑图标 ✏️ 或弹出 prompt 确认）；
  - 改名后即时局部重绘，当前会话顶栏/列表状态无缝刷新；
- **终端 TUI 层**：
  - 会话选择弹窗（`/resume`）优先展示自定义 `title`；
  - 增补 `/title <新标题>` 与 `/session rename <新标题>` 交互命令，便于在终端随时调整当前会话标题。

---

## 需要用户审阅

> [!IMPORTANT]
> **会话文件名与 Title 字段的解耦决策**
> - **现状**：TypeAI 会话文件名为时间戳 + 8 位十六进制 ID（如 `20261024-054013-d9f8a4e7.json`），文件系统路径在多个模块中作为只读标识；
> - **决策**：重命名会话**仅修改 JSON 文件内容中的 `title` 字段与 `updated_at` 时间戳，绝不更改物理文件名**。
> - **收益**：避免跨进程文件锁竞争、无需重建文件路径缓存、不影响任何历史备份或导出逻辑。

> [!TIP]
> **WebUI 改名交互体验规范**
> - 与现有的分支 Tab 改名体验保持风格一致：
>   1. **双击**左侧会话项：直接弹出输入对话框（`window.prompt("请输入新会话标题", currentTitle)`）；
>   2. **悬停按钮**：鼠标悬停在会话卡片上时，右侧浮现轻量 ✏️ 按钮，点击同样触发重命名；
>   3. **清空回退**：若用户清空标题提交，系统自动清除自定义 `title`，恢复为默认的“首条用户提问预览”模式。

---

## 待澄清问题

本方案基于对 `typeai` 现有代码库（`internal/session`、`internal/service`、`internal/api`、`internal/web`、`internal/tui`）的完整走读设计，无阻塞性架构疑问。

---

## 变更方案

### 1. [session] 扩展 Session 与 SessionSummary 数据结构及持久化更新

#### [MODIFY] `internal/session/store.go`
- 在 `Session` 结构体中添加 `Title` 字段：
  ```go
  type Session struct {
      SchemaVersion  int       `json:"schema_version"`
      ID             string    `json:"id"`
      Title          string    `json:"title,omitempty"` // 用户自定义会话标题
      Model          string    `json:"model"`
      CreatedAt      time.Time `json:"created_at"`
      UpdatedAt      time.Time `json:"updated_at"`
      RootBranchID   string    `json:"root_branch_id,omitempty"`
      ActiveBranchID string    `json:"active_branch_id,omitempty"`
      Branches       []Branch  `json:"branches,omitempty"`
      Messages       []Message `json:"messages,omitempty"`
  }
  ```
- 在 `SessionSummary` 中同步添加 `Title string`：
  ```go
  type SessionSummary struct {
      ID            string
      Title         string // 会话自定义标题（如未设置则为空）
      Path          string
      Model         string
      CreatedAt     time.Time
      UpdatedAt     time.Time
      FirstUser     string
      LastAssistant string
      MessageCount  int
      Branches      []string
  }
  ```
- 在 `ListSessions(dataDir string)` 中，提取 `sess.Title` 填充到 `SessionSummary.Title`；
- 新增 `UpdateSessionTitle(dataDir, sessionID, newTitle string) (*Session, error)`：
  支持直接加载指定 session 文件，原子更新 `title` 与 `updated_at` 后保存。

---

### 2. [service] 增加业务服务层会话重命名方法

#### [MODIFY] `internal/service/chat.go`
- 新增 `RenameSession(sessionID, newTitle string) error` 方法：
  ```go
  // RenameSession 重命名指定会话（sessionID 为空或为当前会话 ID 时更新当前会话并即时存盘；否则更新指定磁盘会话）
  func (c *Chat) RenameSession(sessionID, newTitle string) error {
      c.mu.Lock()
      defer c.mu.Unlock()

      newTitle = strings.TrimSpace(newTitle)
      if len(newTitle) > 100 {
          return coded("bad_args", "会话标题长度不能超过 100 个字符")
      }

      targetID := strings.TrimSpace(sessionID)
      if targetID == "" || targetID == c.session.ID {
          c.session.Title = newTitle
          c.session.UpdatedAt = time.Now()
          if c.hasSaved {
              if err := c.store.Save(c.session); err != nil {
                  return coded("internal", err.Error())
              }
          }
          return nil
      }

      // 更新非当前会话
      _, err := session.UpdateSessionTitle(c.dataDir, targetID, newTitle)
      if err != nil {
          return coded("bad_args", err.Error())
      }
      return nil
  }
  ```

---

### 3. [api] 暴露 HTTP REST 重命名接口与视图映射

#### [MODIFY] `internal/api/server.go`
- 在 `sessionView` 与 `sessionSummaryView` 结构体中添加 `Title string `json:"title,omitempty"``；
- 在 `handleSessions` 与 `handleState` 中将 `Title` 映射输出给前端；
- 在 `Handler()` 注册新路由：
  ```go
  mux.HandleFunc("POST /api/sessions/rename", s.handleRenameSession)
  ```
- 实现 `handleRenameSession`：
  ```go
  type renameSessionRequest struct {
      ID    string `json:"id"`
      Title string `json:"title"`
  }

  func (s *Server) handleRenameSession(w http.ResponseWriter, r *http.Request) {
      var req renameSessionRequest
      if !decodeJSON(w, r, maxChatBodyBytes, &req) {
          return
      }
      chat, _, streaming := s.snapshot()
      if streaming && (req.ID == "" || req.ID == chat.Session().ID) {
          writeJSONError(w, http.StatusConflict, "busy", "回答生成中，无法修改当前会话标题")
          return
      }
      if err := chat.RenameSession(req.ID, req.Title); err != nil {
          writeOperationError(w, err)
          return
      }
      writeJSON(w, http.StatusOK, map[string]any{
          "session": s.sessionSnapshot(),
      })
  }
  ```

---

### 4. [web] 桌面 WebUI 会话标题展示与重命名交互

#### [MODIFY] `internal/web/static/app.js`
- 会话列表标题渲染优化：
  ```javascript
  const title = document.createElement("div");
  title.className = "session-title";
  // 优先显示用户命名的 title，其次回退至首条提问，最后回退至 ID
  title.textContent = item.title || item.first_user || item.id;
  ```
- 为每个 `.session-item` 增加操作区域与双击事件：
  - `dblclick` 事件：调用 `renameSession(item.id, item.title || item.first_user || "")`；
  - 悬停浮现 `.session-rename-btn` 图标，点击阻止冒泡并触发 `renameSession`；
- 实现 `renameSession(id, currentTitle)`：
  ```javascript
  async function renameSession(id, currentTitle) {
    const next = window.prompt("输入会话新标题（清空则恢复默认提问预览）：", currentTitle);
    if (next === null) return;
    try {
      await api("/api/sessions/rename", {
        method: "POST",
        body: { id, title: next.trim() },
      });
      await loadSessions();
      if (state.data && state.data.session && state.data.session.id === id) {
        await loadState();
      }
    } catch (error) {
      showError(error.message);
    }
  }
  ```

#### [MODIFY] `internal/web/static/style.css`
- 完善 `.session-item` 样式，支持标题与右侧快捷改名图标的 Flex 布局，悬停时优雅淡入 ✏️ 图标。

---

### 5. [tui] 终端 TUI 会话选择弹窗展示与改名命令支持

#### [MODIFY] `internal/tui/session_picker.go`
- 会话选择弹窗渲染：若 `summary.Title != ""`，顶部标题行突出显示自定义会话名称，次行补充首条提问；若未命名则保持原样。

#### [MODIFY] `internal/tui/model.go`
- 在命令解析逻辑中支持：
  - `/title <新标题>`：快速修改当前会话标题；
  - `/session rename <新标题>`：规范命令，修改当前会话标题；
  - 统一调用 `m.chat.RenameSession("", title)` 并反馈修改成功状态。

---

## 验证方案

### 自动化测试
运行全量单元测试与编译检查：
```powershell
# 1. 运行 session 模块单元测试（新增 Title 存取与原子重命名用例）
go test -v ./internal/session -run "TestUpdateSessionTitle|TestSave|TestListSessions"

# 2. 运行 service 与 api 接口测试
go test -v ./internal/service ./internal/api

# 3. 运行 tui 模块测试
go test -v ./internal/tui

# 4. 全量编译检查（dev 通道）
python scripts/build.py -v dev
```

### 人工验证
1. **桌面工作台（WebUI）验证**：
   - 启动 `bin/typeai-gui-dev.exe`；
   - 鼠标双击左侧任意会话条目，在弹出的 prompt 中输入中文标题（如“Instant 时间语义解析”），点击确定；
   - 验证左侧条目标题瞬间更新为新中文，刷新窗口或重启应用后标题依然持久保持；
   - 鼠标点击会话项上的 ✏️ 按钮，清空内容确认，验证自动回退为默认的首条提问文本；
2. **终端 TUI 验证**：
   - 在控制台运行 `bin/typeai-cli-dev.exe`；
   - 输入 `/title 本地知识库排障`，回车验证提示标题修改成功；
   - 退出后重新运行 `bin/typeai-cli-dev.exe` 并输入 `/resume`，在弹出的会话选择器中验证自定义标题正常高亮显示。
