import type {
  BaseResponse,
  Command,
  CommandCategory,
  CommandCategoryCreate,
  CommandCategoryUpdate,
  CommandCreate,
  CommandUpdate,
  PaginatedResponse
} from '@/types/api'
import api from './index'

export const commandApi = {
  getCategories: async (current = 1, size = 100, nameOrDesc?: string) => {
    const { data } = await api.get<
      BaseResponse<PaginatedResponse<CommandCategory>>
    >('/v1/commands/category', {
      params: { current, size, nameOrDesc }
    })
    return data
  },

  getCategory: async (categoryId: number) => {
    const { data } = await api.get<BaseResponse<CommandCategory>>(
      `/v1/commands/category/${categoryId}`
    )
    return data
  },

  createCategory: async (category: CommandCategoryCreate) => {
    const { data } = await api.post<BaseResponse<CommandCategory>>(
      '/v1/commands/category',
      category
    )
    return data
  },

  updateCategory: async (
    categoryId: number,
    category: CommandCategoryUpdate
  ) => {
    const { data } = await api.put<BaseResponse<{ categoryId: number }>>(
      `/v1/commands/category/${categoryId}`,
      category
    )
    return data
  },

  deleteCategory: async (categoryId: number) => {
    const { data } = await api.delete<BaseResponse>(
      `/v1/commands/category/${categoryId}`
    )
    return data
  },

  getCommands: async (params: {
    current?: number
    size?: number
    keyword?: string
    categoryId?: number
    isActive?: boolean
  }) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<Command>>>(
      '/v1/commands',
      {
        params: {
          current: params.current ?? 1,
          size: params.size ?? 10,
          keyword: params.keyword,
          categoryId: params.categoryId,
          isActive: params.isActive
        }
      }
    )
    return data
  },

  getCommand: async (commandId: number) => {
    const { data } = await api.get<BaseResponse<Command>>(
      `/v1/commands/${commandId}`
    )
    return data
  },

  createCommand: async (command: CommandCreate) => {
    const { data } = await api.post<BaseResponse<Command>>(
      '/v1/commands',
      command
    )
    return data
  },

  updateCommand: async (commandId: number, command: CommandUpdate) => {
    const { data } = await api.put<BaseResponse<Command>>(
      `/v1/commands/${commandId}`,
      command
    )
    return data
  },

  deleteCommand: async (commandId: number) => {
    const { data } = await api.delete<BaseResponse>(`/v1/commands/${commandId}`)
    return data
  },

  batchMoveCommands: async (commandIds: number[], categoryId: number | null) => {
    const { data } = await api.put<BaseResponse>('/v1/commands/batch-move', {
      commandIds,
      categoryId: typeof categoryId === 'number' ? categoryId : null
    })
    return data
  }
}
