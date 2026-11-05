<script setup lang="ts">
// History：高定 ECharts 折线走势 + 精致胶囊选择器 + 拒绝原生糙感下拉
// 支持 GLM 与 OpenCode Go 历史采样曲线分流与动态主题色呈现
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts";
import { bindings } from "../api";
import type { HistoryPoint, HistoryWindow } from "../api";
import {
  store,
  isDemo,
  activeProvider,
  ocHasToken,
  goOpenCodeSettings,
  sampleOpenCodeNow,
} from "../store";

const windows = ref<HistoryWindow[]>([]);
const winKey = ref("");
const hours = ref<24 | 168>(24);
const loading = ref(false);
const empty = ref(false);
const chartEl = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let currentPts: HistoryPoint[] = [];

const isOpencode = computed(() => activeProvider.value === "opencode");
const thresholds = computed(() => store.state?.config?.thresholds ?? [50, 60, 80, 90]);
const markThresholds = computed(() =>
  isOpencode.value ? [60, 85] : thresholds.value,
);

async function loadWindows() {
  try {
    windows.value = ((await bindings.HistoryWindows()) ?? []) as HistoryWindow[];
    if (!windows.value.find((w) => w.key === winKey.value)) {
      winKey.value = windows.value[0]?.key ?? "";
    }
  } catch {
    windows.value = [];
  }
}

async function load() {
  if (!winKey.value) {
    empty.value = true;
    currentPts = [];
    render([]);
    return;
  }
  loading.value = true;
  try {
    const pts = ((await bindings.ReadHistory(winKey.value, hours.value)) ?? []) as HistoryPoint[];
    currentPts = pts;
    empty.value = pts.length === 0;
    render(pts);
  } catch (e) {
    console.error("read history failed:", e);
    currentPts = [];
    empty.value = true;
    render([]);
  } finally {
    loading.value = false;
  }
}

function ensureChart(): echarts.ECharts | null {
  if (!chartEl.value) return null;
  // 如果容器当前不可见（如处于其他 tab，width/height 为 0），暂不初始化避免尺寸塌陷
  if (chartEl.value.clientWidth === 0 || chartEl.value.clientHeight === 0) {
    return null;
  }
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }
  return chart;
}

function render(pts: HistoryPoint[]) {
  nextTick(() => {
    const c = ensureChart();
    if (!c) return;
    c.resize();
    c.setOption(option(pts), true);
  });
}

function resizeChart() {
  if (!chartEl.value) return;
  if (chartEl.value.clientWidth > 0 && chartEl.value.clientHeight > 0) {
    if (!chart) {
      chart = echarts.init(chartEl.value);
    }
    chart.resize();
    if (currentPts.length > 0) {
      chart.setOption(option(currentPts), true);
    }
  }
}

function option(pts: HistoryPoint[]): echarts.EChartsOption {
  const lineColor = isOpencode.value ? "#d97706" : "#0d9468";
  const areaColor = isOpencode.value
    ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(217,119,6,0.18)" },
        { offset: 1, color: "rgba(217,119,6,0.01)" },
      ])
    : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(13,148,104,0.14)" },
        { offset: 1, color: "rgba(13,148,104,0.01)" },
      ]);

  const seriesData = pts
    .map((p) => {
      const t = new Date(p.ts).getTime();
      return Number.isFinite(t) ? [t, p.pct] : null;
    })
    .filter((p): p is [number, number] => p !== null);

  return {
    backgroundColor: "transparent",
    grid: { left: 42, right: 20, top: 20, bottom: 28 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#e1e6e3",
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: "#111827", fontSize: 11, fontFamily: "sans-serif" },
      extraCssText: "box-shadow: 0 4px 16px -2px rgba(15,23,42,0.08); border-radius: 8px;",
      valueFormatter: (v) => `${v}% 占用`,
    },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#e1e6e3" } },
      axisTick: { show: false },
      axisLabel: { color: "#8b97a2", fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      interval: 20,
      axisLabel: { color: "#8b97a2", fontSize: 10, formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#f0f4f2", type: "dashed" } },
    },
    series: [
      {
        type: "line",
        showSymbol: false,
        smooth: 0.15,
        step: false,
        lineStyle: { color: lineColor, width: 2 },
        areaStyle: { color: areaColor },
        data: seriesData,
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: {
            color: isOpencode.value ? "#ea580c" : "#c25e00",
            type: "dashed",
            width: 1,
            opacity: 0.6,
          },
          label: {
            position: "end",
            color: "#8b97a2",
            fontSize: 9,
            formatter: "{c}% 梯级",
            padding: [0, 4, 0, 0],
          },
          data: markThresholds.value.map((t) => ({ yAxis: t })),
        },
      },
    ],
  };
}

