<script setup lang="ts">
import { getKnowledgeCollections, getModels, streamChat } from "@/api/chat";
import { useChatStore } from "@/stores/chat";
import type { KnowledgeCollection, ModelOption } from "@/types/api";
import type { Message, SystemPrompt } from "@/types/chat";
import { Icon } from "@iconify/vue";
import { computed, nextTick, onMounted, ref } from "vue";

const chatStore = useChatStore();

const models = ref<ModelOption[]>([]);
const collections = ref<KnowledgeCollection[]>([]);
const inputText = ref("");
const messagesContainer = ref<HTMLElement | null>(null);

const selectedModel = ref("");
const selectedCollection = ref<string[]>([]);
const streamOutput = ref(true);

const temperature = ref(0.7);
const maxTokens = ref(2048);
const topP = ref(0.9);
const frequencyPenalty = ref(0);

const systemPrompts = ref<SystemPrompt[]>([
  {
    id: "1",
    type: "identity",
    label: "身份设定",
    content: "你是一个专业的技术助手，擅长开发SDK集成和技术问题解答。",
  },
  {
    id: "2",
    type: "constraint",
    label: "约束条件",
    content: "回答时请引用知识库中的来源文档，格式为 [来源: 文件名]",
  },
]);

const promptTokens = ref(0);
const completionTokens = ref(0);
const totalCost = ref(0);

const isLoading = computed(() => chatStore.isLoading);

