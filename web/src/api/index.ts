import { Message } from '@arco-design/web-vue'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
})

api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail
    if (detail) {
      Message.error(detail)
    }
    return Promise.reject(error)
  }
)

export default api
export * from './chat'
export * from './command'
export * from './knowledge'
export * from './model'
