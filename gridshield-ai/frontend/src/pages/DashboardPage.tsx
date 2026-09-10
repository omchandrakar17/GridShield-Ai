import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, PieChart, Pie, Cell,
} from 'recharts'
import {
  Users, AlertTriangle, FolderOpen, TrendingUp,
  ShieldCheck, RefreshCw, Play
} from 'lucide-react'
import { getDashboardStats, runBatchAnalysis } from '../services/api'
import type { DashboardStats } from '../types'
import { getRiskBadgeClass, riskBarColor, formatNumber, formatPeriod } from '../utils/formatting'
import { PageHeader, StatCard, LoadingSpinner, ErrorState, EmptyState } from '../components/shared'

const RISK_PIE_COLORS = { Critical: '#ef4444', High: '#f97316', Medium: '#eab308', Low: '#22c55e' }

export default function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [batchMsg, setBatchMsg] = useState<string | null>(null)

  const fetchStats = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getDashboardStats()
      setStats(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to load dashboard statistics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchStats() }, [])

  const handleRunBatch = async () => {
    setRunning(true)
    setBatchMsg(null)
    try {
      const res = await runBatchAnalysis(500)
      setBatchMsg(`Batch analysis complete: ${res.data.processed} consumers analyzed`)
      fetchStats()
    } catch (e: any) {
      setBatchMsg(e?.response?.data?.detail ?? 'Batch analysis failed')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <LoadingSpinner message="Loading dashboard…" />
  if (error) return <div className="p-6"><ErrorState message={error} onRetry={fetchStats} /></div>
  if (!stats) return null

  const pieData = Object.entries(stats.risk_distribution || {}).map(([level, count]) => ({
    name: level, value: count as number, fill: RISK_PIE_COLORS[level as keyof typeof RISK_PIE_COLORS] ?? '#9ca3af'
  }))

  const trendData = [...(stats.risk_trend || [])].reverse().map(t => ({
    month: formatPeriod(t.month),
    'Total Analyzed': t.total,
    'High/Critical': t.high_risk,
  }))

  return (
    <div>
      <PageHeader
        title="Investigation Dashboard"
        subtitle="Electricity consumption analysis and fraud risk overview"
        actions={
          <div className="flex gap-2 items-center">
            {batchMsg && <span className="text-xs text-blue-600">{batchMsg}</span>}
            <button className="btn-secondary flex items-center gap-1.5" onClick={fetchStats}>
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
            <button className="btn-primary flex items-center gap-1.5" onClick={handleRunBatch} disabled={running}>
              <Play className="w-3.5 h-3.5" />
              {running ? 'Analyzing…' : 'Run Batch Analysis'}
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard label="Total Consumers" value={stats.total_consumers.toLocaleString()}
            icon={<Users className="w-5 h-5" />} />
          <StatCard label="Consumers Analyzed" value={stats.total_analyzed.toLocaleString()}
            sub={stats.total_consumers > 0 ? `${Math.round(stats.total_analyzed / stats.total_consumers * 100)}% of total` : ''}
            icon={<ShieldCheck className="w-5 h-5" />} />
          <StatCard label="High / Critical Risk" value={stats.high_risk_count.toLocaleString()}
            color="text-red-600" icon={<AlertTriangle className="w-5 h-5 text-red-400" />} />
          <StatCard label="Total Anomaly Flags" value={stats.total_anomaly_flags.toLocaleString()}
            icon={<TrendingUp className="w-5 h-5" />} />
          <StatCard label="Open Investigations" value={stats.open_cases.toLocaleString()}
            color="text-orange-600" icon={<FolderOpen className="w-5 h-5 text-orange-400" />} />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Risk distribution pie */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Risk Distribution</h3>
            {pieData.length === 0 ? (
              <EmptyState title="No analysis data yet" description="Run batch analysis to populate this chart." />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={75} dataKey="value"
                    label={(p: any) => (
                      <text x={p.x} y={p.y} textAnchor={p.textAnchor} fill="#D3DEEA" fontSize={11}>
                        {`${p.name}: ${p.value}`}
                      </text>
                    )}
                    labelLine={{ stroke: '#6B85A3' }}>
                    {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Risk trend line */}
          <div className="card p-5 col-span-2">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Investigation Trend (Last 6 Months)</h3>
            {trendData.length === 0 ? (
              <EmptyState title="No trend data yet" description="Run batch analysis over multiple sessions to see trends." />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E344F" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8CA3BF" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#8CA3BF" }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11, color: '#D3DEEA' }} />
                  <Line type="monotone" dataKey="Total Analyzed" stroke="#3b82f6" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="High/Critical" stroke="#ef4444" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Recent flagged consumers */}
        <div className="card">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Recently Analyzed Consumers</h3>
            <button className="text-xs text-blue-600 hover:underline" onClick={() => navigate('/anomalies')}>
              View all →
            </button>
          </div>
          {stats.recent_flagged.length === 0 ? (
            <EmptyState title="No analyzed consumers yet" description="Upload data and run batch analysis to see results." />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-5 py-3 text-left font-medium">Consumer ID</th>
                  <th className="px-5 py-3 text-left font-medium">Risk Score</th>
                  <th className="px-5 py-3 text-left font-medium">Risk Level</th>
                  <th className="px-5 py-3 text-left font-medium">Recommended Action</th>
                  <th className="px-5 py-3 text-left font-medium">Analyzed</th>
                  <th className="px-5 py-3 text-left font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {stats.recent_flagged.map((row) => (
                  <tr key={row.consumer_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono text-xs text-gray-900">{row.consumer_id}</td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full" style={{
                            width: `${row.fraud_risk_score}%`,
                            backgroundColor: riskBarColor[row.risk_level] ?? '#9ca3af',
                          }} />
                        </div>
                        <span className="text-xs text-gray-600">{row.fraud_risk_score.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={getRiskBadgeClass(row.risk_level)}>{row.risk_level}</span>
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-600 max-w-xs truncate">{row.recommended_action}</td>
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
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
