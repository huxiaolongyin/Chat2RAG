import type {
  ApiToolCreate,
  ApiToolUpdate,
  BaseResponse,
  McpServerCreate,
  McpServerUpdate,
  PaginatedResponse,
  Tool,
  ToolQueryParams,
  ToolSyncData
} from '@/types/api'
import api from './index'

export const toolApi = {
  getTools: async (params: ToolQueryParams) => {
    const { data } = await api.get<BaseResponse<PaginatedResponse<Tool>>>('/v1/tools', {
      params: {
        current: params.current ?? 1,
        size: params.size ?? 10,
        toolType: params.toolType,
        toolName: params.toolName,
        toolDesc: params.toolDesc,
        isActive: params.isActive,
        sortBy: params.sortBy,
        sortOrder: params.sortOrder
      }
    })
    return data
  },

  getTool: async (toolId: number, toolType: 'api' | 'mcp') => {
    const { data } = await api.get<BaseResponse<Tool>>(`/v1/tools/${toolId}`, {
      params: { toolType }
    })
    return data
  },

  createApiTool: async (tool: ApiToolCreate) => {
    const { data } = await api.post<BaseResponse<Tool>>('/v1/tools', {
      toolType: 'api',
      data: tool
    })
    return data
  },

  createMcpServer: async (server: McpServerCreate) => {
    const { data } = await api.post<BaseResponse<Tool>>('/v1/tools', {
      toolType: 'mcp',
      data: server
    })
    return data
  },

  updateApiTool: async (toolId: number, tool: ApiToolUpdate) => {
    const { data } = await api.put<BaseResponse<Tool>>(`/v1/tools/${toolId}`, tool, {
      params: { toolType: 'api' }
    })
    return data
  },

  updateMcpServer: async (serverId: number, server: McpServerUpdate) => {
    const { data } = await api.put<BaseResponse<Tool>>(`/v1/tools/${serverId}`, server, {
      params: { toolType: 'mcp' }
    })
    return data
  },

  deleteTool: async (toolId: number, toolType: 'api' | 'mcp') => {
    const { data } = await api.delete<BaseResponse>(`/v1/tools/${toolId}`, {
      params: { toolType }
    })
    return data
  },

  syncMcpTools: async (serverId: number) => {
    const { data } = await api.post<BaseResponse<ToolSyncData>>(`/v1/tools/${serverId}/sync`)
    return data
  }
}