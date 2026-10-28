# clictl 工具多分组支持

## Context

用户询问 clictl 是否支持给工具设置多分组。现状：**不支持**——`group` 藏在 META JSON 内，校验层硬性限定为单字符串（≤32 字节，`internal/store/meta.go:83`），GUI 分组树/标签页按单键分桶。用户确认：**要实现多分组**，展示方式为**工具同时出现在所有所属分组下**（计数重复计入，与 tags 多值行为一致）。

已核实：Go 侧 group 零读取方（全部消费端集中在 app.js 两个函数 + 6 个调用点），读路径高度集中，无需 DB 迁移；MCP 层仅透传 meta，无逻辑改动；tags（`[]string` ≤8 项）是现成的数组校验模板。

## 设计决策

1. **数据形态**：保留 key `group`，校验层接受 `string | []string`，**写入时统一归一化为数组**（`{"group":["dev","ops"]}`）。不做 DB 迁移——旧单字符串行由前端归一函数兼容，用户下次编辑分组时经 ValidateMeta 惰性写回数组。
2. **校验规则**（对齐 tags 模式）：新增常量 `metaGroupMaxCount = 8`；单项 TrimSpace 后 ≤32 字节（复用 `metaGroupMaxLen`）；空项剔除；**大小写敏感精确去重**（保留既有单分组 "Dev" 的语义，不学 tags 的小写化）；去重后 `sort.Strings`；trim 后为空/空数组 → 剔除整个 key（未分组是前端 fallback 概念，不落库）。
3. **前端归一单点**：新增 `groupListOf(tool) → string[]`（容忍 string|array），全部消费点改走它；删除 `groupOf`/`groupKey` 防单值语义回流。
4. **CLI `--group` 便捷 flag**：加到 `add` / `add-cmd` / `edit`（可重复传）；`set` **不加**（整体替换语义下单独给 `--group` 会静默清空 source/tags，易踩坑，走 `set --meta` 传数组即可）。flag 显式给出时覆盖 meta 对象中的 group key。
5. **展示细节**：卡片徽标全部分组平铺；树排序保持全局排序不变仅桶归属变化；不维护孤儿分组名录（与 tags 一致）。

## 改动步骤

### 后端（子仓 go_projects/clictl）

**步骤 1 — meta 校验归一**（`internal/store/meta.go`）
- 常量区（12-18 行）新增 `metaGroupMaxCount = 8`；同步更新 32-35 行的规则注释。
- 新增内部函数 `normalizeGroups([]string) ([]string, error)`：trim → 剔空 → 单项 ≤32B → 精确去重 → >8 报错 → 排序。
- 改写 `case "group"`（83-95 行）：先试 unmarshal 为 string（成功按单元素数组），失败再试 `[]string`，皆败报 `meta_invalid`「group 必须是字符串或字符串数组」；两分支共用 normalizeGroups；空结果 continue（剔 key）。

**步骤 2 — CLI `--group` flag**（`internal/cli/commands.go`）
- `cmdAdd`（~207）、`cmdAddCmd`（~242）、`cmdEdit`（~281）新增 `group stringList` flag（复用 commands.go:231-238 现有类型）并注册进 known 表。
- 新增 helper `mergeGroupFlag(metaRaw, groups) json.RawMessage`：反序列化 meta → 覆盖 group → 重序列化；flag 给空串项表示清除。
- `cmdEdit` 在现有 meta 继承逻辑（~387-392）后追加 `--group` 合成；更新 EmitHelp 与用法串。

**步骤 3 — MCP 文案**（`internal/mcp/tools.go`）
- 116/121/260 三处 jsonschema 描述：group 改为「字符串或字符串数组（≤8 项、单项 ≤32 字节），存为数组」。无逻辑改动。

### GUI 前端（`internal/web/assets/`，原生 JS 三件套）

**步骤 4 — 读取归一**（app.js）
- 新增 `groupListOf(tool)`（263 行附近）；删除 `groupOf`/`groupKey`（263-271），逐调用点（368、450、514、547、651、854、885）替换。

**步骤 5 — 多桶渲染**（app.js）
- `renderTree`（~444）：分桶改双重循环 `for tool → for key of groupListOf(tool)`；无分组才入 `UNGROUPED_KEY` 桶。树头计数天然正确。
- `renderTabs`（~503）：计数与 `runningGroups` 对每个 tool 的全部 key 逐一累计；过滤改「`groupListOf(tool)` 包含 `state.activeGroup`」（activeGroup 为 UNGROUPED_KEY 时匹配无分组工具）。
- `existingGroups()`（~851）：遍历 `groupListOf` 收集全部组名。
- `renderCard`（~368）：单徽标改按分组列表循环输出多个 `.card-group` span。
- 详情徽标（~650）：改 join(" / ") 展示全部分组，无分组仍显「设置分组」。

