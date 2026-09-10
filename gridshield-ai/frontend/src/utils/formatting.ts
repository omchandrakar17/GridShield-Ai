import { type RiskLevel } from '../types'
import clsx from 'clsx'

export const riskColors: Record<RiskLevel | string, string> = {
  Critical: 'text-red-700 bg-red-50 border-red-300',
  High:     'text-orange-700 bg-orange-50 border-orange-300',
  Medium:   'text-yellow-700 bg-yellow-50 border-yellow-300',
  Low:      'text-green-700 bg-green-50 border-green-300',
}

export const riskBarColor: Record<RiskLevel | string, string> = {
  Critical: '#ef4444',
  High:     '#f97316',
  Medium:   '#eab308',
  Low:      '#22c55e',
}

export const riskDotColor: Record<RiskLevel | string, string> = {
  Critical: 'bg-red-500',
  High:     'bg-orange-500',
  Medium:   'bg-yellow-500',
  Low:      'bg-green-500',
}

export function getRiskBadgeClass(level: string): string {
  return clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
    riskColors[level] ?? 'text-gray-700 bg-gray-50 border-gray-200'
  )
}

export function formatPeriod(period: string): string {
  if (!period) return ''
  const parts = period.split('-')
  if (parts.length === 2) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    const m = parseInt(parts[1], 10) - 1
    return `${months[m] ?? parts[1]} ${parts[0]}`
  }
  return period
}

export function formatNumber(n: number | null | undefined, decimals = 1): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(1)
}

export function anomalyTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    SUDDEN_DROP: 'Sudden Drop',
    SUDDEN_SPIKE: 'Sudden Spike',
    HIGH_ZSCORE: 'Statistical Outlier',
    BILLING_MISMATCH: 'Billing Mismatch',
    ZERO_CONSUMPTION: 'Zero Consumption',
    HIGH_VARIABILITY: 'High Variability',
    METER_GAP: 'Meter Reading Gap',
    TREND_REVERSAL: 'Trend Reversal',
  }
  return labels[type] ?? type
}

export function severityColor(severity: string): string {
  const map: Record<string, string> = {
    Critical: 'text-red-600 bg-red-50',
    High:     'text-orange-600 bg-orange-50',
    Medium:   'text-yellow-600 bg-yellow-50',
    Low:      'text-blue-600 bg-blue-50',
  }
  return map[severity] ?? 'text-gray-600 bg-gray-50'
}
