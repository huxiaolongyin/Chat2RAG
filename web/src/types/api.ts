export interface BaseResponse<T = unknown> {
  code: string
  msg: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  current: number
  size: number
  pages?: number
}

export interface ModelOption {
  id: string
  name: string
}

export interface KnowledgeCollection {
  collectionName: string
  pointsCount?: number
  createTime?: string
  updateTime?: string
}

export interface ModelProvider {
  id: string
  name: string
  description?: string
  enabled: boolean
  baseUrl?: string
  createTime?: string
}

export interface ModelSource {
  id: string
  name: string
  alias: string
  providerId: number
  enabled: boolean
  healthy: boolean
  latency?: number
}

export interface Tool {
  id: number
  name: string
  description?: string
  toolType: 'api' | 'mcp'
  isActive: boolean
}

export interface Prompt {
  id: number
  promptName: string
  promptDesc?: string
  content: string
  version: number
}

export interface CommandCategory {
  id: number
  name: string
  description?: string
}

export interface CommandVariant {
  id: number
  text: string
  pattern?: string
}

export type ParamType = 'none' | 'number' | 'text'

export interface Command {
  id: number
  name: string
  code: string
  reply?: string
  categoryId?: number
  priority: number
  description?: string
  isActive: boolean
  commands?: string
  paramType: ParamType
  examples: string[]
  variants: CommandVariant[]
  createTime?: string
  updateTime?: string
}

export interface CommandCreate {
  name: string
  code: string
  reply?: string
  categoryId?: number
  priority?: number
  description?: string
  isActive?: boolean
  commands?: string
  paramType?: ParamType
  examples?: string[]
  variants?: { text: string; pattern?: string }[]
}

export interface CommandUpdate {
  name?: string
  code?: string
  reply?: string
  categoryId?: number
  priority?: number
  description?: string
  isActive?: boolean
  commands?: string
  paramType?: ParamType
  examples?: string[]
  variants?: { text: string; pattern?: string }[]
}

export interface CommandCategoryCreate {
  name: string
  description?: string
}

export interface CommandCategoryUpdate {
  name?: string
  description?: string
}

export interface CommandBatchMove {
  commandIds: number[]
  categoryId: number | null
}

export interface SensitiveWord {
  id: number
  word: string
  categoryId?: number
  level: number
  description?: string
}

export interface Flow {
  id: number
  name: string
  description?: string
  states: unknown
  transitions: unknown
}

export interface RobotAction {
  id: number
  name: string
  code: string
  description?: string
  isActive: boolean
}

export interface RobotExpression {
  id: number
  name: string
  code: string
  description?: string
  isActive: boolean
}

export interface MetricData {
  id: number
  chatId: string
  query: string
  response: string
  model: string
  collections: string
  latency: number
  createTime: string
}

export interface HotQuestion {
  question: string
  count: number
}
