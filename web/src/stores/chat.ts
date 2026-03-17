import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, SystemPrompt, GenerationParams, TokenUsage } from '@/types/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const chatId = ref<string | null>(null)
  const isLoading = ref(false)

  const generationParams = ref<GenerationParams>({
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.9,
    frequencyPenalty: 0.0,
  })

  const systemPrompts = ref<SystemPrompt[]>([
    {
      id: '1',
      type: 'identity',
      label: '身份设定',
      content: '你是一个专业的技术助手，擅长开发SDK集成和技术问题解答。',
    },
    {
      id: '2',
      type: 'constraint',
      label: '约束条件',
      content: '回答时请引用知识库中的来源文档，格式为 [来源: 文件名]',
    },
  ])

  const tokenUsage = ref<TokenUsage>({
    promptTokens: 0,
    completionTokens: 0,
    totalCost: 0,
  })

  const selectedModel = ref<string>('')
  const selectedCollections = ref<string[]>([])
  const streamOutput = ref(true)

  const totalMessages = computed(() => messages.value.length)

  function addMessage(message: Message) {
    messages.value.push(message)
  }

  function updateLastMessage(content: string) {
    if (messages.value.length > 0) {
      messages.value[messages.value.length - 1].content = content
    }
  }

  function clearMessages() {
    messages.value = []
    chatId.value = null
    tokenUsage.value = {
      promptTokens: 0,
      completionTokens: 0,
      totalCost: 0,
    }
  }

  function addSystemPrompt(prompt: SystemPrompt) {
    systemPrompts.value.push(prompt)
  }

  function removeSystemPrompt(id: string) {
    const index = systemPrompts.value.findIndex((p) => p.id === id)
    if (index > -1) {
      systemPrompts.value.splice(index, 1)
    }
  }

  function updateTokenUsage(usage: Partial<TokenUsage>) {
    tokenUsage.value = { ...tokenUsage.value, ...usage }
  }

  function setChatId(id: string) {
    chatId.value = id
  }

  function setLoading(value: boolean) {
    isLoading.value = value
  }

  return {
    messages,
    chatId,
    isLoading,
    generationParams,
    systemPrompts,
    tokenUsage,
    selectedModel,
    selectedCollections,
    streamOutput,
    totalMessages,
    addMessage,
    updateLastMessage,
    clearMessages,
    addSystemPrompt,
    removeSystemPrompt,
    updateTokenUsage,
    setChatId,
    setLoading,
  }
})