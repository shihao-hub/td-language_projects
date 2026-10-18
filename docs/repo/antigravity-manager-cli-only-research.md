# Antigravity-Manager「取消 IDE active 只保留 CLI」调研

## 元信息

| 项 | 内容 |
| :--- | :--- |
| 调研对象 | [lbjlaq/Antigravity-Manager](https://github.com/lbjlaq/Antigravity-Manager)（Antigravity Tools，Tauri v2 + React + Rust），commit [`2f7641a6`](https://github.com/lbjlaq/Antigravity-Manager/commit/2f7641a68e90a2a45e5507903d127bac2d698d53)（main HEAD，2026-10-15），约 3.2 万 star |
| 对照对象 | [shyim/agm](https://github.com/shyim/agm)（Multi-account CLI for Antigravity），commit [`1d3ce849`](https://github.com/shyim/agm/commit/1d3ce8497e36ffa60c3b4e369168315a7ae4d469) |
| 调研日期 | 2026-10-17 |
| 方法 | `git clone --depth 1` 到系统临时目录 + 本地 grep；`gh api` 读取 GitHub issue/PR/仓库元数据；未做任何本机凭据探测、未改动任何仓库 |
| 结论标注 | 【已验证】= 源码/官方文档/官方 issue 直接支持；【推断】= 由代码路径合理推导，未见文档背书 |

以下所有源码引用均为固定 commit 的 permalink，行号以该 commit 为准。

---

## TL;DR

**可以做到「只保留 CLI（agy）、不接管 IDE」。** lbjlaq/Antigravity-Manager 为 CLI 保留了一条**专用免杀免重启通道**：`switch_account(id, target_ide=Some("agy"))`。

1. **操作**：账号列表中目标账号卡片上点 **Terminal 图标按钮**（中文 tooltip「切换到 Antigravity CLI (agy)」），或 HTTP 调 `POST /api/accounts/switch` 带 `{"targetIde":"agy"}`。该路径**只写系统凭据库（Keyring）+ `~/.gemini` 文件凭据**，明确不写 `state.vscdb`、不杀进程、不重启 IDE/经典版。【已验证】
2. **「取消 IDE active」的准确语义**：该工具没有持久化的「接管 IDE 开关」，也没有「撤销 IDE 注入」功能；它只在**每次显式切换时按 target 写对应 surface**。想以后都只作用 CLI，就不要再点 IDE/经典版按钮、Dashboard「一键切换」和托盘「切换下一账号」——后三者 `target=None` → 自动判定（经典版优先，IDE 运行则挑 IDE），会写 IDE 并杀/重启客户端。切到 agy 后，Manager 记录 `current_target_ide="agy"`，后台自动同步只读钥匙环、不回写 IDE 数据库，不会把状态改回去。【已验证】
3. **CLI 凭据是否被连带清除/覆盖**：切到 **IDE 目标不会碰 CLI 凭据**（IDE 写 `state.vscdb`、CLI 写钥匙环，物理隔离）；但切到**经典版目标存在覆盖风险**——经典版 ≥ 2.0.0 时写的是**同一个** `gemini:antigravity` 钥匙环槽位，会顺带把 CLI 凭据改成该账号。删除 Manager 里的账号**不会**清理钥匙环。【已验证】
4. 替代工具 shyim/agm 的对应能力：`agm switch <account> --target agy` 只写 OS credential store、不重启 GUI。【已验证】

---

## 1. 工具识别

- 用户所述 "Antigravity Manager" 判定为 **lbjlaq/Antigravity-Manager**（仓库描述："Professional Antigravity Account Manager & Switcher … 专业的 Antigravity 账号管理与切换工具"）。识别依据：① 仓库自述即「Antigravity 账号管理/切换」；② 中文 README、中文社区广泛使用；③ 其账号卡片同时提供「经典版 / IDE / CLI (agy)」三目标切换，与用户描述的「ide 的 active」「cli」语境完全吻合（源码见 `AccountCard.tsx` 三个按钮，第 2.5 节）。
- 对照对象 shyim/agm 为 Go 编写的纯 CLI 多账号工具（target: `agy`/`ide`/`all`），在下文第 5 节做一段对照。

---

## 2. 各 surface 的写入机制（源码证据）

### 2.1 统一入口：`switch_account(account_id, target_ide)`

- Tauri 命令入口：`src-tauri/src/commands/mod.rs` L152-175，参数 `account_id: String`、`target_ide: Option<String>`，透传给 `modules::account::switch_account`
  （[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/commands/mod.rs#L152-L175)）。
- 核心逻辑：`src-tauri/src/modules/account.rs` L1567-1641 —— 校验账号、刷新 token、生成设备指纹，然后：

  ```rust
  // 3. Execute platform-specific system integration (Close proc, Inject DB, Start proc, etc.)
  integration.on_account_switch(&account, target_ide).await?;   // L1627
  // 4. Update tool internal state
  set_current_account_id_with_target(account_id, target_ide)?;  // L1630
  ```

  （[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/account.rs#L1567-L1641)）
- `target_ide` 会被持久化到账号索引 `AccountIndex.current_target_ide`（`account.rs` L2006-2017；注意 **传 `None` 会把该值重置为 `None`**，有单测断言 L480/L488 佐证）
  （[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/account.rs#L2006-L2017)）。

### 2.2 `target="agy"`：纯 CLI 通道（本问题的核心答案）

`src-tauri/src/modules/integration.rs` `DesktopIntegration::on_account_switch` 的最前面就是 agy 分支（L231-259），它**先于任何进程控制/数据库注入逻辑**直接返回：

```rust
if target_ide == Some("agy") {
    write_to_system_keyring(account)?;                       // L232 只写系统凭据库
    let stored = read_from_system_keyring_only()?;           // L235 回读强校验
    verify_agy_credentials(&account.token.refresh_token, &stored.refresh_token)?; // L236
    if let Ok(storage_path) = device::get_storage_path(target_ide) {
        ... device::write_profile(...)                        // L238-242 best-effort 设备指纹
    }
    self.show_notification("Antigravity CLI", &msg);          // L244-257（含"运行中的 agy 会话可能仍持有旧凭据"提示）
    return Ok(());                                            // L259 直接返回
}
```

（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L231-L259)）

由此可确认 agy 通道的性质【已验证】：
- **写**：系统 Keyring + `~/.gemini` 文件凭据（见 2.4）；
- **不写** `state.vscdb`、不写 IDE `storage.json` 凭据、**不杀进程、不重启 IDE**（代码在写完后即时 `return Ok(())`）；
- 写后**强制回读校验** refresh_token，不一致即报错（杜绝"伪切号"，见 `verify_agy_credentials` L927-934，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L927-L934)）；
- Headless/Docker 模式下不支持 agy 目标，直接报错 `"Switching to the agy CLI is not supported in headless mode"`（L1116-1127，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L1116-L1127)）。

官方 CHANGELOG 对该通道的表述：修复 Issue #3399 后，HTTP `POST /accounts/switch`「支持解析可选的 `targetIde` 参数（如 `"agy"`），使自动化流水线或 CLI 刷新凭据时**仅写系统 Keyring，避免强制杀死并重启正在运行的 Antigravity IDE**」（`CHANGELOG.md` L920-921，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/CHANGELOG.md#L920-L921)；原始 issue [#3399](https://github.com/lbjlaq/Antigravity-Manager/issues/3399)）。

### 2.3 IDE / 经典版目标：写哪里、是否重启

目标解析：`resolve_effective_target`（`integration.rs` L24-68）——显式 `"ide"`/`"classic"` 直接命中；`None` 时智能探测：**经典版正在运行 → 经典版；否则 IDE 正在运行 → IDE；否则有经典版可执行文件 → 经典版；否则存在 IDE 可执行文件 → IDE**
（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L24-L68)）。

凭据写入分流在 `apply_account_credentials`（`integration.rs` L79-217）【已验证】：

| 目标 | 条件 | 写入位置 | 是否碰系统 Keyring |
| :--- | :--- | :--- | :--- |
| IDE（VS Code 定制版） | 恒走 SQLite 分支（`is_ide=true` 不做版本探测） | `state.vscdb` token 注入（`db::inject_token`，写前备份 `*.vscdb.backup`）+ `storage.json` 设备指纹 | **否** |
| 经典版（原生桌面端） | 版本 ≥ 2.0.0 | **系统 Keyring** + `~/.gemini` 文件凭据 | **是（同一槽位）** |
| 经典版 | 版本 < 2.0.0（或探测失败但存在 state.vscdb） | `state.vscdb` SQLite 注入 | 否 |

对应代码：`use_keyring` 判定 L87-131；Keyring 分支 L133-180；SQLite 分支 L181-215（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L79-L217)）。

