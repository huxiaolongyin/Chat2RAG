<script setup lang="ts">
import { getKnowledgeCollections, getModels, getPrompts, getTools } from "@/api/chat"
import { getSessionStats } from "@/api/metric"
import { getVoices } from "@/api/voice"
import { useChatStore } from "@/stores/chat"
import type { KnowledgeCollection, ModelOption, Prompt, Tool } from "@/types/api"
import { Icon } from "@iconify/vue"
import { onMounted, ref } from "vue"
import SessionList from "./components/SessionList.vue"
import ChatMessage from "./components/ChatMessage.vue"
import ChatInput from "./components/ChatInput.vue"
import SettingsPanel from "./components/SettingsPanel.vue"
import { useTTS, useTTSSettings } from "./composables/useTTS"
import { useChatSession } from "./composables/useChatSession"
import { useChatMessage, useMessageUtils } from "./composables/useChatMessage"

const chatStore = useChatStore()
const { copyMessage } = useMessageUtils()

const models = ref<ModelOption[]>([])
const collections = ref<KnowledgeCollection[]>([])
const prompts = ref<Prompt[]>([])
const tools = ref<Tool[]>([])

const selectedModel = ref("")
const selectedCollection = ref<string[]>([])
const selectedPrompt = ref("默认")
const selectedTools = ref<string[]>([])
const temperature = ref(0.7)
const topP = ref(0.9)
const scoreThreshold = ref(0.6)
const topK = ref(5)
const precisionMode = ref(false)
const batchOrStream = ref<"batch" | "stream">("stream")
const extraParamsText = ref("")
const extraParamsError = ref("")

const { enableTts, ttsVoice, ttsSpeed, availableVoices } = useTTSSettings()
const { isPlayingAudio, messageAudioState, stopAudioPlayback, playMessageAudio, collectAudioChunk } = useTTS()
const { messagesContainer, promptTokens, completionTokens, totalCost, isLoading, isAtBottom, scrollToBottom, sendMessage, checkScrollPosition } = useChatMessage()
const {
  sessions,
  sessionsLoading,
  sessionStats,
  showSessionList,
  searchChatId,
  loadSessions,
  handleSearchChatId,
  selectSession,
  startNewSession,
} = useChatSession(scrollToBottom)

const previewVideoUrl = ref("")
const showVideoPreview = ref(false)

function openVideoPreview(url: string) {
  previewVideoUrl.value = url
  showVideoPreview.value = true
}

function validateExtraParams() {
  if (!extraParamsText.value.trim()) {
    extraParamsError.value = ""
    return
  }
  try {
    JSON.parse(extraParamsText.value)
    extraParamsError.value = ""
  } catch {
    extraParamsError.value = "JSON 格式错误"
  }
}

async function handleSendMessage(text: string, image: string) {
  stopAudioPlayback()
  await sendMessage(text, image, getChatSettings(), extraParamsText.value, (audio, messageId, format) => {
    collectAudioChunk(audio, messageId, format)
  }, async () => {
    if (chatStore.chatId) {
      sessionStats.value = await getSessionStats(chatStore.chatId)
    }
    await loadSessions()
  })
  scrollToBottom()
}

function getChatSettings() {
  return {
    selectedModel: selectedModel.value,
    selectedCollection: selectedCollection.value,
    selectedPrompt: selectedPrompt.value,
    selectedTools: selectedTools.value,
    temperature: temperature.value,
    topP: topP.value,
    scoreThreshold: scoreThreshold.value,
    topK: topK.value,
    precisionMode: precisionMode.value,
    batchOrStream: batchOrStream.value,
    enableTts: enableTts.value,
    ttsVoice: ttsVoice.value,
    ttsSpeed: ttsSpeed.value,
  }
}

onMounted(async () => {
  try {
    const [modelsData, collectionsData, promptsData, toolsData, voicesData] = await Promise.all([
      getModels(),
      getKnowledgeCollections(),
      getPrompts(),
      getTools(),
      getVoices(),
    ])
    models.value = modelsData
    collections.value = collectionsData
    prompts.value = promptsData
    tools.value = toolsData
    availableVoices.value = voicesData
    if (models.value.length > 0) {
      selectedModel.value = models.value[0].id
    }
    await loadSessions()
  } catch (error) {
    console.error("Failed to load data:", error)
  }
})
</script>

