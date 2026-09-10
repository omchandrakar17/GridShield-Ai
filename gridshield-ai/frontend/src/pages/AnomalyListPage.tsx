import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAnomalyList } from '../services/api'
import type { AnomalyResult } from '../types'
import { getRiskBadgeClass, riskBarColor, formatNumber, formatPeriod, anomalyTypeLabel } from '../utils/formatting'
import { PageHeader, LoadingSpinner, ErrorState, EmptyState } from '../components/shared'
import { Search, AlertTriangle } from 'lucide-react'

const RISK_FILTERS = ['', 'Critical', 'High', 'Medium', 'Low']

export default function AnomalyListPage() {
  const navigate = useNavigate()
  const [results, setResults] = useState<AnomalyResult[]>([])
  const [total, setTotal] = useState(0)
  const [riskFilter, setRiskFilter] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const PAGE_SIZE = 50

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getAnomalyList(riskFilter || undefined, page, PAGE_SIZE)
      setResults(res.data.results)
      setTotal(res.data.total)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to load anomaly results')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [riskFilter, page])

  return (
    <div>
      <PageHeader
        title="Anomaly Detection Results"
        subtitle="All analyzed consumers with detected anomaly flags and risk scores"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Filter by risk:</span>
            {RISK_FILTERS.map(r => (
              <button
                key={r || 'all'}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  riskFilter === r
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-ink-700 text-gray-600 border-gray-300 hover:border-amber'
                }`}
                onClick={() => { setRiskFilter(r); setPage(1) }}
              >
                {r || 'All'}
              </button>
            ))}
          </div>
        }
      />

      <div className="p-6">
        {loading && <LoadingSpinner message="Loading anomaly results…" />}
        {error && <ErrorState message={error} onRetry={fetchData} />}
        {!loading && !error && results.length === 0 && (
          <EmptyState
            title="No anomaly results"
            description="Run batch analysis from the dashboard to populate this list."
          />
        )}

        {!loading && results.length > 0 && (
          <>
            <div className="text-sm text-gray-500 mb-3">
              Showing {results.length} of {total} analyzed consumers
              {riskFilter ? ` (${riskFilter} risk)` : ''}
            </div>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3 text-left font-medium">Consumer ID</th>
                    <th className="px-5 py-3 text-left font-medium">Risk Score</th>
                    <th className="px-5 py-3 text-left font-medium">Risk Level</th>
                    <th className="px-5 py-3 text-left font-medium">Anomaly Types</th>
                    <th className="px-5 py-3 text-left font-medium">Affected Periods</th>
                    <th className="px-5 py-3 text-left font-medium">Confidence</th>
                    <th className="px-5 py-3 text-left font-medium">Analyzed</th>
                    <th className="px-5 py-3 text-left font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {results.map(row => {
                    const types: string[] = (() => {
                      try {
                        return typeof row.anomaly_flags === 'string'
                          ? (JSON.parse(row.anomaly_flags as any) as any[]).map(f => f.type)
                          : (row.anomaly_flags ?? []).map((f: any) => f.type)
                      } catch { return [] }
                    })()
                    const uniqueTypes = [...new Set(types)]

                    const periods: string[] = (() => {
                      try {
                        return typeof row.affected_periods === 'string'
                          ? JSON.parse(row.affected_periods as any)
                          : (row.affected_periods ?? [])
                      } catch { return [] }
                    })()

                    return (
                      <tr key={row.consumer_id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 font-mono text-xs">{row.consumer_id}</td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div className="h-2 rounded-full transition-all" style={{
                                width: `${row.fraud_risk_score}%`,
                                backgroundColor: riskBarColor[row.risk_level] ?? '#9ca3af',
                              }} />
                            </div>
                            <span className="text-xs font-medium">{row.fraud_risk_score.toFixed(1)}</span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className={getRiskBadgeClass(row.risk_level)}>{row.risk_level}</span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex flex-wrap gap-1">
                            {uniqueTypes.slice(0, 3).map(t => (
                              <span key={t} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                {anomalyTypeLabel(t)}
                              </span>
                            ))}
                            {uniqueTypes.length > 3 && (
                              <span className="text-[10px] text-gray-400">+{uniqueTypes.length - 3}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500">{periods.length}</td>
                        <td className="px-5 py-3 text-xs text-gray-500">
                          {row.confidence_score != null ? `${Math.round(row.confidence_score * 100)}%` : '—'}
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-400">
                          {new Date(row.analysis_timestamp).toLocaleDateString()}
                        </td>
                        <td className="px-5 py-3">
                          <button
                            className="text-xs text-blue-600 hover:underline"
                            onClick={() => navigate(`/investigate/${row.consumer_id}`)}
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
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