进程与重启行为（`integration.rs` L292-408，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L292-L408)）【已验证】：
- **IDE 在运行**：先写凭据 → 杀 `language_server` 子进程（"热切号"，主窗口保留，supervisor 约 2s 原地重建）→ 杀后再补写一次；若找不到子进程或失败，降级为**整窗关闭 + 重新启动**。
- **经典版**：先关进程（`close_antigravity`）→ 再写凭据 → 再启动（旧架构退出时会刷盘覆盖 Token，故顺序相反）。

### 2.4 凭据的物理落点（Keyring / 文件）

`write_to_system_keyring`（`integration.rs` L427-707）与 `write_to_file_credentials`（L711-872）【已验证】：

- **Windows Credential Manager**：`CRED_TYPE_GENERIC`，target = `gemini:antigravity`，user = `antigravity`，先 `CredDeleteW` 再 `CredWriteW`（L545-546、L577-586，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L511-L587)）；
- **macOS**：Keychain `security add-generic-password -s gemini -a antigravity`（L480-503）；**Linux**：secret-tool 显式写 `login` 集合并与 default 同步（这是 #3418 的修复，L670-694）；
- **文件凭据**（跨平台，所有 keyring 写入路径都会同步写）：
  - `~/.gemini/antigravity-cli/antigravity-oauth-token`（agy CLI 原生文件凭据，L728-797）；
  - `~/.gemini/oauth_creds.json` + `~/.gemini/google_accounts.json`（**Gemini CLI 的凭据文件**，L799-864）。