<template>
  <div class="flex h-full">
    <SessionList
      :sessions="sessions"
      :sessions-loading="sessionsLoading"
      :current-chat-id="chatStore.chatId ?? undefined"
      :show-session-list="showSessionList"
      :search-chat-id="searchChatId"
      @start-new-session="startNewSession"
      @select-session="selectSession"
      @handle-search-chat-id="handleSearchChatId"
      @update:show-session-list="showSessionList = $event"
      @update:search-chat-id="searchChatId = $event"
    />

    <section class="flex flex-1 flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 relative">
      <div class="flex items-center justify-between px-6 py-3 border-b border-slate-100 dark:border-slate-800/50">
        <div class="flex items-center gap-2">
          <button
            class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            @click="showSessionList = !showSessionList"
          >
            <Icon :icon="showSessionList ? 'mdi:menu-open' : 'mdi:menu'" class="text-lg" />
          </button>
          <Icon icon="mdi:chat" class="text-primary text-xl" />
          <span class="text-sm font-semibold">对话调试</span>
        </div>
      </div>

      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar" @scroll="checkScrollPosition">
        <div v-if="chatStore.messages.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400">
          <Icon icon="mdi:chat-outline" class="text-4xl mb-4" />
          <p class="text-sm">开始对话吧...</p>
        </div>

        <ChatMessage
          v-for="message in chatStore.messages"
          :key="message.id"
          :message="message"
          :is-loading="isLoading"
          :audio-state="messageAudioState[message.id] || 'idle'"
          @copy-message="copyMessage"
          @play-audio="(msg) => playMessageAudio(msg, ttsVoice, ttsSpeed)"
          @open-video-preview="openVideoPreview"
        />
      </div>

      <transition name="fade">
        <button
          v-if="!isAtBottom"
          class="absolute bottom-[90px] left-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-primary shadow-lg flex items-center justify-center hover:bg-primary/90 transition-all z-10"
          @click="scrollToBottom"
        >
          <Icon icon="mdi:chevron-down" class="text-xl text-white" />
        </button>
      </transition>

      <ChatInput
        :is-loading="isLoading"
        @send-message="handleSendMessage"
      />
    </section>

    <SettingsPanel
      :models="models"
      :collections="collections"
      :prompts="prompts"
      :tools="tools"
      :available-voices="availableVoices"
      :selected-model="selectedModel"
      :selected-collection="selectedCollection"
      :selected-prompt="selectedPrompt"
      :selected-tools="selectedTools"
      :temperature="temperature"
      :top-p="topP"
      :score-threshold="scoreThreshold"
      :top-k="topK"
      :precision-mode="precisionMode"
      :batch-or-stream="batchOrStream"
      :enable-tts="enableTts"
      :tts-voice="ttsVoice"
      :tts-speed="ttsSpeed"
      :is-playing-audio="isPlayingAudio"
      :extra-params-text="extraParamsText"
      :extra-params-error="extraParamsError"
      :prompt-tokens="promptTokens"
      :completion-tokens="completionTokens"
      :total-cost="totalCost"
      :session-stats="sessionStats"
      @update:selected-model="selectedModel = $event"
      @update:selected-collection="selectedCollection = $event"
      @update:selected-prompt="selectedPrompt = $event"
      @update:selected-tools="selectedTools = $event"
      @update:temperature="temperature = $event"
      @update:top-p="topP = $event"
      @update:score-threshold="scoreThreshold = $event"
      @update:top-k="topK = $event"
      @update:precision-mode="precisionMode = $event"
      @update:batch-or-stream="batchOrStream = $event"
      @update:enable-tts="enableTts = $event"
      @update:tts-voice="ttsVoice = $event"
      @update:tts-speed="ttsSpeed = $event"
      @update:extra-params-text="extraParamsText = $event"
      @validate-extra-params="validateExtraParams"
    />

    <a-modal v-model:visible="showVideoPreview" :footer="false" :unmount-on-close="true" simple width="80%">
      <video v-if="showVideoPreview" :src="previewVideoUrl" controls autoplay class="w-full max-h-[80vh] rounded-lg"></video>
    </a-modal>
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
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>