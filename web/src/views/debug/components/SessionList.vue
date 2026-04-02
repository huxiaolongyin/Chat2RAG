<script setup lang="ts">
import type { ChatSession } from "@/types/api"
import { Message as AMessage } from "@arco-design/web-vue"
import { Icon } from "@iconify/vue"

defineProps<{
  sessions: ChatSession[]
  sessionsLoading: boolean
  currentChatId: string | undefined
  showSessionList: boolean
  searchChatId: string
}>()

const emit = defineEmits<{
  startNewSession: []
  selectSession: [session: ChatSession]
  handleSearchChatId: []
  "update:showSessionList": [value: boolean]
  "update:searchChatId": [value: string]
}>()

function truncateText(text: string, maxLength: number = 30): string {
  if (!text) return "新会话"
  return text.length > maxLength ? text.substring(0, maxLength) + "..." : text
}

function formatSessionTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days === 0) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
  } else if (days === 1) {
    return "昨天"
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" })
  }
}

async function copyChatId(chatId: string) {
  try {
    await navigator.clipboard.writeText(chatId)
    AMessage.success("已复制")
  } catch (error) {
    console.error("Failed to copy chat id:", error)
  }
}
</script>

<template>
  <aside
    v-show="showSessionList"
    class="w-[260px] flex flex-col bg-slate-50 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 shrink-0"
  >
    <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
      <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">会话列表</span>
      <a-button size="small" type="primary" @click="emit('startNewSession')">
        <template #icon><Icon icon="mdi:plus" /></template>
        新会话
      </a-button>
    </div>
    <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-800">
      <a-input
        :model-value="searchChatId"
        placeholder="搜索 chat id"
        size="small"
        allow-clear
        @update:model-value="emit('update:searchChatId', $event)"
        @input="emit('handleSearchChatId')"
        @clear="emit('handleSearchChatId')"
      >
        <template #prefix>
          <Icon icon="mdi:magnify" class="text-slate-400" />
        </template>
      </a-input>
    </div>
    <div class="flex-1 overflow-y-auto custom-scrollbar">
      <div v-if="sessionsLoading" class="flex items-center justify-center py-8">
        <Icon icon="mdi:loading" class="text-2xl text-primary animate-spin" />
      </div>
      <div v-else-if="sessions.length === 0" class="text-center text-slate-400 py-8 text-sm">
        暂无会话记录
      </div>
      <div v-else class="py-2">
        <div
          v-for="session in sessions"
          :key="session.chatId"
          class="px-3 py-2.5 mx-2 rounded-lg cursor-pointer transition-colors group"
          :class="
            currentChatId === session.chatId
              ? 'bg-primary/10 border border-primary/20'
              : 'hover:bg-slate-100 dark:hover:bg-slate-800'
          "
          @click="emit('selectSession', session)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                {{ truncateText(session.firstQuestion) }}
              </p>
              <p class="text-[11px] text-slate-400 mt-1">
                {{ session.messageCount }} 条消息 · {{ formatSessionTime(session.updateTime) }}
              </p>
              <p
                class="text-[9px] text-slate-300 dark:text-slate-600 mt-1 font-mono truncate cursor-pointer hover:text-slate-400 dark:hover:text-slate-500 transition-colors"
                @click.stop="copyChatId(session.chatId)"
              >
                {{ session.chatId }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>