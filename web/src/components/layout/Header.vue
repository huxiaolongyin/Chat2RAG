<script setup lang="ts">
import { ref } from 'vue'
import { Icon } from '@iconify/vue'

const searchValue = ref('')
</script>

<template>
  <header
    class="flex items-center justify-between h-14 px-6 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shrink-0"
  >
    <div class="flex items-center gap-2">
      <span class="text-sm font-medium text-slate-500 dark:text-slate-400">环境:</span>
      <a-tag color="arcoblue" size="small">Staging-v1.0.0</a-tag>
    </div>

    <div class="flex items-center gap-4">
      <div class="relative w-64">
        <Icon icon="mdi:magnify" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg" />
        <a-input
          v-model="searchValue"
          placeholder="搜索..."
          class="w-full! bg-slate-100 dark:bg-slate-800 border-none!"
          :input-style="{ paddingLeft: '2.5rem' }"
          allow-clear
        />
      </div>

      <a-badge :count="3" :dot="true">
        <a-button type="text" shape="circle">
          <template #icon>
            <Icon icon="mdi:bell-outline" class="text-lg" />
          </template>
        </a-button>
      </a-badge>
    </div>
  </header>
</template>