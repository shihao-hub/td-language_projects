# 实施计划 - 修复 bindings 失配导致的界面假死并记忆 Provider 选择

**问题陈述**：
用户反馈「GLM Token 出问题时界面似乎一直卡住，OpenCode 切换也点不动，而且每次打开都回到 GLM」。实测定位到两条独立缺陷：

1. **真实根因是 Wails bindings 调用 ID 全面失配（与 Token 无关）。**
   Wails v3 的绑定方法 ID 由 `FNV32a("<模块路径>.<包>.<类型>.<方法>")` 计算。项目在 v0.3.0 由 `glmquotawatch-gui` 更名为 `glmquotawatch`，模块路径随之改变，但 `frontend/bindings/**`（被 `.gitignore` 忽略的生成物）从未重建，仍是旧模块路径下生成的调用 ID。于是运行期每一次前端 → 后端调用都返回
   `Binding call failed: unknown bound method id 719815359`（旧路径 `glmquotawatch-gui.BindingsService.GetState` 的哈希），表现为：
   - `GetState` 永不成功 → `store.state` 恒为 `null` → 仪表盘一直是「正在向 GLM 服务建立首次指标通讯…」的转圈，页脚永远「持续监控中 / 待配置」；
   - `SetActiveProvider` 同样失败 → 点击 Provider 切换没有任何视觉反馈（看起来「点不动」）；
   - 与用户实际 Token 状态毫无关系，所以换 Token、重配密钥都无效。
2. **界面缺少失败出口（鲁棒性缺陷）。**
   旧实现在拿不到快照时只有无限转圈：既没有超时、也没有错误提示与重试入口；Provider 切换的可见状态完全依赖后端回流，后端一挂就表现为「死按钮」。另外构建脚本 `scripts/build.py` 只跑 `npm run build`，从不重建 bindings，使该类故障可以无声复发。

**需求**：
1. 修复 bindings 失配，让全部前端调用可用；并在构建流水线中固化「先重建 bindings 再构建前端」的顺序，杜绝复发。
2. 界面任何「拿不到数据」的情形都必须给出原因 + 可点动作（重连 / 立即探测 / 检查密钥），禁止无出口的加载动画。
3. Provider（智谱 GLM / OpenCode Go）选择持久化，重启后恢复上次停留的视图。
4. 绑定调用加硬超时与乐观切换，后端异常时按钮依旧可用并明确提示「未同步」。

**方案设计**：
1. **bindings 重建（根因修复）**：
   - `scripts/build.py` 新增 `generate_bindings()`：`wails3 generate bindings -clean=true -ts -i ./...`，在 `npm run build` 之前执行；缺 `wails3` 时打印告警而非静默跳过。
2. **Provider 记忆（后端持久化）**：
   - `store.Config` 新增 `active_provider`（omitempty，旧配置天然兼容）；
   - `service` 提供 `GetActiveProvider()`（缺省/脏值回落 `glm`）与 `SetActiveProvider()`（校验后原子写盘），Provider 常量收敛到 `service` 包，`guiapp` 仅别名引用；
   - `MonitorRuntime.startNormal()` 启动时从 config 恢复 `activeProvider`；`SetActiveProvider()` 先更新内存态再落盘，落盘失败只记 `last_error`（不阻断切换）。
3. **快照永不为 null**：
   - `Snapshot()` 在 `config.json` 不可读时下发降级 `ConfigView`（带数据目录）并记 `config_read_failed`，前端不会再把 `config: null` 误判为「未初始化」；自启状态查询（注册表）移到加锁前，缩短持锁时间。
4. **前端三态治理（`store.ts` / `Dashboard.vue` / `App.vue`）**：
   - `guardCall()` 给所有绑定调用加硬超时（默认 8s，采样 35s/20s），超时即取消请求并抛出可读错误；
   - `refreshState()` 记录 `stateError`，失败不吞异常；`bootState()` 启动时按 1.2s/3s/6s 退避补试；
   - Dashboard 分支明确化：`state === null` → 连接中 / 连接失败 + 「重新连接后台」；`config === null` → 读取配置失败 + 重试；无 Token → 原引导卡；有 Token 但无窗口数据 → 「尚未取到用量窗口」+ 失败原因 + 「立即探测 / 检查 API 密钥」；
   - Provider 切换改为乐观生效（`providerChoice` 本地优先 + `localStorage` 首屏镜像），后端未确认时顶栏挂「未同步」徽标并保留本地选择。
5. **验证**：
   - `go test ./...`、`go vet ./...`、`vue-tsc --noEmit`、`vite build` 全绿；
   - 实机（dev 通道）回归：把 `GLMQUOTAWATCH_GUI_API_BASE` 指向不可达地址模拟上游故障 → 界面正确显示「上游同步中断 + 立即探测/检查密钥」，不再转圈；在 `config.json` 写入 `active_provider: opencode` 后重启 → 直接进入 OpenCode 暗色视图（记忆生效）。

**任务分解**：

- [x] Task 1: 重建前端 bindings 并固化构建顺序
  - 文件：`go_projects/glmquotawatch/scripts/build.py`
  - 实现：新增 `generate_bindings()`（`wails3 generate bindings -clean=true -ts -i ./...`），在 `build_frontend()` 之前调用；未安装 `wails3` 时告警提示风险。
- [x] Task 2: 后端持久化 Provider 选择
  - 文件：`internal/store/store.go`、`internal/service/service.go`、`internal/guiapp/runtime.go`
  - 实现：`Config.ActiveProvider` 字段；`service.Provider*` 常量与 `GetActiveProvider/SetActiveProvider/DataDir`；运行时启动恢复 + 切换落盘（失败仅记录）。
- [x] Task 3: 快照健壮化
  - 文件：`internal/guiapp/runtime.go`
  - 实现：`Snapshot()` 配置不可读时降级 `ConfigView` 并记 `config_read_failed`；自启查询移出临界区。
- [x] Task 4: 前端超时、错误态与乐观切换
  - 文件：`frontend/src/store.ts`、`frontend/src/pages/Dashboard.vue`、`frontend/src/App.vue`、`frontend/src/components/oc/ProviderSwitch.vue`
  - 实现：`guardCall` 硬超时、`stateError/stateLoaded/bootState`、Dashboard 四态分支、Provider 乐观切换 + `未同步` 徽标、页脚连接态降级文案。
- [x] Task 5: 回归验证
  - 单测：`internal/service/service_test.go`（Provider 落盘/脏值回落）、`internal/guiapp/runtime_test.go`（切换落盘、快照降级非 nil）；
  - 实机：不可达上游 + `active_provider` 配置两种场景截图核对（无转圈、直接恢复 OpenCode 视图）。

### 未决问题与阻塞确认清单

- [ ] OpenCode Provider 侧同样缺少「无数据 + 失败原因 + 重试」卡片（当前仍是「尚未采样。点击立即采样…」文案），是否要按 GLM 同等规格补齐？
- [ ] 是否把「导航页签（仪表盘/历史走势/偏好配置）」也纳入记忆？本次只记忆 Provider；页签每次仍回仪表盘。
- [ ] 本次只给绑定调用加了前端硬超时，后端 `Snapshot()` 之外的慢路径（如 `EnterDemo`/`ExitDemo` 持有生命周期锁等待 daemon 收敛）是否也需要拆锁重构？
