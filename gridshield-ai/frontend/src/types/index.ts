// Shared TypeScript types for GridShield AI frontend

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'
export type CaseStatus = 'Open' | 'Under Investigation' | 'Inspection Required' | 'Resolved'

export interface ConsumerRecord {
  id: number
  consumer_id: string
  billing_period: string
  meter_reading_start: number | null
  meter_reading_end: number | null
  units_consumed: number | null
  billed_units: number | null
  amount_billed: number | null
  tariff_category: string | null
  sanctioned_load_kw: number | null
  consumer_type: string | null
  location: string | null
  division: string | null
  source_file: string | null
}

export interface AnomalyFlag {
  type: string
  severity: string
  period: string
  description: string
  zscore?: number
  drop_pct?: number
  ratio_to_mean?: number
  discrepancy_pct?: number
  value?: number
}

export interface AnomalyResult {
  id: number
  consumer_id: string
  analysis_timestamp: string
  fraud_risk_score: number
  risk_level: RiskLevel
  anomaly_flags: AnomalyFlag[] | null
  affected_periods: string[] | null
  statistical_evidence: Record<string, unknown> | null
  ai_reasoning: string | null
  recommended_action: string | null
  confidence_score: number | null
  model_version: string | null
  agent_trace: AgentTrace | null
}

export interface AgentOutput {
  agent: string
  status: string
  output?: string
  plain_language_summary?: string
  evidence_items?: EvidenceItem[]
  anomaly_count?: number
  anomaly_types?: string[]
  fraud_risk_score?: number
  risk_level?: RiskLevel
  confidence_score?: number
  investigation_priority?: number
  investigation_priority_label?: string
  recommended_action?: string
  key_evidence?: string[]
  disclaimer?: string
}

export interface AgentTrace {
  started_at: string
  completed_at: string
  watsonx_available: boolean
  model_id: string
  agents: AgentOutput[]
  final_decision: AgentOutput
}

export interface EvidenceItem {
  type: string
  severity: string
  period: string
  description: string
  confidence: number
}

export interface ConsumerProfile {
  consumer_id: string
  consumer_type: string
  tariff_category: string
  location: string
  division: string
  periods_available: number
  periods: string[]
  consumption_values: number[]
  mean_consumption: number
  std_consumption: number
  median_consumption: number
  min_consumption: number
  max_consumption: number
  coefficient_of_variation: number
  trend_slope: number
  avg_mom_change_pct: number
  rolling_3_avg: number
  last_value: number
  prev_value: number | null
  billing_data: BillingRecord[]
}

export interface BillingRecord {
  billing_period: string
  units_consumed: number | null
  billed_units: number | null
  amount_billed: number | null
  meter_reading_start: number | null
  meter_reading_end: number | null
}

export interface InvestigationCase {
  id: number
  case_id: string
  consumer_id: string
  status: CaseStatus
  priority: RiskLevel
  fraud_risk_score: number | null
  risk_level: RiskLevel | null
  assigned_to: string | null
  notes: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
  resolution_notes: string | null
  timeline?: CaseEvent[]
}

export interface CaseEvent {
  id: number
  case_id: string
  event_type: string
  description: string
  performed_by: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface DashboardStats {
  total_consumers: number
  total_analyzed: number
  total_anomaly_flags: number
  high_risk_count: number
  open_cases: number
  risk_distribution: Record<string, number>
  recent_flagged: RecentFlagged[]
  risk_trend: RiskTrend[]
}

export interface RecentFlagged {
  consumer_id: string
  fraud_risk_score: number
  risk_level: RiskLevel
  analysis_timestamp: string
  recommended_action: string
}

export interface RiskTrend {
  month: string
  total: number
  high_risk: number
}
