import { streamChat } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import type { Message } from '@/types/chat'
import { Message as AMessage } from '@arco-design/web-vue'
import { computed, nextTick, ref } from 'vue'

export interface ChatSettings {
  selectedModel: string
  selectedCollection: string[]
  selectedPrompt: string
  selectedTools: string[]
  temperature: number
  topP: number
  scoreThreshold: number
  topK: number
  precisionMode: boolean
  batchOrStream: 'batch' | 'stream'
  enableTts: boolean
  ttsVoice: string
  ttsSpeed: number
}

export function useChatMessage () {
  const chatStore = useChatStore()
  const messagesContainer = ref<HTMLElement | null>(null)

  const promptTokens = ref(0)
  const completionTokens = ref(0)
  const totalCost = ref(0)
  const isAtBottom = ref(true)

  const isLoading = computed(() => chatStore.isLoading)

  function generateId (): string {
    return Math.random().toString(36).substring(2, 15)
  }

  function checkScrollPosition () {
    if (!messagesContainer.value) return
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value
    const threshold = 100
    isAtBottom.value = scrollHeight - scrollTop - clientHeight < threshold
  }

  async function scrollToBottom () {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      isAtBottom.value = true
    }
  }

  function validateExtraParams (
    extraParamsText: string
  ): Record<string, unknown> | undefined {
    if (!extraParamsText.trim()) {
      return undefined
    }
    try {
      return JSON.parse(extraParamsText)
    } catch {
      return undefined
    }
  }

  async function sendMessage (
    inputText: string,
    inputImage: string,
    settings: ChatSettings,
    extraParamsText: string,
    onAudioChunk?: (audio: string, messageId: string, format?: string) => void,
    onSessionStatsUpdate?: () => void
  ) {
    const text = inputText.trim()
    const image = inputImage
    if ((!text && !image) || isLoading.value) return

    const isFirstMessage = chatStore.messages.length === 0

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: new Date(),
      image: image || undefined
    }
    chatStore.addMessage(userMessage)
    await scrollToBottom()

    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date()
    }
    chatStore.addMessage(assistantMessage)
    chatStore.setLoading(true)
    scrollToBottom()

    const startTime = Date.now()
    let firstChunkReceived = false

    try {
      await streamChat({
        request: {
          model: settings.selectedModel || 'Qwen3-235B',
          collections: settings.selectedCollection,
          content: { text, image: image || undefined },
          generation_kwargs: {
            temperature: settings.temperature,
            top_p: settings.topP
          },
          chatId: chatStore.chatId || undefined,
          chatRounds: 5,
          promptName: settings.selectedPrompt || undefined,
          tools:
            settings.selectedTools.length > 0
              ? settings.selectedTools
              : undefined,
          scoreThreshold: settings.scoreThreshold,
          topK: settings.topK,
          precisionMode: settings.precisionMode ? 1 : 0,
          batchOrStream: settings.batchOrStream,
          modalities: settings.enableTts ? ['text', 'audio'] : ['text'],
          audio: settings.enableTts
            ? {
                voice: settings.ttsVoice,
                format: 'ogg_opus',
                sampleRate: 24000,
                provider: 'cosy_voice_tts',
                speed: settings.ttsSpeed,
                language: 'zh'
              }
            : undefined,
          extraParams: validateExtraParams(extraParamsText)
        },
        onChunk: chunk => {
          const lastMessage = chatStore.messages[chatStore.messages.length - 1]
          if (chunk.status === 1 && chunk.content?.text) {
            if (!firstChunkReceived) {
              firstChunkReceived = true
              const firstTokenLatency = (
                (Date.now() - startTime) /
                1000
              ).toFixed(1)
              lastMessage.firstTokenLatency = parseFloat(firstTokenLatency)
            }
            chatStore.appendLastMessage(chunk.content.text)
            scrollToBottom()
          }
          if (chunk.source) {
            lastMessage.source = chunk.source
          }
          if (chunk.document) {
            lastMessage.document = chunk.document
            const docCount = Object.values(chunk.document).reduce(
              (sum, docs) => sum + docs.length,
              0
            )
            promptTokens.value = docCount * 100
          }
          if (chunk.tool?.toolName) {
            lastMessage.tool = chunk.tool
          }
          if (chunk.content?.image) {
            lastMessage.image = chunk.content.image
          }
          if (chunk.content?.video) {
            lastMessage.video = chunk.content.video
          }
          if (chunk.content?.audio && onAudioChunk) {
            onAudioChunk(
              chunk.content.audio.audioBase64,
              assistantMessage.id,
              chunk.content.audio.format
            )
          }
        },
        onError: error => {
          console.error('Stream error:', error)
          chatStore.updateLastMessage('抱歉，发生了错误，请重试。')
          chatStore.setLoading(false)
        },
        onComplete: async () => {
          const latency = ((Date.now() - startTime) / 1000).toFixed(1)
          chatStore.messages[chatStore.messages.length - 1].latency =
            parseFloat(latency)
          completionTokens.value =
            chatStore.messages[chatStore.messages.length - 1].content.length
          totalCost.value =
            (promptTokens.value + completionTokens.value) * 0.00001
          chatStore.setLoading(false)
          scrollToBottom()
          if (onSessionStatsUpdate) {
            onSessionStatsUpdate()
          }
          if (isFirstMessage) {
            onSessionStatsUpdate?.()
          }
        }
      })
    } catch (error) {
      console.error('Chat error:', error)
      chatStore.updateLastMessage('抱歉，发生了错误，请重试。')
      chatStore.setLoading(false)
    }
  }

  return {
    messagesContainer,
    promptTokens,
    completionTokens,
    totalCost,
    isLoading,
    isAtBottom,
    generateId,
    scrollToBottom,
    sendMessage,
    checkScrollPosition
  }
}

export function useMessageUtils () {
  function formatTime (date: Date): string {
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()
    if (isToday) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    return (
      date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) +
      ' ' +
      date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    )
  }

  async function copyMessage (content: string) {
    try {
      await navigator.clipboard.writeText(content)
      AMessage.success('已复制')
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return {
    formatTime,
    copyMessage
  }
}

export function useImageInput () {
  const inputText = ref('')
  const inputImage = ref('')
  const fileInput = ref<HTMLInputElement | null>(null)

  function handleImageSelect (event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      return
    }

    const reader = new FileReader()
    reader.onload = e => {
      inputImage.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }

  function handlePaste (event: ClipboardEvent) {
    const items = event.clipboardData?.items
    if (!items) return

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const file = item.getAsFile()
        if (file) {
          const reader = new FileReader()
          reader.onload = e => {
            inputImage.value = e.target?.result as string
          }
          reader.readAsDataURL(file)
        }
        break
      }
    }
  }

  function removeImage () {
    inputImage.value = ''
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }

  return {
    inputText,
    inputImage,
    fileInput,
    handleImageSelect,
    handlePaste,
    removeImage
  }
}
