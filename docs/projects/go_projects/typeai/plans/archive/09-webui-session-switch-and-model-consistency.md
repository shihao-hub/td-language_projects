# 方案实施计划：修复 WebUI 会话切换消失与模型显示不一致问题

> 计划编号：56
> 关联问题：点击左侧历史会话后条目从侧边栏消失、会话模型显示仍为历史旧模型（glm-5.3-flash）而与当前配置（deepseek-v4.1-flash）割裂

---

## 目标描述

用户反馈在 TypeAI 桌面版（WebUI）中遇到两个异常现象：
1. **点击左侧会话后条目“不知道跳哪里去了”**：点击侧边栏的某条历史会话后，该条目没有保持在列表中并高亮，反而直接从左侧列表中消失蒸发，造成“会话不见了”的严重困惑。
2. **会话内的模型显示仍为 glm-flash（为什么？）**：在全局配置已切换为 `deepseek-v4.1-flash` 的情况下，左侧历史会话摘要以及恢复历史会话后右上角显示的依然是 `glm-5.3-flash`，且底层发送请求与顶栏显示的模型名称脱节。

本次变更目标：
- 恢复 WebUI 侧边栏标准会话列表交互：**完整列出所有历史会话（包含当前会话）**，当前激活的会话应用 `.session-item.active` 高亮标记，切换后条目依然留在列表中，不发生跳跃消失。
- 解决会话恢复后的模型一致性问题：恢复历史会话时，明确当前对话所用的实际模型，使得界面展示、会话元数据与底层实际发起 LLM 调用的 Client 保持绝对一致。

---

## 需要用户审阅

> [!IMPORTANT]
> **设计决策：恢复历史会话后的模型归属逻辑**
> - **现状**：
>   - 历史会话文件（如 `20261009-221107-6c7503d4.json`）在落盘保存时固化了当时的 `"model": "glm-5.3-flash"`。
>   - 当用户在侧边栏点击恢复该会话时，后端执行 `c.session = *loadedSess`，直接将 `c.session.Model` 恢复为旧的 `glm-5.3-flash`。
>   - 但底层的 `c.client` 实际使用的是当前配置文件 `config.json` 中的新模型（如 `deepseek-v4.1-flash`）！这就形成了**“界面显示 glm-5.3-flash，后台真正请求 deepseek-v4.1-flash”**的虚假陈述。
> - **建议策略**：
>   1. 历史摘要中：保留显示该会话最近保存时的历史模型标记（让用户知道过去的记录）。
>   2. 恢复激活到当前窗口后：将当前工作会话的模型动态对齐为当前客户端配置的模型（即 `c.session.Model = c.client.Model`），确保右上角及后续发送消息时展示的模型名与底层实际发起请求的模型严格一致；并在用户产生新对话落盘时，更新保存最新的模型信息。

> [!WARNING]
> **TUI 与 WebUI 接口语义解耦**
> - 原有 `internal/service/chat.go` 的 `SessionSummaries()` 专门针对 TUI `/resume` 弹窗过滤了 `currentID`（避免在命令行弹窗里选自己）。
> - 本次重构将后端底层能力拆分或扩展：
>   - 提供全量列表能力 `ListAllSessions()` / 支持保留 `currentID`；
>   - WebUI 接口 `/api/sessions` 永远返回包含当前会话的全量列表，并在前端将当前会话高亮；
>   - TUI 保持原有“过滤当前会话”的行为不变。

---

## 待澄清问题

无阻塞性问题。两个缺陷的根因代码与复现路径均已在真实运行环境（Dev 通道、进程 PID 46832）中定位并验证完毕。

---

## 变更方案

### 1. [service] 扩展会话摘要接口，支持全量查询与模型对齐
#### [MODIFY] `internal/service/chat.go`
- 在 `Resume(sessionID string)` 中，加载老会话后，将 `c.session.Model` 同步为当前激活的配置模型 `c.client.Model`（或在保留历史的同时更新激活态模型），避免前后端脱节。
- 增加 `AllSessionSummaries()` 方法（返回包含 `currentID` 的全量摘要列表），供 WebUI 使用；保留 `SessionSummaries()` 供 TUI 兼容。

