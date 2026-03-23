import type { BaseResponse, MetricData, ChatSession, SessionStats } from '@/types/api'
import type { HotQuestionData, MetricsQueryParams, SessionsQueryParams } from '@/types/api'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function getMetrics(params: MetricsQueryParams): Promise<{ items: MetricData[]; total: number }> {
  const searchParams = new URLSearchParams({
    current: String(params.current || 1),
    size: String(params.size || 20)
  })
  if (params.startTime) searchParams.append('startTime', params.startTime)
  if (params.endTime) searchParams.append('endTime', params.endTime)
  if (params.collection) searchParams.append('collection', params.collection)
  if (params.chatId) searchParams.append('chatId', params.chatId)

  const response = await fetch(`${BASE_URL}/v1/metrics?${searchParams}`)
  const result = await response.json()
  return {
    items: result.data?.items || [],
    total: result.data?.total || 0
  }
}

export async function getHotQuestions(params?: {
  collection?: string
  days?: number
  limit?: number
}): Promise<HotQuestionData[]> {
  const searchParams = new URLSearchParams()
  if (params?.collection) searchParams.append('collection', params.collection)
  if (params?.days) searchParams.append('days', String(params.days))
  if (params?.limit) searchParams.append('limit', String(params.limit))

  const url = searchParams.toString()
    ? `${BASE_URL}/v1/metrics/hot-questions?${searchParams}`
    : `${BASE_URL}/v1/metrics/hot-questions`

  const response = await fetch(url)
  const data: BaseResponse<HotQuestionData[]> = await response.json()
  return data.data || []
}

export async function getChatSessions(params: SessionsQueryParams): Promise<{ items: ChatSession[]; total: number }> {
  const searchParams = new URLSearchParams({
    current: String(params.current || 1),
    size: String(params.size || 20)
  })
  if (params.startTime) searchParams.append('startTime', params.startTime)
  if (params.endTime) searchParams.append('endTime', params.endTime)
  if (params.chatId) searchParams.append('chatId', params.chatId)

  const response = await fetch(`${BASE_URL}/v1/metrics/sessions?${searchParams}`)
  const result = await response.json()
  return {
    items: result.data?.items || [],
    total: result.data?.total || 0
  }
}

export async function getSessionStats(chatId: string): Promise<SessionStats | null> {
  const response = await fetch(`${BASE_URL}/v1/metrics/sessions/${chatId}/stats`)
  if (!response.ok) return null
  const data: BaseResponse<SessionStats> = await response.json()
  return data.data
}