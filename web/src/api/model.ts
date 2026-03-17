import api from './index'
import type { BaseResponse, PaginatedResponse, ModelProvider, ModelSource, ModelOption } from '@/types/api'

export const modelApi = {
  getOptions: async () => {
    const { data } = await api.get<BaseResponse<ModelOption[]>>('/v1/models/option')
    return data
  },

  getProviders: async (current = 1, size = 10) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<ModelProvider>>>(
      '/v1/models/provider',
      { params: { current, size } }
    )
    return data
  },

  createProvider: async (provider: Partial<ModelProvider>) => {
    const { data } = await api.post<BaseResponse<ModelProvider>>('/v1/models/provider', provider)
    return data
  },

  updateProvider: async (providerId: string, provider: Partial<ModelProvider>) => {
    const { data } = await api.put<BaseResponse<ModelProvider>>(
      `/v1/models/provider/${providerId}`,
      provider
    )
    return data
  },

  deleteProvider: async (providerId: string) => {
    const { data } = await api.delete<BaseResponse>(`/v1/models/provider/${providerId}`)
    return data
  },

  getSources: async (current = 1, size = 10) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<ModelSource>>>(
      '/v1/models/source',
      { params: { current, size } }
    )
    return data
  },

  createSource: async (source: Partial<ModelSource>) => {
    const { data } = await api.post<BaseResponse<ModelSource>>('/v1/models/source', source)
    return data
  },

  updateSource: async (sourceId: string, source: Partial<ModelSource>) => {
    const { data } = await api.put<BaseResponse<ModelSource>>(
      `/v1/models/source/${sourceId}`,
      source
    )
    return data
  },

  deleteSource: async (sourceId: string) => {
    const { data } = await api.delete<BaseResponse>(`/v1/models/source/${sourceId}`)
    return data
  },
}