读取侧：`read_from_system_keyring_only` 只读系统库、拒绝文件回退（L922-925，用于 agy 切换校验与自动同步判定），[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/integration.rs#L917-L925)。

### 2.5 Claude Code / Codex / OpenCode 等第三方 CLI 的「接入」是另一回事

这些工具不是通过凭据注入接入的，而是「**反代配置同步**」：Manager 内置反向代理，把本地代理 URL + API Key 写进各 CLI 的配置文件（Claude / Codex / Gemini / OpenCode / Droid / Hermes / OpenClaw 等），并支持 backup → restore → clear 三步回滚。

- `src-tauri/src/proxy/cli_sync.rs` L219-225（`CliApp` 枚举：Claude/Codex/Gemini/OpenCode/JeikCode…），L1117-1130（`execute_cli_sync` / `execute_cli_restore`）
  （[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/proxy/cli_sync.rs#L1117-L1130)）；
- 前端 `src/components/proxy/CliSyncCard.tsx` L245-252（`execute_opencode_clear` 等清除入口）；README_ZH L296-323 描述「Agent 工具一键配置 / Clear Config / Restore」。
- 与「只保留 CLI」的关系：这条链路只改第三方 CLI 的配置，**不触碰 Antigravity IDE / 经典版 / agy 的凭据**；反之 agy 切换也不会改这些配置。两者正交。【已验证】

### 2.6 后台自动同步（auto-sync）不会反向污染

`sync_account_from_db`（`commands/mod.rs` L680-742）和 Web/Headless 版（`proxy/server.rs` L3415-3428）按 `current_target_ide` 分流【已验证】：

```rust
// The CLI stores its login in the system keyring, not an IDE database.
let current_target = index.current_target_ide.as_deref();
let is_agy = current_target == Some("agy");
let credential = if is_agy {
    modules::integration::read_from_system_keyring_only().map(|state| state.refresh_token)
} else {
    modules::migration::get_refresh_token_from_db(current_target)
};
...
// 更新 Manager 的当前账号并保留客户端目标，不写回客户端凭据。(L728)
```

即：**target=agy 时后台同步只读系统钥匙环（完全跳过 IDE 数据库），且只更新 Manager 自己的记录，不向任何客户端写回凭据**。这就是 CHANGELOG v4.2.3「CLI Sync Isolation」条目所述行为（`CHANGELOG.md` L1353-1355，[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/CHANGELOG.md#L1353-L1355)；PR [#3186](https://github.com/lbjlaq/Antigravity-Manager/pull/3186)）。

---

## 3. 「取消 IDE active 只保留 CLI」操作路径

### 3.1 推荐做法（精确步骤）

**方式 A：GUI（日常使用）**

1. 打开 Manager → 账号页（Accounts）。
2. 在目标账号卡片上点击 **Terminal 图标按钮**（tooltip：「切换到 Antigravity CLI (agy)」；网格视图同位置，列表视图在操作列）。
   源码：`AccountCard.tsx` L400-407、`AccountTable.tsx` L691-696（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src/components/accounts/AccountCard.tsx#L400-L407)），前端统一走 `switchAccount(accountId, 'agy')`（`Accounts.tsx` L323-339、`accountService.ts` L46-48）。
3. 效果：系统钥匙环 `gemini:antigravity` + `~/.gemini` 文件凭据被写成该账号；**IDE 与经典版进程不被杀、不重启，`state.vscdb` 不被改写**；Manager 的当前账号与 `current_target_ide` 更新为「该账号 + agy」，此后后台同步走只读钥匙环分支，不会把 IDE 里的旧账号"同步回来"。
4. 之后启动 `agy` 命令即使用新账号；期间保持**不要点**同一卡片上的经典版/IDE 按钮（见 3.2）。

**方式 B：HTTP API（自动化/脚本）**

```http
POST http://127.0.0.1:<proxy_port>/api/accounts/switch
Authorization: Bearer <API Key>
Content-Type: application/json

{"accountId": "<账号 ID>", "targetIde": "agy"}
```

官方文档：`docs/API_REFERENCE.md` L36「targetIde 可选，如传 `"agy"` 则仅写入凭据免重启 IDE」（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/docs/API_REFERENCE.md#L36)）；实现 `proxy/server.rs` L1534-1539（`SwitchRequest.target_ide`）+ L1569（透传）（[permalink](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/proxy/server.rs#L1534-L1569)）。这是 #3399 修复后提供的「自动化流水线 / CLI 刷新凭据」标准姿势。

### 3.2 必须避开的入口（否则会接管 IDE/经典版）

| 入口 | target 取值 | 后果 |
| :--- | :--- | :--- |
| Dashboard「一键切换 / 最佳账号推荐」 | `None`（`Dashboard.tsx` L254 只传 accountId） | 自动判定目标：经典版优先；IDE 正在运行则写 IDE。会杀/重启对应客户端，并把 `current_target_ide` 重置为 `None`（不再保持 agy 语义） |
| 托盘菜单「切换下一账号」 | `None`（`tray.rs` L216） | 同上 |
| 账号卡片「切换到 Antigravity IDE」按钮 | `"ide"` | 写 `state.vscdb`；IDE 在跑则热切换（杀 language_server）或整窗重启 |
| 账号卡片「切换到 Antigravity (经典版)」按钮 | `"classic"` | 经典版 ≥ 2.0.0 时**顺带覆盖 CLI 钥匙环凭据**（同一槽位）；并重启经典版进程 |

（tray.rs permalink：[L194-221](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src-tauri/src/modules/tray.rs#L194-L221)；Dashboard permalink：[Dashboard.tsx#L246-L256](https://github.com/lbjlaq/Antigravity-Manager/blob/2f7641a68e90a2a45e5507903d127bac2d698d53/src/pages/Dashboard.tsx#L246-L256)。）

### 3.3 若「取消 IDE active」指「清除 IDE 里已被注入的凭据」

**做不到，且这是设计使然**：Manager 全仓没有 logout / clear-credential / 撤销注入 的命令或代码路径（`lib.rs` 命令清单 L655-855 中不存在此类命令；全仓 grep 无凭据删除逻辑）。它只是**写入型**工具：
- 切到 agy 后，IDE 里此前注入的登录态保持原样，不会因为你"取消 active"而被清掉；
- 删除 Manager 账号（`account.rs` L1454-1488）只删 Manager 自己的 JSON 记录与索引，**不动钥匙环、不动 state.vscdb**；
- 要清 IDE 侧，只能在 IDE 内自行退出登录（或手动处理 `state.vscdb`，非官方支持）。

同理，「取消 IDE active」在 Manager 里的唯一可持久化表达就是：**把当前目标切到 agy**（3.1 方式 A/B），让工具此后只写 CLI。【已验证】

---

## 4. 风险与注意事项

1. **经典版目标会连带覆盖 CLI 凭据**（最大的坑）：经典版 Antigravity ≥ 2.0.0 与 agy 共用同一个 `gemini:antigravity` 钥匙环槽位与 `~/.gemini` 文件（2.3/2.4 源码证据）。一旦点了「切换到经典版」，CLI 侧的账号会被静默改成同一账号。【已验证】
2. **agy 通道同时改写 Gemini CLI 的凭据文件** `~/.gemini/oauth_creds.json`、`~/.gemini/google_accounts.json`（L799-864）。若你同时使用 Gemini CLI，切 agy 会同步改写其账号，属官方设计（#3567「agy 原生凭证双向同步」），但需知情。【已验证】
3. **运行中的 agy 会话可能仍持有旧凭据**：切换成功只保证"下一次 CLI 命令"读到新账号；已在运行的 agy 进程可能把旧凭据写回，官方在切号通知文案中明确提示（`integration.rs` L244-255）。【已验证】
4. **headless / Docker 模式不支持切 agy**（直接报错），此时只能选 IDE/经典版或改用反代。【已验证】
5. **Dashboard 与托盘切换会重置 target 语义**：`target=None` 会把 `current_target_ide` 写成 `None`（并有单测固化，L480/L488），Dashboard「一键切换」不提供 agy 选项——想维持「只 CLI」就不要用这两个入口。【已验证】
6. **agy 切换 best-effort 写设备指纹**：agy 分支会按 `device::get_storage_path("agy")`（目录解析回退到经典版 `Antigravity` 路径）尝试把设备指纹写入 `storage.json`（仅 telemetry 字段，不涉及凭据；文件不存在则跳过）。【已验证（代码）/推断（本机是否命中取决于经典版是否安装）】
7. **第三方条款风险**（官方 README 免责声明）：使用第三方工具访问 Antigravity/Gemini 服务可能违反 Google 条款，存在账号被暂停风险；README 明示"建议只使用切换功能"（`CHANGELOG.md` L1444-1445 等处）。【已验证（属官方自述）】

---

## 5. 对照：shyim/agm

`agm switch <email|alias|partial> [--target agy|ide|all]`（README L94-106，[permalink](https://github.com/shyim/agm/blob/1d3ce8497e36ffa60c3b4e369168315a7ae4d469/README.md#L94-L106)）【已验证】：

| Target | 行为（README 原文） |
| :--- | :--- |
| `agy`（`cli`） | "Write OS credential store only (**no GUI process restart**)" |
| `ide` | "Inject OAuth into `state.vscdb`, restart IDE if found" |
| `all`（默认） | "Applies `agy` → `ide`" |

即：agm 与 lbjlaq 工具思路一致——**CLI-only = 只写 OS 凭据库**；agm 的默认值是 `all`（两个面都写），所以要用 agm 实现「只保留 CLI」必须显式 `--target agy`，不要用默认值。agm 用自建加密本地库管理账号（`agm import-cli` 读 agy 的 OS credential store，`agm import-ide` 读 `state.vscdb`，README L70-76）。

---

## 6. 未决问题与阻塞确认清单

- [ ] 用户「取消 ide 的 active」的确切所指：是"Manager 界面当前目标显示"（3.1 切 agy 即可满足），还是"清除 IDE 内已注入的登录态"（3.3 无此功能，需在 IDE 内登出）？
- [ ] 本机是否存在经典版 Antigravity 且版本 ≥ 2.0.0（决定 2.3 表格里经典版走 Keyring 还是 SQLite，也决定风险 1 是否实际存在）——本次未做本机探测，按需人工核实。
- [ ] 用户是否同时使用 Gemini CLI：若是，切 agy 会同步改写 `~/.gemini/oauth_creds.json`（风险 2），需要接受或规避。
- [ ] 是否走 HTTP API 自动化：若是，需确认使用的端口/API Key 属于反代服务（`proxy/server.rs`，支持 `targetIde`），不要混淆 `modules/http_api.rs`（该模块注释自述"预留…当前未在主流程中启用"，且其 switch 硬编码 `None`）。
- [ ] 是否需要为 lbjlaq 工具提交 feature request（如 Dashboard/托盘也支持 agy 目标、或"退出 IDE 接管"清理功能）——当前版本两者均不支持。
