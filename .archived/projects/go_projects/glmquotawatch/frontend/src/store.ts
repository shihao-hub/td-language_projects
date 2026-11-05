// 全局响应式状态：GUIState 快照 + 派生 UI 状态。
// 绑定调用返回的就是普通 JSON 对象（键名与 Go json tag 一致），
// 类型经 GUIState 约束即可，无需生成类的 createFrom 水合。
import { reactive, computed } from "vue";
import { bindings } from "./api";
import type { GUIState, OpenCodeWindowView } from "./api";

export type Provider = "glm" | "opencode";

// 与后端 bindings 通讯的硬超时：Wails 调用若因主进程异常/长任务永不返回，
// 前端不能陪着无限期等待（否则整屏表现为「卡住」且按钮全部失灵）。
const CALL_TIMEOUT_MS = 8000;
// 手动采样超时：后端自身预算 30s（GLM）/ 15s（OpenCode），前端留出余量后兜底。
const SAMPLE_TIMEOUT_MS = 35000;
const OC_SAMPLE_TIMEOUT_MS = 20000;
// 首次状态加载失败后的自动重试节奏（毫秒），共 3 次补试。
const BOOT_RETRY_DELAYS_MS = [1200, 3000, 6000];
// 本地 Provider 镜像键：后端快照到达前先按它渲染，避免每次开窗都闪一下 GLM。
const PROVIDER_STORAGE_KEY = "glmquotawatch.activeProvider";

export const store = reactive({
  state: null as GUIState | null,
  stateLoaded: false, // 是否曾成功拿到过一次快照
  stateError: "", // 最近一次快照读取失败原因（空串=正常）
  refreshBusy: false, // 快照请求进行中（防事件风暴叠加请求）
  sampleBusy: false,
  sampleError: "", // GLM 手动采样失败原因（人类可读）
  ocSampleBusy: false, // OpenCode Go 探测进行中
  ocError: "", // OpenCode Go 最近一次探测错误（人类可读）
  ocFocusToken: false, // 空状态「前往设置」时聚焦 OpenCode Token 输入框
  providerChoice: readProviderSeed(), // 本地乐观选择（用户本次点击/上次镜像）
  providerError: "", // 切换未被后端确认时的提示
  tab: "dashboard" as "dashboard" | "history" | "settings",
});

// 用户本次会话是否主动切过 Provider；发生过即视为「本地选择优先」，
// 不再让后续快照把视觉状态拽回后端存值（否则后端卡住时切换又变回「点了没反应」）。
let providerPinned = false;

export const isDemo = computed(() => store.state?.mode === "demo");
export const hasToken = computed(() => store.state?.config?.has_token === true);
// 后台连接状态：false 时界面须展示可重试的连接失败态，而不是永久转圈。
export const backendReady = computed(() => store.state !== null);

// ---- Provider ----
export const activeProvider = computed<Provider>(() => {
  if (store.providerChoice) return store.providerChoice;
  return store.state?.active_provider === "opencode" ? "opencode" : "glm";
});
// OpenCode 暗色 console 视图生效条件：仪表盘页 + OpenCode Provider
export const isOpenCodeView = computed(
  () => store.tab === "dashboard" && activeProvider.value === "opencode",
);

// ---- OpenCode Go ----
export const ocHasToken = computed(() => store.state?.opencode_config?.has_token === true);
export const ocWindows = computed<OpenCodeWindowView[]>(
  () => store.state?.opencode_status?.windows ?? [],
);

// ---- 绑定调用守卫 ----

type Cancelable = { cancel?: () => void };

// guardCall 给绑定调用加硬超时：超时即取消请求并抛出可读错误，
// 保证任何一次后端异常都不会把界面锁死在等待态。
async function guardCall<T>(call: Promise<T> & Cancelable, ms = CALL_TIMEOUT_MS): Promise<T> {
  let timer = 0;
  const timeout = new Promise<never>((_, reject) => {
    timer = window.setTimeout(() => {
      reject(new Error(`后台响应超时（${Math.round(ms / 1000)}s 无返回）`));
      try {
        call.cancel?.();
      } catch {
        // 取消失败不影响前端错误提示
      }
    }, ms);
  });
  try {
    return await Promise.race([call, timeout]);
  } finally {
    window.clearTimeout(timer);
  }
}

