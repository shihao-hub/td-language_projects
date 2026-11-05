<script setup lang="ts">
// EmptyState：未配置 Key 的引导卡——结构与 GLM 未绑定引导卡完全一致
// （居中：图标 + 标题 + 说明 + 按钮），皮肤取暗色平面（#2e2e2e + 1px 描边，无阴影）。
import SampleButton from "./SampleButton.vue";

const emit = defineEmits<{ (e: "go"): void }>();
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-[6px] border px-6 py-12 text-center"
    style="background: var(--oc-surface); border-color: var(--oc-border)"
  >
    <div
      class="flex h-11 w-11 items-center justify-center rounded-xl"
      style="background: var(--oc-bg); color: var(--oc-text-3)"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    </div>
    <h3 class="mt-3 text-[13px] font-semibold" style="color: var(--oc-text)">
      尚未绑定 OpenCode Go API Key
    </h3>
    <p class="mt-1 max-w-sm text-[11px] leading-5" style="color: var(--oc-text-3)">
      录入密钥后即可探测滑动、周、月三个额度窗口的实时用量。
    </p>
    <div class="mt-5">
      <SampleButton label="前往设置" @click="emit('go')" />
    </div>
  </div>
</template>
