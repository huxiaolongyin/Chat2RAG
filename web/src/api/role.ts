import api from './index'

export interface Role {
  id: number
  tenantId?: number
  name: string
  code: string
  description?: string
  isSystem: boolean
  status: number
  sort: number
  createTime: string
  updateTime: string
}

export interface RoleDetail extends Role {
  permissions: string[]
  permissionNames: string[]
}

export interface RoleCreate {
  name: string
  code: string
  description?: string
  status?: number
  sort?: number
  permissionIds?: number[]
}

export interface RoleUpdate {
  name?: string
  description?: string
  status?: number
  sort?: number
  permissionIds?: number[]
}

export const roleApi = {
  getList: (params?: { current?: number; size?: number }) =>
    api.get<{ items: Role[]; total: number }>('/v1/roles', { params }),

  getDetail: (id: number) => api.get<RoleDetail>(`/v1/roles/${id}`),

  create: (data: RoleCreate) => api.post<Role>('/v1/roles', data),

  update: (id: number, data: RoleUpdate) =>
    api.put<Role>(`/v1/roles/${id}`, data),

  delete: (id: number) => api.delete(`/v1/roles/${id}`)
}
