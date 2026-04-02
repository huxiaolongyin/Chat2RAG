<script setup lang="ts">
import type { Message } from "@/types/chat";
import { Icon } from "@iconify/vue";
import { computed } from "vue";

const props = defineProps<{
  message: Message;
  isLoading: boolean;
  audioState: "idle" | "loading" | "playing";
}>();

const emit = defineEmits<{
  copyMessage: [content: string];
  playAudio: [message: Message];
  openVideoPreview: [url: string];
}>();

function formatTime(date: Date): string {
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return (
    date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) +
    " " +
    date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
  );
}

const hasSourceOrDocument = computed(() => {
  return (
    props.message.source?.items?.length ||
    props.message.document ||
    props.message.tool?.toolName
  );
});
</script>

<template>
  <div
    class="flex items-start gap-4"
    :class="message.role === 'user' ? 'justify-end' : ''"
  >
    <div
      v-if="message.role === 'assistant'"
      class="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 border border-primary/20"
    >
      <Icon icon="mdi:robot" class="text-primary text-sm" />
    </div>

    <div
      class="flex flex-col"
      :class="
        message.role === 'user' ? 'items-end max-w-[80%]' : 'items-start max-w-[85%]'
      "
    >
      <span class="text-[11px] font-bold text-slate-400 mb-1 uppercase tracking-wider">
        {{ message.role === "user" ? "用户" : "AI助手" }}
      </span>

      <div
        class="px-4 py-3 rounded-2xl shadow-sm group relative"
        :class="
          message.role === 'user'
            ? 'bg-primary text-white rounded-tr-none'
            : 'bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-tl-none'
        "
      >
        <a-image
          v-if="message.image"
          :src="message.image"
          :preview="true"
          :preview-props="{ defaultScale: 0.5 }"
          class="max-w-[200px] max-h-[200px] rounded-lg mb-2 object-cover"
          alt="uploaded image"
        />
        <video
          v-if="message.video"
          :src="message.video"
          class="max-w-[200px] max-h-[200px] rounded-lg mb-2 object-cover cursor-pointer"
          @click="emit('openVideoPreview', message.video)"
        ></video>
        <p v-if="message.content" class="text-sm leading-relaxed whitespace-pre-wrap">
          {{ message.content }}
        </p>
        <div
          v-else-if="message.role === 'assistant' && isLoading"
          class="flex items-center gap-1"
        >
          <span
            class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"
            style="animation-delay: 0ms"
          ></span>
          <span
            class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"
            style="animation-delay: 150ms"
          ></span>
          <span
            class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"
            style="animation-delay: 300ms"
          ></span>
        </div>
        <p v-else class="text-sm leading-relaxed">...</p>

        <div
          class="absolute -top-3 flex gap-1"
          :class="message.role === 'user' ? '-left-2' : '-right-2'"
        >
          <button
            v-if="message.role === 'assistant' && message.content"
            class="w-6 h-6 rounded-full bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-slate-50 dark:hover:bg-slate-600"
            :class="{
              'opacity-100': audioState === 'playing' || audioState === 'loading',
            }"
            @click="emit('playAudio', message)"
          >
            <Icon
              v-if="audioState === 'loading'"
              icon="mdi:loading"
              class="text-xs text-primary animate-spin"
            />
            <Icon
              v-else-if="audioState === 'playing'"
              icon="mdi:stop"
              class="text-xs text-primary"
            />
            <Icon v-else icon="mdi:volume-high" class="text-xs text-slate-400" />
          </button>
          <button
            v-if="message.content"
            class="w-6 h-6 rounded-full bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-slate-50 dark:hover:bg-slate-600"
            @click="emit('copyMessage', message.content)"
          >
            <Icon icon="mdi:content-copy" class="text-xs text-slate-400" />
          </button>
        </div>
      </div>

      <div
        v-if="message.role === 'assistant' && hasSourceOrDocument"
        class="flex flex-wrap gap-1.5 mt-2"
      >
        <template v-for="(item, idx) in message.source?.items" :key="idx">
          <a
            v-if="
              item.type === 'document' && item.detail && !item.detail.endsWith('/json')
            "
            :href="`/${item.detail}`"
            target="_blank"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 cursor-pointer"
          >
            <Icon icon="mdi:file-document-outline" class="text-xs" />
            {{ item.display }}
            <Icon icon="mdi:download" class="text-[10px]" />
          </a>
          <span
            v-else-if="item.type === 'document'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
          >
            <Icon icon="mdi:file-document-outline" class="text-xs" />
            {{ item.display }}
          </span>
          <span
            v-else-if="item.type === 'command'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
          >
            <Icon icon="mdi:code-braces" class="text-xs" />
            {{ item.display }}
          </span>
          <a-popover v-else-if="item.type === 'tool'" trigger="click" position="top">
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900/50 transition-colors"
            >
              <Icon icon="mdi:wrench" class="text-xs" />
              {{ item.display }}
            </span>
            <template #content>
              <div class="text-xs space-y-2 max-w-xs">
                <div v-if="message.tool?.toolName">
                  <span class="text-slate-400">工具名称:</span>
                  <span class="ml-1 font-medium">{{ message.tool.toolName }}</span>
                </div>
                <div
                  v-if="
                    message.tool?.arguments &&
                    Object.keys(message.tool.arguments).length > 0
                  "
                >
                  <span class="text-slate-400">调用参数:</span>
                  <pre
                    class="ml-1 mt-1 p-2 bg-slate-100 dark:bg-slate-800 rounded text-[10px] overflow-x-auto"
                    >{{ JSON.stringify(message.tool.arguments, null, 2) }}</pre
                  >
                </div>
                <div v-if="message.tool?.toolResult">
                  <span class="text-slate-400">返回结果:</span>
                  <pre
                    class="ml-1 mt-1 p-2 bg-slate-100 dark:bg-slate-800 rounded text-[10px] overflow-x-auto max-h-32"
                    >{{
                      typeof message.tool.toolResult === "object"
                        ? JSON.stringify(message.tool.toolResult, null, 2)
                        : message.tool.toolResult
                    }}</pre
                  >
                </div>
              </div>
            </template>
          </a-popover>
          <span
            v-else-if="item.type === 'llm'"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          >
            <Icon icon="mdi:robot" class="text-xs" />
            {{ item.display }}
          </span>
        </template>

        <a-popover
          v-if="message.document && Object.keys(message.document).length > 0"
          trigger="click"
          position="top"
        >
          <span
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 cursor-pointer hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors"
          >
            <Icon icon="mdi:file-search-outline" class="text-xs" />
            {{
              Object.values(message.document).reduce((sum, docs) => sum + docs.length, 0)
            }}
            个知识点来源
          </span>
          <template #content>
            <div class="text-xs space-y-3 max-w-md max-h-64 overflow-y-auto">
              <div v-for="(docs, collection) in message.document" :key="collection">
                <div class="text-slate-500 font-medium mb-1 flex items-center gap-1">
                  <Icon icon="mdi:database" class="text-xs" />
                  {{ collection }}
                </div>
                <div class="space-y-1.5">
                  <div
                    v-for="(doc, docIdx) in docs"
                    :key="docIdx"
                    class="p-2 bg-slate-50 dark:bg-slate-800 rounded text-[11px]"
                  >
                    <div class="text-slate-600 dark:text-slate-300 line-clamp-3">
                      {{ doc.content }}
                    </div>
                    <div
                      v-if="doc.score !== null"
                      class="text-[10px] text-slate-400 mt-1"
                    >
                      相似度: {{ (doc.score * 100).toFixed(1) }}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </a-popover>
      </div>

      <span class="text-[10px] text-slate-400 mt-1">
        {{ formatTime(message.timestamp) }}
        <span v-if="message.firstTokenLatency">
          · 首字: {{ message.firstTokenLatency }}s</span
        >
        <span v-if="message.latency"> · 延迟: {{ message.latency }}s</span>
      </span>
    </div>

    <div
      v-if="message.role === 'user'"
      class="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0 border border-slate-200"
    >
      <Icon icon="mdi:account" class="text-slate-400 text-sm" />
    </div>
  </div>
</template>
