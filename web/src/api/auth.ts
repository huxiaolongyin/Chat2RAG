import api from './index'

export interface LoginRequest {
  username: string
  password: string
  tenantCode?: string
}

export interface SmsLoginRequest {
  phone: string
  code: string
  tenantCode?: string
}

export interface SmsCodeRequest {
  phone: string
  tenantCode?: string
}

export interface TokenResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

export interface LoginResponse {
  token: TokenResponse
  userId: number
  username: string
  nickname?: string
  avatar?: string
  tenantId: number
  tenantName: string
  isSuperuser: boolean
  roles: string[]
  permissions: string[]
}

export interface CurrentUserResponse {
  id: number
  username: string
  nickname?: string
  avatar?: string
  email?: string
  phone?: string
  tenantId: number
  tenantName: string
  isSuperuser: boolean
  status: number
  lastLoginTime?: string
  roles: string[]
  permissions: string[]
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/v1/auth/login', data),

  smsLogin: (data: SmsLoginRequest) =>
    api.post<LoginResponse>('/v1/auth/sms-login', data),

  sendSmsCode: (data: SmsCodeRequest) => api.post('/v1/auth/sms-code', data),

  getCurrentUser: () => api.get<CurrentUserResponse>('/v1/auth/me'),

  logout: () => api.post('/v1/auth/logout')
}
