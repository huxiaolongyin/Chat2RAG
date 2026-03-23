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
  documentsCount?: number
  filesCount?: number
  embeddingSize?: number
  distance?: string
  vectorMode?: 'legacy' | 'dense' | 'hybrid'
}

export interface ModelProvider {
  id: string
  name: string
  description?: string
  enabled: boolean
  baseUrl: string
  apiKey?: string
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
  priority?: number
  failureCount?: number
  lastLatency?: number
  lastCheckTime?: string
  generationKwargs?: Record<string, unknown>
}

export type ToolType = 'all' | 'api' | 'mcp'
export type ToolMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
export type McpType = 'stdio' | 'sse'

export interface Tool {
  id: number
  name: string
  description?: string
  toolType: 'api' | 'mcp'
  isActive: boolean
  url?: string
  method?: ToolMethod
  parameters?: Record<string, unknown>
  command?: string
  args?: string[]
  serverId?: number
  inputSchema?: Record<string, unknown>
  outputSchema?: Record<string, unknown>
  createTime?: string
  updateTime?: string
}

export interface ToolQueryParams {
  current?: number
  size?: number
  toolType?: ToolType
  toolName?: string
  toolDesc?: string
  isActive?: boolean
  sortBy?: 'createTime' | 'updateTime' | 'name'
  sortOrder?: 'asc' | 'desc'
}

export interface ApiToolCreate {
  name: string
  description?: string
  url?: string
  method?: ToolMethod
  parameters?: Record<string, unknown>
}

export interface ApiToolUpdate {
  name?: string
  description?: string
  url?: string
  method?: ToolMethod
  parameters?: Record<string, unknown>
  isActive?: boolean
}

export interface McpServerCreate {
  name: string
  mcpType: McpType
  url?: string
  command?: string
  args?: string[]
  env?: Record<string, string>
  isActive?: boolean
}

export interface McpServerUpdate {
  name?: string
  mcpType?: McpType
  url?: string
  command?: string
  args?: string[]
  env?: Record<string, string>
  isActive?: boolean
}

export interface ToolSyncData {
  serverId: number
  toolCount: number
  tools: Tool[]
}

export interface PromptVersionData {
  version: number
  promptDesc: string
  promptText: string
  createTime?: string
  updateTime?: string
}

export interface PromptDetailData {
  id: number
  promptName: string
  currentVersion: number
  versions: PromptVersionData[]
  createTime?: string
  updateTime?: string
}

export interface Prompt {
  id: number
  promptName: string
  promptDesc: string
  promptText: string
  currentVersion: number
  version: number
  createTime?: string
  updateTime?: string
}

export interface PromptCreate {
  promptName: string
  promptDesc: string
  promptText: string
}

export interface PromptUpdate {
  promptName?: string
  promptDesc?: string
  promptText?: string
}