**步骤 6 — 分组对话框多选**（app.js + index.html + style.css）
- `openGroupDialog`：初始化 `state.groupDraft = new Set(groupListOf(current.tool))`。
- `renderGroupOptions`：chips 改多选 toggle（`.selected`/`aria-pressed` 反映归属，点击切换选中而非回填输入框）；移除「未分组」chip（全不选即未分组）。
- 输入框旁新增「添加」按钮：将输入内容作为待选 chip 加入并置选中态（不用逗号拆分，分组名可含逗号）。
- `submitGroup`：收集 draft → 非空 `meta.group = [...draft]`，空则 `delete meta.group` → `PUT /api/tools/{name}/meta`（端点与载荷形状不变，无 API 改动）。
- index.html `groupDialog`（336-351）提示文案改「可多选；全部取消 = 未分组」；`metaDialog`（~323）提示 group 允许字符串或数组。
- style.css：新增 `.group-chip-option.selected` 选中态样式（~6-8 行，挂 694 行既有规则旁）。

### 测试（`internal/`）

**步骤 7**
- **新增** `store/meta_test.go`：string→数组归一、数组直传、>8 报错、单项 >32B、trim、空项剔除、空数组剔 key、大小写保留去重（`["Dev","dev"]`→两项）、输出有序、类型非法报错、与 tags 同存不超 4KB。
- **改写** `api/server_test.go` TestMetaAcceptsGroup（~136-155）：断言改 `[]any{"Dev"}`；新增 `{"group":["a","a","b"]}`→`["a","b"]` 用例。
- **新增** `store/store_test.go` 一组：Add 带 group 数组 → GetTool 往返保形。
- **新增** `mcp/mcp_test.go`：meta.group 数组经 add/set 往返（照搬现有 122-173 行模式）。

### 文档（父仓 `docs/projects/go_projects/clictl/`）

**步骤 8**
- `clictl 使用指南.md`（~99 行分组与视图、~196 行 meta 校验规则）、`MCP 接口文档.md`（~107 行 meta 白名单）更新为多分组语义。
- ⚠️ 这两个文件**已有未提交改动**（v2.3.0 alias 相关）+ 未跟踪的 migrations/003 SQL：开始改文档前先向用户确认现存改动如何处理（建议先独立提交），严禁混提。

## 提交切分（遵守 AGENTS.md 范围隔离）

1. 子仓 clictl：`clictl:feat: 支持工具多分组`（meta 校验 + GUI + 测试，可一笔；CLI flag 与 MCP 文案可并入或拆出）。
2. 父仓 plans：本计划文件按 `**/plans/**` 规则**立即单独提交**（`docs(plans): ...`）。
3. 父仓 docs：`docs: 更新 clictl 多分组文档`——与现存未提交文档改动隔离处理。
4. 父仓子模块指针更新。
5. 完成后按需调用一次 `aoci_maintain` 对齐索引。

## 验证

1. `go build ./...` + `go test ./...`（子仓 clictl 根目录）。
2. CLI 手测：`clictl set nutvault-gui-dev --meta '{"group":["dev","ops"]}'` → `clictl list` 确认；`--group` flag 重复传；>8 项/超长项报 `meta_invalid`。
3. GUI 手测（`clictl gui` 启动）：旧单分组数据正常加载；多分组工具在树/平铺两视图下入多桶、计数重复计入、tab 过滤含语义生效；对话框勾选+新建+全不选=未分组；`active_group` 指向已删分组时自动复位。
4. MCP 冒烟：经 MCP set 传数组 group 往返确认。

### 未决问题与阻塞确认清单

- [x] 已确认：实施多分组，展示为「同时出现在所有所属分组」（用户已选）。
- [x] 已按推荐默认确定：去重大小写敏感（保留存量 "Dev" 语义）。
- [x] 已按推荐默认确定：`--group` flag 随本次交付 add/add-cmd/edit，`set` 不加。
- [x] 已按推荐默认确定：卡片徽标全分组平铺、树排序不变、不维护孤儿分组名录。
- [x] 父仓 docs 现存未提交改动（alias 相关）如何处理？已按推荐处理：先独立提交 alias（clictl `2ceb352`、父仓 `1362b65`），多分组代码与文档再分别单独提交。

### 实施结果

- 后端：`store/meta.go` 归一化 group 为有序数组；CLI `add`/`add-cmd`/`edit` 新增可重复 `--group`；MCP schema 文案同步。
- GUI：`groupListOf`/`toolInGroup` 单点归一，树/标签页多桶、卡片与详情平铺分组、分组对话框改多选并支持新增；注册/编辑弹窗的分组输入改为「追加」语义，留空保持现有分组，避免编辑时静默清空多分组。
- 测试：新增 store/meta 表驱动用例、API 与 MCP 多分组往返、store 往返；`go build ./...`、`go test -count=1 ./internal/...`、`node --check app.js` 全通过。

