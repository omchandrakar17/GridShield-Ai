import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCase, updateCase, addCaseEvent, downloadReport, runInvestigation } from '../services/api'
import type { InvestigationCase } from '../types'
import { getRiskBadgeClass, riskBarColor, anomalyTypeLabel } from '../utils/formatting'
import { PageHeader, LoadingSpinner, ErrorState, RiskScoreGauge } from '../components/shared'
import {
  CheckCircle, Clock, User, FileText, AlertCircle, Bot, Download, ArrowLeft
} from 'lucide-react'

const STATUS_OPTIONS = ['Open', 'Under Investigation', 'Inspection Required', 'Resolved']

const eventTypeIcon: Record<string, React.ReactNode> = {
  case_created: <CheckCircle className="w-4 h-4 text-blue-500" />,
  status_change: <Clock className="w-4 h-4 text-orange-500" />,
  ai_analysis: <Bot className="w-4 h-4 text-purple-500" />,
  note_added: <FileText className="w-4 h-4 text-gray-400" />,
  assigned: <User className="w-4 h-4 text-green-500" />,
  resolved: <CheckCircle className="w-4 h-4 text-green-600" />,
}

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()

  const [caseData, setCaseData] = useState<InvestigationCase | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editStatus, setEditStatus] = useState('')
  const [editAssigned, setEditAssigned] = useState('')
  const [noteText, setNoteText] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [reanalyzing, setReanalyzing] = useState(false)

  const fetchCase = async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const res = await getCase(caseId)
      setCaseData(res.data)
      setEditStatus(res.data.status)
      setEditAssigned(res.data.assigned_to ?? '')
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to load case')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCase() }, [caseId])

  const handleSave = async () => {
    if (!caseId || !caseData) return
    setSaving(true)
    setSaveMsg(null)
    try {
      await updateCase(caseId, {
        status: editStatus !== caseData.status ? editStatus : undefined,
        assigned_to: editAssigned !== (caseData.assigned_to ?? '') ? editAssigned : undefined,
      })
      setSaveMsg('Case updated successfully')
      fetchCase()
    } catch (e: any) {
      setSaveMsg(e?.response?.data?.detail ?? 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  const handleAddNote = async () => {
    if (!caseId || !noteText.trim()) return
    setSaving(true)
    try {
      await addCaseEvent(caseId, 'note_added', noteText.trim())
      setNoteText('')
      fetchCase()
    } catch { } finally { setSaving(false) }
  }

  const handleDownloadPdf = async () => {
    if (!caseId) return
    setDownloading(true)
    try {
      await downloadReport(caseId)
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'Failed to generate report')
    } finally {
      setDownloading(false)
    }
  }

  const handleReanalyze = async () => {
    if (!caseData) return
    setReanalyzing(true)
    try {
      await runInvestigation(caseData.consumer_id)
      fetchCase()
    } catch { } finally { setReanalyzing(false) }
  }

  if (loading) return <LoadingSpinner message="Loading case…" />
  if (error) return <div className="p-6"><ErrorState message={error} onRetry={fetchCase} /></div>
  if (!caseData) return null

  const anomalyFlags: any[] = (() => {
    return []  // flags shown via the investigation page; here we show the AI reasoning
  })()

  return (
    <div>
      <PageHeader
        title={`Case ${caseData.case_id}`}
        subtitle={`Consumer ${caseData.consumer_id} · ${caseData.status}`}
        actions={
          <div className="flex gap-2">
            <button className="btn-secondary flex items-center gap-1.5" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
            <button className="btn-secondary flex items-center gap-1.5" onClick={() => navigate(`/investigate/${caseData.consumer_id}`)}>
              Investigate Consumer
            </button>
            <button className="btn-secondary flex items-center gap-1.5" onClick={handleReanalyze} disabled={reanalyzing}>
              <Bot className="w-3.5 h-3.5" /> {reanalyzing ? 'Analyzing…' : 'Re-analyze'}
            </button>
            <button className="btn-primary flex items-center gap-1.5" onClick={handleDownloadPdf} disabled={downloading}>
              <Download className="w-3.5 h-3.5" /> {downloading ? 'Generating…' : 'Download Report'}
            </button>
          </div>
        }
      />

      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: case info + controls */}
        <div className="lg:col-span-2 space-y-5">
          {/* Summary */}
          <div className="card p-5">
            <div className="flex items-start gap-6">
              <div className="flex-1 grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
                {[
                  ['Case ID', caseData.case_id],
                  ['Consumer ID', caseData.consumer_id],
                  ['Created', new Date(caseData.created_at).toLocaleString()],
                  ['Last Updated', new Date(caseData.updated_at).toLocaleString()],
                  ['Assigned To', caseData.assigned_to ?? 'Unassigned'],
                  ['Priority', caseData.priority ?? '—'],
                  ['Resolution', caseData.resolved_at ? new Date(caseData.resolved_at).toLocaleString() : 'Pending'],
                ].map(([l, v]) => (
                  <div key={String(l)}>
                    <div className="text-xs text-gray-400">{l}</div>
                    <div className="font-medium text-gray-800 text-xs mt-0.5">{String(v)}</div>
                  </div>
                ))}
              </div>
              {caseData.fraud_risk_score != null && caseData.risk_level && (
                <RiskScoreGauge score={caseData.fraud_risk_score} level={caseData.risk_level} />
              )}
            </div>
          </div>

          {/* Update case */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Update Case</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Status</label>
                <select
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={editStatus}
                  onChange={e => setEditStatus(e.target.value)}
                >
                  {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Assigned To</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={editAssigned}
                  onChange={e => setEditAssigned(e.target.value)}
                  placeholder="Investigator name or ID"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button className="btn-primary text-sm" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
              {saveMsg && <span className="text-xs text-green-600">{saveMsg}</span>}
            </div>
          </div>

          {/* Add note */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Add Investigation Note</h3>
            <textarea
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
              placeholder="Enter investigation notes, evidence, or findings…"
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
            />
            <button className="btn-secondary text-sm mt-2" onClick={handleAddNote} disabled={saving || !noteText.trim()}>
              Add Note
            </button>
          </div>

          {/* Resolution notes */}
          {caseData.resolution_notes && (
            <div className="card p-5 bg-green-50 border-green-200">
              <h3 className="text-sm font-semibold text-green-800 mb-2">Resolution Notes</h3>
              <p className="text-sm text-green-700">{caseData.resolution_notes}</p>
            </div>
          )}
        </div>

        {/* Right: timeline */}
        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Investigation Timeline</h3>
            {(!caseData.timeline || caseData.timeline.length === 0) ? (
              <p className="text-xs text-gray-400">No events recorded yet.</p>
            ) : (
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
                <div className="space-y-4">
                  {[...caseData.timeline].reverse().map((ev, i) => (
                    <div key={ev.id} className="flex gap-3 pl-2">
                      <div className="relative z-10 flex-shrink-0 w-6 h-6 bg-ink-800 border border-gray-200 rounded-full flex items-center justify-center">
                        {eventTypeIcon[ev.event_type] ?? <Clock className="w-3 h-3 text-gray-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 mb-0.5">
                          <span className="text-xs font-medium text-gray-700 capitalize">
                            {ev.event_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-gray-400">· {ev.performed_by}</span>
                        </div>
                        <p className="text-xs text-gray-600">{ev.description}</p>
                        <p className="text-[10px] text-gray-400 mt-0.5">
                          {new Date(ev.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
