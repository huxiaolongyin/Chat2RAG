<script setup lang="ts">
import {
  getChatSessions,
  getKnowledgeCollections,
  getModels,
  getPrompts,
  getSessionMessages,
  getSessionStats,
  getTools,
  streamChat,
} from "@/api/chat";
import { useChatStore } from "@/stores/chat";
import type {
  ChatSession,
  KnowledgeCollection,
  ModelOption,
  Prompt,
  SessionStats,
  Tool,
} from "@/types/api";
import type { Message } from "@/types/chat";
import { Icon } from "@iconify/vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();

const models = ref<ModelOption[]>([]);
const collections = ref<KnowledgeCollection[]>([]);
const inputText = ref("");
const inputImage = ref("");
const messagesContainer = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const selectedModel = ref("");
const selectedCollection = ref<string[]>([]);
const selectedPrompt = ref("默认");

const temperature = ref(0.7);

const topP = ref(0.9);

const scoreThreshold = ref(0.6);
const topK = ref(5);

const precisionMode = ref(false);
const batchOrStream = ref<"batch" | "stream">("stream");
const extraParamsText = ref("");
const extraParamsError = ref("");

const tools = ref<Tool[]>([]);
const prompts = ref<Prompt[]>([]);
const selectedTools = ref<string[]>([]);

const promptTokens = ref(0);
const completionTokens = ref(0);
const totalCost = ref(0);

const sessions = ref<ChatSession[]>([]);
const sessionsTotal = ref(0);
const sessionsPage = ref(1);
const sessionsLoading = ref(false);
const sessionStats = ref<SessionStats | null>(null);
const showSessionList = ref(true);
const searchChatId = ref("");
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const isLoading = computed(() => chatStore.isLoading);

function validateExtraParams(): Record<string, unknown> | undefined {
  if (!extraParamsText.value.trim()) {
    extraParamsError.value = "";
    return undefined;
  }
  try {
    const parsed = JSON.parse(extraParamsText.value);
    extraParamsError.value = "";
    return parsed;
  } catch {
    extraParamsError.value = "JSON 格式错误";
    return undefined;
  }
}

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

function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content);
  } catch (error) {
    console.error("Failed to copy:", error);
  }
}

