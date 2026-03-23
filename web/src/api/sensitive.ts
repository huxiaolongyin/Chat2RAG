import type {
  BaseResponse,
  PaginatedResponse,
  SensitiveWord,
  SensitiveWordCategory,
  SensitiveWordCategoryCreate,
  SensitiveWordCategoryUpdate,
  SensitiveWordCreate,
  SensitiveWordUpdate
} from '@/types/api'
import api from './index'

export const sensitiveApi = {
  getCategories: async (current = 1, size = 100, nameOrDesc?: string) => {
    const { data } = await api.get<
      BaseResponse<PaginatedResponse<SensitiveWordCategory>>
    >('/v1/sensitive/category', {
      params: { current, size, nameOrDesc }
    })
    return data
  },

  getCategory: async (categoryId: number) => {
    const { data } = await api.get<BaseResponse<SensitiveWordCategory>>(
      `/v1/sensitive/category/${categoryId}`
    )
    return data
  },

  createCategory: async (category: SensitiveWordCategoryCreate) => {
    const { data } = await api.post<BaseResponse<SensitiveWordCategory>>(
      '/v1/sensitive/category',
      category
    )
    return data
  },

  updateCategory: async (
    categoryId: number,
    category: SensitiveWordCategoryUpdate
  ) => {
    const { data } = await api.put<BaseResponse<SensitiveWordCategory>>(
      `/v1/sensitive/category/${categoryId}`,
      category
    )
    return data
  },

  deleteCategory: async (categoryId: number) => {
    const { data } = await api.delete<BaseResponse>(
      `/v1/sensitive/category/${categoryId}`
    )
    return data
  },

  getWords: async (params: {
    current?: number
    size?: number
    word?: string
    categoryId?: number
    level?: number
  }) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<SensitiveWord>>>(
      '/v1/sensitive/word',
      {
        params: {
          current: params.current ?? 1,
          size: params.size ?? 10,
          word: params.word,
          categoryId: params.categoryId,
          level: params.level
        }
      }
    )
    return data
  },

  getWord: async (wordId: number) => {
    const { data } = await api.get<BaseResponse<SensitiveWord>>(
      `/v1/sensitive/word/${wordId}`
    )
    return data
  },

  createWord: async (word: SensitiveWordCreate) => {
    const { data } = await api.post<BaseResponse<SensitiveWord>>(
      '/v1/sensitive/word',
      word
    )
    return data
  },

  updateWord: async (wordId: number, word: SensitiveWordUpdate) => {
    const { data } = await api.put<BaseResponse<SensitiveWord>>(
      `/v1/sensitive/word/${wordId}`,
      word
    )
    return data
  },

  deleteWord: async (wordId: number) => {
    const { data } = await api.delete<BaseResponse>(
      `/v1/sensitive/word/${wordId}`
    )
    return data
  }
}