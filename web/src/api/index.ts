import { Message } from '@arco-design/web-vue'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('chat2rag-user')
    if (token) {
      try {
        const parsed = JSON.parse(token)
        if (parsed.token) {
          config.headers.Authorization = `Bearer ${parsed.token}`
        }
      } catch {
        // ignore
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('chat2rag-user')
      window.location.href = '/login'
      return Promise.reject(error)
    }
    const detail = error.response?.data?.msg || error.response?.data?.detail
    if (detail) {
      Message.error(detail)
    }
    return Promise.reject(error)
  }
)

export default api
export * from './auth'
export * from './chat'
export * from './command'
export * from './knowledge'
export * from './model'
export * from './prompt'
export * from './metric'
export * from './tool'
export * from './flow'
export * from './user'
export * from './role'
export * from './permission'
export * from './tenant'
