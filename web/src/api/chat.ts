import type {
  BaseResponse,
  KnowledgeCollection,
  ModelOption
} from '@/types/api'
import type { ChatRequest, StreamChunk } from '@/types/chat'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function getModels (): Promise<ModelOption[]> {
  const response = await fetch(`${BASE_URL}/v1/models/option`)
  const data: BaseResponse<ModelOption[]> = await response.json()
  return data.data || []
}

export async function getKnowledgeCollections (
  current = 1,
  size = 100
): Promise<KnowledgeCollection[]> {
  const response = await fetch(
    `${BASE_URL}/v1/knowledge/collection?current=${current}&size=${size}`
  )
  const data: BaseResponse<{ collectionList: KnowledgeCollection[] }> =
    await response.json()
  return data.data?.collectionList || []
}

export interface ChatStreamOptions {
  request: ChatRequest
  onChunk: (chunk: StreamChunk) => void
  onError: (error: Error) => void
  onComplete: () => void
}

export async function streamChat (options: ChatStreamOptions): Promise<void> {
  const { request, onChunk, onError, onComplete } = options
  const response = await fetch(`${BASE_URL}/v2/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ...request,
      batchOrStream: 'stream'
    })
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No reader available')
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n').filter(line => line.trim() !== '')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6)
          if (jsonStr === '[DONE]') {
            onComplete()
            return
          }
          try {
            const chunk: StreamChunk = JSON.parse(jsonStr)
            onChunk(chunk)
          } catch (e) {
            console.warn('Failed to parse chunk:', jsonStr)
          }
        }
      }
    }
    onComplete()
  } catch (error) {
    onError(error as Error)
  }
}
