import axios from 'axios'
import type {
  DashboardStats, ConsumerProfile, AnomalyResult,
  InvestigationCase, CaseEvent, ConsumerRecord,
} from '../types'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

// ── Data ──────────────────────────────────────────────────────────────────────
export const uploadDataset = (file: File, onProgress?: (pct: number) => void) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/data/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
}

export const getConsumers = (page = 1, pageSize = 50, search?: string) =>
  api.get('/data/consumers', { params: { page, page_size: pageSize, search } })

export const getConsumerRecords = (consumerId: string) =>
  api.get<{ consumer_id: string; records: ConsumerRecord[]; count: number }>(
    `/data/consumers/${encodeURIComponent(consumerId)}/records`
  )

export const getDatasetStats = () => api.get('/data/stats')

// ── Analysis ──────────────────────────────────────────────────────────────────
export const getConsumerProfile = (consumerId: string) =>
  api.get<ConsumerProfile>(`/analysis/consumer/${encodeURIComponent(consumerId)}/profile`)

export const getConsumerAnomalies = (consumerId: string) =>
  api.get(`/analysis/consumer/${encodeURIComponent(consumerId)}/anomalies`)

export const getDashboardStats = () =>
  api.get<DashboardStats>('/analysis/dashboard')

export const runBatchAnalysis = (limit = 100) =>
  api.post('/analysis/run-batch', null, { params: { limit } })

export const getAnomalyList = (riskLevel?: string, page = 1, pageSize = 50) =>
  api.get<{ results: AnomalyResult[]; total: number }>(
    '/analysis/anomaly-list',
    { params: { risk_level: riskLevel, page, page_size: pageSize } }
  )

// ── Agents ────────────────────────────────────────────────────────────────────
export const runInvestigation = (consumerId: string) =>
  api.post(`/agents/investigate/${encodeURIComponent(consumerId)}`)

export const getAgentStatus = () => api.get('/agents/status')

// ── Cases ─────────────────────────────────────────────────────────────────────
export const createCase = (consumerId: string, priority?: string, notes?: string) =>
  api.post('/cases/', { consumer_id: consumerId, priority, notes })

export const getCases = (status?: string, riskLevel?: string, page = 1, pageSize = 50) =>
  api.get<{ cases: InvestigationCase[]; total: number }>(
    '/cases/',
    { params: { status, risk_level: riskLevel, page, page_size: pageSize } }
  )

export const getCase = (caseId: string) =>
  api.get<InvestigationCase>(`/cases/${caseId}`)

export const updateCase = (caseId: string, updates: {
  status?: string; assigned_to?: string; notes?: string; resolution_notes?: string
}) => api.patch(`/cases/${caseId}`, updates)

export const addCaseEvent = (caseId: string, eventType: string, description: string, performedBy = 'investigator') =>
  api.post(`/cases/${caseId}/events`, { event_type: eventType, description, performed_by: performedBy })

export const getCaseTimeline = (caseId: string) =>
  api.get<{ case_id: string; events: CaseEvent[] }>(`/cases/${caseId}/timeline`)

// ── Reports ───────────────────────────────────────────────────────────────────
export const downloadReport = async (caseId: string) => {
  const res = await api.get(`/reports/${caseId}/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `gridshield-${caseId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export const getReportJson = (caseId: string) =>
  api.get(`/reports/${caseId}/json`)

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health')
