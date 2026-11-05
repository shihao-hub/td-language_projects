<script setup lang="ts">
// QuotaRow：单窗口额度行（console 范式）——
// 左侧窗口名（13px）+ 重置弱文本（11px，等宽 tabular-nums）；
// 右侧百分比（13px 等宽数字右对齐）+ 4–6px 状态点 + rate-limited 文字标签；
// 下方通栏 6px 细条：轨道 #3a3a3a、圆角 ≤2px，按 60% / 85% / rate-limited 阈值取色。
// 禁用圆环/仪表盘等装饰组件。
import { computed } from "vue";
import type { OpenCodeWindowView } from "../../api";

const props = defineProps<{ win: OpenCodeWindowView; now: number }>();

const rateLimited = computed(() => props.win.status === "rate-limited");

// 状态语义分级：低占用一律灰阶（不用绿色抢眼），≥60 告警、≥85 严重、限流失效
const severity = computed<"danger" | "crit" | "warn" | "ok">(() => {
  if (rateLimited.value) return "danger";
  if (props.win.percent >= 85) return "crit";
  if (props.win.percent >= 60) return "warn";
  return "ok";
});

const fillColor = computed(() => {
  switch (severity.value) {
    case "danger":
      return "var(--oc-danger)";
    case "crit":
      return "var(--oc-crit)";
    case "warn":
      return "var(--oc-warn)";
    default:
      return "var(--oc-text-2)";
  }
});

// 百分比文字：仅 60% 起按语义色提示，正常态保持主文本色
const percentColor = computed(() =>
  severity.value === "ok" ? "var(--oc-text)" : fillColor.value,
);

// 状态点：仅承载 status 语义（ok 灰阶 / rate-limited 红），是视图中少数允许着色处
const statusDot = computed(() =>
  rateLimited.value ? "var(--oc-danger)" : "var(--oc-text-2)",
);

const widthPct = computed(() => Math.min(100, Math.max(0, props.win.percent)));

// 倒计时每秒刷新（现在时间由父级统一驱动），中文人读如 "3小时25分后"
const countdown = computed(() => formatCountdown(props.win.resets_at, props.now));

function formatCountdown(iso: string, nowMs: number): string {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const sec = Math.floor((t - nowMs) / 1000);
  if (sec <= 0) return "已到期";
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (d > 0) return h > 0 ? `${d}天${h}小时后` : `${d}天后`;
  if (h > 0) return m > 0 ? `${h}小时${m}分后` : `${h}小时后`;
  if (m > 0) return `${m}分${s}秒后`;
  return `${s}秒后`;
}
</script>

<template>
  <div class="oc-row">
    <div class="oc-row-head flex items-end justify-between gap-4">
      <div class="min-w-0">
        <div class="oc-row-label text-[13px] leading-5" style="color: var(--oc-text)">
          {{ win.label }}
        </div>
        <div class="oc-mono tnum mt-0.5 truncate text-[11px]" style="color: var(--oc-text-3)">
          重置 · {{ countdown || "--" }}
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-2 pb-0.5">
        <span v-if="rateLimited" class="oc-mono text-[11px]" style="color: var(--oc-danger)">
          rate-limited
        </span>
        <span
          class="oc-mono oc-row-percent tnum text-[13px] font-medium"
          :style="{ color: percentColor }"
        >
          {{ win.percent }}%
        </span>
        <span class="h-1.5 w-1.5 rounded-full" :style="{ background: statusDot }" />
      </div>
    </div>
    <div
      class="mt-2 h-1.5 w-full overflow-hidden"
      style="background: var(--oc-track); border-radius: var(--oc-bar-radius)"
    >
      <div
        class="oc-fill h-full"
        :style="{ width: widthPct + '%', background: fillColor, borderRadius: 'var(--oc-bar-radius)' }"
      />
    </div>
  </div>
</template>

<style scoped>
/* 窄于约 640px 时堆叠为两段式（标签整行 + 数值次行右对齐），不出现横向滚动 */
@media (max-width: 640px) {
  .oc-row-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
  .oc-row-head > :last-child {
    width: 100%;
    justify-content: flex-end;
  }
  /* 窄屏字号降一档 */
  .oc-row-label,
  .oc-row-percent {
    font-size: 12px;
  }
}
</style>
