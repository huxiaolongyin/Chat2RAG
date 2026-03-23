import type {
  BaseResponse,
  PaginatedResponse,
  RobotAction,
  RobotActionCreate,
  RobotActionUpdate
} from '@/types/api'
import api from './index'

export const actionApi = {
  getActions: async (params: {
    current?: number
    size?: number
    nameOrCode?: string
    isActive?: boolean
  }) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<RobotAction>>>(
      '/v1/actions',
      {
        params: {
          current: params.current ?? 1,
          size: params.size ?? 10,
          nameOrCode: params.nameOrCode,
          isActive: params.isActive
        }
      }
    )
    return data
  },

  getAction: async (actionId: number) => {
    const { data } = await api.get<BaseResponse<RobotAction>>(
      `/v1/actions/${actionId}`
    )
    return data
  },

  createAction: async (action: RobotActionCreate) => {
    const { data } = await api.post<BaseResponse<RobotAction>>(
      '/v1/actions',
      action
    )
    return data
  },

  updateAction: async (actionId: number, action: RobotActionUpdate) => {
    const { data } = await api.put<BaseResponse<RobotAction>>(
      `/v1/actions/${actionId}`,
      action
    )
    return data
  },

  deleteAction: async (actionId: number) => {
    const { data } = await api.delete<BaseResponse>(`/v1/actions/${actionId}`)
    return data
  },

  exportActions: async (params: {
    format?: 'xlsx' | 'csv'
    isActive?: boolean
    actionIds?: number[]
  }) => {
    const response = await api.get('/v1/actions/export', {
      params: {
        format: params.format || 'xlsx',
        isActive: params.actionIds ? undefined : params.isActive,
        actionIds: params.actionIds?.join(',')
      },
      responseType: 'blob'
    })
    return response
  },

  downloadTemplate: async () => {
    const response = await api.get('/v1/actions/template', {
      responseType: 'blob'
    })
    return response
  },

  importActions: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<BaseResponse>('/v1/actions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return data
  }
}