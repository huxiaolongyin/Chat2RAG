import api from './index'
import type { BaseResponse, PaginatedResponse, KnowledgeCollection } from '@/types/api'

export const knowledgeApi = {
  getCollections: async (current = 1, size = 10) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<KnowledgeCollection>>>(
      '/v1/knowledge/collection',
      { params: { current, size } }
    )
    return data
  },

  createCollection: async (collectionName: string) => {
    const { data } = await api.post<BaseResponse>('/v1/knowledge/collection', null, {
      params: { collectionName },
    })
    return data
  },

  deleteCollection: async (collectionName: string) => {
    const { data } = await api.delete<BaseResponse>('/v1/knowledge/collection', {
      params: { collectionName },
    })
    return data
  },

  getFiles: async (collectionName: string, current = 1, size = 20) => {
    const { data } = await api.get<BaseResponse>('/v1/knowledge/collection/file', {
      params: { collectionName, current, size },
    })
    return data
  },

  uploadFile: async (collectionName: string, file: File, maxChars = 600, overlap = 100) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<BaseResponse>('/v1/knowledge/collection/file', formData, {
      params: { collectionName, maxChars, overlap, preview: false },
    })
    return data
  },

  deleteFile: async (fileId: number, collectionName: string) => {
    const { data } = await api.delete<BaseResponse>(`/v1/knowledge/collection/file/${fileId}`, {
      params: { collectionName },
    })
    return data
  },

  queryDocuments: async (collectionName: string, query: string, topK = 5) => {
    const { data } = await api.get<BaseResponse>('/v1/knowledge/query', {
      params: { collectionName, query, topK },
    })
    return data
  },
}