export interface PromptPaginatedData {
  promptList: Prompt[]
  total: number
  current: number
  size: number
  pages: number
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

export interface SensitiveWordCategory {
  id: number
  name: string
  description?: string
}

export interface SensitiveWord {
  id: number
  word: string
  categoryId?: number
  level: number
  description?: string
  isActive: boolean
  category?: SensitiveWordCategory
}

export interface SensitiveWordCreate {
  word: string
  categoryId?: number
  level?: number
  description?: string
  isActive?: boolean
}

export interface SensitiveWordUpdate {
  word?: string
  categoryId?: number
  level?: number
  description?: string
  isActive?: boolean
}

export interface SensitiveWordCategoryCreate {
  name: string
  description?: string
}

export interface SensitiveWordCategoryUpdate {
  name?: string
  description?: string
}

export interface Flow {
  id: number
  name: string
  desc?: string
  currentVersion?: number
  flowJson?: Record<string, unknown>
  createTime?: string
  updateTime?: string
}

export interface FlowCreate {
  name: string
  desc?: string
  currentVersion?: number
  flowJson?: Record<string, unknown>
}

export interface FlowUpdate {
  name?: string
  desc?: string
  currentVersion?: number
  flowJson?: Record<string, unknown>
}

export interface RobotAction {
  id: number
  name: string
  code: string
  description?: string
  isActive: boolean
  createTime?: string
  updateTime?: string
}

export interface RobotActionCreate {
  name: string
  code: string
  description?: string
  isActive?: boolean
}

export interface RobotActionUpdate {
  name?: string
  code?: string
  description?: string
  isActive?: boolean
}

export interface RobotExpression {
  id: number
  name: string
  code: string
  description?: string
  isActive: boolean
  createTime?: string
  updateTime?: string
}

export interface RobotExpressionCreate {
  name: string
  code: string
  description?: string
  isActive?: boolean
}

export interface RobotExpressionUpdate {
  name?: string
  code?: string
  description?: string
  isActive?: boolean
}

export interface MetricData {
  id: number
  chatId: string
  chatRounds: number | null
  question: string
  answer: string
  model: string | null
  collections: string | null
  firstResponseMs: number | null
  totalMs: number | null
  tools: string | null
  precisionMode: boolean | null
  prompt: string | null
  createTime: string
  source: { type: string; display: string; detail?: string }[] | null
  toolArguments: Record<string, unknown> | null
  toolResult: Record<string, unknown> | null
  documentCount: number
  retrievalDocuments?: Record<
    string,
    { content: string; score: number | null }
  >[]
  inputTokens: number
  outputTokens: number
  executeTools: string | null
}

export interface ChatSession {
  chatId: string
  firstQuestion: string
  messageCount: number
  totalInputTokens: number
  totalOutputTokens: number
  model: string | null
  collections: string | null
  createTime: string
  updateTime: string
}

export interface SessionStats {
  chatId: string
  messageCount: number
  totalInputTokens: number
  totalOutputTokens: number
  totalTokens: number
  avgFirstResponseMs: number | null
  avgTotalMs: number | null
  modelsUsed: string[]
  collectionsUsed: string[]
}

export interface HotQuestionPoint {
  id: string
  text: string
  collection: string
  createTime: string
  updateTime: string
  count: number
}

export interface HotQuestionData {
  id: string
  representativeQuestion: string
  count: number
  clusterSize: number
  createTime: string
  updateTime: string
  similarQuestions: HotQuestionPoint[]
}

export interface MetricsQueryParams {
  current?: number
  size?: number
  startTime?: string
  endTime?: string
  collection?: string
  chatId?: string
}

export interface SessionsQueryParams {
  current?: number
  size?: number
  startTime?: string
  endTime?: string
  chatId?: string
}

export type FileStatus = 'pending' | 'parsing' | 'parsed' | 'failed'

export type FileType =
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'xls'
  | 'csv'
  | 'tsv'
  | 'json'
  | 'unknown'

export interface FileData {
  id: number
  collectionName: string
  filename: string
  fileType: FileType
  fileSize: number
  filePath?: string
  status: FileStatus
  version: number
  chunkCount: number
  parseConfig?: { maxChars?: number; overlap?: number }
  errorMessage?: string
  createTime: string
  updateTime: string
}

export interface ChunkData {
  id: string
  content: string
  chunkIndex?: number
}

export interface FileVersionData {
  id: number
  version: number
  fileSize: number
  filePath?: string
  changeNote?: string
  chunkCount: number
  parseConfig?: Record<string, unknown>
  createTime: string
}

export interface KnowledgeDocument {
  id: string
  content: string
  docType?: string
  fileId?: number
  source?: { filePath?: string; pageNum?: number }
  chunkIndex?: number
}

export interface QueryResult {
  id: string
  content: string
  score: number
}

export interface FileListResponse {
  fileList: FileData[]
  total: number
  current: number
  size: number
  pages: number
}

export interface FileDetailResponse {
  file: FileData
  chunks: ChunkData[]
  chunkTotal: number
  current: number
  size: number
}

export interface DocumentListResponse {
  docList: KnowledgeDocument[]
  total: number
  current: number
  size: number
  pages: number
}

export interface QueryResponse {
  collectionName: string
  docList: QueryResult[]
  topK: number
  scoreThreshold: number | null
}

export interface ChunkPreview {
  content: string
  chunkIndex?: number
}

export interface PreviewChunksResponse {
  filename: string
  chunks: ChunkPreview[]
  chunkCount: number
  previewId: string
}
