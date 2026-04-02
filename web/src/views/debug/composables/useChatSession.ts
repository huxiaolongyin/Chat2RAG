import { getChatSessions, getSessionStats } from "@/api/metric"
import { getSessionMessages } from "@/api/chat"
import { useChatStore } from "@/stores/chat"
import type { ChatSession, SessionStats } from "@/types/api"
import type { DocumentItem, SourceItem } from "@/types/chat"
import { ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

export function useChatSession(onHistoryLoaded?: () => void) {
  const route = useRoute()
  const router = useRouter()
  const chatStore = useChatStore()

  const sessions = ref<ChatSession[]>([])
  const sessionsTotal = ref(0)
  const sessionsPage = ref(1)
  const sessionsLoading = ref(false)
  const sessionStats = ref<SessionStats | null>(null)
  const showSessionList = ref(true)
  const searchChatId = ref("")
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

  async function loadSessions() {
    sessionsLoading.value = true
    try {
      const result = await getChatSessions({
        current: sessionsPage.value,
        size: 20,
        chatId: searchChatId.value || undefined,
      })
      sessions.value = result.items
      sessionsTotal.value = result.total
    } catch (error) {
      console.error("Failed to load sessions:", error)
    } finally {
      sessionsLoading.value = false
    }
  }

  function handleSearchChatId() {
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer)
    }
    searchDebounceTimer = setTimeout(() => {
      sessionsPage.value = 1
      loadSessions()
    }, 300)
  }

  async function selectSession(session: ChatSession) {
    router.push({ path: route.path, query: { chatId: session.chatId } })
  }

  async function loadSessionHistory(chatId: string) {
    try {
      const [stats, messages] = await Promise.all([getSessionStats(chatId), getSessionMessages(chatId)])
      sessionStats.value = stats
      chatStore.setChatId(chatId)

      chatStore.messages = []
      const sortedMessages = [...messages].sort((a, b) => new Date(a.createTime).getTime() - new Date(b.createTime).getTime())

      for (const metric of sortedMessages) {
        if (metric.question) {
          chatStore.addMessage({
            id: crypto.randomUUID(),
            role: "user",
            content: metric.question,
            timestamp: new Date(metric.createTime),
            image: metric.image || undefined,
          })
        }
        if (metric.answer) {
          chatStore.addMessage({
            id: crypto.randomUUID(),
            role: "assistant",
            content: metric.answer,
            timestamp: new Date(metric.createTime),
            latency: metric.totalMs ? parseFloat((metric.totalMs / 1000).toFixed(2)) : undefined,
            firstTokenLatency: metric.firstResponseMs ? parseFloat((metric.firstResponseMs / 1000).toFixed(2)) : undefined,
            source: metric.source ? { items: metric.source as SourceItem[] } : undefined,
            tool: metric.toolResult
              ? {
                  toolName: metric.executeTools || "",
                  toolType: "",
                  arguments: metric.toolArguments || {},
                  toolResult: metric.toolResult,
                }
              : undefined,
            document: metric.retrievalDocuments as Record<string, DocumentItem[]> | undefined,
            image: metric.answerImage || undefined,
            video: metric.answerVideo || undefined,
          })
        }
      }
      onHistoryLoaded?.()
    } catch (error) {
      console.error("Failed to load session history:", error)
    }
  }

  function startNewSession() {
    chatStore.clearMessages()
    chatStore.setChatId(crypto.randomUUID())
    sessionStats.value = null
    router.push({ path: route.path })
  }

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

  watch(
    () => route.query.chatId,
    (chatId) => {
      if (chatId && typeof chatId === "string") {
        loadSessionHistory(chatId)
      }
    },
    { immediate: true }
  )

  return {
    sessions,
    sessionsTotal,
    sessionsPage,
    sessionsLoading,
    sessionStats,
    showSessionList,
    searchChatId,
    loadSessions,
    handleSearchChatId,
    selectSession,
    loadSessionHistory,
    startNewSession,
    truncateText,
    formatSessionTime,
  }
}