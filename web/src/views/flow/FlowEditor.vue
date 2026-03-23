<script setup lang="ts">
import { flowApi } from "@/api/flow";
import type { Flow } from "@/types/api";
import { Icon } from "@iconify/vue";
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const flowId = Number(route.params.id);
const loading = ref(true);
const flow = ref<Flow | null>(null);

async function loadFlow() {
  loading.value = true;
  try {
    const res = await flowApi.getFlow(flowId);
    if (res.code === "0000" && res.data) {
      flow.value = res.data;
    }
  } catch (e) {
    console.error("Failed to load flow:", e);
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push("/rules/flows");
}

onMounted(() => {
  loadFlow();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <a-button type="text" @click="goBack">
            <template #icon><Icon icon="mdi:arrow-left" /></template>
          </a-button>
          <div class="h-5 w-px bg-slate-200 dark:bg-slate-700"></div>
          <Icon icon="mdi:account-tree" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">
            {{ flow?.name || "流程编辑器" }}
          </h1>
        </div>
        <div class="flex items-center gap-3">
          <a-button type="primary">
            <template #icon><Icon icon="mdi:content-save" /></template>
            保存
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-spin :loading="loading" class="w-full h-full">
        <div
          class="flex items-center justify-center h-full bg-slate-50 dark:bg-slate-900 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700"
        >
          <div class="text-center">
            <Icon
              icon="mdi:account-tree-outline"
              class="text-6xl text-slate-300 dark:text-slate-600 mb-4"
            />
            <p class="text-slate-400 dark:text-slate-500 text-lg">流程编辑器开发中...</p>
            <p class="text-slate-300 dark:text-slate-600 text-sm mt-2">
              ID: {{ flowId }} | 名称: {{ flow?.name || "-" }}
            </p>
          </div>
        </div>
      </a-spin>
    </div>
  </div>
</template>