```go
// AllSessionSummaries 返回包含当前会话在内的全量持久化会话摘要，按更新时间降序排列。
func (c *Chat) AllSessionSummaries() ([]session.SessionSummary, error) {
	return session.ListSessions(c.dataDir)
}

// Resume 根据 session ID 恢复会话，替换 Store 和 session 状态。
func (c *Chat) Resume(sessionID string) (*session.Session, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	newStore, loadedSess, err := session.LoadByID(c.dataDir, sessionID)
	if err != nil {
		return nil, coded("bad_args", err.Error())
	}

	c.store = newStore
	c.session = *loadedSess
	// 将当前会话的模型同步为当前客户端正在生效的模型，保证界面显示与实际请求一致
	if c.client != nil && c.client.Model != "" {
		c.session.Model = c.client.Model
	}
	c.hasSaved = true
	c.imageMu.Lock()
	c.imageCache = make(map[imageCacheKey]Image)
	c.imageMu.Unlock()
	return &c.session, nil
}
```

---

### 2. [api] `/api/sessions` 切换为全量列表
#### [MODIFY] `internal/api/server.go`
- 将 `handleListSessions` 中调用的 `chat.SessionSummaries()` 改为 `chat.AllSessionSummaries()`。

```go
func (s *Server) handleListSessions(w http.ResponseWriter, r *http.Request) {
	chat, _, _ := s.snapshot()
	items, err := chat.AllSessionSummaries()
	if err != nil {
		writeOperationError(w, err)
		return
	}
	// ... 格式化返回
}
```

---

### 3. [web] 前端会话列表渲染：支持当前会话高亮及避免跳动
#### [MODIFY] `internal/web/static/app.js`
- 在 `loadSessions()` 渲染每个按钮时，判断 `item.id === state.data.session.id`：
  - 若为当前会话，添加 `button.classList.add("active")`（对应已有 CSS `.session-item.active`）；
  - 点击事件：若点击的本身就是当前会话，则直接聚焦输入框，不做无谓的重新请求；
  - 切换会话时，由于当前会话依然在列表中（仅高亮状态改变），左侧列表条目保持稳定，再也不会“不知道跳哪里去了”。

```javascript
async function loadSessions() {
  try {
    const data = await api("/api/sessions");
    els.sessionList.innerHTML = "";
    const items = (data && data.items) || [];
    const currentSessionID = state.data && state.data.session ? state.data.session.id : "";
    if (!items.length) {
      const note = document.createElement("div");
      note.className = "empty-note";
      note.textContent = "暂无其他历史会话";
      els.sessionList.append(note);
      return;
    }
    for (const item of items) {
      const button = document.createElement("button");
      button.className = "session-item";
      if (item.id === currentSessionID) {
        button.classList.add("active");
      }
      const title = document.createElement("div");
      title.className = "session-title";
      title.textContent = item.first_user || item.id;
      const meta = document.createElement("div");
      meta.className = "session-meta";
      const when = new Date(item.updated_at).toLocaleString();
      meta.textContent = `${when} · ${item.message_count} 条 · ${item.model}`;
      button.append(title, meta);
      button.title = item.id === currentSessionID ? `当前会话 ${item.id}` : `恢复会话 ${item.id}`;
      button.addEventListener("click", () => {
        if (item.id === currentSessionID) {
          els.input.focus();
          return;
        }
        resumeSession(item.id);
      });
      els.sessionList.append(button);
    }
  } catch (error) {
    showError(error.message);
  }
}
```

---

## 验证方案

### 自动化测试
运行相关单元测试，确保无回归故障：
```powershell
go test ./internal/service/... -v
go test ./internal/api/... -v
go test ./internal/session/... -v
```

### 人工验证
1. 打开 WebUI（Dev 通道）。
2. 查看左侧会话列表：
   - 验证**当前会话**在左侧列表中正常显示，并带有激活高亮背景（`.active`）；
   - 验证其他历史会话也一并陈列，数量和顺序完整。
3. 点击左侧列表中任意一条历史会话：
   - 验证该条目**不会消失**，而是高亮变为它；
   - 右侧主视图平滑切换出该会话的消息记录与分支；
   - 顶部元信息 `${model} · ${id} · [branch]` 显示当前生效的真实模型（`deepseek-v4.1-flash`），不再显示老模型的脱节名称。
4. 发送一条新测试消息：
   - 验证消息生成正常，且落盘保存后模型与当前全局配置一致。
