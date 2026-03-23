<script setup lang="ts">
import { getKnowledgeCollections } from "@/api/chat";
import { getHotQuestions, getMetrics } from "@/api/metric";
import type { HotQuestionData, KnowledgeCollection, MetricData } from "@/types/api";
import { Icon } from "@iconify/vue";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { computed, onMounted, reactive, ref, watch } from "vue";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

const activeTab = ref("metrics");
const loading = ref(false);

const datePreset = ref<number>(30);
const dateRange = ref<string[]>([]);
const selectedCollection = ref<string>("");

const collections = ref<KnowledgeCollection[]>([]);

const stats = reactive({
  totalSessions: 0,
  totalMessages: 0,
  totalInputTokens: 0,
  totalOutputTokens: 0,
  avgResponseMs: 0,
});

const metricsPagination = reactive({ current: 1, pageSize: 20, total: 0 });
const metrics = ref<MetricData[]>([]);
const metricsSearch = ref("");

const hotQuestionsDays = ref<number>(30);
const hotQuestions = ref<HotQuestionData[]>([]);
const hotQuestionsLoading = ref(false);

const hotQuestionDetailVisible = ref(false);
const selectedHotQuestion = ref<HotQuestionData | null>(null);

const collectionChartData = computed(() => {
  const collectionCount: Record<string, number> = {};
  metrics.value.forEach((m) => {
    if (m.collections) {
      const cols = m.collections
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      cols.forEach((col) => {
        collectionCount[col] = (collectionCount[col] || 0) + 1;
      });
    } else {
      collectionCount["无知识库"] = (collectionCount["无知识库"] || 0) + 1;
    }
  });

  const data = Object.entries(collectionCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({ name, value }));

  return {
    title: {
      text: "知识库分布",
      left: "center",
      textStyle: { fontSize: 14, fontWeight: 600 },
    },
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      orient: "vertical",
      right: 10,
      top: "center",
      type: "scroll",
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["35%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 12, fontWeight: "bold" },
        },
        labelLine: { show: false },
        data,
      },
    ],
  };
});

const responseTimeChartData = computed(() => {
  const bins = [
    { name: "<500ms", min: 0, max: 500, count: 0 },
    { name: "500ms-1s", min: 500, max: 1000, count: 0 },
    { name: "1s-2s", min: 1000, max: 2000, count: 0 },
    { name: "2s-5s", min: 2000, max: 5000, count: 0 },
    { name: ">5s", min: 5000, max: Infinity, count: 0 },
  ];

  metrics.value.forEach((m) => {
    if (m.totalMs) {
      const ms = m.totalMs;
      for (const bin of bins) {
        if (ms >= bin.min && ms < bin.max) {
          bin.count++;
          break;
        }
      }
    }
  });

  return {
    title: {
      text: "响应时长分布",
      left: "center",
      textStyle: { fontSize: 14, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: bins.map((b) => b.name),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: "value",
      name: "次数",
    },
    series: [
      {
        type: "bar",
        data: bins.map((b) => b.count),
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "#6366f1" },
              { offset: 1, color: "#a5b4fc" },
            ],
          },
        },
        barWidth: "50%",
      },
    ],
  };
});

const toolUsageChartData = computed(() => {
  const toolCount: Record<string, number> = {};

  metrics.value.forEach((m) => {
    if (m.executeTools) {
      const tools = m.executeTools
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      tools.forEach((tool) => {
        toolCount[tool] = (toolCount[tool] || 0) + 1;
      });
    }
  });

  const data = Object.entries(toolCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return {
    title: {
      text: "技能调用统计",
      left: "center",
      textStyle: { fontSize: 14, fontWeight: 600 },
    },
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c}次 ({d}%)",
    },
    legend: {
      orient: "vertical",
      right: 10,
      top: "center",
      type: "scroll",
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["35%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 12, fontWeight: "bold" },
        },
        labelLine: { show: false },
        data: data.map(([name, value]) => ({ name, value })),
      },
    ],
  };
});

const hotQuestionsChartData = computed(() => {
  const top20 = hotQuestions.value.slice(0, 20);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: { name: string; value: number }[]) => {
        const item = params[0];
        const hq = hotQuestions.value.find((h) => h.representativeQuestion === item.name);
        return `
          <div style="max-width: 300px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${item.name}</div>
            <div>出现次数: ${item.value}</div>
            ${hq ? `<div>相似问题: ${hq.clusterSize}个</div>` : ""}
          </div>
        `;
      },
    },
    grid: {
      left: "3%",
      right: "8%",
      bottom: "3%",
      top: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      name: "次数",
    },
    yAxis: {
      type: "category",
      data: top20
        .map((h) =>
          h.representativeQuestion.length > 25
            ? h.representativeQuestion.slice(0, 25) + "..."
            : h.representativeQuestion
        )
        .reverse(),
      axisLabel: {
        fontSize: 11,
        width: 200,
        overflow: "truncate",
      },
    },
    series: [
      {
        type: "bar",
        data: top20.map((h) => h.count).reverse(),
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: "#f97316" },
              { offset: 1, color: "#fdba74" },
            ],
          },
        },
        barWidth: "60%",
      },
    ],
  };
});

