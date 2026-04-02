const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export interface TTSRequest {
  text: string
  voice?: string
  speed?: number
  format?: string
  sample_rate?: number
  return_type?: 'base64' | 'stream'
}

export interface TTSResponse {
  audio: string
  format: string
  sample_rate: number
}

export interface VoiceInfo {
  id: string
  name: string
  language: string
  gender: string
}

export interface TTSStreamChunk {
  audio?: string
  index?: number
  sentence?: number
  error?: string
}

export async function getVoices (): Promise<VoiceInfo[]> {
  const response = await fetch(`${BASE_URL}/v1/voices/list`)
  const data = await response.json()
  return data.data || []
}

export async function synthesizeTTS (
  request: TTSRequest
): Promise<TTSResponse | null> {
  const response = await fetch(`${BASE_URL}/v1/voices/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: request.text,
      voice: request.voice || 'longanhuan',
      speed: request.speed || 1.0,
      format: request.format || 'wav',
      sample_rate: request.sample_rate || 24000,
      return_type: 'base64'
    })
  })
  if (!response.ok) {
    try {
      const errorData = await response.json()
      console.error('TTS API error:', errorData)
    } catch {
      console.error('TTS API error: HTTP', response.status)
    }
    return null
  }
  const data = await response.json()
  return data.data
}

export async function synthesizeTTSStream (
  request: TTSRequest,
  onChunk: (audio: string, index: number) => void,
  onError?: (error: string) => void
): Promise<void> {
  const response = await fetch(`${BASE_URL}/v1/voices/tts/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: request.text,
      voice: request.voice || 'longanhuan',
      speed: request.speed || 1.0,
      format: request.format || 'ogg_opus',
      sample_rate: request.sample_rate || 24000
    })
  })

  if (!response.ok) {
    if (onError) {
      onError(`HTTP ${response.status}`)
    }
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    if (onError) {
      onError('No response body')
    }
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          try {
            const chunk: TTSStreamChunk = JSON.parse(data)
            if (chunk.error && onError) {
              onError(chunk.error)
            } else if (chunk.audio && chunk.index !== undefined) {
              onChunk(chunk.audio, chunk.index)
            }
          } catch {
            console.error('Failed to parse SSE chunk:', data)
          }
        }
      }
    }
  } catch (error) {
    if (onError) {
      onError(String(error))
    }
  }
}
