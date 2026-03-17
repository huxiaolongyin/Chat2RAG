<script setup lang="ts">
import { ref } from 'vue'

const apiConnected = ref(true)
const ragIndexed = ref(true)
</script>

<template>
  <footer
    class="flex items-center justify-between h-10 px-6 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 shrink-0"
  >
    <div class="flex gap-4">
      <div class="flex items-center gap-1.5">
        <div
          class="size-2 rounded-full"
          :class="apiConnected ? 'bg-emerald-500' : 'bg-red-500'"
        ></div>
        <span class="text-[10px] font-bold text-slate-500">API: {{ apiConnected ? '已连接' : '未连接' }}</span>
      </div>
      <div class="flex items-center gap-1.5">
        <div
          class="size-2 rounded-full"
          :class="ragIndexed ? 'bg-emerald-500' : 'bg-red-500'"
        ></div>
        <span class="text-[10px] font-bold text-slate-500">RAG: {{ ragIndexed ? '已索引' : '未索引' }}</span>
      </div>
    </div>

    <div class="flex items-center gap-4 text-[10px] font-bold text-slate-400">
      <a href="#" class="hover:text-primary transition-colors">文档</a>
      <a href="#" class="hover:text-primary transition-colors">API密钥</a>
      <a href="#" class="hover:text-primary transition-colors">支持</a>
    </div>
  </footer>
</template>