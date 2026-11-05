<script setup lang="ts">
// SampleButton：控制条右侧「立即采样」按钮——与 GLM「即刻核对用量」同位置、
// 同刷新图标与加载旋转、同按压反馈（btn-press）；皮肤为 console 扁平描边
// （1px #ffffff14、透明平面、文字 #f2f2f2；悬停 #2e2e2e；聚焦 outline）。
defineProps<{ busy?: boolean; label?: string; busyLabel?: string; icon?: boolean }>();
defineEmits<{ (e: "click"): void }>();
</script>

<template>
  <button
    type="button"
    class="oc-btn btn-press oc-mono flex shrink-0 items-center gap-1.5 rounded-[5px] border px-2.5 py-1 text-[11px]"
    :disabled="!!busy"
    @click="$emit('click')"
  >
    <svg
      v-if="icon"
      class="h-3 w-3 shrink-0"
      :class="busy ? 'animate-spin' : ''"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <path d="M21 12a9 9 0 1 1-3-6.7M21 3v6h-6" />
    </svg>
    <span>{{ busy ? (busyLabel ?? "采样中…") : (label ?? "立即采样") }}</span>
  </button>
</template>

<style scoped>
.oc-btn {
  border-color: var(--oc-border);
  background: transparent;
  color: var(--oc-text);
}
.oc-btn:hover:not(:disabled) {
  background: var(--oc-surface);
}
.oc-btn:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 3px;
}
.oc-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
