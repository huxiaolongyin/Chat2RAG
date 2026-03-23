import api from './index'

export interface User {
  id: number
  tenantId: number
  username: string
  phone?: string
  nickname?: string
  avatar?: string
  email?: string
  status: number
  isSuperuser: boolean
  lastLoginTime?: string
  lastLoginIp?: string
  createTime: string
  updateTime: string
}

export interface UserDetail extends User {
  roles: string[]
  roleNames: string[]
}

export interface UserCreate {
  username: string
  password: string
  phone?: string
  nickname?: string
  avatar?: string
  email?: string
  status?: number
  roleIds?: number[]
}

export interface UserUpdate {
  phone?: string
  nickname?: string
  avatar?: string
  email?: string
  status?: number
  roleIds?: number[]
}

export const userApi = {
  getList: (params?: { current?: number; size?: number }) =>
    api.get<{ items: User[]; total: number }>('/v1/users', { params }),

  getDetail: (id: number) => api.get<UserDetail>(`/v1/users/${id}`),

  create: (data: UserCreate) => api.post<User>('/v1/users', data),

  update: (id: number, data: UserUpdate) =>
    api.put<User>(`/v1/users/${id}`, data),

  delete: (id: number) => api.delete(`/v1/users/${id}`)
}
