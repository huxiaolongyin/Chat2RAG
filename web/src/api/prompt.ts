import type {
  BaseResponse,
  Prompt,
  PromptCreate,
  PromptDetailData,
  PromptPaginatedData,
  PromptUpdate
} from '@/types/api'
import api from './index'

export const promptApi = {
  getPrompts: async (current = 1, size = 10, promptName?: string, promptDesc?: string) => {
    const { data } = await api.get<BaseResponse<PromptPaginatedData>>('/v1/prompts', {
      params: {
        current,
        size,
        promptName: promptName || undefined,
        promptDesc: promptDesc || undefined
      }
    })
    return data
  },

  getPrompt: async (promptId: number) => {
    const { data } = await api.get<BaseResponse<PromptDetailData>>(`/v1/prompts/${promptId}`)
    return data
  },

  createPrompt: async (prompt: PromptCreate) => {
    const { data } = await api.post<BaseResponse<Prompt>>('/v1/prompts', prompt)
    return data
  },

  updatePrompt: async (promptId: number, prompt: PromptUpdate) => {
    const { data } = await api.put<BaseResponse<{ promptId: number }>>(
      `/v1/prompts/${promptId}`,
      prompt
    )
    return data
  },

  deletePrompt: async (promptId: number) => {
    const { data } = await api.delete<BaseResponse>(`/v1/prompts/${promptId}`)
    return data
  },

  setVersion: async (promptId: number, version: number) => {
    const { data } = await api.get<BaseResponse<Prompt>>('/v1/prompts/version', {
      params: { promptId, version }
    })
    return data
  }
}