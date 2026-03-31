export interface QueryContent {
  text: string
  image?: string
  video?: string
  audio?: string
}

export interface GenerationKwargs {
  temperature?: number

  top_p?: number
}

export interface ChatRequest {
  model: string
  collections: string[]
  content: QueryContent
  generation_kwargs?: GenerationKwargs
  promptName?: string
  tools?: string[]
  flows?: string[]
  chatId?: string
  chatRounds?: number
  precisionMode?: number
  scoreThreshold?: number
  topK?: number
  batchOrStream?: 'batch' | 'stream'
  modalities?: string[]
  extraParams?: Record<string, unknown>
}

export interface ContentSchema {
  text: string
  image?: string
  video?: string
}

export interface BehaviorSchema {
  emoji: string
  action: string
}

export interface ToolSchema {
  toolName: string
  toolType: string
  arguments: Record<string, unknown>
  toolResult: unknown
}

export type SourceType = 'command' | 'document' | 'tool' | 'llm'

export interface SourceItem {
  type: SourceType
  display: string
  detail?: string
}

export interface SourceSchema {
  items: SourceItem[]
}

export interface DocumentItem {
  content: string
  score: number | null
}

export interface StreamChunk {
  object: string
  input: Record<string, unknown>
  content: ContentSchema
  model: string
  status: number
  behavior: BehaviorSchema
  tool: ToolSchema
  source: SourceSchema
  document: Record<string, DocumentItem[]> | null
  createTime: string
  messageId: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  latency?: number
  firstTokenLatency?: number
  source?: SourceSchema
  document?: Record<string, DocumentItem[]>
  behavior?: BehaviorSchema
  tool?: ToolSchema
  image?: string
  video?: string
}

export interface DocumentSource {
  id: string
  content: string
  score: number
  filename?: string
}

export interface SystemPrompt {
  id: string
  type: 'identity' | 'constraint' | 'custom'
  label: string
  content: string
}

export interface GenerationParams {
  temperature: number

  topP: number
}

export interface TokenUsage {
  promptTokens: number
  completionTokens: number
  totalCost: number
}
