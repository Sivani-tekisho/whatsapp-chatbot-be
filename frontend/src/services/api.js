import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export const getMetrics = () => api.get('/conversations/metrics')
export const getConversations = (params) => api.get('/conversations', { params })
export const getConversation = (id) => api.get(`/conversations/${id}`)
export const sendReply = (conversationId, message) =>
  api.post(`/conversations/${conversationId}/reply`, { message })
export const updateConversationStatus = (id, status) =>
  api.patch(`/conversations/${id}/status`, { status })

export const getDocuments = () => api.get('/documents')
export const uploadDocument = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })
}
export const ingestUrl = (url, title) => api.post('/documents/url', { url, title })
export const deleteDocument = (id) => api.delete(`/documents/${id}`)

export const getSettings = () => api.get('/settings')
export const updateSettings = (data) => api.patch('/settings', data)

export default api
