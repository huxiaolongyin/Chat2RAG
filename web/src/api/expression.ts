import type {
  BaseResponse,
  PaginatedResponse,
  RobotExpression,
  RobotExpressionCreate,
  RobotExpressionUpdate
} from '@/types/api'
import api from './index'

export const expressionApi = {
  getExpressions: async (params: {
    current?: number
    size?: number
    nameOrCode?: string
    isActive?: boolean
  }) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<RobotExpression>>>(
      '/v1/expressions',
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

  getExpression: async (expressionId: number) => {
    const { data } = await api.get<BaseResponse<RobotExpression>>(
      `/v1/expressions/${expressionId}`
    )
    return data
  },

  createExpression: async (expression: RobotExpressionCreate) => {
    const { data } = await api.post<BaseResponse<RobotExpression>>(
      '/v1/expressions',
      expression
    )
    return data
  },

  updateExpression: async (expressionId: number, expression: RobotExpressionUpdate) => {
    const { data } = await api.put<BaseResponse<RobotExpression>>(
      `/v1/expressions/${expressionId}`,
      expression
    )
    return data
  },

  deleteExpression: async (expressionId: number) => {
    const { data } = await api.delete<BaseResponse>(`/v1/expressions/${expressionId}`)
    return data
  },

  exportExpressions: async (params: {
    format?: 'xlsx' | 'csv'
    isActive?: boolean
    expressionIds?: number[]
  }) => {
    const response = await api.get('/v1/expressions/export', {
      params: {
        format: params.format || 'xlsx',
        isActive: params.expressionIds ? undefined : params.isActive,
        expressionIds: params.expressionIds?.join(',')
      },
      responseType: 'blob'
    })
    return response
  },

  downloadTemplate: async () => {
    const response = await api.get('/v1/expressions/template', {
      responseType: 'blob'
    })
    return response
  },

  importExpressions: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<BaseResponse>('/v1/expressions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return data
  }
}