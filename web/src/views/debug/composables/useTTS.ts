import type { VoiceInfo } from "@/api/voice"
import { synthesizeTTSStream } from "@/api/voice"
import type { Message } from "@/types/chat"
import { ref } from "vue"

export function useTTS() {
  const audioQueue = ref<{ audio: string; messageId?: string; format?: string }[]>([])
  const isPlayingAudio = ref(false)
  let currentAudioElement: HTMLAudioElement | null = null
  let currentPlayingMessageId: string | null = null

  const messageAudioState = ref<Record<string, "idle" | "loading" | "playing">>({})
  const audioCacheMap = ref<Map<string, { chunks: string[]; format: string }>>(new Map())

  function collectAudioChunk(base64Audio: string, messageId?: string, format: string = "ogg") {
    audioQueue.value.push({ audio: base64Audio, messageId, format })

    if (messageId) {
      const existing = audioCacheMap.value.get(messageId) || { chunks: [], format }
      existing.chunks.push(base64Audio)
      audioCacheMap.value.set(messageId, existing)
    }

    if (!isPlayingAudio.value) {
      playAudioQueue()
    }
  }

  async function playAudioQueue() {
    isPlayingAudio.value = true
    while (audioQueue.value.length > 0) {
      const item = audioQueue.value.shift()
      if (item) {
        if (item.messageId && currentPlayingMessageId !== item.messageId) {
          if (currentPlayingMessageId) {
            messageAudioState.value[currentPlayingMessageId] = "idle"
          }
          currentPlayingMessageId = item.messageId
          messageAudioState.value[item.messageId] = "playing"
        }
        await playSingleAudio(item.audio, item.format)
      }
    }
    if (currentPlayingMessageId) {
      messageAudioState.value[currentPlayingMessageId] = "idle"
      currentPlayingMessageId = null
    }
    isPlayingAudio.value = false
  }

  function playSingleAudio(base64Audio: string, format: string = "ogg"): Promise<void> {
    return new Promise((resolve) => {
      const mimeType = format === "wav" ? "audio/wav" : `audio/${format}`
      const audio = new Audio(`data:${mimeType};base64,${base64Audio}`)
      currentAudioElement = audio
      audio.onended = () => resolve()
      audio.onerror = () => resolve()
      audio.play().catch(() => resolve())
    })
  }

  function stopAudioPlayback() {
    if (currentAudioElement) {
      currentAudioElement.pause()
      currentAudioElement = null
    }
    audioQueue.value = []
    isPlayingAudio.value = false
    if (currentPlayingMessageId) {
      messageAudioState.value[currentPlayingMessageId] = "idle"
      currentPlayingMessageId = null
    }
  }

  async function playMessageAudio(message: Message, voice: string, speed: number) {
    if (messageAudioState.value[message.id] === "playing") {
      stopAudioPlayback()
      messageAudioState.value[message.id] = "idle"
      return
    }

    const cachedData = audioCacheMap.value.get(message.id)

    if (cachedData && cachedData.chunks.length > 0) {
      messageAudioState.value[message.id] = "playing"
      for (const chunk of cachedData.chunks) {
        await playSingleAudio(chunk, cachedData.format)
      }
      messageAudioState.value[message.id] = "idle"
      return
    }

    messageAudioState.value[message.id] = "loading"
    const chunks: Map<number, string> = new Map()
    let nextIndexToPlay = 0
    let streamComplete = false
    let isPlaying = false
    let totalChunks = 0

    const tryPlayNext = async () => {
      if (isPlaying) return
      isPlaying = true
      isPlayingAudio.value = true
      messageAudioState.value[message.id] = "playing"

      while (true) {
        if (messageAudioState.value[message.id] !== "playing") {
          break
        }

        const chunk = chunks.get(nextIndexToPlay)
        if (chunk) {
          await playSingleAudio(chunk, "ogg_opus")
          chunks.delete(nextIndexToPlay)
          nextIndexToPlay++
        } else if (streamComplete && nextIndexToPlay >= totalChunks) {
          break
        } else {
          await new Promise((r) => setTimeout(r, 20))
        }
      }

      messageAudioState.value[message.id] = "idle"
      isPlayingAudio.value = false
      isPlaying = false
    }

    synthesizeTTSStream(
      {
        text: message.content,
        voice,
        speed,
        format: "ogg_opus",
      },
      (audio: string, index: number) => {
        chunks.set(index, audio)
        totalChunks = Math.max(totalChunks, index + 1)
        tryPlayNext()
      },
      (error: string) => {
        console.error("TTS stream error:", error)
        streamComplete = true
        tryPlayNext()
      }
    ).then(() => {
      streamComplete = true
      tryPlayNext()
    })

    audioCacheMap.value.set(message.id, { chunks: [], format: "ogg_opus" })
  }

  return {
    audioQueue,
    isPlayingAudio,
    messageAudioState,
    audioCacheMap,
    collectAudioChunk,
    playAudioQueue,
    playSingleAudio,
    stopAudioPlayback,
    playMessageAudio,
  }
}

export function useTTSSettings() {
  const enableTts = ref(false)
  const ttsVoice = ref("longanhuan")
  const ttsSpeed = ref(1.0)
  const availableVoices = ref<VoiceInfo[]>([])

  return {
    enableTts,
    ttsVoice,
    ttsSpeed,
    availableVoices,
  }
}