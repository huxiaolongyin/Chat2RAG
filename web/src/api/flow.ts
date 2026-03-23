import type { BaseResponse, Flow, FlowCreate, FlowUpdate, PaginatedResponse } from '@/types/api'
import api from './index'

export const flowApi = {
  getFlows: async (current = 1, size = 10, name?: string) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<Flow>>>('/v1/flows', {
      params: { current, size, name: name || undefined }
    })
    return data
  },

  getFlow: async (id: number) => {
    const { data } = await api.get<BaseResponse<Flow>>(`/v1/flows/${id}`)
    return data
  },

  createFlow: async (flow: FlowCreate) => {
    const { data } = await api.post<BaseResponse<Flow>>('/v1/flows', flow)
    return data
  },

  updateFlow: async (id: number, flow: FlowUpdate) => {
    const { data } = await api.put<BaseResponse<Flow>>(`/v1/flows/${id}`, flow)
    return data
  },

  deleteFlow: async (id: number) => {
    const { data } = await api.delete<BaseResponse>(`/v1/flows/${id}`)
    return data
  }
}