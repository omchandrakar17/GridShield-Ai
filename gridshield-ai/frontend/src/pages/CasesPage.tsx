import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCases } from '../services/api'
import type { InvestigationCase, CaseStatus } from '../types'
import { getRiskBadgeClass } from '../utils/formatting'
import { PageHeader, LoadingSpinner, ErrorState, EmptyState } from '../components/shared'

const STATUS_FILTERS: Array<CaseStatus | ''> = ['', 'Open', 'Under Investigation', 'Inspection Required', 'Resolved']

const statusColor: Record<string, string> = {
  'Open': 'text-blue-700 bg-blue-50 border-blue-200',
  'Under Investigation': 'text-orange-700 bg-orange-50 border-orange-200',
  'Inspection Required': 'text-red-700 bg-red-50 border-red-200',
  'Resolved': 'text-green-700 bg-green-50 border-green-200',
}

export default function CasesPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<InvestigationCase[]>([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<CaseStatus | ''>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 50

  const fetchCases = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getCases(statusFilter || undefined, undefined, page, PAGE_SIZE)
      setCases(res.data.cases)
      setTotal(res.data.total)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to load cases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCases() }, [statusFilter, page])

  return (
    <div>
      <PageHeader
        title="Investigation Cases"
        subtitle="Manage and track fraud investigation cases"
        actions={
          <div className="flex items-center gap-2">
            {STATUS_FILTERS.map(s => (
              <button
                key={s || 'all'}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  statusFilter === s
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-ink-700 text-gray-600 border-gray-300 hover:border-amber'
                }`}
                onClick={() => { setStatusFilter(s); setPage(1) }}
              >
                {s || 'All'}
              </button>
            ))}
          </div>
        }
      />

      <div className="p-6">
        {loading && <LoadingSpinner message="Loading cases…" />}
        {error && <ErrorState message={error} onRetry={fetchCases} />}
        {!loading && !error && cases.length === 0 && (
          <EmptyState
            title="No investigation cases"
            description="Create cases from the Consumer Investigation Workspace after analyzing a consumer."
          />
        )}

        {!loading && cases.length > 0 && (
          <>
            <div className="text-sm text-gray-500 mb-3">
              {total} case{total !== 1 ? 's' : ''}{statusFilter ? ` with status "${statusFilter}"` : ''}
            </div>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                    {['Case ID','Consumer ID','Status','Priority','Risk Score','Assigned To','Created',''].map(h => (
                      <th key={h} className="px-5 py-3 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {cases.map(c => (
                    <tr key={c.case_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/cases/${c.case_id}`)}>
                      <td className="px-5 py-3 font-mono text-xs font-medium text-blue-700">{c.case_id}</td>
                      <td className="px-5 py-3 font-mono text-xs">{c.consumer_id}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${statusColor[c.status] ?? ''}`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {c.priority && <span className={getRiskBadgeClass(c.priority)}>{c.priority}</span>}
                      </td>
                      <td className="px-5 py-3 text-xs">
                        {c.fraud_risk_score != null ? c.fraud_risk_score.toFixed(1) : '—'}
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500">{c.assigned_to ?? 'Unassigned'}</td>
                      <td className="px-5 py-3 text-xs text-gray-400">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3">
                        <span className="text-xs text-blue-600 hover:underline">View →</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {total > PAGE_SIZE && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-sm text-gray-500">Page {page} of {Math.ceil(total / PAGE_SIZE)}</span>
                <div className="flex gap-2">
                  <button className="btn-secondary text-xs" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                  <button className="btn-secondary text-xs" disabled={page >= Math.ceil(total / PAGE_SIZE)} onClick={() => setPage(p => p + 1)}>Next →</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
