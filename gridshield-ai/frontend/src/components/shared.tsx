import React from 'react'
import { getRiskBadgeClass, riskBarColor, formatScore } from '../utils/formatting'
import type { RiskLevel } from '../types'

interface RiskBadgeProps { level: string; score?: number | null; showScore?: boolean }

export function RiskBadge({ level, score, showScore = false }: RiskBadgeProps) {
  return (
    <span className={getRiskBadgeClass(level)}>
      {level}{showScore && score != null ? ` · ${formatScore(score)}` : ''}
    </span>
  )
}

interface RiskScoreGaugeProps { score: number; level: RiskLevel | string; size?: 'sm' | 'lg' }

export function RiskScoreGauge({ score, level, size = 'lg' }: RiskScoreGaugeProps) {
  const color = riskBarColor[level] ?? '#6b7280'
  const pct = Math.min(100, Math.max(0, score))
  const r = size === 'lg' ? 44 : 28
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className={`flex flex-col items-center gap-1 ${size === 'lg' ? '' : 'scale-75'}`}>
      <svg width={size === 'lg' ? 110 : 70} height={size === 'lg' ? 110 : 70} viewBox="0 0 110 110">
        <circle cx="55" cy="55" r={r} fill="none" stroke="#1E344F" strokeWidth={size === 'lg' ? 10 : 8} />
        <circle
          cx="55" cy="55" r={r} fill="none"
          stroke={color} strokeWidth={size === 'lg' ? 10 : 8}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 55 55)"
        />
        <text x="55" y="55" textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize={size === 'lg' ? 20 : 14} fontWeight="bold">
          {Math.round(pct)}
        </text>
        <text x="55" y={size === 'lg' ? 70 : 66} textAnchor="middle" fill="#9ca3af" fontSize={size === 'lg' ? 9 : 7}>
          / 100
        </text>
      </svg>
      <RiskBadge level={level} />
      <div className="text-xs text-gray-400 text-center max-w-[100px]">
        AI-assisted fraud risk
      </div>
    </div>
  )
}

interface LoadingSpinnerProps { message?: string }
export function LoadingSpinner({ message = 'Loading…' }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-500">
      <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin border-[3px]" />
      <span className="text-sm">{message}</span>
    </div>
  )
}

interface ErrorStateProps { message: string; onRetry?: () => void }
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-red-600">
      <div className="text-4xl">⚠</div>
      <p className="text-sm text-center max-w-sm">{message}</p>
      {onRetry && (
        <button className="btn-secondary text-sm" onClick={onRetry}>Retry</button>
      )}
    </div>
  )
}

interface EmptyStateProps { title: string; description?: string; action?: React.ReactNode }
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-500">
      <div className="text-4xl">📭</div>
      <p className="font-medium text-gray-700">{title}</p>
      {description && <p className="text-sm text-center max-w-sm">{description}</p>}
      {action}
    </div>
  )
}

interface PageHeaderProps { title: string; subtitle?: string; actions?: React.ReactNode }
export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="bg-ink-800 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  color?: string
  icon?: React.ReactNode
}
export function StatCard({ label, value, sub, color = 'text-gray-900', icon }: StatCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  )
}