async function loadCollections() {
  const result = await getKnowledgeCollections(1, 100);
  collections.value = result || [];
}

async function loadStats() {
  loading.value = true;
  try {
    const startTime = dateRange.value?.[0] || undefined;
    const endTime = dateRange.value?.[1] || undefined;
    const res = await getMetrics({
      size: 10000,
      startTime,
      endTime,
      collection: selectedCollection.value || undefined,
    });

    stats.totalMessages = res.total;

    const chatIds = new Set<string>();
    let totalInput = 0;
    let totalOutput = 0;
    let totalMs = 0;
    let msCount = 0;

    res.items.forEach((m) => {
      if (m.chatId) chatIds.add(m.chatId);
      totalInput += m.inputTokens || 0;
      totalOutput += m.outputTokens || 0;
      if (m.totalMs) {
        totalMs += m.totalMs;
        msCount++;
      }
    });

    stats.totalSessions = chatIds.size;
    stats.totalInputTokens = totalInput;
    stats.totalOutputTokens = totalOutput;
    stats.avgResponseMs = msCount > 0 ? Math.round(totalMs / msCount) : 0;

    metrics.value = res.items;
    metricsPagination.total = res.total;
  } catch (e) {
    console.error("Failed to load stats:", e);
  } finally {
    loading.value = false;
  }
}

async function loadMetrics() {
  loading.value = true;
  try {
    const startTime = dateRange.value?.[0] || undefined;
    const endTime = dateRange.value?.[1] || undefined;
    const result = await getMetrics({
      current: metricsPagination.current,
      size: metricsPagination.pageSize,
      startTime,
      endTime,
      collection: selectedCollection.value || undefined,
    });
    metrics.value = result.items;
    metricsPagination.total = result.total;
  } catch (e) {
    console.error("Failed to load metrics:", e);
  } finally {
    loading.value = false;
  }
}

async function loadHotQuestions() {
  hotQuestionsLoading.value = true;
  try {
    const result = await getHotQuestions({
      collection: selectedCollection.value || undefined,
      days: hotQuestionsDays.value || undefined,
      limit: 50,
    });
    hotQuestions.value = result;
  } catch (e) {
    console.error("Failed to load hot questions:", e);
  } finally {
    hotQuestionsLoading.value = false;
  }
}

function handleSearch() {
  if (activeTab.value === "metrics") {
    metricsPagination.current = 1;
    loadMetrics();
  } else if (activeTab.value === "hotQuestions") {
    loadHotQuestions();
  }
}

function setDatePreset(days: number) {
  datePreset.value = days;
  if (days === 0) {
    dateRange.value = [];
  } else {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    dateRange.value = [
      start.toISOString().split("T")[0],
      end.toISOString().split("T")[0],
    ];
  }
  handleDateChange();
}

function handleDateChange() {
  loadStats();
  handleSearch();
}

function handleCollectionChange() {
  loadStats();
  handleSearch();
}

function handleMetricsPageChange(page: number) {
  metricsPagination.current = page;
  loadMetrics();
}

function handleHotQuestionsDaysChange() {
  loadHotQuestions();
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return String(num);
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("zh-CN");
}

function filterMetrics() {
  if (!metricsSearch.value.trim()) return metrics.value;
  const keyword = metricsSearch.value.toLowerCase();
  return metrics.value.filter(
    (m) =>
      m.question.toLowerCase().includes(keyword) ||
      m.answer?.toLowerCase().includes(keyword)
  );
}

const filteredMetrics = computed(() => filterMetrics());

function showHotQuestionDetail(question: HotQuestionData) {
  selectedHotQuestion.value = question;
  hotQuestionDetailVisible.value = true;
}

function handleHotQuestionChartClick(params: { name: string }) {
  const question = hotQuestions.value.find(
    (h) =>
      h.representativeQuestion === params.name ||
      h.representativeQuestion.slice(0, 25) + "..." === params.name
  );
  if (question) {
    showHotQuestionDetail(question);
  }
}

watch(activeTab, () => {
  if (activeTab.value === "metrics" && metrics.value.length === 0) {
    loadMetrics();
  } else if (activeTab.value === "hotQuestions" && hotQuestions.value.length === 0) {
    loadHotQuestions();
  }
});

