import api from './index'

export interface Tenant {
  id: number
  name: string
  code: string
  logo?: string
  contactName?: string
  contactPhone?: string
  status: number
  expireTime?: string
  remark?: string
  createTime: string
  updateTime: string
}

export interface TenantCreate {
  name: string
  code: string
  logo?: string
  contactName?: string
  contactPhone?: string
  status?: number
  expireTime?: string
  remark?: string
}

export interface TenantUpdate {
  name?: string
  logo?: string
  contactName?: string
  contactPhone?: string
  status?: number
  expireTime?: string
  remark?: string
}

export const tenantApi = {
  getList: (params?: { current?: number; size?: number }) =>
    api.get<{ items: Tenant[]; total: number }>('/v1/tenants', { params }),

  getDetail: (id: number) => api.get<Tenant>(`/v1/tenants/${id}`),

  create: (data: TenantCreate) => api.post<Tenant>('//v1/tenants', data),

  update: (id: number, data: TenantUpdate) =>
    api.put<Tenant>(`/v1/tenants/${id}`, data),

  delete: (id: number) => api.delete(`/v1/tenants/${id}`)
}
