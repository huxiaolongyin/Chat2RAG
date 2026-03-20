import type {
  BaseResponse,
  DocumentListResponse,
  FileDetailResponse,
  FileListResponse,
  FileVersionData,
  KnowledgeCollection,
  PaginatedResponse,
  PreviewChunksResponse,
  QueryResponse
} from '@/types/api'
import api from './index'

export const knowledgeApi = {
  getCollections: (current = 1, size = 12, collectionName?: string) => {
    const params: Record<string, unknown> = { current, size }
    if (collectionName) params.collectionName = collectionName
    return api.get<BaseResponse<PaginatedResponse<KnowledgeCollection>>>(
      '/v1/knowledge/collection',
      { params }
    )
  },

  createCollection: (collectionName: string) => {
    return api.post<BaseResponse>('/v1/knowledge/collection', null, {
      params: { collectionName }
    })
  },

  deleteCollection: (collectionName: string) => {
    return api.delete<BaseResponse>('/v1/knowledge/collection', {
      params: { collectionName }
    })
  },

  reindexCollection: (collectionName: string, backup = true) => {
    return api.post<BaseResponse>('/v1/knowledge/collection/reindex', null, {
      params: { collectionName, backup }
    })
  },

  getFiles: (
    collectionName: string,
    current = 1,
    size = 10,
    filename?: string,
    status?: string
  ) => {
    const params: Record<string, unknown> = { collectionName, current, size }
    if (filename) params.filename = filename
    if (status) params.status = status
    return api.get<BaseResponse<FileListResponse>>(
      '/v1/knowledge/collection/file',
      {
        params
      }
    )
  },

  getFileDetail: (
    fileId: number,
    collectionName: string,
    current = 1,
    size = 20
  ) => {
    return api.get<BaseResponse<FileDetailResponse>>(
      `/v1/knowledge/collection/file/${fileId}`,
      { params: { collectionName, current, size } }
    )
  },

  uploadFile: (
    collectionName: string,
    file: File,
    maxChars = 600,
    overlap = 100,
    previewId?: string
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: Record<string, unknown> = {
      collectionName,
      maxChars,
      overlap
    }
    if (previewId) params.previewId = previewId
    return api.post<BaseResponse>('/v1/knowledge/collection/file', formData, {
      params
    })
  },

  deleteFile: (fileId: number, collectionName: string) => {
    return api.delete<BaseResponse>(`/v1/knowledge/collection/file/${fileId}`, {
      params: { collectionName }
    })
  },

  uploadFileVersion: (
    fileId: number,
    file: File,
    changeNote?: string,
    maxChars = 600,
    overlap = 100
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: Record<string, unknown> = { maxChars, overlap }
    if (changeNote) params.changeNote = changeNote
    return api.post<BaseResponse>(
      `/v1/knowledge/collection/file/${fileId}/version`,
      formData,
      { params }
    )
  },

  getFileVersions: (fileId: number) => {
    return api.get<BaseResponse<{ versions: FileVersionData[] }>>(
      `/v1/knowledge/collection/file/${fileId}/versions`
    )
  },

  rollbackVersion: (fileId: number, version: number) => {
    return api.post<BaseResponse>(
      `/v1/knowledge/collection/file/${fileId}/rollback/${version}`
    )
  },

  reparseFile: (fileId: number, maxChars = 600, overlap = 100) => {
    return api.post<BaseResponse>(
      `/v1/knowledge/collection/file/${fileId}/reparse`,
      null,
      { params: { maxChars, overlap } }
    )
  },

  previewFileChunks: (file: File, maxChars = 600, overlap = 100) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<BaseResponse<PreviewChunksResponse>>(
      '/v1/knowledge/collection/file/preview',
      formData,
      { params: { maxChars, overlap } }
    )
  },

  getDocuments: (
    collectionName: string,
    current = 1,
    size = 10,
    documentContent?: string,
    fileId?: number,
    filePath?: string
  ) => {
    const params: Record<string, unknown> = { collectionName, current, size }
    if (documentContent) params.documentContent = documentContent
    if (fileId !== undefined) params.fileId = fileId
    if (filePath) params.filePath = filePath
    return api.get<BaseResponse<DocumentListResponse>>(
      '/v1/knowledge/collection/document',
      { params }
    )
  },

  createDocumentsByJson: (
    collectionName: string,
    docList: { question: string; answer: string }[]
  ) => {
    return api.post<BaseResponse>(
      '/v1/knowledge/collection/document',
      docList,
      { params: { collectionName } }
    )
  },

  createDocumentsByFile: (
    collectionName: string,
    file: File,
    maxChars = 600,
    overlap = 100,
    preview = false
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<BaseResponse>(
      '/v1/knowledge/collection/document/file',
      formData,
      { params: { collectionName, maxChars, overlap, preview } }
    )
  },

  deleteDocuments: (collectionName: string, docIdList: string[]) => {
    return api.delete<BaseResponse>('/v1/knowledge/collection/document', {
      params: { collectionName },
      data: docIdList
    })
  },

  queryDocuments: (
    collectionName: string,
    query: string,
    topK = 5,
    scoreThreshold?: number,
    type = 'qa_pair'
  ) => {
    const params: Record<string, unknown> = {
      collectionName,
      query,
      topK,
      type
    }
    if (scoreThreshold !== undefined) params.scoreThreshold = scoreThreshold
    return api.get<BaseResponse<QueryResponse>>('/v1/knowledge/query', {
      params
    })
  }
}
