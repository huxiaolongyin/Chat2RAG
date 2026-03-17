<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'

const router = useRouter()

const quickActions = [
  { icon: 'mdi:chat', label: '交互调试', path: '/debug', color: 'bg-primary' },
  { icon: 'mdi:database', label: '知识库管理', path: '/knowledge', color: 'bg-emerald-500' },
  { icon: 'mdi:tools', label: '工具管理', path: '/tools', color: 'bg-amber-500' },
  { icon: 'mdi:chart-line', label: '数据分析', path: '/analytics', color: 'bg-violet-500' },
]

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="p-8">
    <div class="max-w-4xl mx-auto">
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">欢迎使用 Chat2RAG</h1>
        <p class="text-slate-500 dark:text-slate-400">AI交互管理平台，支持知识库检索、RAG对话、工具调用等功能</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div
          v-for="action in quickActions"
          :key="action.path"
          class="p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 cursor-pointer hover:shadow-lg transition-shadow"
          @click="navigateTo(action.path)"
        >
          <div :class="[action.color, 'w-10 h-10 rounded-lg flex items-center justify-center mb-3']">
            <Icon :icon="action.icon" class="text-white text-xl" />
          </div>
          <h3 class="font-semibold text-slate-900 dark:text-white">{{ action.label }}</h3>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <h3 class="font-semibold text-slate-900 dark:text-white mb-4">系统状态</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">API服务</span>
              <a-tag color="green">正常</a-tag>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">向量数据库</span>
              <a-tag color="green">正常</a-tag>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">模型服务</span>
              <a-tag color="green">正常</a-tag>
            </div>
          </div>
        </div>

        <div class="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <h3 class="font-semibold text-slate-900 dark:text-white mb-4">快速统计</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">知识库数量</span>
              <span class="font-bold text-slate-900 dark:text-white">0</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">今日对话</span>
              <span class="font-bold text-slate-900 dark:text-white">0</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">工具数量</span>
              <span class="font-bold text-slate-900 dark:text-white">0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>