onMounted(() => {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  dateRange.value = [start.toISOString().split("T")[0], end.toISOString().split("T")[0]];
  loadCollections();
  loadStats();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-3 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:chart-line" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">数据分析</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-radio-group
            :model-value="datePreset"
            type="button"
            size="small"
            @change="(val: number | string) => setDatePreset(Number(val))"
          >
            <a-radio :value="7">近7天</a-radio>
            <a-radio :value="30">近30天</a-radio>
            <a-radio :value="90">近90天</a-radio>
            <a-radio :value="0">全部</a-radio>
          </a-radio-group>
          <a-range-picker
            v-model="dateRange"
            style="width: 240px"
            :placeholder="['开始日期', '结束日期']"
            allow-clear
            @change="handleDateChange"
            @clear="handleDateChange"
          />
          <a-select
            v-model="selectedCollection"
            placeholder="全部知识库"
            allow-clear
            style="width: 180px"
            @change="handleCollectionChange"
          >
            <a-option
              v-for="c in collections"
              :key="c.collectionName"
              :value="c.collectionName"
            >
              {{ c.collectionName }}
            </a-option>
          </a-select>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
        >
          <div class="flex items-center gap-3 mb-2">
            <div
              class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"
            >
              <Icon
                icon="mdi:chat-outline"
                class="text-xl text-blue-600 dark:text-blue-400"
              />
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">会话总数</span>
          </div>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">
            {{ formatNumber(stats.totalSessions) }}
          </p>
        </div>

        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
        >
          <div class="flex items-center gap-3 mb-2">
            <div
              class="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center"
            >
              <Icon
                icon="mdi:message-text-outline"
                class="text-xl text-emerald-600 dark:text-emerald-400"
              />
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">消息总数</span>
          </div>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">
            {{ formatNumber(stats.totalMessages) }}
          </p>
        </div>

        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
        >
          <div class="flex items-center gap-3 mb-2">
            <div
              class="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center"
            >
              <Icon
                icon="mdi:arrow-up-bold"
                class="text-xl text-amber-600 dark:text-amber-400"
              />
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">输入Token</span>
          </div>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">
            {{ formatNumber(stats.totalInputTokens) }}
          </p>
        </div>

        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
        >
          <div class="flex items-center gap-3 mb-2">
            <div
              class="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center"
            >
              <Icon
                icon="mdi:arrow-down-bold"
                class="text-xl text-purple-600 dark:text-purple-400"
              />
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">输出Token</span>
          </div>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">
            {{ formatNumber(stats.totalOutputTokens) }}
          </p>
        </div>

        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
        >
          <div class="flex items-center gap-3 mb-2">
            <div
              class="w-10 h-10 rounded-lg bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center"
            >
              <Icon
                icon="mdi:speedometer"
                class="text-xl text-rose-600 dark:text-rose-400"
              />
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">平均响应</span>
          </div>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">
            {{ stats.avgResponseMs
            }}<span class="text-sm font-normal text-slate-400 ml-1">ms</span>
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
        >
          <v-chart :option="collectionChartData" autoresize style="height: 300px" />
        </div>
        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
        >
          <v-chart :option="responseTimeChartData" autoresize style="height: 300px" />
        </div>
        <div
          class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
        >
          <v-chart :option="toolUsageChartData" autoresize style="height: 300px" />
        </div>
      </div>

      <div
        class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
      >
        <a-tabs v-model:active-key="activeTab" class="px-4">
          <a-tab-pane key="metrics" title="对话历史">
            <div class="pb-4">
              <div class="mb-4">
                <a-input-search
                  v-model="metricsSearch"
                  placeholder="搜索问题或回答..."
                  style="width: 300px"
                  allow-clear
                />
              </div>
              <a-table
                :data="filteredMetrics"
                :loading="loading"
                :pagination="{
                  current: metricsPagination.current,
                  pageSize: metricsPagination.pageSize,
                  total: metricsPagination.total,
                  showTotal: true,
                }"
                @page-change="handleMetricsPageChange"
              >
                <template #columns>
                  <a-table-column
                    title="问题"
                    data-index="question"
                    :ellipsis="true"
                    :tooltip="true"
                  >
                    <template #cell="{ record }">
                      <span class="text-slate-700 dark:text-slate-200">{{
                        record.question
                      }}</span>
                    </template>
                  </a-table-column>
                  <a-table-column
                    title="回答"
                    data-index="answer"
                    :ellipsis="true"
                    :tooltip="true"
                    :width="600"
                  >
                    <template #cell="{ record }">
                      <span
                        v-if="record.answer"
                        class="text-slate-600 dark:text-slate-300"
                        >{{ record.answer }}</span
                      >
                      <span v-else class="text-slate-400">-</span>
                    </template>
                  </a-table-column>
                  <a-table-column title="模型" data-index="model" :width="150">
                    <template #cell="{ record }">
                      <a-tag v-if="record.model" color="arcoblue" size="small">{{
                        record.model
                      }}</a-tag>
                      <span v-else class="text-slate-400">-</span>
                    </template>
                  </a-table-column>
                  <a-table-column
                    title="知识库"
                    data-index="collections"
                    :width="150"
                    :ellipsis="true"
                  >
                    <template #cell="{ record }">
                      <span v-if="record.collections" class="text-sm">{{
                        record.collections
                      }}</span>
                      <span v-else class="text-slate-400">-</span>
                    </template>
                  </a-table-column>
                  <a-table-column
                    title="响应时间"
                    data-index="totalMs"
                    :width="120"
                    align="center"
                  >
                    <template #cell="{ record }">
                      <span v-if="record.totalMs" class="text-rose-600 dark:text-rose-400"
                        >{{ Math.round(record.totalMs) }}ms</span
                      >
                      <span v-else class="text-slate-400">-</span>
                    </template>
                  </a-table-column>
                  <a-table-column title="创建时间" data-index="createTime" :width="180">
                    <template #cell="{ record }">
                      <span class="text-sm text-slate-500">{{
                        formatDateTime(record.createTime)
                      }}</span>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </div>
          </a-tab-pane>

          <a-tab-pane key="hotQuestions" title="热点问题">
            <div class="pb-4">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-slate-500">统计周期：</span>
                  <a-radio-group
                    v-model="hotQuestionsDays"
                    type="button"
                    size="small"
                    @change="handleHotQuestionsDaysChange"
                  >
                    <a-radio :value="7">7天</a-radio>
                    <a-radio :value="30">30天</a-radio>
                    <a-radio :value="90">90天</a-radio>
                    <a-radio :value="0">全部</a-radio>
                  </a-radio-group>
                </div>
                <span class="text-sm text-slate-500"
                  >共 {{ hotQuestions.length }} 个热点问题</span
                >
              </div>

              <a-spin :loading="hotQuestionsLoading" class="w-full">
                <div
                  v-if="hotQuestions.length === 0 && !hotQuestionsLoading"
                  class="text-center py-16"
                >
                  <Icon
                    icon="mdi:fire-off"
                    class="text-5xl text-slate-300 dark:text-slate-600 mb-4"
                  />
                  <p class="text-slate-400 dark:text-slate-500">暂无热点问题数据</p>
                </div>
                <div v-else class="bg-slate-50 dark:bg-slate-700/30 rounded-lg p-4">
                  <v-chart
                    :option="hotQuestionsChartData"
                    autoresize
                    style="height: 500px"
                    @click="handleHotQuestionChartClick"
                  />
                  <p class="text-center text-xs text-slate-400 mt-2">
                    点击柱状图查看详情
                  </p>
                </div>
              </a-spin>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <a-modal
      v-model:visible="hotQuestionDetailVisible"
      title="热点问题详情"
      :width="720"
      :footer="false"
    >
      <div v-if="selectedHotQuestion" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-1">出现次数</p>
            <p class="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {{ selectedHotQuestion.count }}
            </p>
          </div>
          <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-1">相似问题数</p>
            <p class="text-2xl font-bold text-slate-900 dark:text-white">
              {{ selectedHotQuestion.clusterSize }}
            </p>
          </div>
        </div>

        <div>
          <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            代表性问题
          </p>
          <div
            class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800"
          >
            <p class="text-slate-800 dark:text-slate-200">
              {{ selectedHotQuestion.representativeQuestion }}
            </p>
          </div>
        </div>

        <div>
          <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            相似问题列表 ({{ selectedHotQuestion.similarQuestions.length }}个)
          </p>
          <a-table
            :data="selectedHotQuestion.similarQuestions"
            :pagination="{ pageSize: 10 }"
            size="small"
          >
            <template #columns>
              <a-table-column
                title="问题"
                data-index="text"
                :ellipsis="true"
                :tooltip="true"
              />
              <a-table-column title="知识库" data-index="collection" :width="150">
                <template #cell="{ record }">
                  <a-tag size="small" color="green">{{ record.collection }}</a-tag>
                </template>
              </a-table-column>
              <a-table-column title="次数" data-index="count" :width="80" align="center">
                <template #cell="{ record }">
                  <span class="text-orange-600 dark:text-orange-400 font-medium">{{
                    record.count
                  }}</span>
                </template>
              </a-table-column>
              <a-table-column title="更新时间" :width="160">
                <template #cell="{ record }">
                  <span class="text-xs text-slate-500">{{
                    formatDateTime(record.updateTime)
                  }}</span>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
      </div>
    </a-modal>
  </div>
</template>