async function reload() {
  await loadWindows();
  await load();
}

watch([winKey, hours], () => void load());
watch(
  [
    () => store.state?.status?.sampled_at,
    () => store.state?.opencode_status?.sampled_at,
  ],
  () => {
    if (store.tab === "history") void load();
  },
);
watch(activeProvider, async () => {
  winKey.value = "";
  await reload();
  await nextTick();
  resizeChart();
});
watch(
  () => store.tab,
  async (tab) => {
    if (tab === "history") {
      await reload();
      await nextTick();
      resizeChart();
    }
  },
);

const ro = new ResizeObserver((entries) => {
  for (const entry of entries) {
    if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
      resizeChart();
    }
  }
});

onMounted(() => {
  if (chartEl.value) {
    ro.observe(chartEl.value);
  }
  void reload();
});

onUnmounted(() => {
  ro.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div class="mx-auto flex max-w-4xl flex-col gap-3.5">
    <!-- 过滤器栏：Linear 式胶囊切换 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <span class="text-xs font-semibold text-ink">观察窗口</span>
        <div class="flex rounded-lg border border-edge bg-well/80 p-0.5 shadow-inner">
          <button
            v-for="w in windows"
            :key="w.key"
            class="btn-press rounded-[6px] px-2.5 py-1 text-xs transition-all"
            :class="
              winKey === w.key
                ? 'bg-panel font-medium text-ink shadow-xs inset-highlight'
                : 'text-dim hover:text-ink'
            "
            @click="winKey = w.key"
          >
            {{ w.label }}
          </button>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span v-if="loading" class="text-[11px] text-faint">同步数据点…</span>
        <div class="flex rounded-lg border border-edge bg-well/80 p-0.5 shadow-inner">
          <button
            v-for="h in [24, 168] as const"
            :key="h"
            class="btn-press rounded-[6px] px-2.5 py-1 text-xs transition-all"
            :class="
              hours === h
                ? 'bg-panel font-medium text-ink shadow-xs inset-highlight'
                : 'text-dim hover:text-ink'
            "
            @click="hours = h"
          >
            {{ h === 24 ? "近 24 小时" : "近 7 天" }}
          </button>
        </div>
      </div>
    </div>

    <!-- 图表容器卡片 -->
    <div class="relative rounded-2xl border border-edge bg-panel p-3 shadow-card inset-highlight">
      <div
        v-if="empty && !loading"
        class="flex h-80 flex-col items-center justify-center text-center"
      >
        <div class="rounded-full bg-well p-3 text-dim">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
        </div>

        <template v-if="isOpencode && !ocHasToken">
          <p class="mt-2.5 text-xs font-medium text-ink">尚未配置 OpenCode API Key</p>
          <p class="mt-1 text-[11px] text-faint">请在偏好配置中配置 API Key 以开启额度监控与历史走势记录。</p>
          <button
            class="btn-press mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-1.5 text-xs font-medium text-white shadow-subtle hover:bg-brand-deep"
            @click="goOpenCodeSettings"
          >
            前往配置 API Key
          </button>
        </template>

        <template v-else>
          <p class="mt-2.5 text-xs font-medium text-ink">所选时间跨度内暂无轨迹记录</p>
          <p class="mt-1 max-w-sm text-[11px] text-faint">
            {{
              isOpencode
                ? "监控守护进程将随着每次探测周期自动描绘折线，也可随时立即采样汇入数据。"
                : isDemo
                  ? "沙盒正在后台以 60 倍速率回放，请稍候几秒等待点阵汇入。"
                  : "监控守护进程将随着每次探测周期自动描绘折线。"
            }}
          </p>
          <button
            v-if="isOpencode"
            class="btn-press mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-1.5 text-xs font-medium text-white shadow-subtle hover:bg-brand-deep"
            @click="sampleOpenCodeNow"
          >
            立即采样汇入数据
          </button>
        </template>
      </div>

      <div
        v-show="!empty || loading"
        ref="chartEl"
        class="h-80 w-full"
      ></div>
    </div>
  </div>
</template>