// ---- 快照刷新 ----

export async function refreshState(): Promise<void> {
  if (store.refreshBusy) return;
  store.refreshBusy = true;
  try {
    const snapshot = (await guardCall(bindings.GetState())) as GUIState;
    store.state = snapshot;
    store.stateError = "";
    if (!store.stateLoaded) {
      store.stateLoaded = true;
      // 后端快照为权威来源：首次成功加载后丢弃本地种子（此后以 config.json 为准）
      if (!providerPinned) store.providerChoice = null;
    }
    if (!providerPinned) writeProviderSeed(activeProvider.value);
  } catch (e) {
    // 保留上一份可用快照（若有），只更新错误态：界面可继续用旧数据并提示重连
    store.stateError = errText(e) || "后台状态读取失败";
  } finally {
    store.refreshBusy = false;
  }
}

// bootState 启动引导：失败按退避补试，全部失败后保留 stateError 供界面展示。
export async function bootState(): Promise<void> {
  for (let attempt = 0; attempt <= BOOT_RETRY_DELAYS_MS.length; attempt++) {
    await refreshState();
    if (store.state) return;
    if (attempt < BOOT_RETRY_DELAYS_MS.length) {
      await new Promise((r) => window.setTimeout(r, BOOT_RETRY_DELAYS_MS[attempt]));
    }
  }
}

export async function sampleNow(): Promise<void> {
  if (store.sampleBusy) return;
  store.sampleBusy = true;
  store.sampleError = "";
  try {
    await guardCall(bindings.SampleNow(), SAMPLE_TIMEOUT_MS);
    // 成功结果经 "status" 事件回流（runtime.onSample 广播），此处兜底刷新
    await refreshState();
  } catch (e) {
    console.error("sample failed:", e);
    store.sampleError = errText(e) || "采样失败";
    await refreshState();
  } finally {
    store.sampleBusy = false;
  }
}

export async function setActiveProvider(p: Provider): Promise<void> {
  if (p === activeProvider.value) return;
  providerPinned = true;
  // 乐观生效：不等后端回流，界面立即响应（后端坏死也不会「点了没反应」）
  store.providerChoice = p;
  store.providerError = "";
  writeProviderSeed(p);
  try {
    await guardCall(bindings.SetActiveProvider(p));
    await refreshState();
  } catch (e) {
    // 后端未确认：保留本地选择，但明确提示选择未落盘
    store.providerError = `已在本机切换到 ${providerLabel(p)}，但后台未确认：${errText(e)}`;
  }
}

// sampleOpenCodeNow 立即探测一次 OpenCode Go（真实网络，不落历史）。
export async function sampleOpenCodeNow(): Promise<void> {
  if (store.ocSampleBusy) return;
  store.ocSampleBusy = true;
  store.ocError = "";
  try {
    await guardCall(bindings.SampleOpenCodeNow(), OC_SAMPLE_TIMEOUT_MS);
    // 成功结果经 "opencode-status" 事件回流
    await refreshState();
  } catch (e) {
    store.ocError = errText(e);
    await refreshState();
  } finally {
    store.ocSampleBusy = false;
  }
}

// goOpenCodeSettings 跳转设置页并请求聚焦 OpenCode Token 输入框。
export function goOpenCodeSettings(): void {
  store.ocFocusToken = true;
  store.tab = "settings";
}

export function providerLabel(p: Provider): string {
  return p === "opencode" ? "OpenCode Go" : "智谱 GLM";
}

export function errText(e: unknown): string {
  const s = String(e ?? "");
  const i = s.indexOf(": ");
  return i > 0 ? s.slice(i + 2) : s;
}

// ---- 本地 Provider 镜像（仅用于首屏渲染与后端不可用时的记忆兜底） ----

function readProviderSeed(): Provider | null {
  try {
    const v = window.localStorage.getItem(PROVIDER_STORAGE_KEY);
    return v === "opencode" || v === "glm" ? v : null;
  } catch {
    return null; // 隐私模式 / 存储被禁时静默降级
  }
}

function writeProviderSeed(p: Provider): void {
  try {
    window.localStorage.setItem(PROVIDER_STORAGE_KEY, p);
  } catch {
    // 存储不可用时忽略：记忆功能退化为后端 config.json 单通道
  }
}
