import api from './index'

export interface Permission {
  id: number
  parentId?: number
  name: string
  code: string
  type: 'menu' | 'api' | 'button'
  path?: string
  component?: string
  icon?: string
  sort: number
  status: number
  visible: boolean
  cache: boolean
  remark?: string
  createTime: string
  updateTime: string
}

export interface PermissionTree extends Permission {
  children: PermissionTree[]
}

export interface PermissionCreate {
  parentId?: number
  name: string
  code: string
  type?: 'menu' | 'api' | 'button'
  path?: string
  component?: string
  icon?: string
  sort?: number
  status?: number
  visible?: boolean
  cache?: boolean
  remark?: string
}

export interface PermissionUpdate {
  name?: string
  path?: string
  component?: string
  icon?: string
  sort?: number
  status?: number
  visible?: boolean
  cache?: boolean
  remark?: string
}

export const permissionApi = {
  getList: (params?: { current?: number; size?: number }) =>
    api.get<{ items: Permission[]; total: number }>('/v1/permissions', {
      params
    }),

  getTree: () => api.get<PermissionTree[]>('/v1/permissions/tree'),

  create: (data: PermissionCreate) =>
    api.post<Permission>('/v1/permissions', data),

  update: (id: number, data: PermissionUpdate) =>
    api.put<Permission>(`/v1/permissions/${id}`, data),

  delete: (id: number) => api.delete(`/v1/permissions/${id}`)
}
