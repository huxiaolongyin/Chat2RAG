<script setup lang="ts">
import {
  getKnowledgeCollections,
  getModels,
  getPrompts,
  getTools,
  streamChat,
} from "@/api/chat";
import { useChatStore } from "@/stores/chat";
import type { KnowledgeCollection, ModelOption, Prompt, Tool } from "@/types/api";
import type { Message } from "@/types/chat";
import { Icon } from "@iconify/vue";
import { computed, nextTick, onMounted, ref } from "vue";

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

const scoreThreshold = ref(0.5);
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
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
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
    documents: [],
  };
  chatStore.addMessage(assistantMessage);
  chatStore.setLoading(true);

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
        chatRounds: chatStore.messages.length,
        promptName: selectedPrompt.value || undefined,
        tools: selectedTools.value.length > 0 ? selectedTools.value : undefined,
        scoreThreshold: scoreThreshold.value,
        topK: topK.value,
        precisionMode: precisionMode.value ? 1 : 0,
        batchOrStream: batchOrStream.value,
        extraParams: validateExtraParams(),
      },
      onChunk: (chunk) => {
        if (chunk.status === 1 && chunk.content?.text) {
          if (!firstChunkReceived) {
            firstChunkReceived = true;
            const firstTokenLatency = ((Date.now() - startTime) / 1000).toFixed(1);
            chatStore.messages[
              chatStore.messages.length - 1
            ].firstTokenLatency = parseFloat(firstTokenLatency);
          }
          chatStore.appendLastMessage(chunk.content.text);
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
        <div class="flex items-center gap-2">
          <Icon icon="mdi:chat" class="text-primary text-xl" />
          <span class="text-sm font-semibold">对话调试</span>
        </div>
        <a-button size="small" @click="clearMessages">
          <template #icon><Icon icon="mdi:delete" /></template>
          清空对话
        </a-button>
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
              <p v-if="message.content" class="text-sm leading-relaxed whitespace-pre-wrap">
                {{ message.content }}
              </p>
              <div
                v-else-if="message.role === 'assistant' && isLoading"
                class="flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 300ms"></span>
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
        <div
          v-if="inputImage"
          class="mb-2 relative inline-block"
        >
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
            <div class="flex rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
              <button
                type="button"
                class="px-3 py-1 text-[11px] font-medium transition-colors"
                :class="precisionMode ? 'bg-primary text-white' : 'bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'"
                @click="precisionMode = true"
              >
                是
              </button>
              <button
                type="button"
                class="px-3 py-1 text-[11px] font-medium transition-colors"
                :class="!precisionMode ? 'bg-primary text-white' : 'bg-white dark:bg-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700'"
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
              <label class="text-[11px] font-medium text-slate-500 block mb-1"
                >Batch/Stream</label
              >
              <a-select v-model="batchOrStream" size="small" style="width: 100%">
                <a-option value="stream">Stream</a-option>
                <a-option value="batch">Batch</a-option>
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
          </div>
          <div class="bg-slate-900 dark:bg-slate-950 rounded-lg p-3 font-mono">
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
  0%, 80%, 100% {
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