function formatTime(date: Date): string {
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

async function scrollToBottom() {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || isLoading.value) return;

  const userMessage: Message = {
    id: generateId(),
    role: "user",
    content: text,
    timestamp: new Date(),
  };
  chatStore.addMessage(userMessage);
  inputText.value = "";
  await scrollToBottom();

  const assistantMessage: Message = {
    id: generateId(),
    role: "assistant",
    content: "",
    timestamp: new Date(),
    documents: [],
  };
  chatStore.addMessage(assistantMessage);
  chatStore.setLoading(true);

  const startTime = Date.now();

  try {
    await streamChat({
      request: {
        model: selectedModel.value || "Qwen3-235B",
        collections: selectedCollection.value,
        content: { text },
        generation_kwargs: {
          temperature: temperature.value,
          maxTokens: maxTokens.value,
          top_p: topP.value,
          frequencyPenalty: frequencyPenalty.value,
        },
        chatId: chatStore.chatId || undefined,
        chatRounds: chatStore.messages.length,
      },
      onChunk: (chunk) => {
        if (chunk.status === 1 && chunk.content?.text) {
          chatStore.updateLastMessage(chunk.content.text);
          scrollToBottom();
        }
        if (chunk.documentCount) {
          promptTokens.value = chunk.documentCount * 100;
        }
      },
      onError: (error) => {
        console.error("Stream error:", error);
        chatStore.updateLastMessage("抱歉，发生了错误，请重试。");
        chatStore.setLoading(false);
      },
      onComplete: () => {
        const latency = ((Date.now() - startTime) / 1000).toFixed(1);
        chatStore.messages[chatStore.messages.length - 1].latency = parseFloat(latency);
        completionTokens.value =
          chatStore.messages[chatStore.messages.length - 1].content.length;
        totalCost.value = (promptTokens.value + completionTokens.value) * 0.00001;
        chatStore.setLoading(false);
        scrollToBottom();
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    chatStore.updateLastMessage("抱歉，发生了错误，请重试。");
    chatStore.setLoading(false);
  }
}

function clearMessages() {
  chatStore.clearMessages();
  promptTokens.value = 0;
  completionTokens.value = 0;
  totalCost.value = 0;
}

function addPrompt() {
  const newPrompt: SystemPrompt = {
    id: generateId(),
    type: "custom",
    label: "自定义",
    content: "",
  };
  systemPrompts.value.push(newPrompt);
}

function removePrompt(id: string) {
  const index = systemPrompts.value.findIndex((p) => p.id === id);
  if (index > -1) {
    systemPrompts.value.splice(index, 1);
  }
}

function getPromptTypeColor(type: string): string {
  switch (type) {
    case "identity":
      return "arcoblue";
    case "constraint":
      return "orangered";
    default:
      return "green";
  }
}

onMounted(async () => {
  try {
    const [modelsData, collectionsData] = await Promise.all([
      getModels(),
      getKnowledgeCollections(),
    ]);
    models.value = modelsData;
    collections.value = collectionsData;
    if (models.value.length > 0) {
      selectedModel.value = models.value[0].id;
    }
  } catch (error) {
    console.error("Failed to load data:", error);
  }
});
</script>

<template>
  <div class="flex h-full">
    <section
      class="flex flex-1 flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800"
    >
      <div
        class="flex items-center justify-between px-6 py-3 border-b border-slate-100 dark:border-slate-800/50"
      >
        <div class="flex gap-4">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-slate-500">模型:</span>
            <a-select v-model="selectedModel" size="small" style="width: 160px">
              <a-option v-for="model in models" :key="model.id" :value="model.id">
                {{ model.name }}
              </a-option>
            </a-select>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-slate-500">知识库:</span>
            <a-select
              v-model="selectedCollection"
              size="small"
              style="width: 180px"
              allow-clear
              multiple
            >
              <a-option
                v-for="col in collections"
                :key="col.collectionName"
                :value="col.collectionName"
              >
                {{ col.collectionName }}
              </a-option>
            </a-select>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-slate-500">流式输出</span>
            <a-switch v-model="streamOutput" size="small" />
          </div>
          <a-button size="small" @click="clearMessages">
            <template #icon><Icon icon="mdi:delete" /></template>
            清空对话
          </a-button>
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
              class="px-4 py-3 rounded-2xl shadow-sm"
              :class="
                message.role === 'user'
                  ? 'bg-primary text-white rounded-tr-none'
                  : 'bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-tl-none'
              "
            >
              <p class="text-sm leading-relaxed whitespace-pre-wrap">
                {{ message.content || "..." }}
              </p>
              <div
                v-if="message.role === 'assistant' && isLoading && !message.content"
                class="mt-2 h-0.5 w-4 bg-primary animate-pulse inline-block"
              ></div>
            </div>

            <span class="text-[10px] text-slate-400 mt-1">
              {{ formatTime(message.timestamp) }}
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
        <div
          class="relative flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-2 pr-3 focus-within:border-primary transition-all"
        >
          <textarea
            v-model="inputText"
            class="flex-1 bg-transparent border-none focus:ring-0 text-sm resize-none py-2 max-h-32 custom-scrollbar outline-none"
            placeholder="输入消息..."
            rows="1"
            @keydown.enter.ctrl="sendMessage"
          ></textarea>
          <a-button
            type="primary"
            shape="circle"
            :disabled="!inputText.trim() || isLoading"
            :loading="isLoading"
            @click="sendMessage"
          >
            <template #icon><Icon icon="mdi:send" /></template>
          </a-button>
        </div>
      </div>
    </section>

    <aside
      class="w-[380px] flex flex-col bg-slate-50 dark:bg-background-dark overflow-y-auto custom-scrollbar"
    >
      <div class="p-6 space-y-8">
        <div>
          <div class="flex items-center gap-2 mb-4">
            <Icon icon="mdi:tune" class="text-primary text-xl" />
            <h3 class="text-sm font-bold uppercase tracking-wider text-slate-500">
              超参数
            </h3>
          </div>
          <div class="space-y-6">
            <div>
              <div class="flex justify-between items-center mb-2">
                <label class="text-xs font-semibold">Temperature</label>
                <span
                  class="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded font-bold"
                  >{{ temperature.toFixed(1) }}</span
                >
              </div>
              <a-slider v-model="temperature" :min="0" :max="2" :step="0.1" />
              <div class="flex justify-between mt-1">
                <span class="text-[10px] text-slate-400">精确</span>
                <span class="text-[10px] text-slate-400">创造</span>
              </div>
            </div>

            <div>
              <div class="flex justify-between items-center mb-2">
                <label class="text-xs font-semibold">Max Tokens</label>
                <span
                  class="text-xs bg-slate-200 dark:bg-slate-700 px-2 py-0.5 rounded font-bold"
                  >{{ maxTokens }}</span
                >
              </div>
              <a-slider v-model="maxTokens" :min="256" :max="4096" :step="256" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-[11px] font-semibold text-slate-500 block mb-1"
                  >Top P</label
                >
                <a-input-number
                  v-model="topP"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  size="small"
                />
              </div>
              <div>
                <label class="text-[11px] font-semibold text-slate-500 block mb-1"
                  >Frequency Penalty</label
                >
                <a-input-number
                  v-model="frequencyPenalty"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <Icon icon="mdi:text-box-outline" class="text-primary text-xl" />
              <h3 class="text-sm font-bold uppercase tracking-wider text-slate-500">
                系统提示词
              </h3>
            </div>
            <a-button size="small" type="text" @click="addPrompt">
              <template #icon><Icon icon="mdi:plus" /></template>
              添加
            </a-button>
          </div>
          <div class="space-y-3">
            <div
              v-for="prompt in systemPrompts"
              :key="prompt.id"
              class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-3 shadow-sm group"
            >
              <div class="flex justify-between items-start mb-2">
                <a-tag :color="getPromptTypeColor(prompt.type)" size="small">{{
                  prompt.label
                }}</a-tag>
                <div
                  class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <a-button type="text" size="mini">
                    <template #icon><Icon icon="mdi:pencil" /></template>
                  </a-button>
                  <a-button
                    type="text"
                    size="mini"
                    status="danger"
                    @click="removePrompt(prompt.id)"
                  >
                    <template #icon><Icon icon="mdi:delete" /></template>
                  </a-button>
                </div>
              </div>
              <p class="text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                {{ prompt.content }}
              </p>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-200 dark:border-slate-800">
          <h3 class="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
            Token使用统计
          </h3>
          <div class="bg-slate-900 dark:bg-slate-950 rounded-lg p-4 font-mono">
            <div class="flex justify-between text-[11px] text-slate-400 mb-1">
              <span>提示词Tokens</span>
              <span class="text-white">{{ promptTokens }}</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full mb-3">
              <div
                class="bg-primary h-1.5 rounded-full transition-all"
                :style="{ width: `${Math.min(promptTokens / 10, 100)}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-[11px] text-slate-400 mb-1">
              <span>补全Tokens</span>
              <span class="text-white">{{ completionTokens }}</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full">
              <div
                class="bg-emerald-500 h-1.5 rounded-full transition-all"
                :style="{ width: `${Math.min(completionTokens / 20, 100)}%` }"
              ></div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-800 flex justify-between">
              <span class="text-[11px] font-bold text-slate-400">预估成本</span>
              <span class="text-xs font-bold text-emerald-400"
                >${{ totalCost.toFixed(4) }}</span
              >
            </div>
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
</style>