function handleImageSelect(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    inputImage.value = e.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  inputImage.value = "";
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

async function scrollToBottom() {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

async function sendMessage() {
  const text = inputText.value.trim();
  const image = inputImage.value;
  if ((!text && !image) || isLoading.value) return;

  const isFirstMessage = chatStore.messages.length === 0;

  const userMessage: Message = {
    id: generateId(),
    role: "user",
    content: text,
    timestamp: new Date(),
    image: image || undefined,
  };
  chatStore.addMessage(userMessage);
  inputText.value = "";
  inputImage.value = "";
  if (fileInput.value) {
    fileInput.value.value = "";
  }
  await scrollToBottom();

  const assistantMessage: Message = {
    id: generateId(),
    role: "assistant",
    content: "",
    timestamp: new Date(),
  };
  chatStore.addMessage(assistantMessage);
  chatStore.setLoading(true);
  scrollToBottom();

  const startTime = Date.now();
  let firstChunkReceived = false;

  try {
    await streamChat({
      request: {
        model: selectedModel.value || "Qwen3-235B",
        collections: selectedCollection.value,
        content: { text, image: image || undefined },
        generation_kwargs: {
          temperature: temperature.value,

          top_p: topP.value,
        },
        chatId: chatStore.chatId || undefined,
        chatRounds: 5,
        promptName: selectedPrompt.value || undefined,
        tools: selectedTools.value.length > 0 ? selectedTools.value : undefined,
        scoreThreshold: scoreThreshold.value,
        topK: topK.value,
        precisionMode: precisionMode.value ? 1 : 0,
        batchOrStream: batchOrStream.value,
        extraParams: validateExtraParams(),
      },
      onChunk: (chunk) => {
        const lastMessage = chatStore.messages[chatStore.messages.length - 1];
        if (chunk.status === 1 && chunk.content?.text) {
          if (!firstChunkReceived) {
            firstChunkReceived = true;
            const firstTokenLatency = ((Date.now() - startTime) / 1000).toFixed(1);
            lastMessage.firstTokenLatency = parseFloat(firstTokenLatency);
          }
          chatStore.appendLastMessage(chunk.content.text);
          scrollToBottom();
        }
        if (chunk.source) {
          lastMessage.source = chunk.source;
        }
        if (chunk.document) {
          lastMessage.document = chunk.document;
          const docCount = Object.values(chunk.document).reduce(
            (sum, docs) => sum + docs.length,
            0
          );
          promptTokens.value = docCount * 100;
        }
        if (chunk.tool?.toolName) {
          lastMessage.tool = chunk.tool;
        }
        if (chunk.link) {
          lastMessage.link = chunk.link;
        }
      },
      onError: (error) => {
        console.error("Stream error:", error);
        chatStore.updateLastMessage("抱歉，发生了错误，请重试。");
        chatStore.setLoading(false);
      },
      onComplete: async () => {
        const latency = ((Date.now() - startTime) / 1000).toFixed(1);
        chatStore.messages[chatStore.messages.length - 1].latency = parseFloat(latency);
        completionTokens.value =
          chatStore.messages[chatStore.messages.length - 1].content.length;
        totalCost.value = (promptTokens.value + completionTokens.value) * 0.00001;
        chatStore.setLoading(false);
        scrollToBottom();
        if (chatStore.chatId) {
          sessionStats.value = await getSessionStats(chatStore.chatId);
        }
        if (isFirstMessage) {
          loadSessions();
        }
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    chatStore.updateLastMessage("抱歉，发生了错误，请重试。");
    chatStore.setLoading(false);
  }
}

async function loadSessions() {
  sessionsLoading.value = true;
  try {
    const result = await getChatSessions(
      sessionsPage.value,
      20,
      undefined,
      undefined,
      searchChatId.value || undefined
    );
    sessions.value = result.items;
    sessionsTotal.value = result.total;
  } catch (error) {
    console.error("Failed to load sessions:", error);
  } finally {
    sessionsLoading.value = false;
  }
}

function handleSearchChatId() {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
  searchDebounceTimer = setTimeout(() => {
    sessionsPage.value = 1;
    loadSessions();
  }, 300);
}

async function selectSession(session: ChatSession) {
  router.push({ path: route.path, query: { chatId: session.chatId } });
}

async function loadSessionHistory(chatId: string) {
  try {
    const [stats, messages] = await Promise.all([
      getSessionStats(chatId),
      getSessionMessages(chatId),
    ]);
    sessionStats.value = stats;
    chatStore.setChatId(chatId);

    chatStore.messages = [];
    const sortedMessages = [...messages].sort(
      (a, b) => new Date(a.createTime).getTime() - new Date(b.createTime).getTime()
    );

    for (const metric of sortedMessages) {
      if (metric.question) {
        chatStore.addMessage({
          id: crypto.randomUUID(),
          role: "user",
          content: metric.question,
          timestamp: new Date(metric.createTime),
        });
      }
      if (metric.answer) {
        chatStore.addMessage({
          id: crypto.randomUUID(),
          role: "assistant",
          content: metric.answer,
          timestamp: new Date(metric.createTime),
          latency: metric.totalMs
            ? parseFloat((metric.totalMs / 1000).toFixed(2))
            : undefined,
          firstTokenLatency: metric.firstResponseMs
            ? parseFloat((metric.firstResponseMs / 1000).toFixed(2))
            : undefined,
          source: metric.source ? { items: metric.source } : undefined,
          tool: metric.toolResult
            ? {
                toolName: metric.executeTools || "",
                toolType: "",
                arguments: metric.toolArguments || {},
                toolResult: metric.toolResult,
              }
            : undefined,
          document: metric.retrievalDocuments,
        });
      }
    }
    await scrollToBottom();
  } catch (error) {
    console.error("Failed to load session history:", error);
  }
}

function startNewSession() {
  chatStore.clearMessages();
  chatStore.setChatId(crypto.randomUUID());
  promptTokens.value = 0;
  completionTokens.value = 0;
  totalCost.value = 0;
  sessionStats.value = null;
  router.push({ path: route.path });
}

function truncateText(text: string, maxLength: number = 30): string {
  if (!text) return "新会话";
  return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
}

function formatSessionTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } else if (days === 1) {
    return "昨天";
  } else if (days < 7) {
    return `${days}天前`;
  } else {
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  }
}

watch(
  () => route.query.chatId,
  (chatId) => {
    if (chatId && typeof chatId === "string") {
      loadSessionHistory(chatId);
    }
  },
  { immediate: true }
);

onMounted(async () => {
  try {
    const [modelsData, collectionsData, promptsData, toolsData] = await Promise.all([
      getModels(),
      getKnowledgeCollections(),
      getPrompts(),
      getTools(),
    ]);
    models.value = modelsData;
    collections.value = collectionsData;
    prompts.value = promptsData;
    tools.value = toolsData;
    if (models.value.length > 0) {
      selectedModel.value = models.value[0].id;
    }
    await loadSessions();
    const chatId = route.query.chatId;
    if (chatId && typeof chatId === "string") {
      await loadSessionHistory(chatId);
    }
  } catch (error) {
    console.error("Failed to load data:", error);
  }
});
</script>

<template>
  <div class="flex h-full">
    <aside
      v-show="showSessionList"
      class="w-[260px] flex flex-col bg-slate-50 dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 shrink-0"
    >
      <div
        class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800"
      >
        <span class="text-sm font-semibold text-slate-700 dark:text-slate-300"
          >会话列表</span
        >
        <a-button size="small" type="primary" @click="startNewSession">
          <template #icon><Icon icon="mdi:plus" /></template>
          新会话
        </a-button>
      </div>
      <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-800">
        <a-input
          v-model="searchChatId"
          placeholder="搜索 chat id"
          size="small"
          allow-clear
          @input="handleSearchChatId"
          @clear="handleSearchChatId"
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
        <div
          v-else-if="sessions.length === 0"
          class="text-center text-slate-400 py-8 text-sm"
        >
          暂无会话记录
        </div>
        <div v-else class="py-2">
          <div
            v-for="session in sessions"
            :key="session.chatId"
            class="px-3 py-2.5 mx-2 rounded-lg cursor-pointer transition-colors group"
            :class="
              chatStore.chatId === session.chatId
                ? 'bg-primary/10 border border-primary/20'
                : 'hover:bg-slate-100 dark:hover:bg-slate-800'
            "
            @click="selectSession(session)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <p
                  class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate"
                >
                  {{ truncateText(session.firstQuestion) }}
                </p>
                <p class="text-[11px] text-slate-400 mt-1">
                  {{ session.messageCount }} 条消息 ·
                  {{ formatSessionTime(session.updateTime) }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <section
      class="flex flex-1 flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800"
    >
      <div
        class="flex items-center justify-between px-6 py-3 border-b border-slate-100 dark:border-slate-800/50"
      >
        <div class="flex items-center gap-2">
          <button
            class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            @click="showSessionList = !showSessionList"
          >
            <Icon
              :icon="showSessionList ? 'mdi:menu-open' : 'mdi:menu'"
              class="text-lg"
            />
          </button>
          <Icon icon="mdi:chat" class="text-primary text-xl" />
          <span class="text-sm font-semibold">对话调试</span>
        </div>
      </div>

      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar"
      >
        <div
          v-if="chatStore.messages.length === 0"
          class="flex flex-col items-center justify-center h-full text-slate-400"
        >
          <Icon icon="mdi:chat-outline" class="text-4xl mb-4" />
          <p class="text-sm">开始对话吧...</p>
        </div>

        <div
          v-for="message in chatStore.messages"
          :key="message.id"
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
              message.role === 'user'
                ? 'items-end max-w-[80%]'
                : 'items-start max-w-[85%]'
            "
          >
            <span
              class="text-[11px] font-bold text-slate-400 mb-1 uppercase tracking-wider"
            >
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
              <img
                v-if="message.image"
                :src="message.image"
                class="max-w-[200px] max-h-[200px] rounded-lg mb-2 object-cover"
                alt="uploaded image"
              />
              <p
                v-if="message.content"
                class="text-sm leading-relaxed whitespace-pre-wrap"
              >
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
              <button
                v-if="message.content"
                class="absolute -right-2 -top-2 w-6 h-6 rounded-full bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-slate-50 dark:hover:bg-slate-600"
                @click="copyMessage(message.content)"
              >
                <Icon icon="mdi:content-copy" class="text-xs text-slate-400" />
              </button>
            </div>

            <div
              v-if="
                message.role === 'assistant' &&
                (message.source?.items?.length ||
                  message.document ||
                  message.tool?.toolName ||
                  message.link)
              "
              class="flex flex-wrap gap-1.5 mt-2"
            >
              <template v-for="(item, idx) in message.source?.items" :key="idx">
                <a
                  v-if="
                    item.type === 'document' &&
                    item.detail &&
                    !item.detail.endsWith('/json')
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
                <a-popover
                  v-else-if="item.type === 'tool'"
                  trigger="click"
                  position="top"
                >
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
                    Object.values(message.document).reduce(
                      (sum, docs) => sum + docs.length,
                      0
                    )
                  }}
                  个知识点来源
                </span>
                <template #content>
                  <div class="text-xs space-y-3 max-w-md max-h-64 overflow-y-auto">
                    <div v-for="(docs, collection) in message.document" :key="collection">
                      <div
                        class="text-slate-500 font-medium mb-1 flex items-center gap-1"
                      >
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
      </div>

      <div
        class="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
      >
        <div v-if="inputImage" class="mb-2 relative inline-block">
          <img
            :src="inputImage"
            class="max-w-[120px] max-h-[120px] rounded-lg object-cover border border-slate-200 dark:border-slate-700"
            alt="preview"
          />
          <button
            class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-colors"
            @click="removeImage"
          >
            <Icon icon="mdi:close" class="text-xs" />
          </button>
        </div>
        <div
          class="relative flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-2 pr-3 focus-within:border-primary transition-all"
        >
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleImageSelect"
          />
          <button
            class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="fileInput?.click()"
          >
            <Icon icon="mdi:image-outline" class="text-lg" />
          </button>
          <textarea
            v-model="inputText"
            class="flex-1 bg-transparent border-none focus:ring-0 text-sm resize-none py-2 max-h-32 custom-scrollbar outline-none"
            placeholder="输入消息..."
            rows="1"
            @keydown.enter.exact.prevent="sendMessage"
          ></textarea>
          <a-button
            type="primary"
            shape="circle"
            :disabled="(!inputText.trim() && !inputImage) || isLoading"
            :loading="isLoading"
            @click="sendMessage"
          >
            <template #icon><Icon icon="mdi:send" /></template>
          </a-button>
        </div>
      </div>
    </section>

    <aside
      class="w-[340px] flex flex-col bg-slate-50 dark:bg-background-dark overflow-y-auto custom-scrollbar border-l border-slate-200 dark:border-slate-800"
    >
      <div class="p-4 space-y-6">
        <div>
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:robot" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              模型设置
            </h3>
          </div>
          <a-select v-model="selectedModel" style="width: 100%" size="small">
            <a-option v-for="model in models" :key="model.id" :value="model.id">
              {{ model.name }}
            </a-option>
          </a-select>
          <a-collapse :default-active-key="[]" expand-icon-position="right" class="mt-3">
            <a-collapse-item key="1" header="进阶">
              <div class="space-y-3">
                <div>
                  <div class="flex justify-between items-center mb-1.5">
                    <label class="text-xs font-medium text-slate-600 dark:text-slate-400"
                      >Temperature</label
                    >
                    <span
                      class="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-semibold"
                    >
                      {{ temperature.toFixed(1) }}
                    </span>
                  </div>
                  <a-slider v-model="temperature" :min="0" :max="2" :step="0.1" />
                </div>
                <div>
                  <label class="text-[11px] font-medium text-slate-500 block mb-1"
                    >Top P</label
                  >
                  <a-input-number
                    v-model="topP"
                    :min="0"
                    :max="1"
                    :step="0.1"
                    size="small"
                    style="width: 100%"
                  />
                </div>
              </div>
            </a-collapse-item>
          </a-collapse>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:database" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              知识库
            </h3>
          </div>
          <a-select
            v-model="selectedCollection"
            style="width: 100%"
            size="small"
            allow-clear
            multiple
            placeholder="选择知识库"
          >
            <a-option
              v-for="col in collections"
              :key="col.collectionName"
              :value="col.collectionName"
            >
              {{ col.collectionName }}
            </a-option>
          </a-select>
          <div class="mt-3 flex items-center justify-between">
            <label class="text-[11px] font-medium text-slate-500">精准模式</label>
            <div
              class="flex rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700"
            >
              <button
                type="button"
                class="px-3 py-1 text-[11px] font-medium transition-colors"
                :class="
                  precisionMode
                    ? 'bg-primary text-white'
                    : 'bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'
                "
                @click="precisionMode = true"
              >
                是
              </button>
              <button
                type="button"
                class="px-3 py-1 text-[11px] font-medium transition-colors"
                :class="
                  !precisionMode
                    ? 'bg-primary text-white'
                    : 'bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'
                "
                @click="precisionMode = false"
              >
                否
              </button>
            </div>
          </div>
          <a-collapse :default-active-key="[]" expand-icon-position="right" class="mt-3">
            <a-collapse-item key="1" header="进阶">
              <div class="space-y-4">
                <div>
                  <div class="flex justify-between items-center mb-1.5">
                    <label class="text-xs font-medium text-slate-600 dark:text-slate-400"
                      >Score Threshold</label
                    >
                    <span
                      class="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-semibold"
                    >
                      {{ scoreThreshold.toFixed(1) }}
                    </span>
                  </div>
                  <a-slider v-model="scoreThreshold" :min="0" :max="1" :step="0.1" />
                  <p class="text-[10px] text-slate-400 mt-1">
                    检索相似度阈值，低于此值的结果将被过滤
                  </p>
                </div>
                <div>
                  <label class="text-[11px] font-medium text-slate-500 block mb-1"
                    >Top K</label
                  >
                  <a-input-number
                    v-model="topK"
                    :min="1"
                    :max="100"
                    :step="1"
                    size="small"
                    style="width: 100%"
                  />
                  <p class="text-[10px] text-slate-400 mt-1">返回最相关的 K 条文档</p>
                </div>
              </div>
            </a-collapse-item>
          </a-collapse>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:text-box-outline" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              系统提示词
            </h3>
          </div>
          <a-select
            v-model="selectedPrompt"
            style="width: 100%"
            size="small"
            allow-clear
            placeholder="选择提示词"
          >
            <a-option
              v-for="prompt in prompts"
              :key="prompt.id"
              :value="prompt.promptName"
            >
              {{ prompt.promptName }}
            </a-option>
          </a-select>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:wrench" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              工具配置
            </h3>
          </div>
          <a-select
            v-model="selectedTools"
            style="width: 100%"
            size="small"
            multiple
            allow-clear
            placeholder="选择工具"
          >
            <a-option v-for="tool in tools" :key="tool.id" :value="tool.name">
              {{ tool.name }}
            </a-option>
          </a-select>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:cog" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              高级配置
            </h3>
          </div>
          <div class="space-y-3">
            <div>
              <label class="text-[11px] font-medium text-slate-500 block mb-1">
                输出模式
              </label>
              <a-select v-model="batchOrStream" size="small" style="width: 100%">
                <a-option value="stream">流式</a-option>
                <a-option value="batch">批式</a-option>
              </a-select>
            </div>
            <div>
              <label class="text-[11px] font-medium text-slate-500 block mb-1"
                >Extra Params (JSON)</label
              >
              <textarea
                v-model="extraParamsText"
                class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-xs p-2 resize-none font-mono"
                :class="{ 'border-red-500': extraParamsError }"
                rows="3"
                placeholder='{"key": "value"}'
                @blur="validateExtraParams"
              ></textarea>
              <p v-if="extraParamsError" class="text-[10px] text-red-500 mt-1">
                {{ extraParamsError }}
              </p>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:chart-bar" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              Token 统计
            </h3>
            <span
              v-if="sessionStats"
              class="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded"
              >会话</span
            >
          </div>
          <div class="bg-slate-900 dark:bg-slate-950 rounded-lg p-3 font-mono">
            <template v-if="sessionStats">
              <div class="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>输入 Token</span>
                <span class="text-white">{{ sessionStats.totalInputTokens }}</span>
              </div>
              <div class="w-full bg-slate-800 h-1 rounded-full mb-2">
                <div
                  class="bg-primary h-1 rounded-full transition-all"
                  :style="{
                    width: `${Math.min(sessionStats.totalInputTokens / 100, 100)}%`,
                  }"
                ></div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>输出 Token</span>
                <span class="text-white">{{ sessionStats.totalOutputTokens }}</span>
              </div>
              <div class="w-full bg-slate-800 h-1 rounded-full mb-2">
                <div
                  class="bg-emerald-500 h-1 rounded-full transition-all"
                  :style="{
                    width: `${Math.min(sessionStats.totalOutputTokens / 100, 100)}%`,
                  }"
                ></div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>总计</span>
                <span class="text-amber-400 font-semibold">{{
                  sessionStats.totalTokens
                }}</span>
              </div>
              <div class="mt-2.5 pt-2 border-t border-slate-800 space-y-1">
                <div
                  v-if="sessionStats.avgFirstResponseMs"
                  class="flex justify-between text-[10px]"
                >
                  <span class="text-slate-400">平均首字延迟</span>
                  <span class="text-white"
                    >{{ sessionStats.avgFirstResponseMs.toFixed(0) }}ms</span
                  >
                </div>
                <div
                  v-if="sessionStats.avgTotalMs"
                  class="flex justify-between text-[10px]"
                >
                  <span class="text-slate-400">平均总延迟</span>
                  <span class="text-white"
                    >{{ sessionStats.avgTotalMs.toFixed(0) }}ms</span
                  >
                </div>
                <div class="flex justify-between text-[10px]">
                  <span class="text-slate-400">消息数</span>
                  <span class="text-white">{{ sessionStats.messageCount }}</span>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>提示词</span>
                <span class="text-white">{{ promptTokens }}</span>
              </div>
              <div class="w-full bg-slate-800 h-1 rounded-full mb-2">
                <div
                  class="bg-primary h-1 rounded-full transition-all"
                  :style="{ width: `${Math.min(promptTokens / 10, 100)}%` }"
                ></div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>补全</span>
                <span class="text-white">{{ completionTokens }}</span>
              </div>
              <div class="w-full bg-slate-800 h-1 rounded-full">
                <div
                  class="bg-emerald-500 h-1 rounded-full transition-all"
                  :style="{ width: `${Math.min(completionTokens / 20, 100)}%` }"
                ></div>
              </div>
              <div class="mt-2.5 pt-2 border-t border-slate-800 flex justify-between">
                <span class="text-[10px] font-semibold text-slate-400">预估成本</span>
                <span class="text-[11px] font-bold text-emerald-400"
                  >${{ totalCost.toFixed(4) }}</span
                >
              </div>
            </template>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
}

:deep(.arco-collapse) {
  border: none;
  background: transparent;
}

:deep(.arco-collapse-item) {
  border: none;
}

:deep(.arco-collapse-item-header) {
  padding: 8px 0;
  border: none;
  background: transparent;
  font-size: 11px;
  color: #64748b;
}

:deep(.arco-collapse-item-content) {
  padding: 0;
  border: none;
  background: transparent;
}

@keyframes bounce-dot {
  0%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-6px);
  }
}

.animate-bounce {
  animation: bounce-dot 1s infinite ease-in-out;
}
</style>
