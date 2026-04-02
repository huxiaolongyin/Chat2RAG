<script setup lang="ts">
import type { VoiceInfo } from "@/api/voice";
import type {
  KnowledgeCollection,
  ModelOption,
  Prompt,
  SessionStats,
  Tool,
} from "@/types/api";
import { Icon } from "@iconify/vue";

defineProps<{
  models: ModelOption[];
  collections: KnowledgeCollection[];
  prompts: Prompt[];
  tools: Tool[];
  availableVoices: VoiceInfo[];
  selectedModel: string;
  selectedCollection: string[];
  selectedPrompt: string;
  selectedTools: string[];
  temperature: number;
  topP: number;
  scoreThreshold: number;
  topK: number;
  precisionMode: boolean;
  batchOrStream: "batch" | "stream";
  enableTts: boolean;
  ttsVoice: string;
  ttsSpeed: number;
  isPlayingAudio: boolean;
  extraParamsText: string;
  extraParamsError: string;
  promptTokens: number;
  completionTokens: number;
  totalCost: number;
  sessionStats: SessionStats | null;
}>();

const emit = defineEmits<{
  "update:selectedModel": [value: string];
  "update:selectedCollection": [value: string[]];
  "update:selectedPrompt": [value: string];
  "update:selectedTools": [value: string[]];
  "update:temperature": [value: number];
  "update:topP": [value: number];
  "update:scoreThreshold": [value: number];
  "update:topK": [value: number];
  "update:precisionMode": [value: boolean];
  "update:batchOrStream": [value: "batch" | "stream"];
  "update:enableTts": [value: boolean];
  "update:ttsVoice": [value: string];
  "update:ttsSpeed": [value: number];
  "update:extraParamsText": [value: string];
  validateExtraParams: [];
}>();
</script>

<template>
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
        <a-select
          :model-value="selectedModel"
          style="width: 100%"
          size="small"
          @update:model-value="emit('update:selectedModel', $event)"
        >
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
                <a-slider
                  :model-value="temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  @update:model-value="emit('update:temperature', $event)"
                />
              </div>
              <div>
                <label class="text-[11px] font-medium text-slate-500 block mb-1"
                  >Top P</label
                >
                <a-input-number
                  :model-value="topP"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  size="small"
                  style="width: 100%"
                  @update:model-value="emit('update:topP', $event)"
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
          :model-value="selectedCollection"
          style="width: 100%"
          size="small"
          allow-clear
          multiple
          placeholder="选择知识库"
          @update:model-value="emit('update:selectedCollection', $event)"
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
              @click="emit('update:precisionMode', true)"
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
              @click="emit('update:precisionMode', false)"
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
                <a-slider
                  :model-value="scoreThreshold"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  @update:model-value="emit('update:scoreThreshold', $event)"
                />
                <p class="text-[10px] text-slate-400 mt-1">
                  检索相似度阈值，低于此值的结果将被过滤
                </p>
              </div>
              <div>
                <label class="text-[11px] font-medium text-slate-500 block mb-1"
                  >Top K</label
                >
                <a-input-number
                  :model-value="topK"
                  :min="1"
                  :max="100"
                  :step="1"
                  size="small"
                  style="width: 100%"
                  @update:model-value="emit('update:topK', $event)"
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
          :model-value="selectedPrompt"
          style="width: 100%"
          size="small"
          allow-clear
          placeholder="选择提示词"
          @update:model-value="emit('update:selectedPrompt', $event)"
        >
          <a-option v-for="prompt in prompts" :key="prompt.id" :value="prompt.promptName">
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
          :model-value="selectedTools"
          style="width: 100%"
          size="small"
          multiple
          allow-clear
          placeholder="选择工具"
          @update:model-value="emit('update:selectedTools', $event)"
        >
          <a-option v-for="tool in tools" :key="tool.id" :value="tool.name">
            {{ tool.name }}
          </a-option>
        </a-select>
      </div>

      <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <Icon icon="mdi:volume-high" class="text-primary text-lg" />
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              语音输出
            </h3>
          </div>
          <a-switch
            :model-value="enableTts"
            size="small"
            @change="(val: string | number | boolean) => emit('update:enableTts', Boolean(val))"
          />
        </div>
        <div v-if="enableTts" class="space-y-3">
          <div>
            <label class="text-[11px] font-medium text-slate-500 block mb-1"
              >音色选择</label
            >
            <a-select
              :model-value="ttsVoice"
              size="small"
              style="width: 100%"
              @update:model-value="emit('update:ttsVoice', $event)"
            >
              <a-option
                v-for="voice in availableVoices"
                :key="voice.id"
                :value="voice.id"
              >
                {{ voice.name }}
              </a-option>
            </a-select>
          </div>
          <div>
            <div class="flex justify-between items-center mb-1.5">
              <label class="text-xs font-medium text-slate-600 dark:text-slate-400"
                >语速</label
              >
              <span
                class="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-semibold"
              >
                {{ ttsSpeed.toFixed(1) }}
              </span>
            </div>
            <a-slider
              :model-value="ttsSpeed"
              :min="0.5"
              :max="2"
              :step="0.1"
              @update:model-value="emit('update:ttsSpeed', $event)"
            />
          </div>
        </div>
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
              >输出模式</label
            >
            <a-select
              :model-value="batchOrStream"
              size="small"
              style="width: 100%"
              @update:model-value="emit('update:batchOrStream', $event)"
            >
              <a-option value="stream">流式</a-option>
              <a-option value="batch">批式</a-option>
            </a-select>
          </div>
          <div>
            <label class="text-[11px] font-medium text-slate-500 block mb-1"
              >Extra Params (JSON)</label
            >
            <textarea
              :value="extraParamsText"
              class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-xs p-2 resize-none font-mono"
              :class="{ 'border-red-500': extraParamsError }"
              rows="3"
              placeholder='{"key": "value"}'
              @update:model-value="emit('update:extraParamsText', $event)"
              @blur="emit('validateExtraParams')"
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
                <span class="text-white">{{ sessionStats.avgTotalMs.toFixed(0) }}ms</span>
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
