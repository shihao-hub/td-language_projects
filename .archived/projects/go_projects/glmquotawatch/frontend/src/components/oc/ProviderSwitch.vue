<script setup lang="ts">
// ProviderSwitch：Provider 分段切换（GLM / OpenCode Go）。
// 常驻应用顶栏：两个 Provider 视图下位置、形态与交互完全一致，
// 不随切换移位或隐藏；沿用既有胶囊分段控件外形（浅色外壳令牌）。
// 交互约束：点击立即本地切换（乐观生效），不等后端回流；后端未确认时
// 在旁边挂一枚「未同步」提示，而不是让按钮看起来失灵。
import { activeProvider, setActiveProvider, store } from "../../store";
import type { Provider } from "../../store";

const options: { key: Provider; label: string }[] = [
  { key: "glm", label: "智谱 GLM" },
  { key: "opencode", label: "OpenCode Go" },
];

function btnClass(key: Provider): string {
  return activeProvider.value === key
    ? "bg-panel text-ink shadow-xs"
    : "text-dim hover:text-ink";
}

function onClick(key: Provider): void {
  if (key === activeProvider.value) return;
  void setActiveProvider(key);
}
</script>

<template>
  <div class="flex items-center gap-1.5">
    <div
      class="flex shrink-0 items-center gap-0.5 rounded-full border border-edge bg-well/90 p-0.5 shadow-inner"
      role="group"
      aria-label="切换 Provider"
    >
      <button
        v-for="o in options"
        :key="o.key"
        type="button"
        class="provider-btn rounded-full px-2.5 py-[3px] text-[11px] font-medium"
        :class="btnClass(o.key)"
        @click="onClick(o.key)"
      >
        {{ o.label }}
      </button>
    </div>
    <span
      v-if="store.providerError"
      class="rounded-full border border-warn/30 bg-warn-light px-1.5 py-[1px] text-[10px] font-medium text-warn"
      :title="store.providerError"
    >
      未同步
    </span>
  </div>
</template>

<style scoped>
/* 切换动画 ≤150ms */
.provider-btn {
  transition:
    color 150ms ease,
    background-color 150ms ease;
}
</style>
