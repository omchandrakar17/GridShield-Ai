import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { Search, Play, FolderPlus, Bot, CheckCircle, AlertCircle } from 'lucide-react'
import {
  getConsumerProfile, getConsumerAnomalies, runInvestigation, createCase, getConsumers,
} from '../services/api'
import type { ConsumerProfile, AgentTrace } from '../types'
import {
  getRiskBadgeClass, riskBarColor, formatNumber, formatPeriod,
  anomalyTypeLabel, severityColor,
} from '../utils/formatting'
import {
  PageHeader, RiskScoreGauge, LoadingSpinner, ErrorState, EmptyState,
} from '../components/shared'

export default function InvestigatePage() {
  const { consumerId: paramCid } = useParams<{ consumerId: string }>()
  const navigate = useNavigate()

  const [search, setSearch] = useState(paramCid ?? '')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const [selectedConsumer, setSelectedConsumer] = useState<string | null>(paramCid ?? null)
  const [profile, setProfile] = useState<ConsumerProfile | null>(null)
  const [anomalyData, setAnomalyData] = useState<any>(null)
  const [agentTrace, setAgentTrace] = useState<AgentTrace | null>(null)

  const [loadingProfile, setLoadingProfile] = useState(false)
  const [loadingInvestigation, setLoadingInvestigation] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [investigationError, setInvestigationError] = useState<string | null>(null)
  const [caseCreated, setCaseCreated] = useState<string | null>(null)
  const [caseError, setCaseError] = useState<string | null>(null)

  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q || q.length < 2) { setSuggestions([]); return }
    try {
      const res = await getConsumers(1, 10, q)
      setSuggestions(res.data.consumers)
    } catch { setSuggestions([]) }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchSuggestions(search), 250)
    return () => clearTimeout(t)
  }, [search, fetchSuggestions])

  const loadConsumer = useCallback(async (cid: string) => {
    setSelectedConsumer(cid)
    setProfile(null)
    setAnomalyData(null)
    setAgentTrace(null)
    setProfileError(null)
    setInvestigationError(null)
    setCaseCreated(null)
    setCaseError(null)
    setLoadingProfile(true)
    setShowSuggestions(false)
    navigate(`/investigate/${cid}`, { replace: true })

    try {
      const [profileRes, anomalyRes] = await Promise.all([
        getConsumerProfile(cid),
        getConsumerAnomalies(cid),
      ])
      setProfile(profileRes.data)
      setAnomalyData(anomalyRes.data)
    } catch (e: any) {
      setProfileError(e?.response?.data?.detail ?? 'Failed to load consumer data')
    } finally {
      setLoadingProfile(false)
    }
  }, [navigate])

  useEffect(() => {
    if (paramCid && paramCid !== selectedConsumer) loadConsumer(paramCid)
  }, [paramCid])

  const handleRunInvestigation = async () => {
    if (!selectedConsumer) return
    setLoadingInvestigation(true)
    setInvestigationError(null)
    try {
      const res = await runInvestigation(selectedConsumer)
      setAgentTrace(res.data.agent_trace)
      setAnomalyData((prev: any) => ({
        ...prev,
        risk_assessment: res.data.risk_assessment,
        anomaly_result: {
          ...prev?.anomaly_result,
          flags: res.data.agent_trace?.agents?.find((a: any) => a.agent === 'ExplainabilityAgent')?.evidence_items ?? prev?.anomaly_result?.flags,
          anomaly_types: res.data.anomaly_summary?.anomaly_types,
          affected_periods: res.data.anomaly_summary?.affected_periods,
        },
        recommended_action: res.data.recommended_action,
      }))
    } catch (e: any) {
      setInvestigationError(e?.response?.data?.detail ?? 'AI investigation failed')
    } finally {
      setLoadingInvestigation(false)
    }
  }

  const handleCreateCase = async () => {
    if (!selectedConsumer) return
    setCaseCreated(null)
    setCaseError(null)
    try {
      const res = await createCase(selectedConsumer, anomalyData?.risk_assessment?.risk_level)
      setCaseCreated(res.data.case_id)
    } catch (e: any) {
      setCaseError(e?.response?.data?.detail ?? 'Failed to create case')
    }
  }

  // Chart data
  const chartData = profile
    ? profile.periods.map((p, i) => ({
        period: formatPeriod(p),
        consumption: profile.consumption_values[i],
        mean: profile.mean_consumption,
      }))
    : []

  const riskScore = anomalyData?.risk_assessment?.fraud_risk_score ?? null
  const riskLevel = anomalyData?.risk_assessment?.risk_level ?? null
  const flags = anomalyData?.anomaly_result?.flags ?? []

  return (
    <div>
      <PageHeader
        title="Consumer Investigation Workspace"
        subtitle="Search a consumer, analyze consumption behavior, run AI investigation"
      />

      <div className="p-6 space-y-5">
        {/* Search */}
        <div className="card p-4">
          <div className="relative flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter consumer ID…"
                value={search}
                onChange={e => { setSearch(e.target.value); setShowSuggestions(true) }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                onKeyDown={e => { if (e.key === 'Enter' && search) loadConsumer(search) }}
              />
              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-10 top-full mt-1 left-0 right-0 bg-ink-800 border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
                  {suggestions.map(s => (
                    <button
                      key={s}
                      className="block w-full text-left px-4 py-2 text-sm hover:bg-blue-50 font-mono"
                      onMouseDown={() => { setSearch(s); loadConsumer(s) }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="btn-primary" onClick={() => search && loadConsumer(search)}>
              Load Consumer
            </button>
          </div>
        </div>

        {/* Loading / error */}
        {loadingProfile && <LoadingSpinner message="Loading consumer profile…" />}
        {profileError && <ErrorState message={profileError} onRetry={() => selectedConsumer && loadConsumer(selectedConsumer)} />}

        {!loadingProfile && !profile && !profileError && !selectedConsumer && (
          <EmptyState
            title="No consumer selected"
            description="Enter a consumer ID above to begin investigation. Upload billing data via Data Management if no consumers are available."
          />
        )}

        {profile && (
          <>
            {/* Consumer header */}
            <div className="card p-5 flex flex-wrap items-start gap-6">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-3">
                  <h2 className="text-lg font-semibold text-gray-900 font-mono">{profile.consumer_id}</h2>
                  {riskLevel && <span className={getRiskBadgeClass(riskLevel)}>{riskLevel}</span>}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm">
                  {[
                    ['Type', profile.consumer_type], ['Tariff', profile.tariff_category],
                    ['Location', profile.location], ['Division', profile.division],
                    ['Periods', profile.periods_available], ['Mean Consumption', `${formatNumber(profile.mean_consumption)} kWh`],
                    ['Std Dev', `${formatNumber(profile.std_consumption)} kWh`], ['Trend', `${profile.trend_slope > 0 ? '+' : ''}${profile.trend_slope.toFixed(2)} kWh/period`],
                  ].map(([l, v]) => (
                    <div key={String(l)}>
                      <span className="text-gray-400 text-xs">{l}</span>
                      <div className="font-medium text-gray-800 text-xs">{String(v)}</div>
                    </div>
                  ))}
                </div>
              </div>
              {riskScore !== null && (
                <RiskScoreGauge score={riskScore} level={riskLevel ?? 'Low'} />
              )}
            </div>

            {/* Consumption chart */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Consumption History</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E344F" />
                  <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#8CA3BF" }} angle={-30} textAnchor="end" height={40} />
                  <YAxis tick={{ fontSize: 11, fill: "#8CA3BF" }} unit=" kWh" />
                  <Tooltip formatter={(v: any) => [`${Number(v).toFixed(1)} kWh`]} />
                  <ReferenceLine y={profile.mean_consumption} stroke="#9ca3af" strokeDasharray="4 4"
                    label={{ value: 'Mean', position: 'insideTopRight', fontSize: 10, fill: '#9ca3af' }} />
                  <Line type="monotone" dataKey="consumption" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Consumption" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Billing table */}
            <div className="card">
              <div className="px-5 py-3 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">Billing Records</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 uppercase tracking-wide">
                      {['Period','Units Consumed','Billed Units','Amount','Meter Start','Meter End'].map(h => (
                        <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {profile.billing_data.map(row => (
                      <tr key={row.billing_period} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium">{formatPeriod(row.billing_period)}</td>
                        <td className="px-4 py-2">{formatNumber(row.units_consumed)}</td>
                        <td className="px-4 py-2">{formatNumber(row.billed_units)}</td>
                        <td className="px-4 py-2">{row.amount_billed != null ? `$${formatNumber(row.amount_billed)}` : '—'}</td>
                        <td className="px-4 py-2">{formatNumber(row.meter_reading_start)}</td>
                        <td className="px-4 py-2">{formatNumber(row.meter_reading_end)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Anomaly flags */}
            {flags.length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">
                  Detected Anomalies ({flags.length})
                </h3>
                <div className="space-y-2">
                  {flags.map((flag: any, i: number) => (
                    <div key={i} className={`flex items-start gap-3 p-3 rounded-md border ${severityColor(flag.severity)} border-current border-opacity-20`}>
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-xs">{anomalyTypeLabel(flag.type ?? flag.type_name)}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${severityColor(flag.severity)}`}>
                            {flag.severity}
                          </span>
                          <span className="text-[10px] text-gray-400">Period: {flag.period}</span>
                          {flag.confidence != null && (
                            <span className="text-[10px] text-gray-400">Confidence: {Math.round(flag.confidence * 100)}%</span>
                          )}
                        </div>
                        <p className="text-xs">{flag.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Investigation controls */}
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">AI Investigation</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    5-agent pipeline: Data Analysis → Anomaly Detection → Fraud Investigation → Explainability → Decision Support
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="btn-secondary flex items-center gap-1.5" onClick={handleCreateCase}
                    disabled={!profile}>
                    <FolderPlus className="w-3.5 h-3.5" /> Create Case
                  </button>
                  <button className="btn-primary flex items-center gap-1.5" onClick={handleRunInvestigation}
                    disabled={loadingInvestigation || !profile}>
                    <Bot className="w-3.5 h-3.5" />
                    {loadingInvestigation ? 'Investigating…' : 'Run AI Investigation'}
                  </button>
                </div>
              </div>

              {caseCreated && (
                <div className="flex items-center gap-2 text-green-700 bg-green-50 rounded-md px-3 py-2 text-sm mb-3">
                  <CheckCircle className="w-4 h-4" />
                  Case created: <strong>{caseCreated}</strong>
                  <button className="ml-auto text-xs text-blue-600 hover:underline"
                    onClick={() => navigate(`/cases/${caseCreated}`)}>
                    View Case →
                  </button>
                </div>
              )}
              {caseError && <div className="text-red-600 text-sm bg-red-50 rounded-md px-3 py-2 mb-3">{caseError}</div>}

              {loadingInvestigation && <LoadingSpinner message="Running IBM watsonx.ai agent pipeline…" />}
              {investigationError && <ErrorState message={investigationError} />}

              {/* Agent trace */}
              {agentTrace && (
                <div className="space-y-3 mt-2">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                    <span>Model: <code className="bg-gray-100 px-1 rounded">{agentTrace.model_id}</code></span>
                    <span>•</span>
                    <span className={agentTrace.watsonx_available ? 'text-green-600' : 'text-orange-600'}>
                      {agentTrace.watsonx_available ? '● watsonx.ai connected' : '○ watsonx.ai not configured'}
                    </span>
                    {!agentTrace.watsonx_available && (
                      <span className="text-orange-500">– statistical analysis complete, set IBM_WATSONX_API_KEY for AI narratives</span>
                    )}
                  </div>
                  {agentTrace.agents.map((ag, i) => (
                    <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
                      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${ag.status === 'completed' ? 'bg-green-500' : 'bg-orange-400'}`} />
                        <span className="text-xs font-semibold text-gray-700">{ag.agent}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${ag.status === 'completed' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'}`}>
                          {ag.status}
                        </span>
                      </div>
                      <div className="px-4 py-3">
                        <p className="text-xs text-gray-600 leading-relaxed">
                          {ag.plain_language_summary ?? ag.output ?? '—'}
                        </p>
                        {ag.agent === 'DecisionSupportAgent' && (
                          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                            {ag.investigation_priority_label && (
                              <div><span className="text-gray-400">Priority: </span><strong>{ag.investigation_priority_label}</strong></div>
                            )}
                            {ag.recommended_action && (
                              <div className="col-span-2"><span className="text-gray-400">Action: </span><strong>{ag.recommended_action}</strong></div>
                            )}
                            {ag.disclaimer && (
                              <div className="col-span-2 text-gray-400 italic">{ag.disclaimer}</div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
